#!/usr/bin/env python3
"""Regression test for GH-71: a filterable read over the event log, so a developer/agent can
debug or audit past verification runs without needing the live board open at the time they
happened. Covers events.query() directly and the get_verification_history MCP tool that exposes
it."""
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import events
import mcp_server


class EventsQueryTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.events_path = Path(self.tmpdir.name) / "events.jsonl"
        self._patches = [
            unittest.mock.patch.object(events, "EVENTS_PATH", self.events_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def _write_raw_events(self, *raw_lines: str) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("w") as f:
            for line in raw_lines:
                f.write(line + "\n")

    def test_query_with_no_filters_returns_everything(self):
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-a")
        events.emit("verify.pass", "structured-data", founder={"label": "y"}, app_context="app-b")
        self.assertEqual(len(events.query()), 2)

    def test_query_filters_by_app_context(self):
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-a")
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-b")
        results = events.query(app_context="app-a")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["app_context"], "app-a")

    def test_query_filters_by_capability(self):
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-a")
        events.emit("verify.pass", "structured-data", founder={"label": "x"}, app_context="app-a")
        results = events.query(capability="structured-data")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["capability"], "structured-data")

    def test_query_filters_combine_with_and(self):
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-a")
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-b")
        events.emit("verify.pass", "structured-data", founder={"label": "x"}, app_context="app-a")
        results = events.query(app_context="app-a", capability="file-storage")
        self.assertEqual(len(results), 1)

    def test_query_filters_by_time_range(self):
        self._write_raw_events(
            json.dumps({"seq": 1, "t": "2026-01-01T00:00:00Z", "kind": "x", "capability": None,
                        "app_context": None, "founder": {}, "dev": {}}),
            json.dumps({"seq": 2, "t": "2026-06-01T00:00:00Z", "kind": "x", "capability": None,
                        "app_context": None, "founder": {}, "dev": {}}),
            json.dumps({"seq": 3, "t": "2026-12-01T00:00:00Z", "kind": "x", "capability": None,
                        "app_context": None, "founder": {}, "dev": {}}),
        )
        results = events.query(since="2026-03-01T00:00:00Z", until="2026-09-01T00:00:00Z")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["seq"], 2)

    def test_query_skips_a_torn_last_line_instead_of_crashing(self):
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-a")
        with self.events_path.open("a") as f:
            f.write('{"seq": 2, "t": "2026-0')  # deliberately truncated, no trailing newline
        results = events.query()
        self.assertEqual(len(results), 1)

    def test_query_on_missing_file_returns_empty_list(self):
        self.assertEqual(events.query(), [])

    def test_query_does_not_hold_any_lock(self):
        # A filtered read must not require the write lock -- confirmed by patching `locked` to
        # raise if called; query() must never touch it.
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_path.write_text(
            '{"seq": 1, "t": "x", "kind": "y", "capability": null, '
            '"app_context": null, "founder": {}, "dev": {}}\n'
        )
        with unittest.mock.patch.object(events, "locked", side_effect=AssertionError("locked!")):
            events.query()  # must not raise


class GetVerificationHistoryToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.events_path = Path(self.tmpdir.name) / "events.jsonl"
        self._patches = [unittest.mock.patch.object(events, "EVENTS_PATH", self.events_path)]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_tool_delegates_to_events_query_with_matching_filters(self):
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-a")
        events.emit("verify.pass", "file-storage", founder={"label": "x"}, app_context="app-b")
        results = mcp_server.get_verification_history(app_context="app-a")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["app_context"], "app-a")

    def test_tool_docstring_says_not_founder_facing(self):
        doc = (mcp_server.get_verification_history.__doc__ or "").lower()
        self.assertIn("founder", doc)
        self.assertIn("not founder-facing", doc)


if __name__ == "__main__":
    unittest.main()
