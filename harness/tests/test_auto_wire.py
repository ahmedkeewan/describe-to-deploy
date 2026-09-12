#!/usr/bin/env python3
"""Unit tests for auto_wire.py's pure logic: env-value derivation and idempotent .env merging."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auto_wire import derive_env_values, merge_env_file, MANAGED_MARKER


class DeriveEnvValuesTests(unittest.TestCase):
    def test_file_storage_maps_bucket_name(self):
        values = derive_env_values("file-storage", "photo-bucket", ["S3_BUCKET_NAME"])
        self.assertEqual(values["S3_BUCKET_NAME"], "photo-bucket")
        self.assertEqual(values["AWS_ENDPOINT_URL"], "http://localhost:4566")

    def test_unknown_capability_only_gets_endpoint(self):
        values = derive_env_values("not-a-real-capability", "whatever", ["SOME_VAR"])
        self.assertEqual(values, {"AWS_ENDPOINT_URL": "http://localhost:4566"})

    def test_send_email_never_guesses_sender_identity(self):
        # Regression: an earlier version guessed `<resource_name>@local.test`, which was wrong
        # in practice. The real identity isn't derivable from resource_name alone, so it must
        # stay unfilled rather than invented.
        values = derive_env_values("send-email", "photo-confirm-email-notify", ["SES_SENDER_ADDRESS"])
        self.assertNotIn("SES_SENDER_ADDRESS", values)

    def test_only_declared_env_vars_are_returned(self):
        # structured-data derives DYNAMODB_TABLE_NAME, but it should be dropped if the catalog
        # entry didn't actually declare it as a wiring var.
        values = derive_env_values("structured-data", "users-table", [])
        self.assertNotIn("DYNAMODB_TABLE_NAME", values)


class MergeEnvFileTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.tmpdir.name) / ".env"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_creates_file_when_missing(self):
        merge_env_file(self.env_path, {"S3_BUCKET_NAME": "photos"})
        content = self.env_path.read_text()
        self.assertIn(MANAGED_MARKER, content)
        self.assertIn("S3_BUCKET_NAME=photos", content)

    def test_preserves_unrelated_existing_lines(self):
        self.env_path.write_text("APP_SECRET=keep-me\n")
        merge_env_file(self.env_path, {"S3_BUCKET_NAME": "photos"})
        content = self.env_path.read_text()
        self.assertIn("APP_SECRET=keep-me", content)
        self.assertIn("S3_BUCKET_NAME=photos", content)

    def test_rerun_is_idempotent_not_duplicated(self):
        merge_env_file(self.env_path, {"S3_BUCKET_NAME": "photos"})
        merge_env_file(self.env_path, {"S3_BUCKET_NAME": "photos"})
        content = self.env_path.read_text()
        self.assertEqual(content.count("S3_BUCKET_NAME=photos"), 1)
        self.assertEqual(content.count(MANAGED_MARKER), 1)

    def test_rerun_replaces_stale_managed_values(self):
        merge_env_file(self.env_path, {"S3_BUCKET_NAME": "old-bucket"})
        merge_env_file(self.env_path, {"S3_BUCKET_NAME": "new-bucket"})
        content = self.env_path.read_text()
        self.assertNotIn("old-bucket", content)
        self.assertIn("S3_BUCKET_NAME=new-bucket", content)


if __name__ == "__main__":
    unittest.main()
