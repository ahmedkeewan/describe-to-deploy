#!/usr/bin/env python3
"""
Fix #4: a deterministic, computational verification gate.

Fix #2's executor was TOLD to verify its own work before claiming done -- that instruction did
real work (VOCAB.md 6d's t6 result), but it's still inferential: an LLM choosing to comply. This
gate is the computational counterpart (VOCAB.md sec 3: "prefer computational over inferential
wherever a deterministic check exists") -- a plain script that independently re-runs each
capability's real verify check against live Floci state, with no LLM in the loop and no way for
an executor's self-report to override it. It reads only stack-plan.json + catalog/capabilities.json
and prints a structured verdict; a founder-facing "ready" message should never be shown unless
this gate exits 0.

Usage: python3 harness/verify_gate.py /path/to/stack-plan.json
Exit code 0 = every matched capability verified live and healthy. Exit code 1 = at least one
capability failed its live check (see the printed report for which, and why).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog" / "capabilities.json"

ENV = {
    **os.environ,
    "AWS_ENDPOINT_URL": "http://localhost:4566",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
}


def load_catalog_by_id() -> dict:
    catalog = json.loads(CATALOG_PATH.read_text())
    return {c["id"]: c for c in catalog["capabilities"]}


def run_check(cli_template: str, resource_name: str) -> tuple[bool, str]:
    """Substitutes the plan's resource_name into the catalog's verify.cli placeholder pattern
    and actually runs it against live Floci. No LLM judgment involved -- exit code is truth."""
    cmd = (
        cli_template
        .replace("<bucketName>", resource_name)
        .replace("<tableName>", resource_name)
        .replace("<functionName>", resource_name)
        .replace("<userPoolId>", resource_name)
        .replace("<topicArn>", resource_name)
        .replace("<queueUrl>", resource_name)
        .replace("<secretName>", resource_name)
        .replace("<domainName>", resource_name)
    )
    try:
        result = subprocess.run(
            cmd, shell=True, env=ENV, capture_output=True, text=True, timeout=30
        )
        ok = result.returncode == 0
        output = (result.stdout or result.stderr or "").strip()
        return ok, output[:500]
    except subprocess.TimeoutExpired:
        return False, "verification command timed out after 30s"


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: verify_gate.py /path/to/stack-plan.json", file=sys.stderr)
        sys.exit(2)

    plan_path = Path(sys.argv[1])
    plan = json.loads(plan_path.read_text())
    catalog_by_id = load_catalog_by_id()

    if plan.get("fallback") is not None:
        print(json.dumps({
            "gate_result": "PASS",
            "reason": "plan is a fallback (no capabilities to provision) -- nothing to verify",
        }, indent=2))
        sys.exit(0)

    results = []
    all_passed = True
    for entry in plan.get("matched_capabilities", []):
        cap_id = entry["capability_id"]
        resource_name = entry["resource_name"]
        catalog_entry = catalog_by_id.get(cap_id)
        if catalog_entry is None:
            results.append({
                "capability_id": cap_id, "resource_name": resource_name,
                "passed": False, "detail": f"'{cap_id}' is not in the catalog -- cannot verify",
            })
            all_passed = False
            continue
        cli = catalog_entry["verify"]["cli"]
        passed, output = run_check(cli, resource_name)
        results.append({
            "capability_id": cap_id, "resource_name": resource_name,
            "passed": passed, "detail": output,
        })
        all_passed = all_passed and passed

    report = {
        "gate_result": "PASS" if all_passed else "FAIL",
        "app_context": plan.get("app_context"),
        "capabilities_checked": results,
    }
    print(json.dumps(report, indent=2))
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
