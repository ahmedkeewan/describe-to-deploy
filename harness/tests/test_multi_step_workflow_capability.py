#!/usr/bin/env python3
"""Regression test for GH-66: the new multi-step-workflow (Step Functions) capability entry.
Its verify.cli was manually round-trip tested against live Floci (create -> execute -> poll to
SUCCEEDED, plus a failure case with a nonexistent state machine ARN) -- this test pins the
catalog entry's shape and the placeholder substitution, not a live re-run of that check."""
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_server

CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "catalog" / "capabilities.json"


class MultiStepWorkflowCapabilityTests(unittest.TestCase):
    def setUp(self):
        catalog = json.loads(CATALOG_PATH.read_text())
        self.by_id = {c["id"]: c for c in catalog["capabilities"]}

    def test_capability_exists_with_required_schema_fields(self):
        cap = self.by_id.get("multi-step-workflow")
        self.assertIsNotNone(cap, "multi-step-workflow capability is missing from the catalog")
        for field in ("phrases", "founder_description", "aws_service", "provision", "verify",
                      "wiring", "cloud_equivalent_note"):
            self.assertIn(field, cap)

    def test_founder_description_has_no_infra_jargon(self):
        cap = self.by_id["multi-step-workflow"]
        desc = cap["founder_description"].lower()
        for jargon in ("aws", "arn", "stepfunctions", "step functions", "state machine"):
            self.assertNotIn(jargon, desc, f"founder_description leaks jargon: {jargon!r}")

    def test_verify_cli_placeholder_is_substituted(self):
        cap = self.by_id["multi-step-workflow"]
        # _run_verify's substitution chain is private to mcp_server.py; exercise it the same way
        # every other capability's verify.cli is exercised, through _run_verify itself, rather
        # than depending on a specific helper function's name (which is refactored separately in
        # GH-77 / PR #78).
        resource_name = "arn:aws:states:us-east-1:000000000000:stateMachine:my-sm"
        with unittest.mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = unittest.mock.Mock(returncode=0, stdout="", stderr="")
            mcp_server._run_verify(cap["verify"]["cli"], resource_name)
        ran_cmd = mock_run.call_args[0][0]
        self.assertNotIn("<stateMachineArn>", ran_cmd)
        self.assertIn(resource_name, ran_cmd)

    def test_state_fields_match_the_placeholder_used_in_verify_cli(self):
        cap = self.by_id["multi-step-workflow"]
        self.assertIn("stateMachineArn", cap["provision"]["state_fields"])
        self.assertIn("<stateMachineArn>", cap["verify"]["cli"])


if __name__ == "__main__":
    unittest.main()
