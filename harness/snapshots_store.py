#!/usr/bin/env python3
"""
Load/save helpers for harness/environment-snapshots.json -- durable point-in-time copies of an
environment's stack-state.json entry, recorded by snapshot_environment() and consumed by
restore_environment() (GH-67, AgDR-0003).

Snapshots are scoped to ONE environment's own app_context -- they are not a mechanism for
seeding a second, independent environment (see AgDR-0003 for why a true clone would violate the
resource-name-to-environment binding from GH-29). restore_environment() re-verifies each
snapshotted capability live before writing it back to stack-state.json, so a snapshot only ever
resurrects state that still checks out for real right now.

Same lock-free-primitives-plus-caller-locks-the-whole-cycle pattern as environments_store.py and
stack-state.json -- see that module's docstring for the full rationale.
"""
import json
from pathlib import Path
from typing import Iterator
import contextlib

from state_lock import locked

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS_PATH = REPO_ROOT / "harness" / "environment-snapshots.json"
SNAPSHOTS_LOCK_PATH = REPO_ROOT / "harness" / ".environment-snapshots.lock"


@contextlib.contextmanager
def snapshots_lock() -> Iterator[None]:
    """Hold the exclusive lock for environment-snapshots.json. Wrap every read-modify-write
    cycle in this, not just the save -- see the module docstring for why."""
    with locked(SNAPSHOTS_LOCK_PATH):
        yield


def load_snapshots() -> dict:
    """Read environment-snapshots.json. Returns {} if the file doesn't exist yet. Does not
    itself lock -- see the module docstring."""
    if SNAPSHOTS_PATH.exists():
        return json.loads(SNAPSHOTS_PATH.read_text())
    return {}


def save_snapshots(snapshots: dict) -> None:
    """Write environment-snapshots.json. Does not itself lock -- see the module docstring."""
    SNAPSHOTS_PATH.write_text(json.dumps(snapshots, indent=2) + "\n")
