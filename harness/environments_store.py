#!/usr/bin/env python3
"""
Load/save helpers for harness/environments.json -- the sidecar file recording each named
environment's `app_context` and board port (see the technical design and AgDR-0001).

`load_environments()` and `save_environments()` are lock-free primitives on purpose. A caller
that needs a consistent check-then-write cycle -- for example `create_environment`'s uniqueness
check, port scan, and write, which the technical design requires to be one atomic section
(Data Flow step 2) -- wraps ALL of those steps in one `with environments_lock():` block, not
just the final save. Locking only the save call would still race on the uniqueness check.

Uses the same `state_lock.locked()` helper as `stack-state.json` (GH-24), so concurrent
`mcp_server.py` processes (one per connected agent) never race on this file either.
"""
import json
from pathlib import Path
from typing import Iterator
import contextlib

from state_lock import locked

REPO_ROOT = Path(__file__).resolve().parent.parent
ENVIRONMENTS_PATH = REPO_ROOT / "harness" / "environments.json"
ENVIRONMENTS_LOCK_PATH = REPO_ROOT / "harness" / ".environments.lock"


@contextlib.contextmanager
def environments_lock() -> Iterator[None]:
    """Hold the exclusive lock for environments.json. Wrap every read-modify-write cycle in
    this, not just the save -- see the module docstring for why."""
    with locked(ENVIRONMENTS_LOCK_PATH):
        yield


def load_environments() -> dict:
    """Read environments.json. Returns {} if the file doesn't exist yet (no environments
    created so far). Does not itself lock -- see the module docstring."""
    if ENVIRONMENTS_PATH.exists():
        return json.loads(ENVIRONMENTS_PATH.read_text())
    return {}


def save_environments(environments: dict) -> None:
    """Write environments.json. Does not itself lock -- see the module docstring."""
    ENVIRONMENTS_PATH.write_text(json.dumps(environments, indent=2) + "\n")
