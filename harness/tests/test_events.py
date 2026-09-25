#!/usr/bin/env python3
"""Unit tests for events.py's cross-process locking (GH-31). Before this fix, emit()'s
_next_seq() read and the append write were unlocked across processes -- a threading.Lock only
serialized within one process, so two mcp_server.py processes could compute the same seq."""
import itertools
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import events


class EventsLockingTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.events_path = Path(self.tmpdir.name) / "events.jsonl"
        self.lock_path = Path(self.tmpdir.name) / ".events.lock"
        self._patches = [
            patch.object(events, "EVENTS_PATH", self.events_path),
            patch.object(events, "EVENTS_LOCK_PATH", self.lock_path),
            # _seq_counter is module-level state, shared across every test in this process --
            # reset it per test so one test's calls don't shift another's expected seq numbers.
            # This is a quirk of the file-missing fallback path, unrelated to the locking under
            # test here.
            patch.object(events, "_seq_counter", itertools.count(1)),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmpdir.cleanup()

    def test_single_emit_gets_seq_one(self):
        event = events.emit("provision.start", "file-storage", founder={"label": "x"})
        self.assertEqual(event["seq"], 1)

    def test_sequential_emits_increment(self):
        first = events.emit("provision.start", "file-storage", founder={"label": "x"})
        second = events.emit("verify.pass", "file-storage", founder={"label": "x"})
        self.assertEqual(second["seq"], first["seq"] + 1)

    def test_concurrent_emits_never_produce_the_same_seq(self):
        """The acceptance criterion, proven with real threads racing the same lock -- each
        thread opens its own file handle via `locked()`, so this exercises the same contention
        two separate mcp_server.py processes would hit, not just an in-process race."""
        results = []
        lock = threading.Lock()

        def do_emit(i):
            event = events.emit("provision.start", f"cap-{i}", founder={"label": f"x{i}"})
            with lock:
                results.append(event)

        threads = [threading.Thread(target=do_emit, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        seqs = [r["seq"] for r in results]
        self.assertEqual(len(seqs), 10)
        self.assertEqual(len(set(seqs)), 10, f"duplicate seq among {seqs}")

    def test_events_file_has_no_corrupted_lines_after_concurrent_emits(self):
        """Locking only the write (not the read+write together) can still let two processes
        interleave a torn append. Confirm every line in the file parses and every seq from 1
        to N is present exactly once."""
        threads = [
            threading.Thread(
                target=events.emit, args=("provision.start", f"cap-{i}", {"label": f"x{i}"})
            )
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        all_events = events.read_all()
        self.assertEqual(len(all_events), 10)
        self.assertEqual(sorted(e["seq"] for e in all_events), list(range(1, 11)))


if __name__ == "__main__":
    unittest.main()
