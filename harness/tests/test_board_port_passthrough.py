#!/usr/bin/env python3
"""Regression test for GH-33: FLOCI_BOARD_PORT set on `make board` / `./setup.sh --start-board`
must reach the actual server process.

Reconciliation note: `make board` runs `./setup.sh --start-board`, which -- per setup.sh's
own `exec "$VENV_PYTHON" "$WEB_SERVER"` line -- execs directly into `web_server.py`, inheriting
the calling shell's environment unchanged. No explicit "passthrough" code was needed once GH-32
(web_server.py reading FLOCI_BOARD_PORT) and GH-49 (landing the Makefile/setup.sh commit stack)
were both in place -- plain process env inheritance already does the job. Manually verified with
a real `FLOCI_BOARD_PORT=8905 make board` run (confirmed via lsof) before writing this test.

This test proves the same mechanism two ways without needing setup.sh's full Docker/Floci
checks (too slow and environment-dependent for a unit test):
  1. Static check that setup.sh's --start-board path execs into web_server.py without ever
     unsetting or overriding FLOCI_BOARD_PORT in between.
  2. A real subprocess test of web_server.py itself (the exact binary setup.sh execs into),
     confirming the process actually binds to the env-supplied port over a real socket."""
import os
import re
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = HARNESS_DIR.parent
SETUP_SH = REPO_ROOT / "setup.sh"
WEB_SERVER = HARNESS_DIR / "web_server.py"
VENV_PYTHON = HARNESS_DIR / ".venv" / "bin" / "python3"


class SetupShStaticChecks(unittest.TestCase):
    def test_start_board_execs_web_server_without_touching_floci_board_port(self):
        text = SETUP_SH.read_text()
        match = re.search(
            r'if \[ "\$START_BOARD" = true \]; then(.*?)\bfi\b', text, re.DOTALL
        )
        self.assertIsNotNone(match, "could not find the --start-board block in setup.sh")
        block = match.group(1)
        self.assertIn("exec", block, "the --start-board block should exec into web_server.py")
        self.assertNotIn("unset FLOCI_BOARD_PORT", block)
        self.assertNotIn("FLOCI_BOARD_PORT=", block, "should not override the caller's value")
        self.assertNotRegex(block, r"\benv\s+-i\b", "env -i would strip FLOCI_BOARD_PORT")


class WebServerRealBindTests(unittest.TestCase):
    """Starts the actual server process setup.sh execs into, with FLOCI_BOARD_PORT set, and
    confirms it really binds there over a real socket -- not just that the helper function
    returns the right int (GH-32 already covers that in isolation)."""

    def _wait_for_port(self, port: int, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    return True
            time.sleep(0.1)
        return False

    def test_server_binds_to_env_supplied_port(self):
        if not VENV_PYTHON.exists():
            self.skipTest("harness/.venv not set up -- run pip install -r requirements.txt first")

        port = 8905
        env = {**os.environ, "FLOCI_BOARD_PORT": str(port)}
        proc = subprocess.Popen(
            [str(VENV_PYTHON), str(WEB_SERVER)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            self.assertTrue(self._wait_for_port(port), f"server never bound to {port}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                self.assertNotEqual(
                    s.connect_ex(("127.0.0.1", 7777)),
                    0,
                    "default port 7777 should NOT be bound during this run",
                )
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
