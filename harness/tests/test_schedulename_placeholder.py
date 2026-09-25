#!/usr/bin/env python3
"""Regression test for GH-77: catalog verify.cli placeholders were substituted via a hardcoded
per-name replace() chain that had to be updated by hand for every new placeholder. This missed
<scheduleName> first, then review of the first fix found <apiId> missing too -- the same bug
class, a second time, in the same hardcoded-list mechanism. The real fix (not just adding the two
missing names) is a general regex substitution: every capability's verify.cli uses at most one
placeholder, always meaning the one real resource being checked, so any <word> token can be
substituted with resource_name with no per-name list to keep in sync ever again.

Confirmed live against Floci before fixing: `aws scheduler get-schedule --name <scheduleName>`
failed with a ValidationException instead of resolving to the real resource."""
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_server
import verify_gate

CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "catalog" / "capabilities.json"


class GeneralPlaceholderSubstitutionTests(unittest.TestCase):
    def test_mcp_server_substitutes_any_placeholder_token(self):
        for placeholder, value in [
            ("<scheduleName>", "my-real-schedule"),
            ("<apiId>", "abc123"),
            ("<somethingBrandNew>", "future-resource"),
        ]:
            cmd = mcp_server._substitute_placeholders(f"aws x --name {placeholder}", value)
            self.assertEqual(cmd, f"aws x --name {value}")

    def test_verify_gate_run_check_substitutes_any_placeholder_token(self):
        # run_check shells out; exercise its substitution via a mocked subprocess.run so this
        # test doesn't need live Floci.
        with unittest.mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = unittest.mock.Mock(returncode=0, stdout="", stderr="")
            verify_gate.run_check("aws scheduler get-schedule --name <scheduleName>", "real-name")
        ran_cmd = mock_run.call_args[0][0]
        self.assertNotIn("<scheduleName>", ran_cmd)
        self.assertIn("real-name", ran_cmd)

    def test_diagnostic_field_uses_the_same_shared_helper(self):
        # The FAIL-path diagnostic field must use _substitute_placeholders too, not a second
        # hand-maintained copy of the chain -- that duplication is exactly what caused GH-77.
        import inspect
        source = inspect.getsource(mcp_server.record_provisioned)
        self.assertIn("_substitute_placeholders(cap[\"verify\"][\"cli\"], resource_name)", source)

    def test_get_provisioning_recipe_uses_the_same_shared_helper(self):
        # A third, independent copy of this chain lived here (a for-loop over a placeholder
        # tuple, also missing scheduleName) -- caught in review of the first fix.
        import inspect
        source = inspect.getsource(mcp_server.get_provisioning_recipe)
        self.assertIn("_substitute_placeholders(cap[\"verify\"][\"cli\"], resource_name)", source)

    def test_get_provisioning_recipe_substitutes_schedulename_in_preview(self):
        with unittest.mock.patch.object(
            mcp_server, "_load_catalog",
            return_value={
                "scheduled-task": {
                    "verify": {"cli": "aws scheduler get-schedule --name <scheduleName>"},
                    "founder_description": "x", "aws_service": "scheduler",
                    "provision": {"steps": []},
                }
            },
        ):
            result = mcp_server.get_provisioning_recipe("scheduled-task", "my-real-schedule")
        self.assertNotIn("<scheduleName>", result["verify_command_preview"])
        self.assertIn("my-real-schedule", result["verify_command_preview"])

    def test_every_catalog_capability_verify_cli_uses_at_most_one_placeholder(self):
        # Pins the assumption the regex substitution relies on: no capability combines two
        # distinct placeholders in one verify.cli command. If this ever stops being true, the
        # blanket substitution below would silently substitute the wrong value into one of them.
        import re
        catalog = json.loads(CATALOG_PATH.read_text())
        for cap in catalog["capabilities"]:
            placeholders = set(re.findall(r"<\w+>", cap["verify"]["cli"]))
            self.assertLessEqual(
                len(placeholders), 1,
                f"{cap['id']}'s verify.cli combines multiple placeholders: {placeholders} -- "
                "the blanket <word> substitution in _substitute_placeholders/run_check assumes "
                "at most one per command and would need reworking for this capability.",
            )

    def test_apiid_is_substituted_end_to_end_via_backend_api_capability(self):
        catalog = json.loads(CATALOG_PATH.read_text())
        backend_api = next(c for c in catalog["capabilities"] if c["id"] == "backend-api")
        cmd = mcp_server._substitute_placeholders(backend_api["verify"]["cli"], "my-api-id")
        self.assertNotIn("<apiId>", cmd)
        self.assertIn("my-api-id", cmd)

    def test_resource_name_with_backslash_backreference_is_treated_literally(self):
        # re.sub's replacement is a STRING here, not a function -- if a plain string arg were used
        # instead of a replacement function, \1 and \g<0> in resource_name would be interpreted
        # as regex backreferences instead of literal text: \1 raises re.error (no such group),
        # and \g<0> silently reinjects the original matched placeholder text. Found in review.
        cmd = mcp_server._substitute_placeholders(
            "aws x --name <scheduleName>", "my-app-sched\\1ule"
        )
        self.assertEqual(cmd, "aws x --name my-app-sched\\1ule")

        cmd2 = mcp_server._substitute_placeholders(
            "aws x --name <scheduleName>", "foo\\g<0>bar"
        )
        self.assertEqual(cmd2, "aws x --name foo\\g<0>bar")

    def test_verify_gate_resource_name_with_backslash_is_also_treated_literally(self):
        with unittest.mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = unittest.mock.Mock(returncode=0, stdout="", stderr="")
            verify_gate.run_check("aws x --name <scheduleName>", "sched\\1ule")
        ran_cmd = mock_run.call_args[0][0]
        self.assertEqual(ran_cmd, "aws x --name sched\\1ule")


if __name__ == "__main__":
    unittest.main()
