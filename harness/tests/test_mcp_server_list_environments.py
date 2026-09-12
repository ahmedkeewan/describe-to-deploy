#!/usr/bin/env python3
"""Unit tests for mcp_server.py's list_environments tool. Requires the `mcp` package -- run via
harness/.venv, same as the other mcp_server_* test modules."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server


class ListEnvironmentsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.tmpdir.name) / "environments.json"
        self.env_lock_path = Path(self.tmpdir.name) / ".environments.lock"
        self._patches = [
            patch.object(environments_store, "ENVIRONMENTS_PATH", self.env_path),
            patch.object(environments_store, "ENVIRONMENTS_LOCK_PATH", self.env_lock_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_returns_empty_list_when_no_environments_registered(self):
        self.assertEqual(mcp_server.list_environments(), [])

    def test_returns_accurate_list_matching_environments_json(self):
        created_alpha = mcp_server.create_environment("alpha")
        created_beta = mcp_server.create_environment("beta")

        result = mcp_server.list_environments()

        by_name = {entry["name"]: entry for entry in result}
        self.assertEqual(set(by_name), {"alpha", "beta"})
        self.assertEqual(by_name["alpha"]["app_context"], created_alpha["app_context"])
        self.assertEqual(by_name["alpha"]["board_port"], created_alpha["board_port"])
        self.assertIn("created", by_name["alpha"])
        self.assertEqual(by_name["beta"]["app_context"], created_beta["app_context"])

    def test_reflects_destroy(self):
        mcp_server.create_environment("alpha")
        mcp_server.create_environment("beta")
        mcp_server.destroy_environment("alpha")

        result = mcp_server.list_environments()

        self.assertEqual([entry["name"] for entry in result], ["beta"])


if __name__ == "__main__":
    unittest.main()
