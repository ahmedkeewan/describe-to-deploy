#!/usr/bin/env python3
"""
Shared file-locking helper for the harness's plain-JSON state files.

Each MCP client (each agent) runs its own mcp_server.py subprocess over stdio. Without a lock,
two processes racing a read-modify-write cycle on the same file (harness/stack-state.json today;
harness/environments.json and harness/events.jsonl once GH-25 and GH-31 land) can silently
clobber each other's write. `locked()` wraps a POSIX fcntl.flock around that critical section so
only one process holds it at a time.

POSIX only. This repo documents direct macOS/Linux support and Windows-via-WSL, both POSIX.
See AgDR-0002 for why flock was chosen over a database.
"""
import contextlib
import fcntl
from pathlib import Path
from typing import Iterator


@contextlib.contextmanager
def locked(lock_path: Path) -> Iterator[None]:
    """Hold an exclusive OS-level lock on `lock_path` for the duration of the `with` block.

    Callers are responsible for keeping the locked section to just the read-modify-write cycle
    it protects. Do not hold the lock across a slow operation such as a verify command -- per
    AgDR-0002, verification stays outside the locked section so one slow check never blocks
    every other agent's writes.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a") as lockfile:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)
