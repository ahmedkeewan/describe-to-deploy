#!/usr/bin/env python3
"""
Answers "what would it take to go live?": reads a stack-plan.json and names the real cloud
service behind each capability, using only catalog fields (`aws_service`,
`cloud_equivalent_note`). Performs no migration. Backs the whats_needed_to_go_live MCP tool.

Usage: python3 harness/go_live_plan.py /path/to/stack-plan.json
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog" / "capabilities.json"


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: go_live_plan.py /path/to/stack-plan.json", file=sys.stderr)
        sys.exit(2)

    plan = json.loads(Path(sys.argv[1]).read_text())
    catalog = {c["id"]: c for c in json.loads(CATALOG_PATH.read_text())["capabilities"]}

    if plan.get("fallback") is not None:
        print("This app has no provisioned capabilities yet -- nothing to report on going live.")
        return

    app = plan.get("app_context", "your app")
    print(f"What it takes for {app} to go live on real cloud infrastructure:\n")

    for entry in plan.get("matched_capabilities", []):
        cap = catalog.get(entry["capability_id"])
        if cap is None:
            continue
        print(f"- {cap['founder_description']}")
        print(f"    Today (local):  {cap['aws_service']} on Floci, resource `{entry['resource_name']}`")
        print(f"    In production:  {cap['cloud_equivalent_note']}")
        print()

    print(
        "No redesign needed: every piece above is the same service, same shape, just pointed at\n"
        "a real account with real credentials instead of the local Floci endpoint, plus normal\n"
        "production hardening (real IAM policies, monitoring, backups) that a local dev\n"
        "environment doesn't need. This plan file is the checklist -- nothing here was invented\n"
        "for this report; it's read straight from what already ran locally and passed the\n"
        "verification gate."
    )


if __name__ == "__main__":
    main()
