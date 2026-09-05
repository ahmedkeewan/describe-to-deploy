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
Then open http://localhost:7777
"""
import asyncio
import json
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


def _load_catalog() -> dict:
    return {c["id"]: c for c in json.loads(CATALOG_PATH.read_text())["capabilities"]}


async def index(request):
    return FileResponse(LIVE_HTML_PATH)


async def state(request):
    """Reconciles every row against live Floci before returning -- interface/README.md's
    'never trust the state file on startup' rule. A row only reports working if its check
    genuinely passes right now, not because the file says it did once."""
    if not STATE_PATH.exists():
        return JSONResponse({})

    raw_state = json.loads(STATE_PATH.read_text())
    catalog = _load_catalog()
    reconciled = {}

    for app_context, app in raw_state.items():
        reconciled[app_context] = {"created": app.get("created"), "capabilities": {}}
        for cap_id, info in app.get("capabilities", {}).items():
            cap = catalog.get(cap_id)
            if cap is None:
                continue
            passed, _ = verify_gate.run_check(cap["verify"]["cli"], info["resource_name"])
            reconciled[app_context]["capabilities"][cap_id] = {
                "label": cap["founder_description"],
                "status": "working" if passed else "not working yet",
                "proof": cap["verify"].get("founder_proof") if passed else None,
                "last_checked": "just now",
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


app = Starlette(routes=[
    Route("/", index),
    Route("/state", state),
    Route("/events", events_stream),
])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7777)
