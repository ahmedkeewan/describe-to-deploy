#!/usr/bin/env python3
"""
The Floci control-plane harness, exposed as an MCP server.

Delivery surface decision (2026-09-05): expose this as MCP tools rather than build a bespoke
chat frontend. A founder's existing AI chat client (Claude Desktop, Claude Code) becomes the UI
for free; this server supplies the harness -- catalog, gate, state, wiring, go-live report --
that the fix-1 through fix-7 experiments in tasks/README.md already validated.

Architecture mirrors fix #2's planner/executor split, now as an explicit tool contract instead of
two separate agent prompts:
  - The CALLING AGENT (whatever LLM is driving this MCP client) is the "planner + executor": it
    reads list_capabilities(), matches the founder's plain-language request to a capability_id,
    calls get_provisioning_recipe() to learn what to actually run, and executes those commands
    with its own tool access (bash, or whatever the client provides).
  - THIS SERVER is the "gate + state": record_provisioned() independently re-verifies via the
    exact same check as harness/verify_gate.py before it will EVER update stack-state.json --
    state can only advance on a real, server-side-checked PASS, never on the calling agent's own
    claim of success. This makes fix #4's gate a structural boundary instead of a step an agent
    could accidentally skip.

Jargon boundary: every string this server returns is built to be founder-safe (plain language,
no AWS/Floci service names, no ARNs, no ports) EXCEPT whats_needed_to_go_live(), which is
explicitly the one technical/graduation report in this whole harness and is documented as such.

Run: source harness/.venv/bin/activate && python3 harness/mcp_server.py
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.mcpserver import MCPServer

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog" / "capabilities.json"
STATE_PATH = REPO_ROOT / "harness" / "stack-state.json"
FALLBACK_LOG_PATH = Path("/tmp/floci-hackathon-mcp-fallback-log.jsonl")

ENV = {
    "AWS_ENDPOINT_URL": "http://localhost:4566",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
}

server = MCPServer(
    name="floci-control-plane",
    title="Floci Control Plane",
    description=(
        "Turns a plain-language product request into real, verified local infrastructure on "
        "Floci, without ever exposing cloud/infra terminology to the person driving this chat."
    ),
)


def _load_catalog() -> dict:
    return {c["id"]: c for c in json.loads(CATALOG_PATH.read_text())["capabilities"]}


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def _run_verify(cli_template: str, resource_name: str) -> tuple[bool, str]:
    """Identical substitution + execution logic to harness/verify_gate.py -- kept as one
    function there and reused here would be cleaner long-term, but the exact-match duplication
    is intentional for now so this server's gate check can never silently diverge from the
    standalone script's behavior without both being edited."""
    import os
    cmd = (
        cli_template
        .replace("<bucketName>", resource_name)
        .replace("<tableName>", resource_name)
        .replace("<functionName>", resource_name)
        .replace("<userPoolId>", resource_name)
        .replace("<topicArn>", resource_name)
        .replace("<queueUrl>", resource_name)
        .replace("<secretName>", resource_name)
        .replace("<domainName>", resource_name)
    )
    try:
        result = subprocess.run(
            cmd, shell=True, env={**os.environ, **ENV},
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0, (result.stdout or result.stderr or "").strip()[:500]
    except subprocess.TimeoutExpired:
        return False, "verification timed out"


@server.tool()
def list_capabilities() -> list[dict]:
    """List every product capability this harness can build, in plain language. Match the
    founder's request to one of these by MEANING, not exact phrase match. Never mention AWS,
    Floci, or any cloud service name to the founder -- these entries deliberately omit that."""
    catalog = _load_catalog()
    return [
        {
            "capability_id": c["id"],
            "example_phrases": c["phrases"],
            "what_it_does": c["founder_description"],
            "requires_first": c.get("depends_on", []),
        }
        for c in catalog.values()
    ]


@server.tool()
def get_app_state(app_context: str) -> dict:
    """Look up what has already been built and verified for a given app. Call this before
    assuming a request needs new infrastructure -- a follow-up request should extend or reuse
    what's here, not duplicate it."""
    state = _load_state()
    app = state.get(app_context)
    if app is None:
        return {"known": False, "capabilities": []}
    catalog = _load_catalog()
    return {
        "known": True,
        "capabilities": [
            {
                "capability_id": cap_id,
                "what_it_does": catalog.get(cap_id, {}).get("founder_description", cap_id),
                "last_gate_result": info.get("last_gate_result"),
            }
            for cap_id, info in app.get("capabilities", {}).items()
        ],
    }


@server.tool()
def get_provisioning_recipe(capability_id: str, resource_name: str) -> dict:
    """Get the exact technical steps and verification command to actually build a capability.
    This is the ONLY tool that returns technical/infra detail -- it's for YOUR use in executing
    the work with your own tools, never for repeating to the founder. If capability_id isn't in
    list_capabilities(), do not call this -- use report_unsupported_request instead."""
    catalog = _load_catalog()
    cap = catalog.get(capability_id)
    if cap is None:
        return {"error": f"'{capability_id}' is not a known capability"}
    verify_cli = cap["verify"]["cli"]
    for placeholder in ("bucketName", "tableName", "functionName", "userPoolId", "topicArn", "queueUrl", "secretName", "domainName"):
        verify_cli = verify_cli.replace(f"<{placeholder}>", resource_name)
    return {
        "capability_id": capability_id,
        "resource_name": resource_name,
        "steps": cap["provision"]["steps"],
        "verify_command_preview": verify_cli,
        "endpoint": ENV["AWS_ENDPOINT_URL"],
        "credentials": {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test", "AWS_DEFAULT_REGION": "us-east-1"},
    }


@server.tool()
def record_provisioned(app_context: str, capability_id: str, resource_name: str) -> dict:
    """Call this after you've actually run the provisioning steps. This server independently
    re-verifies for real against live Floci -- your own belief that it worked is not sufficient
    and is not trusted. State is only ever updated on a genuine, freshly-checked PASS. Returns a
    founder-safe message either way; relay it as-is or in your own words, but do not add
    technical detail that isn't in it."""
    catalog = _load_catalog()
    cap = catalog.get(capability_id)
    if cap is None:
        return {"gate_result": "FAIL", "founder_message": "That isn't something I can verify."}

    passed, detail = _run_verify(cap["verify"]["cli"], resource_name)
    now = datetime.now(timezone.utc).isoformat()

    if not passed:
        return {
            "gate_result": "FAIL",
            "founder_message": (
                f"I tried to set up '{cap['founder_description'][:1].lower()}"
                f"{cap['founder_description'][1:]}' but it isn't actually working yet -- "
                "I won't tell you it's ready until it really is."
            ),
        }

    state = _load_state()
    state.setdefault(app_context, {"created": now, "capabilities": {}})
    state[app_context]["capabilities"][capability_id] = {
        "resource_name": resource_name,
        "last_verified": now,
        "last_gate_result": "PASS",
    }
    _save_state(state)
    return {
        "gate_result": "PASS",
        "founder_message": f"Done and verified: {cap['founder_description']}",
    }


@server.tool()
def report_unsupported_request(app_context: str, request_text: str, closest_capability_id: str | None = None) -> dict:
    """Call this instead of inventing anything when a request doesn't match list_capabilities().
    Logs the gap durably (so it can become a future capability) and returns a safe response you
    can relay -- never provision anything outside the catalog, no matter how confident you are."""
    FALLBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FALLBACK_LOG_PATH.open("a") as f:
        f.write(json.dumps({
            "app_context": app_context,
            "request": request_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }) + "\n")

    if closest_capability_id:
        catalog = _load_catalog()
        cap = catalog.get(closest_capability_id)
        if cap:
            return {
                "founder_message": (
                    f"That's not something I can set up directly right now. The closest thing "
                    f"I can offer today: {cap['founder_description'][:1].lower()}"
                    f"{cap['founder_description'][1:]} Want that instead?"
                )
            }
    return {"founder_message": "That's not something I can set up directly yet. I've made a note of it."}


@server.tool()
def check_app_readiness(app_context: str) -> dict:
    """Re-verify, live and right now, everything on record for this app -- don't trust
    last_verified timestamps as current truth. Use this when a founder asks 'is everything
    working' or before telling them something is ready."""
    state = _load_state()
    app = state.get(app_context)
    if app is None:
        return {"overall_ready": True, "founder_message": "There's nothing set up for this app yet."}

    catalog = _load_catalog()
    problems = []
    for cap_id, info in app.get("capabilities", {}).items():
        cap = catalog.get(cap_id)
        if cap is None:
            continue
        passed, _ = _run_verify(cap["verify"]["cli"], info["resource_name"])
        if not passed:
            problems.append(cap["founder_description"])

    if not problems:
        return {"overall_ready": True, "founder_message": "Everything is working."}
    return {
        "overall_ready": False,
        "founder_message": "Some things aren't working right now: " + "; ".join(problems),
    }


@server.tool()
def wire_app_config(app_context: str, app_directory: str) -> dict:
    """Write the real connection details for this app's verified infrastructure directly into
    its config file (.env) at app_directory -- no manual copy-paste step for the founder.
    Preserves anything already in that file. Only wires capabilities already recorded as PASS."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "harness" / "auto_wire.py"),
         "/dev/stdin", app_directory],
        input=json.dumps(_plan_from_state(app_context)),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return {"founder_message": "I couldn't update the app's configuration.", "detail": result.stderr[:300]}
    return {"founder_message": "Your app's settings are updated -- no setup needed on your end."}


def _plan_from_state(app_context: str) -> dict:
    state = _load_state()
    app = state.get(app_context, {"capabilities": {}})
    return {
        "app_context": app_context,
        "founder_request": "",
        "provider": "aws",
        "fallback": None,
        "matched_capabilities": [
            {"capability_id": cap_id, "resource_name": info["resource_name"], "reused_existing": True, "depends_on": []}
            for cap_id, info in app["capabilities"].items()
        ],
    }


@server.tool()
def whats_needed_to_go_live(app_context: str) -> str:
    """TECHNICAL REPORT -- the one tool in this server that names real cloud services. Use only
    when explicitly asked something like 'what happens after we launch for real' or 'what would
    it take to go live' -- this is meant for a technical audience (an engineer joining later, an
    investor), not routine conversation. Reads straight from what's already verified; performs
    no migration."""
    plan_path = Path("/tmp/floci-mcp-go-live-plan.json")
    plan_path.write_text(json.dumps(_plan_from_state(app_context)))
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "harness" / "go_live_plan.py"), str(plan_path)],
        capture_output=True, text=True,
    )
    return result.stdout or "Nothing is set up for this app yet."


if __name__ == "__main__":
    server.run()
