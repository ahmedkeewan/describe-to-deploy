#!/usr/bin/env python3
"""
Real AWS pricing data for describe_environment()'s cost estimates. Fetches AWS's own public,
unauthenticated Price List Bulk API -- confirmed live to require no AWS account or credentials anywhere, unlike every other AWS call
this harness makes (which all go through Floci's local test/test-credentialed endpoint).

Products are matched by ATTRIBUTES (productFamily + a set of attribute key/values), not by a
fixed SKU string. A first version of this module hardcoded specific SKU IDs; SKU IDs are AWS's
own internal identifiers and have been observed to change across price-list revisions, while
productFamily/usagetype/storageClass-style attributes are the same descriptive names that show
up on a real AWS bill and change far less often. Attribute matching also generalizes better: a
new capability just needs a productFamily + attribute filter, not a fresh round of hunting for a
SKU string by hand.

Only implemented for capabilities where the attribute filter resolves to EXACTLY ONE product --
ambiguity (zero or multiple matches) is treated as a failure and the caller falls back to the
hand-written APPROX_MONTHLY_COST_USD estimates in mcp_server.py. Six capabilities are covered so
far: DynamoDB storage, SQS requests, SNS requests, Step Functions state transitions, S3 standard
storage, and Lambda (requests + GB-second compute, summed). The remaining capabilities
(Cognito, SES, EventBridge Scheduler, Secrets Manager, SSM, API Gateway, OpenSearch) have more
multi-dimensional real pricing models that risk a subtly wrong match if rushed, so they use
the hand-written estimates -- a network fetch, a changed file shape, or an ambiguous match
must NEVER crash describe_environment() over a pricing lookup; real_monthly_estimate() never
raises, it returns None on any failure and the caller falls back.

IMPORTANT ACCURACY NOTE, found while verifying these six against live data: AWS's perpetual
"Always Free" tier (distinct from the temporary 12-month promotional Free Tier new accounts get)
is inconsistently represented in the Bulk Price List files. DynamoDB's 25 GB-month free storage
and SNS's first 1M free requests/month both show up as a genuine $0 price tier in the file itself
-- but Lambda's 1M free requests + 400,000 free GB-seconds/month, and SQS's and Step Functions'
1M and 4,000 free-units/month respectively, do NOT appear anywhere in these files at all (verified
by inspecting every price dimension for each). Those are a separate, account-level AWS program
applied at billing time, not part of the service's own on-demand pricing structure. Without a
correction, this module would silently OVERSTATE the real cost for light usage on those three
services. ALWAYS_FREE_MONTHLY corrects for this with AWS's own publicly documented, permanent
Always-Free allowances (not the 12-month promotional ones, which are temporary and excluded on
purpose -- this module estimates ongoing/steady-state cost, not a new account's first year).
"""
import json
import urllib.request

PRICING_BASE = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws"
REGION = "us-east-1"

# Per aws_service (catalog key): the AWS Price List service code, and one or more "dimensions" to
# sum together (Lambda needs two: requests + compute; everything else here needs just one). Each
# dimension names a productFamily + attribute filter that must resolve to exactly one product in
# that service's region-scoped file, an assumed monthly usage volume for "light early-stage
# usage" (the same framing the hardcoded estimates already use, just multiplied against a real
# AWS unit price instead of an eyeballed guess), and a human-readable label for that assumption.
# Every filter here was hand-verified against a live fetch -- see the
# spike memo (research/history/spike-memos/gh-94-real-cost-estimates.md) for how these were found.
REAL_PRICING_CONFIG = {
    "dynamodb": {
        "service_code": "AmazonDynamoDB",
        "dimensions": [
            {
                "match": {"productFamily": "Database Storage", "usagetype": "TimedStorage-ByteHrs"},
                "assumed_quantity": 1,
                "unit_label": "1 GB of table storage/month",
            },
        ],
    },
    "sqs": {
        "service_code": "AWSQueueService",
        "dimensions": [
            {
                "match": {"productFamily": "API Request", "usagetype": "Requests-RBP"},
                "assumed_quantity": 100_000,
                "unit_label": "100,000 requests/month",
                "always_free_units": 1_000_000,  # SQS Always Free: 1M requests/month, permanent
            },
        ],
    },
    "sns": {
        "service_code": "AmazonSNS",
        "dimensions": [
            {
                "match": {"productFamily": "API Request", "usagetype": "Requests-Tier1"},
                "assumed_quantity": 100_000,
                "unit_label": "100,000 requests/month",
                # Not needed here: SNS's first 1M free requests/month already appears as its own
                # $0 price tier in the Bulk Price List file itself -- see the module docstring.
            },
        ],
    },
    "stepfunctions": {
        "service_code": "AmazonStates",
        "dimensions": [
            {
                "match": {"productFamily": "AWS Step Functions", "usagetype": "USE1-StateTransition"},
                "assumed_quantity": 10_000,
                "unit_label": "10,000 state transitions/month",
                "always_free_units": 4_000,  # Step Functions Always Free: 4,000 transitions/month
            },
        ],
    },
    "s3": {
        "service_code": "AmazonS3",
        "dimensions": [
            {
                "match": {
                    "productFamily": "Storage",
                    "usagetype": "TimedStorage-ByteHrs",
                    "storageClass": "General Purpose",
                    "volumeType": "Standard",
                },
                "assumed_quantity": 5,
                "unit_label": "5 GB of Standard storage/month",
            },
        ],
    },
    "lambda": {
        "service_code": "AWSLambda",
        "dimensions": [
            {
                "match": {"productFamily": "Serverless", "usagetype": "Request"},
                "assumed_quantity": 100_000,
                "unit_label": "100,000 requests/month",
                "always_free_units": 1_000_000,  # Lambda Always Free: 1M requests/month, permanent
            },
            {
                "match": {"productFamily": "Serverless", "usagetype": "Lambda-GB-Second"},
                "assumed_quantity": 400_000,
                "unit_label": "400,000 GB-seconds of compute/month "
                "(~100k invocations x 128MB x ~3s average duration)",
                "always_free_units": 400_000,  # Lambda Always Free: 400,000 GB-s/month, permanent
            },
        ],
    },
}

_cache: dict[str, dict] = {}


def _fetch_service_pricing(service_code: str) -> dict:
    """Fetch and cache (in-process only, no disk persistence) one service's region-scoped Price
    List JSON. Raises on any network/parse failure -- callers must catch and fall back, never let
    this crash a caller. Region-scoped files are small (tens to hundreds of KB, confirmed during
    the spike), so a live per-request fetch is reasonable; no separate caching infra needed."""
    if service_code in _cache:
        return _cache[service_code]
    url = f"{PRICING_BASE}/{service_code}/current/{REGION}/index.json"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
    _cache[service_code] = data
    return data


def _find_matching_sku(data: dict, match: dict) -> str | None:
    """Find the one product whose productFamily and attributes match every key in `match`.
    Returns None (never raises) if zero or more than one product matches -- ambiguity is a
    failure the caller must fall back on, not something to guess through."""
    product_family = match["productFamily"]
    attribute_filters = {k: v for k, v in match.items() if k != "productFamily"}
    found = [
        sku
        for sku, product in data["products"].items()
        if product.get("productFamily") == product_family
        and all(product["attributes"].get(k) == v for k, v in attribute_filters.items())
    ]
    return found[0] if len(found) == 1 else None


def _price_for_quantity(data: dict, sku: str, quantity: float) -> float:
    """Given a SKU's OnDemand price dimensions (each a [beginRange, endRange) tier with its own
    per-unit price), compute the cost of `quantity` units by walking the tiers in order -- the
    same tiered-billing shape AWS itself uses (e.g. DynamoDB's first 25 GB free, then
    $0.25/GB)."""
    terms = data["terms"]["OnDemand"][sku]
    term = next(iter(terms.values()))
    dimensions = sorted(term["priceDimensions"].values(), key=lambda d: float(d["beginRange"]))
    remaining = quantity
    total = 0.0
    for dim in dimensions:
        begin = float(dim["beginRange"])
        end = float(dim["endRange"]) if dim["endRange"] != "Inf" else float("inf")
        tier_width = end - begin
        used = min(remaining, tier_width)
        if used <= 0:
            continue
        total += used * float(dim["pricePerUnit"]["USD"])
        remaining -= used
        if remaining <= 0:
            break
    return total


def real_monthly_estimate(aws_service: str) -> dict | None:
    """Return a real, AWS-Price-List-backed monthly cost estimate for aws_service, or None if
    this service isn't in REAL_PRICING_CONFIG, any of its dimensions fails to resolve to exactly
    one product, or the live fetch fails for any reason. Callers must treat None as "fall back to
    the hardcoded estimate" -- this function never raises. When a capability has more than one
    dimension (e.g. Lambda: requests + compute), all dimensions must resolve for a result to be
    returned -- a partial number would misrepresent the estimate as more complete than it is."""
    config = REAL_PRICING_CONFIG.get(aws_service)
    if config is None:
        return None
    try:
        data = _fetch_service_pricing(config["service_code"])
        total = 0.0
        labels = []
        for dimension in config["dimensions"]:
            sku = _find_matching_sku(data, dimension["match"])
            if sku is None:
                return None
            free_units = dimension.get("always_free_units", 0)
            billable_quantity = max(0, dimension["assumed_quantity"] - free_units)
            total += _price_for_quantity(data, sku, billable_quantity)
            labels.append(dimension["unit_label"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        # OSError covers urllib.error.URLError/HTTPError (both subclasses) and raw connection
        # failures (DNS, reset, refused) that can surface as a plain OSError, not just URLError.
        return None
    return {
        "monthly_usd": round(total, 2),
        "assumption": " + ".join(labels),
        "source": f"AWS Price List (public, unauthenticated), {REGION}",
    }
