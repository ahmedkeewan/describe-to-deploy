#!/usr/bin/env python3
"""Resource ownership: the isolation between environments that share one Floci backend.

A resource (AWS service + the name or ID its verify check uses) belongs to the first app_context
that records it; any other app_context recording or restoring it is rejected. This replaced a
naming rule (`<app_context>::<name>`) that no real AWS resource could satisfy -- `:` is illegal
in S3/DynamoDB/Lambda/... names, and AWS-assigned IDs (queue URLs, ARNs, pool IDs) can't carry a
prefix at all (https://github.com/ahmedkeewan/service-buddy/issues/85)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import environments_store
import events
import mcp_server
import snapshots_store


class OwnershipTestBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(self.tmpdir.name)
        self._patches = [
            patch.object(environments_store, "ENVIRONMENTS_PATH", tmp / "environments.json"),
            patch.object(environments_store, "ENVIRONMENTS_LOCK_PATH", tmp / ".environments.lock"),
            patch.object(snapshots_store, "SNAPSHOTS_PATH", tmp / "environment-snapshots.json"),
            patch.object(snapshots_store, "SNAPSHOTS_LOCK_PATH", tmp / ".environment-snapshots.lock"),
            patch.object(mcp_server, "STATE_PATH", tmp / "stack-state.json"),
            patch.object(mcp_server, "STATE_LOCK_PATH", tmp / ".stack-state.lock"),
            patch.object(events, "EVENTS_PATH", tmp / "events.jsonl"),
            patch.object(events, "EVENTS_LOCK_PATH", tmp / ".events.lock"),
        ]
        for p in self._patches:
            p.start()
        self.alpha = mcp_server.create_environment("alpha")["app_context"]
        self.beta = mcp_server.create_environment("beta")["app_context"]

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def record(self, app_context, capability_id, resource_name):
        with patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            return mcp_server.record_provisioned(app_context, capability_id, resource_name)


class RecordProvisionedOwnershipTests(OwnershipTestBase):
    def test_plain_aws_valid_name_is_accepted(self):
        # The #85 regression: a name S3 actually accepts must work inside an environment.
        self.assertEqual(self.record(self.alpha, "file-storage", "alpha-photos")["gate_result"], "PASS")

    def test_aws_assigned_ids_are_accepted(self):
        # These can never carry an environment prefix; ownership doesn't need one.
        arn = "arn:aws:sns:us-east-1:000000000000:alpha-alerts"
        self.assertEqual(self.record(self.alpha, "push-notifications", arn)["gate_result"], "PASS")
        queue = "http://localhost:4566/000000000000/alpha-jobs"
        self.assertEqual(self.record(self.alpha, "background-queue", queue)["gate_result"], "PASS")

    def test_same_resource_in_another_environment_is_rejected_before_verify(self):
        self.record(self.alpha, "file-storage", "shared-photos")
        with patch.object(mcp_server, "_run_verify") as mock_verify:
            result = mcp_server.record_provisioned(self.beta, "file-storage", "shared-photos")
        mock_verify.assert_not_called()
        self.assertIn("error", result)

    def test_same_name_on_a_different_service_is_not_a_conflict(self):
        # A bucket and a table can both be called "photos"; they're different resources.
        self.record(self.alpha, "file-storage", "photos")
        self.assertEqual(self.record(self.beta, "structured-data", "photos")["gate_result"], "PASS")

    def test_owner_can_record_its_own_resource_again(self):
        self.record(self.alpha, "file-storage", "alpha-photos")
        self.assertEqual(self.record(self.alpha, "file-storage", "alpha-photos")["gate_result"], "PASS")

    def test_claim_made_while_verify_was_running_is_caught_under_the_lock(self):
        # beta passes the early check, then alpha records the same bucket while beta's verify
        # runs. The re-check inside the state lock must still reject beta.
        def alpha_claims_first(*_args):
            self.record(self.alpha, "file-storage", "raced-photos")
            return True, "ok"

        with patch.object(mcp_server, "_run_verify", side_effect=alpha_claims_first):
            result = mcp_server.record_provisioned(self.beta, "file-storage", "raced-photos")
        self.assertIn("error", result)
        state = mcp_server._load_state()
        self.assertNotIn("file-storage", state.get(self.beta, {}).get("capabilities", {}))

    def test_dry_run_still_enforces_ownership(self):
        self.record(self.alpha, "file-storage", "shared-photos")
        with patch("subprocess.run") as mock_run:
            result = mcp_server.record_provisioned(
                self.beta, "file-storage", "shared-photos", dry_run=True
            )
        mock_run.assert_not_called()
        self.assertIn("error", result)
        self.assertNotIn("dry_run", result)


class GetProvisioningRecipeOwnershipTests(OwnershipTestBase):
    def test_unowned_resource_returns_steps(self):
        result = mcp_server.get_provisioning_recipe("file-storage", "alpha-photos", app_context=self.alpha)
        self.assertIn("steps", result)

    def test_resource_owned_elsewhere_is_rejected_before_returning_steps(self):
        self.record(self.alpha, "file-storage", "shared-photos")
        result = mcp_server.get_provisioning_recipe("file-storage", "shared-photos", app_context=self.beta)
        self.assertIn("error", result)
        self.assertNotIn("steps", result)


class RestoreOwnershipTests(OwnershipTestBase):
    def test_restore_skips_a_resource_another_environment_now_owns(self):
        self.record(self.alpha, "file-storage", "alpha-photos")
        snapshot_id = mcp_server.snapshot_environment("alpha")["snapshot_id"]
        # alpha lets go of it (e.g. its state was rebuilt), and beta records the same bucket.
        state = mcp_server._load_state()
        del state[self.alpha]["capabilities"]["file-storage"]
        mcp_server._save_state(state)
        self.record(self.beta, "file-storage", "alpha-photos")

        with patch.object(mcp_server, "_run_verify", return_value=(True, "ok")):
            result = mcp_server.restore_environment("alpha", snapshot_id)
        self.assertEqual(result["restored"], [])
        self.assertEqual(result["skipped"][0]["reason"], "now owned by a different environment")


class AppContextTests(OwnershipTestBase):
    def test_app_context_is_short_enough_to_embed_in_resource_names(self):
        # name + "-" + 6 hex: short enough to embed in a 28-character search domain name.
        self.assertRegex(self.alpha, r"^alpha-[0-9a-f]{6}$")

    def test_app_context_never_reuses_one_a_snapshot_still_holds(self):
        mcp_server.snapshot_environment("alpha")
        mcp_server.destroy_environment("alpha")
        taken = self.alpha
        with patch("secrets.token_hex", side_effect=[taken.split("-")[-1], "abc123"]):
            recreated = mcp_server.create_environment("alpha")["app_context"]
        self.assertEqual(recreated, "alpha-abc123")


if __name__ == "__main__":
    unittest.main()
