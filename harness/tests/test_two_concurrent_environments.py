#!/usr/bin/env python3
"""Integration test for GH-37: the feature's actual end-to-end goal. Two environments, the same
capability_id provisioned in both concurrently, through the real create_environment ->
get_provisioning_recipe -> record_provisioned flow -- not just the individual pieces each
already have unit tests for (create_environment's port uniqueness, record_provisioned's
concurrency safety, the resource-name binding's bypass resistance). Requires the `mcp` package
-- run via harness/.venv."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server


class TwoConcurrentEnvironmentsTests(unittest.TestCase):
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
            # No live Floci in a unit test -- always PASS, so this exercises the harness's own
            # concurrency/binding correctness, not infra availability.
            patch.object(mcp_server, "_run_verify", return_value=(True, "ok")),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_same_capability_provisioned_concurrently_in_two_environments_no_collision(self):
        alpha = mcp_server.create_environment("alpha")
        beta = mcp_server.create_environment("beta")

        # AC-2: distinct board ports, checked immediately -- this is deterministic (GH-26's own
        # locked port scan), not a race, but worth asserting explicitly in the end-to-end test.
        self.assertNotEqual(
            alpha["board_port"], beta["board_port"], "environments collided on board_port"
        )

        results = {}
        lock = threading.Lock()

        def provision(name, env):
            app_context = env["app_context"]
            resource_name = f"{app_context}::photos"

            # Mirrors the real calling-agent flow: get the recipe first, then record.
            recipe = mcp_server.get_provisioning_recipe(
                "file-storage", resource_name, app_context=app_context
            )
            record = mcp_server.record_provisioned(app_context, "file-storage", resource_name)
            with lock:
                results[name] = {"recipe": recipe, "record": record, "resource_name": resource_name}

        threads = [
            threading.Thread(target=provision, args=("alpha", alpha)),
            threading.Thread(target=provision, args=("beta", beta)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # AC-1: both environments end up with independently correct, verified state.
        for name in ("alpha", "beta"):
            self.assertNotIn("error", results[name]["recipe"], f"{name}'s recipe call failed")
            self.assertEqual(
                results[name]["record"]["gate_result"], "PASS", f"{name} did not PASS"
            )

        state = mcp_server._load_state()
        alpha_entry = state[alpha["app_context"]]["capabilities"]["file-storage"]
        beta_entry = state[beta["app_context"]]["capabilities"]["file-storage"]

        self.assertEqual(alpha_entry["resource_name"], results["alpha"]["resource_name"])
        self.assertEqual(beta_entry["resource_name"], results["beta"]["resource_name"])
        # Neither environment's resource_name leaked into the other's recorded state.
        self.assertNotEqual(alpha_entry["resource_name"], beta_entry["resource_name"])
        self.assertEqual(alpha_entry["last_gate_result"], "PASS")
        self.assertEqual(beta_entry["last_gate_result"], "PASS")

        # environments.json itself still shows both, independently, with the original ports.
        envs = environments_store.load_environments()
        self.assertEqual(envs["alpha"]["board_port"], alpha["board_port"])
        self.assertEqual(envs["beta"]["board_port"], beta["board_port"])


if __name__ == "__main__":
    unittest.main()
