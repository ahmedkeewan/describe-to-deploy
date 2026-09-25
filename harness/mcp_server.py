#!/usr/bin/env python3
"""
The Floci control-plane harness, exposed as an MCP server.

Delivery surface decision (2026-09-05): expose this as MCP tools rather than build a bespoke
chat frontend. A founder's existing AI chat client (Claude Desktop, Claude Code) becomes the UI
for free; this server supplies the harness -- catalog, gate, state, wiring, go-live report --
that the experiments in tasks/README.md already validated.

Architecture mirrors the planner/executor split, now as an explicit tool contract instead of
two separate agent prompts:
  - The CALLING AGENT (whatever LLM is driving this MCP client) is the "planner + executor": it
    reads list_capabilities(), matches the founder's plain-language request to a capability_id,
    calls get_provisioning_recipe() to learn what to actually run, and executes those commands
    with its own tool access (bash, or whatever the client provides).
  - THIS SERVER is the "gate + state": record_provisioned() independently re-verifies via the
    exact same check as harness/verify_gate.py before it will EVER update stack-state.json --
    state can only advance on a real, server-side-checked PASS, never on the calling agent's own
    claim of success. This makes the verification gate a structural boundary instead of a step an
    agent could accidentally skip.

Jargon boundary: every string this server returns is built to be founder-safe (plain language,
no AWS/Floci service names, no ARNs, no ports), EXCEPT the ten tools below. Each documents why
in its own docstring:
  - whats_needed_to_go_live() -- the one technical/graduation report in this whole harness.
  - get_provisioning_recipe() -- returns steps, an endpoint, and credentials for the calling
    agent's own tool use; never for the founder.
  - create_environment(), destroy_environment(), list_environments() -- return an app_context
    and/or a board port for the developer/agent managing environments, not the founder.
  - get_verification_history() -- returns raw event-log entries whose `dev` field carries real
    service names, commands, and exit codes; never relay one to the founder as-is.
  - snapshot_environment(), restore_environment() -- return a snapshot_id, capability_id list,
    and app_context-scoped resource state for the developer/agent, not the founder.
  - describe_environment() -- returns AWS service names and cost estimates for the
    developer/agent, not the founder.
One narrower, field-level exception: record_provisioned()'s FAIL path and its dry_run=True
preview path both also return `_diagnostic_for_you_the_calling_agent`, an explicitly-labeled,
non-founder-safe field carrying the raw verify command (and, on FAIL, its real output). Unlike
the tools above, record_provisioned()'s own `founder_message` stays founder-safe in every case --
only that one extra, clearly-named field is not. See its own docstring.

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
from snapshots_store import snapshots_lock, load_snapshots, save_snapshots
from state_lock import locked
import pricing

from mcp.server.mcpserver import MCPServer

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog" / "capabilities.json"
STATE_PATH = REPO_ROOT / "harness" / "stack-state.json"
STATE_LOCK_PATH = REPO_ROOT / "harness" / ".stack-state.lock"
FALLBACK_LOG_PATH = Path("/tmp/floci-mcp-fallback-log.jsonl")

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

# Rough, illustrative monthly cost ranges for LIGHT early-stage usage on real AWS, keyed by
# aws_service (GH-68). These are commonly-cited free-tier/pricing figures, not a quote -- actual
# cost depends on usage volume, region, and AWS's own pricing changes over time. Only used by
# describe_environment() to give a developer/agent a rough sense of what "going live" (see
# go_live_plan.py/whats_needed_to_go_live()) would cost, never surfaced to the founder as a
# precise number.
APPROX_MONTHLY_COST_USD = {
    "cognito-idp": "~$0 under ~50k monthly active users (Cognito's free tier), then usage-based",
    "s3": "~$0-5 for light storage + request volume (mostly covered by the free tier initially)",
    "dynamodb": "~$0-5 on-demand pricing for light usage (free tier covers the first 25GB storage)",
    "lambda": "~$0 for light usage (1M free requests/month)",
    "ses": "~$0-a few dollars for light usage (about $0.10 per 1,000 emails after the free tier)",
    "scheduler": "~$0 for light usage (1M free EventBridge invocations/month)",
    "sqs": "~$0 for light usage (1M free requests/month)",
    "sns": "~$0 for light usage (1M free requests/month for many message types)",
    "secretsmanager": "~$0.40/month per secret, plus a small per-API-call cost",
    "ssm": "~$0 for standard-tier parameters",
    "apigateway": "~$0-5 for light usage (1M free API calls/month for the first 12 months)",
    "es": "~$25-50+/month minimum -- typically the most expensive capability here; managed search domains aren't covered by the same free tier as the others",
    "stepfunctions": "~$0 for light usage (4,000 free state transitions/month)",
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


def _substitute_placeholders(cli_template: str, resource_name: str) -> str:
    """Single source of truth for substituting a catalog verify.cli's placeholder with the real
    resource_name. _run_verify, get_provisioning_recipe, and the FAIL-path diagnostic field all
    need this exact substitution -- extracted here after a bug (GH-77) where <scheduleName>, and
    then <apiId> (found in review), were each missing from a hardcoded per-name replace() chain
    that had to be updated by hand for every new placeholder a capability introduced.

    Every capability's verify.cli uses at most one placeholder, always meaning "the one real
    resource this check is about" -- confirmed by inspecting every entry in
    catalog/capabilities.json (none combine two distinct placeholders in one command). A single
    regex substitution of any <word> token is therefore correct for every existing capability and
    every future one following the same one-placeholder-per-check shape, with no per-name list to
    keep in sync ever again.

    The identical substitution in harness/verify_gate.py stays a deliberate, separate copy (see
    _run_verify's docstring) so this server's gate check can never silently diverge from that
    standalone script without both being edited."""
    # A plain string replacement arg would let re.sub interpret backslash sequences in
    # resource_name (\1, \g<0>, ...) as backreferences instead of literal text -- a resource_name
    # containing one could crash with re.error or silently corrupt the substituted command. A
    # replacement function's return value is always used literally, with no such interpretation.
    return re.sub(r"<\w+>", lambda _match: resource_name, cli_template)


def _run_verify(cli_template: str, resource_name: str) -> tuple[bool, str]:
    """Identical substitution + execution logic to harness/verify_gate.py -- kept as one
    function there and reused here would be cleaner long-term, but the exact-match duplication
    is intentional for now so this server's gate check can never silently diverge from the
    standalone script's behavior without both being edited."""
    import os
    cmd = _substitute_placeholders(cli_template, resource_name)
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
def create_environment(name: str, owner: str | None = None) -> dict:
    """Mint a new, isolated environment so one agent/worktree can provision and verify its own
    infra without colliding with another agent's environment. Reserves a permanently-unique
    app_context (never reused, even if `name` is reused after a later destroy_environment call
    within the same second) and a free board port, both recorded in environments.json.

    `owner` is optional, purely descriptive bookkeeping (GH-69, AgDR-0004) -- e.g. a founder or
    team-member name/identifier, for a human reading list_environments()/describe_environment()
    to see who created what. It is NOT a permission check: this harness has no authentication or
    identity system, and any connected MCP client can still act on any app_context it knows,
    regardless of the recorded owner. Never represent `owner` as an access-control feature.

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
            "owner": owner,
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
def list_environments() -> list[dict]:
    """List every currently registered environment: name, app_context, board_port, and when it
    was created. A plain read, not locked -- matches how get_app_state() reads stack-state.json
    without a lock elsewhere in this file; only the check-then-write sequences in
    create_environment/destroy_environment need one.

    NOT founder-facing -- app_context and board_port are for the developer/agent, never for the
    founder."""
    envs = load_environments()
    return [{"name": name, **info} for name, info in envs.items()]


@server.tool()
def get_verification_history(
    app_context: str | None = None,
    capability_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[dict]:
    """Query the durable event log for what changed and when, without needing the live board open
    at the time it happened (GH-71). Filters are all optional and combine with AND: app_context
    narrows to one environment/product, capability_id to one capability, since/until (ISO-8601
    timestamps, e.g. "2026-09-25T00:00:00Z") to a time range. With no filters, returns the entire
    history.

    NOT founder-facing -- each event's `dev` field carries real service names, commands, and exit
    codes (the interface's "Details for a developer" panel data). Never relay a raw event to the
    founder; each event's `founder` field is the plain-language version if you need to summarize
    one for them."""
    return events_log.query(
        app_context=app_context, capability=capability_id, since=since, until=until
    )


@server.tool()
def snapshot_environment(name: str) -> dict:
    """Save a durable, point-in-time copy of an environment's currently-recorded provisioned
    capabilities (GH-67, AgDR-0003). This snapshots RECORDED STATE, not real infrastructure --
    Floci is one shared backend (AgDR-0001), so nothing about the actual resources changes.
    Restore it later with restore_environment(); a snapshot only ever exists to let you undo a
    later change back to this point.

    NOT founder-facing -- the returned snapshot_id and capability list are for the
    developer/agent, never for the founder."""
    envs = load_environments()
    env = envs.get(name)
    if env is None:
        return {"error": f"No environment named '{name}'."}
    app_context = env["app_context"]

    state = _load_state()
    capabilities = state.get(app_context, {}).get("capabilities", {})

    snapshot_id = f"{app_context}::{time.time_ns()}-{secrets.token_hex(2)}"
    with snapshots_lock():
        snapshots = load_snapshots()
        snapshots[snapshot_id] = {
            "app_context": app_context,
            "environment_name": name,
            "created": datetime.now(timezone.utc).isoformat(),
            "capabilities": capabilities,
        }
        save_snapshots(snapshots)

    return {"snapshot_id": snapshot_id, "capabilities_snapshotted": list(capabilities.keys())}


@server.tool()
def restore_environment(name: str, snapshot_id: str) -> dict:
    """Restore capabilities from a snapshot_environment() snapshot back into an environment's
    recorded state (GH-67, AgDR-0003). Every capability in the snapshot is FRESHLY RE-VERIFIED
    against live Floci before being written back -- this never blindly copies old state. A
    capability that no longer verifies (its real resource was deleted, or Floci was reset) is
    skipped, not restored, and reported as such.

    Only restores into the SAME environment the snapshot was taken from -- a snapshot's
    capabilities carry resource_name values prefixed with the snapshot's own app_context (GH-29's
    binding), so restoring into a different environment would violate that binding. If `name`'s
    current app_context doesn't match the snapshot's, this returns an error instead of restoring.

    NOT founder-facing."""
    envs = load_environments()
    env = envs.get(name)
    if env is None:
        return {"error": f"No environment named '{name}'."}
    app_context = env["app_context"]

    snapshots = load_snapshots()
    snapshot = snapshots.get(snapshot_id)
    if snapshot is None:
        return {"error": f"No snapshot with id '{snapshot_id}'."}
    if snapshot["app_context"] != app_context:
        return {
            "error": "This snapshot belongs to a different environment's app_context -- "
            "restoring it here would violate the resource-name-to-environment binding."
        }

    catalog = _load_catalog()
    restored = []
    skipped = []
    for capability_id, entry in snapshot["capabilities"].items():
        cap = catalog.get(capability_id)
        if cap is None:
            skipped.append({"capability_id": capability_id, "reason": "no longer in the catalog"})
            continue
        resource_name = entry["resource_name"]
        passed, detail = _run_verify(cap["verify"]["cli"], resource_name)
        if not passed:
            skipped.append({
                "capability_id": capability_id,
                "reason": "no longer verifies live",
            })
            continue
        restored.append(capability_id)

    if restored:
        now = datetime.now(timezone.utc).isoformat()
        with locked(STATE_LOCK_PATH):
            state = _load_state()
            state.setdefault(app_context, {"created": now, "capabilities": {}})
            for capability_id in restored:
                entry = snapshot["capabilities"][capability_id]
                state[app_context]["capabilities"][capability_id] = {
                    "resource_name": entry["resource_name"],
                    "last_verified": now,
                    "last_gate_result": "PASS",
                }
            _save_state(state)

    return {"restored": restored, "skipped": skipped}


@server.tool()
def describe_environment(name: str) -> dict:
    """Report each of an environment's currently-provisioned capabilities alongside an estimate
    of what it would cost per month on real AWS (GH-68, GH-95) -- built from the same
    aws_service/cloud_equivalent_note fields go_live_plan.py and whats_needed_to_go_live()
    already use, just with a cost figure attached. For six capabilities (DynamoDB, SQS, SNS, Step
    Functions, S3, Lambda) this is computed live from AWS's own public Price List data against a
    documented light-usage assumption; every other capability falls back to a rough, hand-written
    estimate. Either way this is an ESTIMATE for light, early-stage usage, not a quote -- actual
    cost depends on real usage volume, region, and AWS's own pricing over time. Always relay it
    with that caveat, never as a guaranteed number.

    NOT founder-facing -- service names, cost figures, and cloud_equivalent_note text are all
    developer/agent-facing detail."""
    envs = load_environments()
    env = envs.get(name)
    if env is None:
        return {"error": f"No environment named '{name}'."}
    app_context = env["app_context"]

    state = _load_state()
    capabilities = state.get(app_context, {}).get("capabilities", {})
    catalog = _load_catalog()

    line_items = []
    for capability_id, entry in capabilities.items():
        cap = catalog.get(capability_id)
        if cap is None:
            continue
        real = pricing.real_monthly_estimate(cap["aws_service"])
        if real is not None:
            cost_line = {
                "approx_monthly_cost_usd": f"~${real['monthly_usd']} for {real['assumption']}",
                "cost_source": real["source"],
            }
        else:
            cost_line = {
                "approx_monthly_cost_usd": APPROX_MONTHLY_COST_USD.get(
                    cap["aws_service"], "no estimate available for this service"
                ),
                "cost_source": "hand-written estimate (no live AWS pricing match for this service)",
            }
        line_items.append({
            "capability_id": capability_id,
            "aws_service": cap["aws_service"],
            "cloud_equivalent_note": cap["cloud_equivalent_note"],
            **cost_line,
        })

    return {
        "environment": name,
        "capabilities": line_items,
        "caveat": (
            "These are rough, illustrative estimates for light early-stage usage on real AWS -- "
            "not a quote. Actual cost depends on real usage volume, region, and AWS's own "
            "pricing over time."
        ),
    }


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


def _registered_app_contexts() -> set[str]:
    return {info["app_context"] for info in load_environments().values()}


def _resource_name_binding_error(app_context: str | None, resource_name: str) -> dict | None:
    """Enforce GH-29: when `app_context` belongs to a registered environment, `resource_name`
    must split on the first `::` into a segment EXACTLY equal to that `app_context` -- not
    merely a prefix. A naive `resource_name.startswith(app_context)` check is defeatable: an
    environment can be named after another environment's full app_context, making a prefix
    check pass across environments. Exact equality on the pre-`::` segment closes that hole
    (see AgDR-0001 and the technical design's Data Flow step 6).

    An app_context with no matching registered environment (today's default, single-app usage)
    is unaffected -- this is an accepted, documented gap for FR-7 backward compatibility, not
    an oversight. Returns None when the call may proceed, or the error dict to return as-is."""
    if app_context is None or app_context not in _registered_app_contexts():
        return None
    prefix, sep, _ = resource_name.partition("::")
    if sep != "::" or prefix != app_context:
        return {
            "error": "resource_name must be prefixed with this environment's app_context, "
            "separated by '::'."
        }
    return None


@server.tool()
def get_provisioning_recipe(capability_id: str, resource_name: str, app_context: str | None = None) -> dict:
    """Get the exact technical steps and verification command to actually build a capability.
    Pass app_context if you have it (the app/product this is for) so the live board can group
    activity by product -- optional, omit if you don't know it yet.
    Returns technical/infra detail (endpoint, credentials, resource_name) -- it's for YOUR use
    in executing the work with your own tools, never for repeating to the founder. The other
    tools returning non-founder-safe values are named in this module's own docstring. If
    capability_id isn't in list_capabilities(), do not call this -- use
    report_unsupported_request instead."""
    binding_error = _resource_name_binding_error(app_context, resource_name)
    if binding_error is not None:
        return binding_error

    catalog = _load_catalog()
    cap = catalog.get(capability_id)
    if cap is None:
        return {"error": f"'{capability_id}' is not a known capability"}
    verify_cli = _substitute_placeholders(cap["verify"]["cli"], resource_name)

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
def record_provisioned(
    app_context: str, capability_id: str, resource_name: str, dry_run: bool = False
) -> dict:
    """Call this after you've actually run the provisioning steps. This server independently
    re-verifies for real against live Floci -- your own belief that it worked is not sufficient
    and is not trusted. State is only ever updated on a genuine, freshly-checked PASS. Returns a
    founder-safe message either way; relay it as-is or in your own words, but do not add
    technical detail that isn't in it. On FAIL only, the response also carries
    `_diagnostic_for_you_the_calling_agent`: the raw verify command and its real output, for your
    own debugging. That field can contain AWS/Floci jargon (an ARN, a bucket or table name, raw
    CLI output) -- it is not founder-safe and must never be relayed to the founder.

    Pass dry_run=True to preview the exact command this call would run and what it would check,
    WITHOUT executing anything against live Floci and WITHOUT touching stack-state.json or the
    live board's event log. Useful right before the real call, when you want to double-check the
    invocation rather than fire it live. A dry run can never itself produce a PASS -- it never
    ran anything real to justify one."""
    binding_error = _resource_name_binding_error(app_context, resource_name)
    if binding_error is not None:
        return binding_error

    catalog = _load_catalog()
    cap = catalog.get(capability_id)
    if cap is None:
        return {"gate_result": "FAIL", "founder_message": "That isn't something I can verify."}

    if dry_run:
        return {
            "dry_run": True,
            "gate_result": "NOT_RUN",
            "founder_message": (
                "Just double-checking before I confirm anything's ready -- nothing has actually "
                "been checked yet."
            ),
            "_diagnostic_for_you_the_calling_agent": {
                "note": "PREVIEW ONLY -- not executed. This is the exact command a real "
                "(non-dry-run) call would run, and what it would check.",
                "command_that_would_run": _substitute_placeholders(
                    cap["verify"]["cli"], resource_name
                ),
                "success_criteria": cap["verify"]["success_criteria"],
            },
        }

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
                "command_that_ran": _substitute_placeholders(cap["verify"]["cli"], resource_name),
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
