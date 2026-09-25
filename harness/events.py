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


def query(
    app_context: str | None = None,
    capability: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[dict]:
    """Filterable read over the whole event log (GH-71), for debugging/auditing past runs without
    needing the live board open at the time they happened. `since`/`until` are ISO-8601 timestamp
    strings compared lexicographically against each event's `t` field -- safe because `t` is
    always written by `datetime.now(timezone.utc).isoformat()`, which sorts the same lexically and
    chronologically.

    A single read of the whole file, same as read_all() -- no lock held across it. This mirrors
    read_all()'s existing lock-free read; the lock in emit() only needs to cover its own read of
    the last seq plus its own write, not every reader (GH-24's original concern was two WRITERS
    computing the same seq, not a reader racing a writer). A line that fails to parse (e.g. the
    very last line, mid-write by another process at the exact moment of this read) is skipped
    rather than raising, so a filtered history read can never crash on a benign race."""
    events = []
    if not EVENTS_PATH.exists():
        return events
    with EVENTS_PATH.open() as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if app_context is not None and event.get("app_context") != app_context:
                continue
            if capability is not None and event.get("capability") != capability:
                continue
            if since is not None and event.get("t", "") < since:
                continue
            if until is not None and event.get("t", "") > until:
                continue
            events.append(event)
    return events
