#!/usr/bin/env python3
"""
Local web server for the founder-facing live board (interface/README.md's "Platform" section).

Serves:
  GET  /              interface/live.html, the hand-built two-pane board
  GET  /state          current stack-state.json, reconciled against live Floci before returning
                        (interface/README.md's "state file is never trusted on startup" rule)
  GET  /events          SSE stream tailing harness/events.jsonl

The UI is a pure renderer (interface/README.md's "Coupling" section) -- this server writes
nothing new. Provisioning/verification actions happen through harness/mcp_server.py's MCP tools,
called by whatever agent (Claude Code, Claude Desktop) is driving the conversation; this server
only tails what those tool calls already write to events.jsonl and stack-state.json.

Run: source harness/.venv/bin/activate && python3 harness/web_server.py
Then open http://localhost:7777 -- or set FLOCI_BOARD_PORT to run more than one board
side by side (e.g. one per environment from GH-26's create_environment tool).
"""
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import events as events_log
import verify_gate

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Route

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "harness" / "stack-state.json"
CATALOG_PATH = REPO_ROOT / "catalog" / "capabilities.json"
LIVE_HTML_PATH = REPO_ROOT / "interface" / "live.html"

# Resolved once at import time via the server process's own PATH (the user's normal shell PATH,
# not this repo's harness/.venv) -- claude itself is not a project dependency.
CLAUDE_BIN = shutil.which("claude") or "claude"
MCP_SERVER_CMD = str(REPO_ROOT / "harness" / ".venv" / "bin" / "python3")
MCP_SERVER_ARGS = [str(REPO_ROOT / "harness" / "mcp_server.py")]

# A full system-prompt override (not an append) for the spawned /chat session -- Claude Code's
# own default system prompt (memory, general coding-assistant framing) is exactly what caused
# the first real bug found in this feature: asked for uncatalogued "real-time chat," the spawned
# session ignored the harness entirely and talked about "updating memory" instead of calling
# report_unsupported_request. This replaces that default outright so the spawned session behaves
# as the harness, not as a general assistant that happens to have some extra tools.
CHAT_SYSTEM_PROMPT = """You are a software agent that turns a non-technical founder's plain-language product request into real, working local infrastructure on Floci, through the floci-control-plane MCP server's tools. You have no other job in this session -- ignore any general-purpose skills, memory, or persona you might otherwise have.

For every request, in order:
1. Call list_capabilities() to see what you can build. Match the request to one entry BY MEANING.
2. Call get_app_state(app_context) to check what already exists for this app before assuming you need to build something new.
3. If it matches a capability: call get_provisioning_recipe(), actually run the returned steps with Bash, then call record_provisioned() -- which independently re-verifies before it will ever say something is done. Trust its gate_result, not your own belief that your steps should have worked.
4. If nothing in the catalog matches (this includes anything like real-time chat/websockets, video processing, ML inference, or payments): do NOT invent a capability, do NOT build anything with raw Bash outside what the recipe gave you, and do NOT do anything else instead (no memory updates, no unrelated file edits). Call report_unsupported_request() and relay its founder_message as your entire final reply.
5. If a capability's provisioning fails and a fix isn't a single obvious retry, call check_app_readiness() and report honestly rather than guessing further.

Your final reply to the founder must be plain, jargon-free language only -- never name the underlying AWS/Floci service, port, ARN, resource name, or endpoint URL. That is the single most important rule here: a jargon leak or an off-topic reply is a failure even if you technically did something useful."""


def _load_catalog() -> dict:
    return {c["id"]: c for c in json.loads(CATALOG_PATH.read_text())["capabilities"]}


async def index(request):
    return FileResponse(LIVE_HTML_PATH)


async def _check_one(cap: dict, resource_name: str) -> bool:
    """Runs one blocking verify_gate check off the event loop, so N capabilities across M apps
    reconcile concurrently instead of one HTTP request blocking on a serial chain of real AWS CLI
    round trips -- with growing demo data (multiple apps, some checks doing multi-step Cognito
    sign-up/confirm/login/delete) the serial version measured 11s+ and only gets worse. Caught by
    actually loading the page in a browser and watching /state hang pending, not by curl alone."""
    loop = asyncio.get_event_loop()
    passed, _ = await loop.run_in_executor(None, verify_gate.run_check, cap["verify"]["cli"], resource_name)
    return passed


async def state(request):
    """Reconciles every row against live Floci before returning -- interface/README.md's
    'never trust the state file on startup' rule. A row only reports working if its check
    genuinely passes right now, not because the file says it did once. Runs all checks
    concurrently (see _check_one) rather than serially."""
    if not STATE_PATH.exists():
        return JSONResponse({})

    raw_state = json.loads(STATE_PATH.read_text())
    catalog = _load_catalog()

    jobs = []  # (app_context, cap_id, cap) in the same order as the gathered results
    for app_context, app in raw_state.items():
        for cap_id, info in app.get("capabilities", {}).items():
            cap = catalog.get(cap_id)
            if cap is None:
                continue
            jobs.append((app_context, cap_id, cap, info["resource_name"]))

    results = await asyncio.gather(*[_check_one(cap, resource_name) for _, _, cap, resource_name in jobs])

    reconciled = {app_context: {"created": raw_state[app_context].get("created"), "capabilities": {}}
                  for app_context in raw_state}
    for (app_context, cap_id, cap, resource_name), passed in zip(jobs, results):
        reconciled[app_context]["capabilities"][cap_id] = {
            "label": cap["founder_description"],
            "status": "working" if passed else "not working yet",
            "proof": cap["verify"].get("founder_proof") if passed else None,
            "last_checked": "just now",
            "depends_on": cap.get("depends_on", []),
            # Technical fields -- the UI must only ever show these behind the explicit
            # "Details for a developer" disclosure or the technical export option, never in the
            # founder-facing board itself (interface/README.md's language rule).
            "_dev": {
                "service": cap["aws_service"],
                "resource_name": resource_name,
                "endpoint": "http://localhost:4566",
                "cloud_equivalent": cap.get("cloud_equivalent_note", ""),
            },
        }

    return JSONResponse(reconciled)


async def events_stream(request):
    """SSE endpoint. Sends everything already in events.jsonl on connect, then tails for new
    lines -- a browser opening this mid-run sees full history, not just what happens next."""

    async def generator():
        sent = 0
        for event in events_log.read_all():
            yield f"data: {json.dumps(event)}\n\n"
            sent += 1
        last_size = events_log.EVENTS_PATH.stat().st_size if events_log.EVENTS_PATH.exists() else 0
        while True:
            await asyncio.sleep(1)
            if not events_log.EVENTS_PATH.exists():
                continue
            size = events_log.EVENTS_PATH.stat().st_size
            if size > last_size:
                all_events = events_log.read_all()
                for event in all_events[sent:]:
                    yield f"data: {json.dumps(event)}\n\n"
                sent = len(all_events)
                last_size = size

    return StreamingResponse(generator(), media_type="text/event-stream")


async def chat(request):
    """Bridges the board's chat box to a real Claude Code invocation, so a request typed
    directly on localhost:7777 can actually plan/execute/verify against Floci -- there's no raw
    LLM API key in this environment, so this is the only way to make the chat box real: spawn
    `claude -p` (one-shot, non-interactive) with the floci-control-plane MCP server attached,
    using the user's own Claude Code login rather than a new credential.

    Trust boundary, stated plainly: this endpoint lets anything that can reach
    http://127.0.0.1:7777 (this process only binds localhost) trigger a real, tool-using Claude
    Code run with --permission-mode bypassPermissions. That's scoped as tightly as the CLI
    allows short of no tool access at all: --allowedTools restricts the spawned session to Bash
    and this repo's own MCP tools specifically, and --strict-mcp-config means only the
    floci-control-plane server is attached, ignoring any other MCP config the user has (project
    or global) that this process might otherwise inherit. It still means a local page can make
    real, billed API calls and real changes to local Floci state without a human approving each
    one -- acceptable for a single-user local dev tool, not something to expose beyond
    localhost. Progress streams to the caller for free: the spawned session's own tool calls hit
    the same events.jsonl this server already tails, so the board's Activity feed and capability
    rows update live while this request is still in flight, exactly like a run driven from a
    separate Claude Code/Desktop window."""
    body = await request.json()
    message = (body.get("message") or "").strip()
    app_context = (body.get("app_context") or "").strip() or None

    if not message:
        return JSONResponse({"error": "Message can't be empty."}, status_code=400)

    prompt = f'The app is called "{app_context}". {message}' if app_context else message

    mcp_config = json.dumps({
        "mcpServers": {
            "floci-control-plane": {"command": MCP_SERVER_CMD, "args": MCP_SERVER_ARGS}
        }
    })

    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--system-prompt", CHAT_SYSTEM_PROMPT,
        "--mcp-config", mcp_config,
        "--strict-mcp-config",
        "--allowedTools", "Bash mcp__floci-control-plane__*",
        "--permission-mode", "bypassPermissions",
        "--output-format", "json",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    except FileNotFoundError:
        return JSONResponse({"error": "claude CLI not found on this server's PATH."}, status_code=500)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "Timed out after 5 minutes."}, status_code=504)

    if proc.returncode != 0:
        return JSONResponse({"error": stderr.decode(errors="replace")[:2000] or "Unknown error."}, status_code=500)

    raw = stdout.decode(errors="replace")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return JSONResponse({"reply": raw})

    if result.get("is_error"):
        return JSONResponse({"error": result.get("result", "The assistant reported an error.")}, status_code=500)

    return JSONResponse({
        "reply": result.get("result", ""),
        "cost_usd": result.get("total_cost_usd"),
        "duration_ms": result.get("duration_ms"),
    })


app = Starlette(routes=[
    Route("/", index),
    Route("/state", state),
    Route("/events", events_stream),
    Route("/chat", chat, methods=["POST"]),
])

def _resolve_board_port() -> int:
    """FLOCI_BOARD_PORT lets two developers each run their own board side by side (see
    create_environment's board_port, GH-26). Defaults to today's 7777 when unset. Pulled out as
    its own function so it's importable and testable without actually starting the server."""
    return int(os.environ.get("FLOCI_BOARD_PORT", "7777"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=_resolve_board_port())
