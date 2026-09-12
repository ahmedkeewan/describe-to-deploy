#!/usr/bin/env python3
"""Unit tests for GH-29's resource_name-to-environment binding.

Covers _resource_name_binding_error directly (the exact-match logic and the specific
prefix-but-not-equal bypass that broke an earlier, naive version of this fix during design
review), plus integration-level checks that get_provisioning_recipe and record_provisioned
actually enforce it before doing anything else."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server


class ResourceNameBindingErrorTests(unittest.TestCase):
    """Direct tests of _resource_name_binding_error, isolated from any file I/O."""

    def setUp(self):
        self._patch = patch.object(
            mcp_server, "_registered_app_contexts", return_value={"alpha-1000-aaaa"}
        )
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def test_exact_match_is_allowed(self):
        self.assertIsNone(
            mcp_server._resource_name_binding_error("alpha-1000-aaaa", "alpha-1000-aaaa::photos")
        )

    def test_unregistered_app_context_is_unaffected(self):
        # "beta-2000-bbbb" is not in the registered set -- today's default usage, untouched.
        self.assertIsNone(
            mcp_server._resource_name_binding_error("beta-2000-bbbb", "anything-goes")
        )

    def test_none_app_context_is_unaffected(self):
        self.assertIsNone(mcp_server._resource_name_binding_error(None, "anything-goes"))

    def test_missing_separator_is_rejected(self):
        result = mcp_server._resource_name_binding_error("alpha-1000-aaaa", "alpha-1000-aaaaphotos")
        self.assertIsNotNone(result)
        self.assertIn("error", result)

    def test_wrong_app_context_is_rejected(self):
        result = mcp_server._resource_name_binding_error("alpha-1000-aaaa", "beta-2000-bbbb::photos")
        self.assertIsNotNone(result)

    def test_prefix_but_not_equal_bypass_is_rejected(self):
        """The exact bug design review found in the naive `startswith` version: an environment
        named after another environment's full app_context makes a prefix check pass across
        environments. A resource_name whose pre-:: segment merely STARTS WITH (but isn't equal
        to) the registered app_context must still be rejected."""
        # "alpha-1000-aaaa-9999-bbbb" starts with "alpha-1000-aaaa" but is not equal to it.
        result = mcp_server._resource_name_binding_error(
            "alpha-1000-aaaa", "alpha-1000-aaaa-9999-bbbb::photos"
        )
        self.assertIsNotNone(result)

    def test_reversed_bypass_is_also_rejected(self):
        """The mirror case: the registered app_context is longer than the resource_name's
        pre-:: segment (a truncated match), which must also fail exact equality."""
        result = mcp_server._resource_name_binding_error("alpha-1000-aaaa", "alpha-1000::photos")
        self.assertIsNotNone(result)


class GetProvisioningRecipeBindingTests(unittest.TestCase):
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
        self.env = mcp_server.create_environment("alpha")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_correctly_prefixed_resource_name_proceeds(self):
        result = mcp_server.get_provisioning_recipe(
            "file-storage",
            f"{self.env['app_context']}::photos",
            app_context=self.env["app_context"],
        )
        self.assertNotIn("error", result)
        self.assertIn("steps", result)

    def test_mismatched_resource_name_is_rejected_before_returning_steps(self):
        result = mcp_server.get_provisioning_recipe(
            "file-storage", "someone-elses-bucket", app_context=self.env["app_context"]
        )
        self.assertIn("error", result)
        self.assertNotIn("steps", result)


class RecordProvisionedBindingTests(unittest.TestCase):
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
        self.env = mcp_server.create_environment("alpha")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_mismatched_resource_name_never_reaches_verify(self):
        with patch.object(mcp_server, "_run_verify") as mock_verify:
            result = mcp_server.record_provisioned(
                self.env["app_context"], "file-storage", "someone-elses-bucket"
            )
        mock_verify.assert_not_called()
        self.assertIn("error", result)

    def test_correctly_prefixed_resource_name_reaches_verify(self):
        resource_name = f"{self.env['app_context']}::photos"
        with patch.object(mcp_server, "_run_verify", return_value=(True, "ok")) as mock_verify:
            result = mcp_server.record_provisioned(
                self.env["app_context"], "file-storage", resource_name
            )
        mock_verify.assert_called_once()
        self.assertEqual(result["gate_result"], "PASS")


if __name__ == "__main__":
    unittest.main()
