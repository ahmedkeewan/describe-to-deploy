"""The GitHub Pages capability cards must match the catalog.

`docs/index.html` renders its capability grid from `docs/assets/capabilities.json`,
a hand-kept copy of `catalog/capabilities.json` (Pages serves `docs/` only, so it
can't read the catalog directly). A copy can drift: a capability added to the
catalog but missing from the site, or a proof sentence reworded in one place only.
This test fails until both agree.
"""

import json
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
CATALOG = REPO / "catalog" / "capabilities.json"
SITE = REPO / "docs" / "assets" / "capabilities.json"


class SiteCapabilitiesInSyncTest(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(CATALOG.read_text())["capabilities"]
        self.site = json.loads(SITE.read_text())

    def test_same_capabilities_in_same_order(self):
        self.assertEqual(
            [c["id"] for c in self.site],
            [c["id"] for c in self.catalog],
            "docs/assets/capabilities.json lists different capabilities than the catalog",
        )

    def test_card_text_matches_catalog(self):
        by_id = {c["id"]: c for c in self.catalog}
        for card in self.site:
            cap = by_id[card["id"]]
            with self.subTest(capability=card["id"]):
                self.assertEqual(card["description"], cap["founder_description"])
                self.assertEqual(card["proof"], cap["verify"]["founder_proof"])
                self.assertEqual(card["aws_service"], cap["aws_service"])


if __name__ == "__main__":
    unittest.main()
