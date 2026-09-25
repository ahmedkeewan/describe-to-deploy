#!/usr/bin/env python3
"""Regression test for GH-70: record_provisioned(dry_run=True) previews the exact verify command
and its success criteria without executing anything against live Floci or touching state -- so
an agent can double-check the invocation right before firing it for real."""
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_server


class RecordProvisionedDryRunTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self.tmpdir.name) / "stack-state.json"
        self.state_lock_path = Path(self.tmpdir.name) / ".stack-state.lock"
        self._patches = [
            unittest.mock.patch.object(mcp_server, "STATE_PATH", self.state_path),
            unittest.mock.patch.object(mcp_server, "STATE_LOCK_PATH", self.state_lock_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_dry_run_does_not_execute_subprocess(self):
        with unittest.mock.patch("subprocess.run") as mock_run:
            result = mcp_server.record_provisioned(
                "myapp", "file-storage", "myapp-photos", dry_run=True
            )
        mock_run.assert_not_called()
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["gate_result"], "NOT_RUN")

    def test_dry_run_does_not_write_state(self):
        with unittest.mock.patch("subprocess.run"):
            mcp_server.record_provisioned("myapp", "file-storage", "myapp-photos", dry_run=True)
        self.assertFalse(self.state_path.exists())

    def test_dry_run_does_not_emit_a_live_board_event(self):
        with unittest.mock.patch("subprocess.run"), \
             unittest.mock.patch.object(mcp_server.events_log, "emit") as mock_emit:
            mcp_server.record_provisioned("myapp", "file-storage", "myapp-photos", dry_run=True)
        mock_emit.assert_not_called()

    def test_dry_run_response_carries_the_substituted_command_and_success_criteria(self):
        with unittest.mock.patch("subprocess.run"):
            result = mcp_server.record_provisioned(
                "myapp", "file-storage", "myapp-photos", dry_run=True
            )
        diagnostic = result["_diagnostic_for_you_the_calling_agent"]
        self.assertIn("myapp-photos", diagnostic["command_that_would_run"])
        self.assertNotIn("<bucketName>", diagnostic["command_that_would_run"])
        self.assertIn("success_criteria", diagnostic)

    def test_dry_run_response_founder_message_never_claims_success_or_failure(self):
        with unittest.mock.patch("subprocess.run"):
            result = mcp_server.record_provisioned(
                "myapp", "file-storage", "myapp-photos", dry_run=True
            )
        msg = result["founder_message"].lower()
        self.assertNotIn("it's ready", msg)
        self.assertNotIn("isn't actually working", msg)
        self.assertIn("nothing has actually been checked", msg)

    def test_dry_run_never_returns_pass_or_fail(self):
        with unittest.mock.patch("subprocess.run"):
            result = mcp_server.record_provisioned(
                "myapp", "file-storage", "myapp-photos", dry_run=True
            )
        self.assertNotIn(result["gate_result"], ("PASS", "FAIL"))

    def test_a_real_non_dry_run_call_is_unaffected(self):
        with unittest.mock.patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            result = mcp_server.record_provisioned("myapp", "file-storage", "myapp-photos")
        self.assertNotIn("dry_run", result)
        self.assertEqual(result["gate_result"], "PASS")
        self.assertTrue(self.state_path.exists())


if __name__ == "__main__":
    unittest.main()
