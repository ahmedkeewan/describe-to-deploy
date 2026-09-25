#!/usr/bin/env python3
"""record_provisioned()'s FAIL-path diagnostic field carries real AWS/Floci-jargon-capable content
(an ARN, a bucket/table name, raw CLI output). It has an inline "Not for the founder" label at
runtime, but that isn't enough on its own -- the tool's own docstring, and the module's
jargon-boundary docstring, must also say so explicitly, matching the rigor applied to the
whole-tool exceptions. This test pins that so it can't quietly regress."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_server


class RecordProvisionedDiagnosticFieldDocsTests(unittest.TestCase):
    def test_own_docstring_documents_the_diagnostic_field_is_not_founder_safe(self):
        doc = (mcp_server.record_provisioned.__doc__ or "").lower()
        self.assertIn("_diagnostic_for_you_the_calling_agent", doc)
        self.assertIn("founder", doc)
        self.assertIn("not founder-safe", doc)

    def test_module_docstring_documents_the_narrower_field_level_exception(self):
        module_doc = mcp_server.__doc__
        self.assertIn("_diagnostic_for_you_the_calling_agent", module_doc)
        self.assertIn("record_provisioned", module_doc)

    def test_diagnostic_field_is_absent_on_pass(self):
        with patch.object(mcp_server, "_run_verify", return_value=(True, "ok")), \
             patch.object(mcp_server, "locked"), \
             patch.object(mcp_server, "_load_state", return_value={}), \
             patch.object(mcp_server, "_save_state"):
            result = mcp_server.record_provisioned("app-x", "file-storage", "app-x-photos")
        self.assertEqual(result["gate_result"], "PASS")
        self.assertNotIn("_diagnostic_for_you_the_calling_agent", result)

    def test_diagnostic_field_is_present_and_labeled_on_fail(self):
        with patch.object(mcp_server, "_run_verify", return_value=(False, "not found")):
            result = mcp_server.record_provisioned("app-x", "file-storage", "app-x-photos")
        self.assertEqual(result["gate_result"], "FAIL")
        diagnostic = result["_diagnostic_for_you_the_calling_agent"]
        self.assertIn("Not for the founder", diagnostic["note"])


if __name__ == "__main__":
    unittest.main()
