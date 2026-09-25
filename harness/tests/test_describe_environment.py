#!/usr/bin/env python3
"""Regression test for GH-68 / GH-95: describe_environment() reports each of an environment's
provisioned capabilities alongside a monthly cost estimate, built from catalog/capabilities.json's
existing aws_service/cloud_equivalent_note fields. GH-95 added a live-AWS-pricing path for six
capabilities (pricing.real_monthly_estimate()); every other capability, and any failure of that
live lookup, falls back to the hand-written APPROX_MONTHLY_COST_USD estimates.

pricing.real_monthly_estimate is mocked to None by default in every test here (forcing the
fallback path) so this suite never makes a real network call -- see
test_describe_environment_real_pricing.py for tests that exercise the real-pricing integration
with a mocked return value."""
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server


class DescribeEnvironmentTests(unittest.TestCase):
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
                mcp_server, "STATE_PATH", Path(self.tmpdir.name) / "stack-state.json"
            ),
            unittest.mock.patch.object(
                mcp_server, "STATE_LOCK_PATH", Path(self.tmpdir.name) / ".stack-state.lock"
            ),
            unittest.mock.patch.object(mcp_server.pricing, "real_monthly_estimate", return_value=None),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_unknown_environment_returns_error(self):
        result = mcp_server.describe_environment("does-not-exist")
        self.assertIn("error", result)

    def test_environment_with_no_capabilities_returns_empty_list(self):
        mcp_server.create_environment("app-a")
        result = mcp_server.describe_environment("app-a")
        self.assertEqual(result["capabilities"], [])
        self.assertIn("caveat", result)

    def test_reports_cost_estimate_and_cloud_equivalent_note_per_capability(self):
        env = mcp_server.create_environment("app-a")
        app_context = env["app_context"]
        resource_name = f"{app_context}-photos"
        with unittest.mock.patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            mcp_server.record_provisioned(app_context, "file-storage", resource_name)

        result = mcp_server.describe_environment("app-a")
        self.assertEqual(len(result["capabilities"]), 1)
        item = result["capabilities"][0]
        self.assertEqual(item["capability_id"], "file-storage")
        self.assertEqual(item["aws_service"], "s3")
        self.assertIn("approx_monthly_cost_usd", item)
        self.assertIn("cloud_equivalent_note", item)
        self.assertEqual(
            item["cost_source"], "hand-written estimate (no live AWS pricing match for this service)"
        )

    def test_every_capability_in_the_catalog_has_a_cost_estimate(self):
        # Pins that APPROX_MONTHLY_COST_USD stays in sync with the catalog -- a capability with
        # no entry would silently fall back to "no estimate available," which is a real gap
        # worth a test failure, not a silent miss.
        catalog = mcp_server._load_catalog()
        for capability_id, cap in catalog.items():
            self.assertIn(
                cap["aws_service"],
                mcp_server.APPROX_MONTHLY_COST_USD,
                f"{capability_id} (aws_service={cap['aws_service']}) has no cost estimate",
            )

    def test_cost_estimates_are_explicitly_labeled_as_estimates(self):
        for estimate in mcp_server.APPROX_MONTHLY_COST_USD.values():
            self.assertTrue(estimate.startswith("~"), f"not clearly an estimate: {estimate!r}")

    def test_skips_a_capability_no_longer_in_the_catalog(self):
        env = mcp_server.create_environment("app-a")
        app_context = env["app_context"]
        resource_name = f"{app_context}-photos"
        with unittest.mock.patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            mcp_server.record_provisioned(app_context, "file-storage", resource_name)

        with unittest.mock.patch.object(mcp_server, "_load_catalog", return_value={}):
            result = mcp_server.describe_environment("app-a")
        self.assertEqual(result["capabilities"], [])


if __name__ == "__main__":
    unittest.main()
