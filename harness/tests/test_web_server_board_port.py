#!/usr/bin/env python3
"""Unit tests for web_server.py's _resolve_board_port (GH-32)."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import web_server


class ResolveBoardPortTests(unittest.TestCase):
    def test_defaults_to_7777_when_unset(self):
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("FLOCI_BOARD_PORT", None)
            self.assertEqual(web_server._resolve_board_port(), 7777)

    def test_uses_env_var_when_set(self):
        with patch.dict("os.environ", {"FLOCI_BOARD_PORT": "8123"}):
            self.assertEqual(web_server._resolve_board_port(), 8123)

    def test_returns_an_int_not_a_string(self):
        with patch.dict("os.environ", {"FLOCI_BOARD_PORT": "9001"}):
            result = web_server._resolve_board_port()
            self.assertIsInstance(result, int)


if __name__ == "__main__":
    unittest.main()
