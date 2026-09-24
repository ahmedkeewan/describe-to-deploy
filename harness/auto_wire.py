#!/usr/bin/env python3
"""
Auto-wiring: writes wiring env vars directly into a founder's app, no manual paste step.

Reads a gate-passed stack-plan.json and, for each matched capability, looks up its
`wiring.env_vars` in catalog/capabilities.json, derives real values (the plan's resource_name
plus the shared Floci endpoint/credentials), and merges them into <target_dir>/.env -- creating
the file if it doesn't exist, preserving every line it doesn't own, and updating in place any
line it wrote on a previous run (idempotent: running twice produces the same file, not duplicate
entries). This should only ever run after harness/verify_gate.py has returned PASS for the same
plan -- wiring config for infrastructure that isn't actually verified working would hand the
founder's app real-looking values that silently don't work.

Usage: python3 harness/auto_wire.py /path/to/stack-plan.json /path/to/founder-app-dir
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog" / "capabilities.json"

MANAGED_MARKER = "# --- managed by floci harness, do not hand-edit (auto_wire.py) ---"


def derive_env_values(capability_id: str, resource_name: str, env_var_names: list) -> dict:
    """Maps a catalog capability's declared env var names to real values for this resource.
    Deliberately explicit per-capability, not a generic template -- a wrong guessed value here
    is worse than no value, since the app would silently point at nothing real."""
    values = {"AWS_ENDPOINT_URL": "http://localhost:4566"}
    if capability_id == "user-accounts":
        pass  # COGNITO_USER_POOL_ID / COGNITO_CLIENT_ID come from provisioning output,
              # not derivable from resource_name alone -- left for the executor to fill in
              # via a richer plan in a future iteration; noted, not silently guessed here.
    elif capability_id == "file-storage":
        values["S3_BUCKET_NAME"] = resource_name
    elif capability_id == "structured-data":
        values["DYNAMODB_TABLE_NAME"] = resource_name
    elif capability_id == "send-email":
        pass  # SES_SENDER_ADDRESS is the identity the executor actually verified (e.g.
              # "confirmations@local.test"), NOT derivable from resource_name -- an earlier
              # version of this function guessed `<resource_name>@local.test` here and it was
              # genuinely wrong (caught 2026-09-05: real identity was "confirmations@local.test",
              # resource_name was "photo-confirm-email-notify", an unrelated label). Left unfilled
              # rather than guessed, same as user-accounts above.
    elif capability_id == "background-queue":
        values["SQS_QUEUE_URL"] = resource_name
    elif capability_id == "push-notifications":
        values["SNS_TOPIC_ARN"] = resource_name
    return {k: v for k, v in values.items() if k in env_var_names or k == "AWS_ENDPOINT_URL"}


def merge_env_file(target_path: Path, new_vars: dict) -> None:
    """Idempotent merge: existing unrelated lines are untouched; lines this tool previously
    wrote (inside the MANAGED_MARKER block) are fully replaced, never duplicated or appended
    again on a re-run."""
    existing_lines = target_path.read_text().splitlines() if target_path.exists() else []

    if MANAGED_MARKER in existing_lines:
        marker_idx = existing_lines.index(MANAGED_MARKER)
        kept_lines = existing_lines[:marker_idx]
    else:
        kept_lines = existing_lines
        if kept_lines and kept_lines[-1].strip() != "":
            kept_lines.append("")

    managed_block = [MANAGED_MARKER] + [f"{k}={v}" for k, v in sorted(new_vars.items())]
    target_path.write_text("\n".join(kept_lines + managed_block) + "\n")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: auto_wire.py /path/to/stack-plan.json /path/to/founder-app-dir", file=sys.stderr)
        sys.exit(2)

    plan_path = Path(sys.argv[1])
    app_dir = Path(sys.argv[2])
    plan = json.loads(plan_path.read_text())
    catalog = {c["id"]: c for c in json.loads(CATALOG_PATH.read_text())["capabilities"]}

    if plan.get("fallback") is not None:
        print("Plan is a fallback (nothing provisioned) -- nothing to wire.")
        sys.exit(0)

    all_vars = {}
    for entry in plan.get("matched_capabilities", []):
        cap = catalog.get(entry["capability_id"])
        if cap is None:
            continue
        env_var_names = cap.get("wiring", {}).get("env_vars", [])
        all_vars.update(derive_env_values(entry["capability_id"], entry["resource_name"], env_var_names))

    app_dir.mkdir(parents=True, exist_ok=True)
    env_path = app_dir / ".env"
    merge_env_file(env_path, all_vars)
    print(f"Wired {len(all_vars)} value(s) into {env_path}")


if __name__ == "__main__":
    main()
