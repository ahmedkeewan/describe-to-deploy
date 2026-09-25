#!/usr/bin/env python3
"""Regression test for GH-95: describe_environment() prefers pricing.real_monthly_estimate()
when it returns a value, and falls back to the hand-written APPROX_MONTHLY_COST_USD estimate
when it returns None (unknown service, ambiguous match, or network/parse failure). Mocks
pricing.real_monthly_estimate directly -- no real network calls here; see test_pricing.py for
the module's own internal logic tests, verified against live data during development."""
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import mcp_server


class DescribeEnvironmentRealPricingTests(unittest.TestCase):
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
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def _provision(self, name, capability_id):
        env = mcp_server.create_environment(name)
        app_context = env["app_context"]
        resource_name = f"{app_context}-x"
        with unittest.mock.patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            mcp_server.record_provisioned(app_context, capability_id, resource_name)
        return app_context

    def test_uses_real_pricing_when_available(self):
        self._provision("app-a", "structured-data")  # aws_service: dynamodb
        fake_real_result = {
            "monthly_usd": 0.0,
            "assumption": "1 GB of table storage/month",
            "source": "AWS Price List (public, unauthenticated), us-east-1",
        }
        with unittest.mock.patch.object(
            mcp_server.pricing, "real_monthly_estimate", return_value=fake_real_result
        ):
            result = mcp_server.describe_environment("app-a")
        item = result["capabilities"][0]
        self.assertIn("$0.0", item["approx_monthly_cost_usd"])
        self.assertIn("1 GB of table storage/month", item["approx_monthly_cost_usd"])
        self.assertEqual(item["cost_source"], fake_real_result["source"])

    def test_falls_back_to_hardcoded_estimate_when_real_pricing_returns_none(self):
        self._provision("app-a", "structured-data")
        with unittest.mock.patch.object(
            mcp_server.pricing, "real_monthly_estimate", return_value=None
        ):
            result = mcp_server.describe_environment("app-a")
        item = result["capabilities"][0]
        self.assertEqual(item["approx_monthly_cost_usd"], mcp_server.APPROX_MONTHLY_COST_USD["dynamodb"])
        self.assertIn("hand-written estimate", item["cost_source"])

    def test_falls_back_cleanly_for_a_service_with_no_real_pricing_config(self):
        # "search" (aws_service: es) is not one of the six real-pricing-covered services.
        self._provision("app-a", "search")
        result = mcp_server.describe_environment("app-a")
        item = result["capabilities"][0]
        self.assertEqual(item["aws_service"], "es")
        self.assertIn("hand-written estimate", item["cost_source"])


if __name__ == "__main__":
    unittest.main()
