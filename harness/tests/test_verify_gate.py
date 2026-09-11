#!/usr/bin/env python3
"""Unit tests for verify_gate.py's plan-handling logic, with run_check mocked so no live Floci
is required. The real subprocess call in run_check is out of scope for a unit test -- see
tasks/README.md for how a live scoring pass exercises it end to end."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verify_gate


class LoadCatalogByIdTests(unittest.TestCase):
    def test_indexes_by_capability_id(self):
        catalog = verify_gate.load_catalog_by_id()
        self.assertIn("file-storage", catalog)
        self.assertEqual(catalog["file-storage"]["id"], "file-storage")


class MainGateTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.plan_path = Path(self.tmpdir.name) / "stack-plan.json"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run_main(self, plan: dict) -> int:
        self.plan_path.write_text(json.dumps(plan))
        with patch.object(sys, "argv", ["verify_gate.py", str(self.plan_path)]):
            with self.assertRaises(SystemExit) as ctx:
                verify_gate.main()
        return ctx.exception.code

    def test_fallback_plan_passes_without_checking_anything(self):
        with patch.object(verify_gate, "run_check") as mock_run_check:
            code = self._run_main({"fallback": "no catalog match"})
        self.assertEqual(code, 0)
        mock_run_check.assert_not_called()

    def test_unknown_capability_fails_the_gate(self):
        plan = {
            "matched_capabilities": [
                {"capability_id": "does-not-exist", "resource_name": "whatever"}
            ]
        }
        code = self._run_main(plan)
        self.assertEqual(code, 1)

    def test_all_capabilities_passing_exits_zero(self):
        plan = {
            "matched_capabilities": [
                {"capability_id": "file-storage", "resource_name": "photo-bucket"}
            ]
        }
        with patch.object(verify_gate, "run_check", return_value=(True, "ok")):
            code = self._run_main(plan)
        self.assertEqual(code, 0)

    def test_one_failing_capability_fails_the_whole_gate(self):
        plan = {
            "matched_capabilities": [
                {"capability_id": "file-storage", "resource_name": "photo-bucket"},
                {"capability_id": "structured-data", "resource_name": "users-table"},
            ]
        }
        with patch.object(
            verify_gate, "run_check", side_effect=[(True, "ok"), (False, "not found")]
        ):
            code = self._run_main(plan)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
