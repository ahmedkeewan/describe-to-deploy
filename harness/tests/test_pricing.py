#!/usr/bin/env python3
"""Regression test for GH-95: pricing.py's attribute-based SKU matching and always-free-tier
correction. All tests mock urllib.request.urlopen -- no real network calls in the unit suite.
Live correctness (does this actually match a real product in AWS's real pricing file) was
verified manually against a live fetch during development; see the module docstring and the
GH-94 spike memo for how the matched attributes and always_free_units values were found."""
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pricing


def _fake_pricing_file(products: dict, terms: dict) -> bytes:
    return json.dumps({"products": products, "terms": {"OnDemand": terms}}).encode()


class FindMatchingSkuTests(unittest.TestCase):
    def test_returns_the_one_matching_sku(self):
        data = {
            "products": {
                "SKU1": {"productFamily": "Storage", "attributes": {"foo": "bar"}},
                "SKU2": {"productFamily": "Storage", "attributes": {"foo": "baz"}},
            }
        }
        result = pricing._find_matching_sku(data, {"productFamily": "Storage", "foo": "bar"})
        self.assertEqual(result, "SKU1")

    def test_returns_none_when_zero_products_match(self):
        data = {"products": {"SKU1": {"productFamily": "Storage", "attributes": {"foo": "bar"}}}}
        result = pricing._find_matching_sku(data, {"productFamily": "Storage", "foo": "nope"})
        self.assertIsNone(result)

    def test_returns_none_when_multiple_products_match(self):
        # Ambiguity must fall back, never guess.
        data = {
            "products": {
                "SKU1": {"productFamily": "Storage", "attributes": {"foo": "bar"}},
                "SKU2": {"productFamily": "Storage", "attributes": {"foo": "bar"}},
            }
        }
        result = pricing._find_matching_sku(data, {"productFamily": "Storage", "foo": "bar"})
        self.assertIsNone(result)


class PriceForQuantityTests(unittest.TestCase):
    def test_single_flat_tier(self):
        data = {
            "terms": {
                "OnDemand": {
                    "SKU1": {
                        "term1": {
                            "priceDimensions": {
                                "dim1": {
                                    "beginRange": "0",
                                    "endRange": "Inf",
                                    "pricePerUnit": {"USD": "0.0000002000"},
                                }
                            }
                        }
                    }
                }
            }
        }
        cost = pricing._price_for_quantity(data, "SKU1", 100_000)
        self.assertAlmostEqual(cost, 0.02)

    def test_tiered_pricing_walks_tiers_in_order(self):
        # Mirrors DynamoDB's real shape: first 25 free, then $0.25/unit.
        data = {
            "terms": {
                "OnDemand": {
                    "SKU1": {
                        "term1": {
                            "priceDimensions": {
                                "free_tier": {
                                    "beginRange": "0",
                                    "endRange": "25",
                                    "pricePerUnit": {"USD": "0.0000000000"},
                                },
                                "paid_tier": {
                                    "beginRange": "25",
                                    "endRange": "Inf",
                                    "pricePerUnit": {"USD": "0.2500000000"},
                                },
                            }
                        }
                    }
                }
            }
        }
        self.assertAlmostEqual(pricing._price_for_quantity(data, "SKU1", 10), 0.0)
        self.assertAlmostEqual(pricing._price_for_quantity(data, "SKU1", 30), 5 * 0.25)


class RealMonthlyEstimateTests(unittest.TestCase):
    def test_unknown_service_returns_none(self):
        self.assertIsNone(pricing.real_monthly_estimate("not-a-real-service"))

    def test_network_failure_returns_none_not_an_exception(self):
        pricing._cache.clear()
        with unittest.mock.patch(
            "urllib.request.urlopen", side_effect=OSError("network down")
        ):
            result = pricing.real_monthly_estimate("dynamodb")
        self.assertIsNone(result)

    def test_ambiguous_or_missing_match_returns_none(self):
        pricing._cache.clear()
        fake_response = unittest.mock.MagicMock()
        fake_response.read.return_value = _fake_pricing_file(products={}, terms={})
        fake_response.__enter__ = lambda self: fake_response
        fake_response.__exit__ = lambda self, *a: False
        with unittest.mock.patch("urllib.request.urlopen", return_value=fake_response):
            result = pricing.real_monthly_estimate("dynamodb")
        self.assertIsNone(result)

    def test_always_free_units_reduce_billable_quantity(self):
        # Mirrors Lambda's real gap: the Bulk Price List has no $0 tier for Lambda at all, but
        # Lambda's Always Free allowance (1M requests/month) must still zero out light usage.
        pricing._cache.clear()
        products = {
            "SKU1": {"productFamily": "Serverless", "attributes": {"usagetype": "Request"}},
        }
        terms = {
            "SKU1": {
                "term1": {
                    "priceDimensions": {
                        "dim1": {
                            "beginRange": "0",
                            "endRange": "Inf",
                            "pricePerUnit": {"USD": "0.0000002000"},
                        }
                    }
                }
            }
        }
        fake_response = unittest.mock.MagicMock()
        fake_response.read.return_value = _fake_pricing_file(products, terms)
        fake_response.__enter__ = lambda self: fake_response
        fake_response.__exit__ = lambda self, *a: False
        with unittest.mock.patch.object(
            pricing,
            "REAL_PRICING_CONFIG",
            {
                "fake-lambda": {
                    "service_code": "FakeLambda",
                    "dimensions": [
                        {
                            "match": {"productFamily": "Serverless", "usagetype": "Request"},
                            "assumed_quantity": 100_000,
                            "unit_label": "100,000 requests/month",
                            "always_free_units": 1_000_000,
                        }
                    ],
                }
            },
        ), unittest.mock.patch("urllib.request.urlopen", return_value=fake_response):
            result = pricing.real_monthly_estimate("fake-lambda")
        self.assertEqual(result["monthly_usd"], 0.0)

    def test_result_includes_assumption_and_source(self):
        pricing._cache.clear()
        products = {
            "SKU1": {"productFamily": "Database Storage", "attributes": {"usagetype": "TimedStorage-ByteHrs"}},
        }
        terms = {
            "SKU1": {
                "term1": {
                    "priceDimensions": {
                        "dim1": {
                            "beginRange": "0",
                            "endRange": "Inf",
                            "pricePerUnit": {"USD": "0.2500000000"},
                        }
                    }
                }
            }
        }
        fake_response = unittest.mock.MagicMock()
        fake_response.read.return_value = _fake_pricing_file(products, terms)
        fake_response.__enter__ = lambda self: fake_response
        fake_response.__exit__ = lambda self, *a: False
        with unittest.mock.patch("urllib.request.urlopen", return_value=fake_response):
            result = pricing.real_monthly_estimate("dynamodb")
        self.assertIn("assumption", result)
        self.assertIn("source", result)
        self.assertIn("AWS Price List", result["source"])


if __name__ == "__main__":
    unittest.main()
