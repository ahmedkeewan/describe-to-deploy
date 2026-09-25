"""`llms.txt` has to be served, not just committed.

The llms.txt convention is about a file an agent can fetch over HTTP. The
copy at the repo root is the one a human browsing the repo finds; the copy
under `docs/` is the one GitHub Pages actually serves, at
`https://ahmedkeewan.github.io/service-buddy/llms.txt`.

Two copies means they can drift, and a stale served copy is worse than none —
it points agents at links that have moved. This test is the mechanism that
stops the drift: edit one, the suite fails until you edit the other.
"""

import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
ROOT_COPY = REPO / "llms.txt"
SERVED_COPY = REPO / "docs" / "llms.txt"


class LlmsTxtPublishedCopyTest(unittest.TestCase):
    def test_both_copies_exist(self):
        self.assertTrue(ROOT_COPY.is_file(), f"missing {ROOT_COPY}")
        self.assertTrue(
            SERVED_COPY.is_file(),
            f"missing {SERVED_COPY} -- the root llms.txt is not published anywhere",
        )

    def test_copies_are_identical(self):
        self.assertEqual(
            ROOT_COPY.read_bytes(),
            SERVED_COPY.read_bytes(),
            "llms.txt and docs/llms.txt have drifted -- copy one over the other",
        )

    def test_starts_with_the_required_h1(self):
        """The spec's one hard requirement: an H1 naming the project."""
        first = ROOT_COPY.read_text(encoding="utf-8").lstrip("﻿").splitlines()[0]
        self.assertTrue(
            first.startswith("# ") and len(first) > 2,
            f"llms.txt must open with an H1 naming the project, got: {first!r}",
        )


if __name__ == "__main__":
    unittest.main()
