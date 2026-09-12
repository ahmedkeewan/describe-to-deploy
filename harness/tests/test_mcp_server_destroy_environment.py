#!/usr/bin/env python3
"""Unit tests for mcp_server.py's destroy_environment tool. Requires the `mcp` package -- run
via harness/.venv, same as test_mcp_server_environments.py."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server


class DestroyEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.tmpdir.name) / "environments.json"
        self.env_lock_path = Path(self.tmpdir.name) / ".environments.lock"
        self.state_path = Path(self.tmpdir.name) / "stack-state.json"
        self.state_lock_path = Path(self.tmpdir.name) / ".stack-state.lock"
        self._patches = [
            patch.object(environments_store, "ENVIRONMENTS_PATH", self.env_path),
            patch.object(environments_store, "ENVIRONMENTS_LOCK_PATH", self.env_lock_path),
            patch.object(mcp_server, "STATE_PATH", self.state_path),
            patch.object(mcp_server, "STATE_LOCK_PATH", self.state_lock_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_destroy_removes_environments_entry_and_returns_released_port(self):
        created = mcp_server.create_environment("alpha")
        result = mcp_server.destroy_environment("alpha")
        self.assertEqual(result, {"name": "alpha", "released_port": created["board_port"]})
        self.assertNotIn("alpha", environments_store.load_environments())

    def test_destroy_removes_matching_stack_state_entry(self):
        created = mcp_server.create_environment("alpha")
        app_context = created["app_context"]
        # Seed a stack-state.json entry directly, the way record_provisioned would.
        state = mcp_server._load_state()
        state[app_context] = {"created": "now", "capabilities": {"file-storage": {}}}
        mcp_server._save_state(state)

        mcp_server.destroy_environment("alpha")

        self.assertNotIn(app_context, mcp_server._load_state())

    def test_destroying_unknown_name_returns_error_not_a_crash(self):
        result = mcp_server.destroy_environment("does-not-exist")
        self.assertIn("error", result)

    def test_released_port_is_available_to_a_later_create(self):
        first = mcp_server.create_environment("alpha")
        mcp_server.destroy_environment("alpha")
        second = mcp_server.create_environment("beta")
        self.assertEqual(second["board_port"], first["board_port"])

    def test_destroy_does_not_affect_other_environments(self):
        mcp_server.create_environment("alpha")
        beta = mcp_server.create_environment("beta")

        mcp_server.destroy_environment("alpha")

        remaining = environments_store.load_environments()
        self.assertNotIn("alpha", remaining)
        self.assertIn("beta", remaining)
        self.assertEqual(remaining["beta"]["app_context"], beta["app_context"])


if __name__ == "__main__":
    unittest.main()
