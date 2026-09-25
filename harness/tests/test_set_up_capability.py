#!/usr/bin/env python3
"""set_up_capability(): the server creates, verifies, and records a capability itself, so a client
with no shell -- or one whose shell is sandboxed away from the local engine, like Claude Desktop's
-- can still set things up.

The unit tests mock the setup command. The live test at the bottom runs every capability for real
against Floci; it's skipped unless SERVICE_BUDDY_LIVE=1 (CI has no Floci):

    SERVICE_BUDDY_LIVE=1 harness/.venv/bin/python3 -m unittest harness/tests/test_set_up_capability.py
"""
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import events
import mcp_server
import snapshots_store

CATALOG = json.loads((Path(__file__).resolve().parents[2] / "catalog" / "capabilities.json").read_text())


class IsolatedStateTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(self.tmpdir.name)
        self._patches = [
            patch.object(environments_store, "ENVIRONMENTS_PATH", tmp / "environments.json"),
            patch.object(environments_store, "ENVIRONMENTS_LOCK_PATH", tmp / ".environments.lock"),
            patch.object(snapshots_store, "SNAPSHOTS_PATH", tmp / "environment-snapshots.json"),
            patch.object(snapshots_store, "SNAPSHOTS_LOCK_PATH", tmp / ".environment-snapshots.lock"),
            patch.object(mcp_server, "STATE_PATH", tmp / "stack-state.json"),
            patch.object(mcp_server, "STATE_LOCK_PATH", tmp / ".stack-state.lock"),
            patch.object(events, "EVENTS_PATH", tmp / "events.jsonl"),
            patch.object(events, "EVENTS_LOCK_PATH", tmp / ".events.lock"),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()


class CatalogSetupCommandTests(unittest.TestCase):
    def test_every_capability_has_a_setup_command(self):
        for cap in CATALOG["capabilities"]:
            with self.subTest(capability=cap["id"]):
                provision = cap["provision"]
                self.assertIn("<name>", provision["cli"])
                self.assertRegex(provision["name_suffix"], r"^[a-z]+$")
                self.assertGreater(provision["name_max_length"], len(provision["name_suffix"]) + 10)


class DeriveResourceNameTests(unittest.TestCase):
    VALID = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")

    def test_short_app_context_is_kept_readable(self):
        self.assertEqual(mcp_server._derive_resource_name("photo-demo-eb35dd", "files", 63),
                         "photo-demo-eb35dd-files")

    def test_every_capability_gets_a_valid_name_even_for_a_long_messy_app_context(self):
        app_context = "My Startup!! 2026 -- the Photo_App-with-a-very-long-name-a1b2c3"
        for cap in CATALOG["capabilities"]:
            p = cap["provision"]
            with self.subTest(capability=cap["id"]):
                name = mcp_server._derive_resource_name(app_context, p["name_suffix"], p["name_max_length"])
                self.assertLessEqual(len(name), p["name_max_length"])
                self.assertRegex(name, self.VALID)
                self.assertNotIn("--", name)

    def test_shortened_names_for_different_apps_do_not_collide(self):
        a = mcp_server._derive_resource_name("a-very-long-app-name-number-one", "search", 28)
        b = mcp_server._derive_resource_name("a-very-long-app-name-number-two", "search", 28)
        self.assertNotEqual(a, b)

    def test_app_context_starting_with_a_digit_gets_a_letter_first(self):
        self.assertRegex(mcp_server._derive_resource_name("123shop", "files", 63), r"^[a-z]")


class SetUpCapabilityTests(IsolatedStateTest):
    def test_runs_the_setup_command_then_records_what_it_printed(self):
        created = subprocess.CompletedProcess("", 0, stdout="photo-demo-files\n", stderr="")
        with patch("subprocess.run", return_value=created) as mock_run, \
             patch.object(mcp_server, "_run_verify", return_value=(True, "ok")) as mock_verify:
            result = mcp_server.set_up_capability("photo-demo", "file-storage")
        self.assertIn("create-bucket --bucket photo-demo-files", mock_run.call_args.args[0])
        mock_verify.assert_called_once()
        self.assertEqual(mock_verify.call_args.args[1], "photo-demo-files")
        self.assertEqual(result["gate_result"], "PASS")
        recorded = mcp_server._load_state()["photo-demo"]["capabilities"]["file-storage"]
        self.assertEqual(recorded["resource_name"], "photo-demo-files")

    def test_records_an_aws_assigned_id_printed_by_the_setup_command(self):
        arn = "arn:aws:sns:us-east-1:000000000000:photo-demo-alerts"
        created = subprocess.CompletedProcess("", 0, stdout=f"{arn}\n", stderr="")
        with patch("subprocess.run", return_value=created), \
             patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            mcp_server.set_up_capability("photo-demo", "push-notifications")
        recorded = mcp_server._load_state()["photo-demo"]["capabilities"]["push-notifications"]
        self.assertEqual(recorded["resource_name"], arn)

    def test_failed_setup_is_founder_safe_and_never_recorded(self):
        failed = subprocess.CompletedProcess("", 255, stdout="", stderr="BucketAlreadyExists s3://x")
        with patch("subprocess.run", return_value=failed), \
             patch.object(mcp_server, "_run_verify") as mock_verify:
            result = mcp_server.set_up_capability("photo-demo", "file-storage")
        mock_verify.assert_not_called()
        self.assertEqual(result["gate_result"], "FAIL")
        self.assertNotIn("s3", result["founder_message"].lower())
        self.assertIn("BucketAlreadyExists", result["_diagnostic_for_you_the_calling_agent"]["output_or_error"])
        self.assertNotIn("photo-demo", mcp_server._load_state())

    def test_already_recorded_capability_is_reverified_not_created_again(self):
        created = subprocess.CompletedProcess("", 0, stdout="photo-demo-files\n", stderr="")
        with patch("subprocess.run", return_value=created), \
             patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            mcp_server.set_up_capability("photo-demo", "file-storage")
        with patch("subprocess.run") as mock_run, \
             patch.object(mcp_server, "_run_verify", return_value=(True, "ok")) as mock_verify:
            result = mcp_server.set_up_capability("photo-demo", "file-storage")
        mock_run.assert_not_called()
        mock_verify.assert_called_once()
        self.assertEqual(result["gate_result"], "PASS")

    def test_unknown_capability_is_refused_in_plain_language(self):
        with patch("subprocess.run") as mock_run:
            result = mcp_server.set_up_capability("photo-demo", "real-time-chat")
        mock_run.assert_not_called()
        self.assertEqual(result["gate_result"], "FAIL")
        self.assertNotIn("_diagnostic_for_you_the_calling_agent", result)


@unittest.skipUnless(os.environ.get("SERVICE_BUDDY_LIVE") == "1", "needs a running Floci; set SERVICE_BUDDY_LIVE=1")
class LiveEveryCapabilityTest(IsolatedStateTest):
    def test_every_capability_sets_up_and_verifies_against_real_floci(self):
        env = mcp_server.create_environment(f"live-{secrets.token_hex(2)}")
        for cap in CATALOG["capabilities"]:
            with self.subTest(capability=cap["id"]):
                result = mcp_server.set_up_capability(env["app_context"], cap["id"])
                self.assertEqual(result["gate_result"], "PASS", result)
                self.assertTrue(result["founder_message"].startswith("Done and verified"))


if __name__ == "__main__":
    unittest.main()
