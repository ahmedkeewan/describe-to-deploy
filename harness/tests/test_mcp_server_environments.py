#!/usr/bin/env python3
"""Unit tests for mcp_server.py's create_environment tool.

Requires the `mcp` package (see harness/requirements.txt / harness/.venv) since mcp_server.py
imports mcp.server.mcpserver at module load time -- run these via the project's venv, same as
any live run of the server itself."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server


class CreateEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.tmpdir.name) / "environments.json"
        self.lock_path = Path(self.tmpdir.name) / ".environments.lock"
        self._patches = [
            patch.object(environments_store, "ENVIRONMENTS_PATH", self.env_path),
            patch.object(environments_store, "ENVIRONMENTS_LOCK_PATH", self.lock_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_fresh_name_returns_app_context_and_port(self):
        result = mcp_server.create_environment("alpha")
        self.assertIn("app_context", result)
        self.assertIn("board_port", result)
        self.assertTrue(result["app_context"].startswith("alpha-"))
        self.assertEqual(result["board_port"], mcp_server.BOARD_PORT_RANGE.start)

    def test_duplicate_name_is_rejected_without_writing_state(self):
        first = mcp_server.create_environment("alpha")
        second = mcp_server.create_environment("alpha")
        self.assertIn("error", second)
        # The original entry must be untouched -- a duplicate call must not overwrite it.
        envs = environments_store.load_environments()
        self.assertEqual(envs["alpha"]["app_context"], first["app_context"])

    def test_invalid_name_is_rejected(self):
        for bad_name in ["AB", "ab", "has space", "has_underscore", "x" * 41, "has::colon"]:
            result = mcp_server.create_environment(bad_name)
            self.assertIn("error", result, f"expected an error for name={bad_name!r}")

    def test_two_environments_get_different_ports(self):
        first = mcp_server.create_environment("alpha")
        second = mcp_server.create_environment("beta")
        self.assertNotEqual(first["board_port"], second["board_port"])

    def test_reused_name_after_destroy_gets_a_different_app_context(self):
        """Guards the exact residual design review flagged: a same-second destroy-then-recreate
        of the same name must never mint the same app_context."""
        first = mcp_server.create_environment("alpha")
        envs = environments_store.load_environments()
        del envs["alpha"]
        environments_store.save_environments(envs)

        second = mcp_server.create_environment("alpha")
        self.assertNotEqual(first["app_context"], second["app_context"])

    def test_concurrent_creates_with_different_names_never_collide_on_port(self):
        results = {}
        lock = threading.Lock()

        def create(name):
            result = mcp_server.create_environment(name)
            with lock:
                results[name] = result

        names = [f"env-{i}" for i in range(6)]
        threads = [threading.Thread(target=create, args=(n,)) for n in names]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        ports = [r["board_port"] for r in results.values()]
        self.assertEqual(len(ports), len(set(ports)), f"port collision among {results}")


if __name__ == "__main__":
    unittest.main()
