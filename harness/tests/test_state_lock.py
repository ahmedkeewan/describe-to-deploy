#!/usr/bin/env python3
"""Unit tests for state_lock.py's `locked()` context manager.

Verifies the lock actually excludes concurrent access (a second thread blocks until the first
releases) and that it never swallows an exception raised inside the `with` block."""
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state_lock import locked


class LockedTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.lock_path = Path(self.tmpdir.name) / "sub" / ".test.lock"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_creates_parent_directory(self):
        with locked(self.lock_path):
            pass
        self.assertTrue(self.lock_path.exists())

    def test_second_holder_blocks_until_first_releases(self):
        order = []
        holder_ready = threading.Event()
        release_holder = threading.Event()

        def hold_first():
            with locked(self.lock_path):
                order.append("first-acquired")
                holder_ready.set()
                release_holder.wait(timeout=5)
                # Recorded while still holding the lock: appending after the `with` would race
                # the main thread, which can acquire and append the instant the lock drops.
                order.append("first-released")

        t = threading.Thread(target=hold_first)
        t.start()
        holder_ready.wait(timeout=5)

        # The main thread should block here until `hold_first` releases the lock.
        start = time.monotonic()
        release_holder.set()
        with locked(self.lock_path):
            elapsed = time.monotonic() - start
            order.append("second-acquired")

        t.join(timeout=5)
        self.assertEqual(order, ["first-acquired", "first-released", "second-acquired"])

    def test_lock_released_even_if_body_raises(self):
        with self.assertRaises(ValueError):
            with locked(self.lock_path):
                raise ValueError("boom")

        # A fresh acquisition must succeed immediately -- proves the lock was released.
        acquired = threading.Event()

        def try_acquire():
            with locked(self.lock_path):
                acquired.set()

        t = threading.Thread(target=try_acquire)
        t.start()
        t.join(timeout=5)
        self.assertTrue(acquired.is_set())


if __name__ == "__main__":
    unittest.main()
