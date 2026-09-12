#!/usr/bin/env python3
"""Unit tests for environments_store.py's load/save helpers and shared lock."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store


class EnvironmentsStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.tmpdir.name) / "environments.json"
        self.lock_path = Path(self.tmpdir.name) / ".environments.lock"
        self._patched_path = patch.object(environments_store, "ENVIRONMENTS_PATH", self.env_path)
        self._patched_lock = patch.object(
            environments_store, "ENVIRONMENTS_LOCK_PATH", self.lock_path
        )
        self._patched_path.start()
        self._patched_lock.start()

    def tearDown(self):
        self._patched_path.stop()
        self._patched_lock.stop()
        self.tmpdir.cleanup()

    def test_load_returns_empty_dict_when_file_missing(self):
        self.assertEqual(environments_store.load_environments(), {})

    def test_save_then_load_round_trips(self):
        environments_store.save_environments({"alpha": {"app_context": "alpha-123-abcd"}})
        self.assertEqual(
            environments_store.load_environments(),
            {"alpha": {"app_context": "alpha-123-abcd"}},
        )

    def test_environments_lock_excludes_concurrent_writers(self):
        """A read-modify-write cycle held under environments_lock() must not lose an update
        from a concurrent writer -- the same failure mode GH-24 closed for stack-state.json."""

        def add_environment(name: str):
            with environments_store.environments_lock():
                envs = environments_store.load_environments()
                envs[name] = {"app_context": f"{name}-0"}
                environments_store.save_environments(envs)

        threads = [threading.Thread(target=add_environment, args=(f"env-{i}",)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        final = environments_store.load_environments()
        self.assertEqual(len(final), 8, f"expected 8 environments, got {list(final.keys())}")


if __name__ == "__main__":
    unittest.main()
