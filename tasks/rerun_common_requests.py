"""Re-run the three most common requests (file storage, structured data, email) against local Floci.

For each one: provision it the way an agent would, then time record_provisioned(), which re-runs the
catalog's verify check server-side before recording anything. Prints a JSON log to stdout.

Needs Floci running and harness/.venv set up (./setup.sh). Run from the repo root:
    harness/.venv/bin/python3 tasks/rerun_common_requests.py . > docs/assets/recorded-run-YYYY-MM-DD.json
Resources are created under the app_context "launch-proof"; delete them first to re-run from scratch.
"""
import datetime, json, os, platform, re, subprocess, sys, time

REPO = sys.argv[1]
sys.path.insert(0, os.path.join(REPO, "harness"))
import mcp_server as s  # noqa: E402

env = {**os.environ, **s.ENV}
APP = "launch-proof"
RUNS = [
    ("file-storage", "launch-proof-uploads", "aws s3 mb s3://launch-proof-uploads"),
    ("structured-data", "launch-proof-records",
     "aws dynamodb create-table --table-name launch-proof-records "
     "--attribute-definitions AttributeName=id,AttributeType=S --key-schema AttributeName=id,KeyType=HASH "
     "--billing-mode PAY_PER_REQUEST"),
    ("send-email", "hello@launch-proof.example", "aws ses verify-email-identity --email-address hello@launch-proof.example"),
]
JARGON = re.compile(r"arn:|s3://|dynamodb|\bses\b|bucket|table|lambda|localhost|4566|launch-proof-", re.I)

results = []
for cap, name, cmd in RUNS:
    recipe = s.get_provisioning_recipe(cap, name, APP)
    assert "error" not in recipe, recipe
    t0 = time.perf_counter()
    p = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
    provision_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    r = s.record_provisioned(APP, cap, name)
    verify_s = time.perf_counter() - t1
    founder = r.get("founder_message", "")
    results.append({
        "capability_id": cap,
        "provision_command": cmd,
        "provision_exit": p.returncode,
        "provision_seconds": round(provision_s, 2),
        "verify_command": recipe["verify_command_preview"],
        "record_provisioned_seconds": round(verify_s, 2),
        "gate_result": r.get("gate_result"),
        "founder_message": founder,
        "founder_message_jargon_hits": JARGON.findall(founder),
    })

out = {
    "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "what": "Each capability provisioned, then record_provisioned() re-runs its catalog verify check "
            "against local Floci before recording it. record_provisioned_seconds is that server-side re-check.",
    "machine": f"{platform.system()} {platform.machine()}",
    "results": results,
    "summary": {
        "passed": sum(1 for x in results if x["gate_result"] == "PASS"),
        "total": len(results),
        "avg_record_provisioned_seconds": round(sum(x["record_provisioned_seconds"] for x in results) / len(results), 2),
        "founder_messages_with_jargon": sum(1 for x in results if x["founder_message_jargon_hits"]),
    },
}
print(json.dumps(out, indent=2))
