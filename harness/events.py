#!/usr/bin/env python3
"""
Two-channel event log, per interface/README.md's event contract.

Every event carries `founder` (plain language, safe to render directly) and `dev` (real service
names, commands, exit codes -- rendered only behind the explicit "Details for a developer" panel).
Append-only, one JSON object per line, so the UI can tail it live over SSE.

This is the missing piece interface/README.md names explicitly: the "events.jsonl with founder/dev
channels" work, which depends on the executor tool. The executor here is the MCP server's tools
(harness/mcp_server.py) -- each call that changes state also appends an event, so a browser
tailing this file sees the same actions in real time that Claude (as the calling agent) is taking
through the MCP tools.
"""
import json
import itertools
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_lock import locked

REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = REPO_ROOT / "harness" / "events.jsonl"
EVENTS_LOCK_PATH = REPO_ROOT / "harness" / ".events.lock"

_seq_counter = itertools.count(1)


def _next_seq() -> int:
    if EVENTS_PATH.exists():
        try:
            with EVENTS_PATH.open() as f:
                last = 0
                for line in f:
                    if line.strip():
                        last = json.loads(line)["seq"]
                return last + 1
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    return next(_seq_counter)


def emit(kind: str, capability: str | None, founder: dict, dev: dict | None = None, app_context: str | None = None) -> dict:
    """Append one event. `founder` and `dev` are both plain dicts -- founder must never contain
    a service name, port, ARN, or error code; dev is exactly that detail, addressed to someone
    else (interface/README.md's "Details for a developer" panel). `app_context` lets the UI
    filter the activity feed per product once more than one exists on the same board.

    Locked with the same fcntl.flock helper GH-24 introduced for stack-state.json.
    `_next_seq()` reads the whole file and computes `last + 1`, and each MCP client runs its own
    process, so two processes could previously compute the same seq (the old threading.Lock only
    serialized within one process). The lock has to cover both `_next_seq()`'s read and the
    write in one critical section, not just the write -- locking only the write would still let
    two processes read the same "current last line" before either appends."""
    with locked(EVENTS_LOCK_PATH):
        event = {
            "seq": _next_seq(),
            "t": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "capability": capability,
            "app_context": app_context,
            "founder": founder,
            "dev": dev or {},
        }
        EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EVENTS_PATH.open("a") as f:
            f.write(json.dumps(event) + "\n")
        return event


def read_all() -> list[dict]:
    if not EVENTS_PATH.exists():
        return []
    events = []
    with EVENTS_PATH.open() as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events
