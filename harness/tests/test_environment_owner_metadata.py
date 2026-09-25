#!/usr/bin/env python3
"""Regression test for GH-69 / AgDR-0004: create_environment() accepts an optional, purely
descriptive `owner` field, surfaced by list_environments() -- and explicitly NOT enforced as a
permission check anywhere."""
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server


class EnvironmentOwnerMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self._patches = [
            unittest.mock.patch.object(
                environments_store, "ENVIRONMENTS_PATH", Path(self.tmpdir.name) / "environments.json"
            ),
            unittest.mock.patch.object(
                environments_store, "ENVIRONMENTS_LOCK_PATH", Path(self.tmpdir.name) / ".environments.lock"
            ),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_owner_defaults_to_none_when_not_provided(self):
        mcp_server.create_environment("app-a")
        envs = mcp_server.list_environments()
        self.assertIsNone(envs[0]["owner"])

    def test_owner_is_recorded_and_surfaced_by_list_environments(self):
        mcp_server.create_environment("app-a", owner="alice")
        envs = mcp_server.list_environments()
        self.assertEqual(envs[0]["owner"], "alice")

    def test_owner_is_not_a_permission_check(self):
        # Explicit regression guard for AgDR-0004's decision: a DIFFERENT caller (no owner
        # identity concept exists at all) can still fully act on an environment regardless of
        # its recorded owner. There is no code path that could even check "who is calling" --
        # this test documents that absence rather than exercising a check that doesn't exist.
        mcp_server.create_environment("app-a", owner="alice")
        # destroy_environment takes no caller-identity argument of any kind -- anyone who knows
        # the environment name can destroy it, regardless of who "owns" it.
        result = mcp_server.destroy_environment("app-a")
        self.assertNotIn("error", result)


if __name__ == "__main__":
    unittest.main()
