#!/usr/bin/env python3
"""Regression test for GH-35: concurrent record_provisioned calls against the same
stack-state.json must never lose an update. stack-state.json's read-modify-write cycle had no
cross-process lock before GH-24; this test exercises record_provisioned itself (not just the
raw locking primitive, which test_state_lock.py already covers) to prove the fix holds
end-to-end. Requires the `mcp` package -- run via harness/.venv."""
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_server

# On a fast local filesystem, threads can run the unlocked read-modify-write so quickly that
# they rarely interleave -- an early version of this test passed 0-failures even with the lock
# disabled entirely, which would have made it a false confidence check, not a real regression
# test. Wrapping _load_state with a small forced delay widens the window deterministically: it
# still passes under the real lock (correctly serialized, just slower), but reliably fails if
# the lock is ever removed. Confirmed manually: disabling the lock without this delay produced
# 0 failures; disabling it WITH this delay produced consistent lost-update failures and even a
# torn-write JSONDecodeError, matching the exact failure mode GH-24 exists to prevent.
_ORIGINAL_LOAD_STATE = mcp_server._load_state


def _slow_load_state():
    state = _ORIGINAL_LOAD_STATE()
    time.sleep(0.01)
    return state

CAPABILITY_IDS = [
    "user-accounts", "file-storage", "structured-data", "background-job", "send-email",
    "scheduled-task", "background-queue", "push-notifications", "app-secrets", "app-settings",
    "backend-api", "search",
]


class ConcurrentRecordProvisionedTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self.tmpdir.name) / "stack-state.json"
        self.state_lock_path = Path(self.tmpdir.name) / ".stack-state.lock"
        self._patches = [
            patch.object(mcp_server, "STATE_PATH", self.state_path),
            patch.object(mcp_server, "STATE_LOCK_PATH", self.state_lock_path),
            # _run_verify would shell out to live Floci; mock it to a deterministic PASS so
            # this test exercises the state-locking path, not infra availability.
            patch.object(mcp_server, "_run_verify", return_value=(True, "ok")),
            # See _slow_load_state's comment above -- widens the race window deterministically.
            patch.object(mcp_server, "_load_state", _slow_load_state),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_concurrent_calls_against_the_same_app_context_lose_no_update(self):
        app_context = "shared-app"
        results = []
        lock = threading.Lock()

        def call(cap_id):
            result = mcp_server.record_provisioned(app_context, cap_id, f"{cap_id}-resource")
            with lock:
                results.append((cap_id, result))

        threads = [threading.Thread(target=call, args=(cap_id,)) for cap_id in CAPABILITY_IDS]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # Every call must have reported PASS -- _run_verify was mocked to always pass.
        for cap_id, result in results:
            self.assertEqual(result["gate_result"], "PASS", f"{cap_id} did not PASS: {result}")

        # The real assertion: every capability's entry survived the concurrent writes. A lost
        # update under the pre-GH-24 unlocked read-modify-write would silently drop some of
        # these -- reading fewer than len(CAPABILITY_IDS) entries here is the failure mode.
        state = mcp_server._load_state()
        recorded = set(state[app_context]["capabilities"].keys())
        self.assertEqual(
            recorded,
            set(CAPABILITY_IDS),
            f"lost update(s): expected {set(CAPABILITY_IDS)}, got {recorded}",
        )

    def test_concurrent_calls_against_different_app_contexts_dont_interfere(self):
        results = {}
        lock = threading.Lock()

        def call(i):
            app_context = f"app-{i}"
            result = mcp_server.record_provisioned(app_context, "file-storage", f"bucket-{i}")
            with lock:
                results[app_context] = result

        threads = [threading.Thread(target=call, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        state = mcp_server._load_state()
        for i in range(10):
            app_context = f"app-{i}"
            self.assertIn(app_context, state, f"{app_context} missing from state -- lost update")
            self.assertIn("file-storage", state[app_context]["capabilities"])


if __name__ == "__main__":
    unittest.main()
