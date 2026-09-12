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
import re
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import events as events_log
from environments_store import environments_lock, load_environments, save_environments
from state_lock import locked

from mcp.server.mcpserver import MCPServer

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog" / "capabilities.json"
STATE_PATH = REPO_ROOT / "harness" / "stack-state.json"
STATE_LOCK_PATH = REPO_ROOT / "harness" / ".stack-state.lock"
FALLBACK_LOG_PATH = Path("/tmp/floci-hackathon-mcp-fallback-log.jsonl")

ENV = {
    "AWS_ENDPOINT_URL": "http://localhost:4566",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
}

# Lowercase alphanumeric + hyphen, 3-40 chars. This allowlist already excludes `::`, the
# reserved separator the resource-name-to-environment binding (GH-29) relies on -- see the
# technical design's Error responses table.
ENVIRONMENT_NAME_RE = re.compile(r"^[a-z0-9-]{3,40}$")
BOARD_PORT_RANGE = range(7777, 7877)

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


def _scan_free_board_port(taken_ports: set[int]) -> int | None:
    """Return the first port in BOARD_PORT_RANGE that isn't already registered to another
    environment AND is actually bindable right now. Two checks, not one: `taken_ports` catches
    ports this harness already handed out; the bind attempt catches anything else already
    listening on the machine (an unrelated local service, a board still running from a prior
    session)."""
    for port in BOARD_PORT_RANGE:
        if port in taken_ports:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
        return port
    return None


@server.tool()
def create_environment(name: str) -> dict:
    """Mint a new, isolated environment so one agent/worktree can provision and verify its own
    infra without colliding with another agent's environment. Reserves a permanently-unique
    app_context (never reused, even if `name` is reused after a later destroy_environment call
    within the same second) and a free board port, both recorded in environments.json.

    NOT founder-facing -- the returned app_context and board_port are for the developer/agent
    driving this session. Never relay either value to the founder; see AgDR-0001 and the
    technical design's jargon-boundary contract update for why."""
    if not ENVIRONMENT_NAME_RE.match(name):
        return {
            "error": "Environment name must be lowercase alphanumeric with hyphens, "
            "3-40 characters."
        }

    with environments_lock():
        envs = load_environments()
        if name in envs:
            return {"error": f"Environment '{name}' already exists."}

        taken_ports = {e["board_port"] for e in envs.values()}
        board_port = _scan_free_board_port(taken_ports)
        if board_port is None:
            return {
                "error": f"No free board port available in range "
                f"{BOARD_PORT_RANGE.start}-{BOARD_PORT_RANGE.stop - 1}."
            }

        # Nanosecond timestamp + random suffix, not a plain per-second timestamp -- a same-second
        # destroy_environment(name) followed by create_environment(name) must never mint the same
        # app_context, or the new environment would inherit the destroyed one's namespace. See
        # AgDR-0001 and the technical design's Data Model section.
        app_context = f"{name}-{time.time_ns()}-{secrets.token_hex(2)}"
        envs[name] = {
            "app_context": app_context,
            "board_port": board_port,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        save_environments(envs)

    return {"app_context": app_context, "board_port": board_port}


@server.tool()
def destroy_environment(name: str) -> dict:
    """Release an environment's board port and remove its entries from environments.json and
    stack-state.json. Does NOT delete any real backend resources those entries pointed to --
    capabilities.json defines no teardown step for any capability, so the underlying Floci
    resources become permanently unreachable (the resource-name binding, GH-29, ties them to
    this environment's now-removed app_context) but are never actually deleted. This is a known,
    accepted limitation, not a bug -- see AgDR-0001.

    NOT founder-facing -- the returned name/port are for the developer/agent driving this
    session, never to be relayed to the founder."""
    with environments_lock():
        envs = load_environments()
        entry = envs.pop(name, None)
        if entry is None:
            return {"error": f"No environment named '{name}'."}
        save_environments(envs)

    with locked(STATE_LOCK_PATH):
        state = _load_state()
        state.pop(entry["app_context"], None)
        _save_state(state)

    return {"name": name, "released_port": entry["board_port"]}


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
def get_provisioning_recipe(capability_id: str, resource_name: str, app_context: str | None = None) -> dict:
    """Get the exact technical steps and verification command to actually build a capability.
    Pass app_context if you have it (the app/product this is for) so the live board can group
    activity by product -- optional, omit if you don't know it yet.
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

    events_log.emit(
        "provision.start", capability_id,
        founder={"label": cap["founder_description"], "status": "setting up…"},
        dev={"service": cap["aws_service"], "resource_name": resource_name},
        app_context=app_context,
    )
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

    events_log.emit(
        "verify.start", capability_id,
        founder={"label": cap["founder_description"], "status": "setting up…"},
        dev={"cmd": cap["verify"]["cli"], "resource_name": resource_name},
        app_context=app_context,
    )

    passed, detail = _run_verify(cap["verify"]["cli"], resource_name)
    now = datetime.now(timezone.utc).isoformat()

    if not passed:
        founder_message = (
            f"I tried to set up '{cap['founder_description'][:1].lower()}"
            f"{cap['founder_description'][1:]}' but it isn't actually working yet -- "
            "I won't tell you it's ready until it really is."
        )
        events_log.emit(
            "verify.fail", capability_id,
            founder={"label": cap["founder_description"], "status": "not working yet"},
            dev={"cmd": cap["verify"]["cli"], "resource_name": resource_name, "detail": detail, "exit": 1},
            app_context=app_context,
        )
        return {
            "gate_result": "FAIL",
            "founder_message": founder_message,
            "_diagnostic_for_you_the_calling_agent": {
                "note": "Not for the founder. The independent check that just ran, and exactly what it returned.",
                "command_that_ran": cap["verify"]["cli"].replace("<userPoolId>", resource_name)
                    .replace("<bucketName>", resource_name).replace("<tableName>", resource_name)
                    .replace("<functionName>", resource_name).replace("<topicArn>", resource_name)
                    .replace("<queueUrl>", resource_name).replace("<secretName>", resource_name)
                    .replace("<domainName>", resource_name),
                "output_or_error": detail,
            },
        }

    with locked(STATE_LOCK_PATH):
        state = _load_state()
        state.setdefault(app_context, {"created": now, "capabilities": {}})
        state[app_context]["capabilities"][capability_id] = {
            "resource_name": resource_name,
            "last_verified": now,
            "last_gate_result": "PASS",
        }
        _save_state(state)
    events_log.emit(
        "verify.pass", capability_id,
        founder={
            "label": cap["founder_description"],
            "status": "working",
            "proof": cap["verify"].get("founder_proof", "checked that it's up and answering"),
        },
        dev={"cmd": cap["verify"]["cli"], "resource_name": resource_name, "detail": detail, "exit": 0},
        app_context=app_context,
    )
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
            founder_message = (
                f"That's not something I can set up directly right now. The closest thing "
                f"I can offer today: {cap['founder_description'][:1].lower()}"
                f"{cap['founder_description'][1:]} Want that instead?"
            )
            events_log.emit(
                "question.asked", closest_capability_id,
                founder={"label": founder_message, "status": "waiting on your answer"},
                dev={"unmatched_request": request_text},
                app_context=app_context,
            )
            return {"founder_message": founder_message}

    founder_message = "That's not something I can set up directly yet. I've made a note of it."
    events_log.emit(
        "question.asked", None,
        founder={"label": founder_message, "status": "waiting on your answer"},
        dev={"unmatched_request": request_text},
        app_context=app_context,
    )
    return {"founder_message": founder_message}


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
