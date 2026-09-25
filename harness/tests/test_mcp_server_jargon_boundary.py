#!/usr/bin/env python3
"""Regression test for GH-30: the module docstring's founder-safe exception list must name
every tool that actually returns non-founder-safe output. This exact claim already went stale
once (get_provisioning_recipe was already returning infra detail before the module docstring
said so) -- this test exists so the next new non-founder-safe tool doesn't repeat that."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_server


NON_FOUNDER_SAFE_TOOLS = [
    "whats_needed_to_go_live",
    "get_provisioning_recipe",
    "create_environment",
    "destroy_environment",
    "list_environments",
    "get_verification_history",
]

# whats_needed_to_go_live predates GH-30 and documents its non-founder audience without the
# literal word "founder" ("technical audience", "not routine conversation") -- already adequate,
# left alone rather than reworded just to satisfy this test's string match.
TOOLS_REQUIRING_EXPLICIT_FOUNDER_WORDING = [
    "get_provisioning_recipe",
    "create_environment",
    "destroy_environment",
    "list_environments",
    "get_verification_history",
]


class JargonBoundaryDocstringTests(unittest.TestCase):
    def test_module_docstring_names_every_non_founder_safe_tool(self):
        module_doc = mcp_server.__doc__
        for tool_name in NON_FOUNDER_SAFE_TOOLS:
            self.assertIn(
                tool_name,
                module_doc,
                f"module docstring's founder-safe exception list is missing {tool_name}()",
            )

    def test_each_non_founder_safe_tool_documents_it_in_its_own_docstring(self):
        for tool_name in TOOLS_REQUIRING_EXPLICIT_FOUNDER_WORDING:
            tool = getattr(mcp_server, tool_name)
            doc = (tool.__doc__ or "").lower()
            self.assertTrue(
                "founder" in doc,
                f"{tool_name}()'s own docstring doesn't mention founder-safety at all",
            )


if __name__ == "__main__":
    unittest.main()
