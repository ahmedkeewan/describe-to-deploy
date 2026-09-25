#!/usr/bin/env python3
"""Regression test for GH-67 / AgDR-0003: snapshot_environment() saves a point-in-time copy of an
environment's recorded capabilities; restore_environment() re-verifies each one live before
writing it back, so a snapshot can never resurrect a false claim. Also confirms the binding
AgDR-0003 relies on: a snapshot can only be restored into the SAME environment it came from."""
import sys
import tempfile
import threading
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server
import snapshots_store


class EnvironmentSnapshotRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self._patches = [
            unittest.mock.patch.object(
                environments_store, "ENVIRONMENTS_PATH", Path(self.tmpdir.name) / "environments.json"
            ),
            unittest.mock.patch.object(
                environments_store, "ENVIRONMENTS_LOCK_PATH", Path(self.tmpdir.name) / ".environments.lock"
            ),
            unittest.mock.patch.object(
                snapshots_store, "SNAPSHOTS_PATH", Path(self.tmpdir.name) / "environment-snapshots.json"
            ),
            unittest.mock.patch.object(
                snapshots_store, "SNAPSHOTS_LOCK_PATH", Path(self.tmpdir.name) / ".environment-snapshots.lock"
            ),
            unittest.mock.patch.object(
                mcp_server, "STATE_PATH", Path(self.tmpdir.name) / "stack-state.json"
            ),
            unittest.mock.patch.object(
                mcp_server, "STATE_LOCK_PATH", Path(self.tmpdir.name) / ".stack-state.lock"
            ),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def _create_and_provision(self, name, capability_id="file-storage"):
        env = mcp_server.create_environment(name)
        app_context = env["app_context"]
        resource_name = f"{app_context}::photos"
        with unittest.mock.patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            mcp_server.record_provisioned(app_context, capability_id, resource_name)
        return app_context, resource_name

    def test_snapshot_unknown_environment_returns_error(self):
        result = mcp_server.snapshot_environment("does-not-exist")
        self.assertIn("error", result)

    def test_snapshot_captures_currently_recorded_capabilities(self):
        self._create_and_provision("app-a")
        snap = mcp_server.snapshot_environment("app-a")
        self.assertIn("snapshot_id", snap)
        self.assertEqual(snap["capabilities_snapshotted"], ["file-storage"])

    def test_restore_unknown_environment_returns_error(self):
        result = mcp_server.restore_environment("does-not-exist", "whatever")
        self.assertIn("error", result)

    def test_restore_unknown_snapshot_returns_error(self):
        self._create_and_provision("app-a")
        result = mcp_server.restore_environment("app-a", "does-not-exist")
        self.assertIn("error", result)

    def test_restore_re_verifies_and_skips_when_no_longer_passing(self):
        self._create_and_provision("app-a")
        snap = mcp_server.snapshot_environment("app-a")
        with unittest.mock.patch.object(mcp_server, "_run_verify", return_value=(False, "gone")):
            result = mcp_server.restore_environment("app-a", snap["snapshot_id"])
        self.assertEqual(result["restored"], [])
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(result["skipped"][0]["capability_id"], "file-storage")

    def test_restore_writes_state_when_still_passing(self):
        self._create_and_provision("app-a")
        snap = mcp_server.snapshot_environment("app-a")
        with unittest.mock.patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            result = mcp_server.restore_environment("app-a", snap["snapshot_id"])
        self.assertEqual(result["restored"], ["file-storage"])
        state = mcp_server._load_state()
        app_context = list(state.keys())[0]
        self.assertEqual(state[app_context]["capabilities"]["file-storage"]["last_gate_result"], "PASS")

    def test_cannot_restore_a_snapshot_into_a_different_environment(self):
        # AgDR-0003's binding: a snapshot's capabilities carry resource_name values prefixed
        # with the SNAPSHOT's app_context. Restoring into a different environment (different
        # app_context) must be rejected, not silently allowed.
        self._create_and_provision("app-a")
        snap = mcp_server.snapshot_environment("app-a")
        self._create_and_provision("app-b", capability_id="structured-data")
        result = mcp_server.restore_environment("app-b", snap["snapshot_id"])
        self.assertIn("error", result)
        self.assertIn("different environment", result["error"])

    def test_restore_skips_a_capability_no_longer_in_the_catalog(self):
        self._create_and_provision("app-a")
        snap = mcp_server.snapshot_environment("app-a")
        # Simulate the catalog having dropped this capability since the snapshot was taken.
        with unittest.mock.patch.object(mcp_server, "_load_catalog", return_value={}):
            result = mcp_server.restore_environment("app-a", snap["snapshot_id"])
        self.assertEqual(result["restored"], [])
        self.assertEqual(result["skipped"][0]["reason"], "no longer in the catalog")

    def test_concurrent_snapshots_of_two_environments_do_not_collide(self):
        # Concurrency requirement from the ticket's acceptance criteria.
        self._create_and_provision("app-a")
        self._create_and_provision("app-b", capability_id="structured-data")
        results = {}
        lock = threading.Lock()

        def snapshot(name):
            r = mcp_server.snapshot_environment(name)
            with lock:
                results[name] = r

        threads = [threading.Thread(target=snapshot, args=(n,)) for n in ("app-a", "app-b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual(results["app-a"]["capabilities_snapshotted"], ["file-storage"])
        self.assertEqual(results["app-b"]["capabilities_snapshotted"], ["structured-data"])
        snapshots = snapshots_store.load_snapshots()
        self.assertEqual(len(snapshots), 2)


if __name__ == "__main__":
    unittest.main()
