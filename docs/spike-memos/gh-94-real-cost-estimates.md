# [Spike] Replace hardcoded cost estimates with real AWS pricing data (GH-94)

**Disposition: PROMOTE.**

## Hypothesis

`describe_environment()`'s cost estimates can be replaced with real, queryable AWS pricing data
instead of hardcoded, hand-written rough figures. Suggested source: instances.vantage.sh.

## Findings

**instances.vantage.sh is not usable here.** It covers EC2, RDS, ElastiCache, Redshift, and
OpenSearch — all instance/capacity-provisioned services. It does not cover S3, DynamoDB, Lambda,
Cognito, SES, SQS, SNS, Secrets Manager, SSM, or API Gateway — 11 of this harness's 13
capabilities. It only overlaps on OpenSearch (the `search` capability), and even there it's a
comparison UI, not a stable API to build against.

**The real feasible path: AWS's own public Price List Bulk files.** Confirmed live, unauthenticated:

- Index: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/index.json`
- Per-service, per-region: `.../offers/v1.0/aws/<ServiceCode>/current/us-east-1/index.json`
  (e.g. `AmazonDynamoDB`, `AmazonS3`, `AWSLambda`)
- All return `200 OK` with zero auth headers — genuinely public data, no AWS account or
  credentials needed anywhere.

**File sizes are small when region-scoped**, not the 100MB+ feared for the un-scoped global
bulk file: AmazonS3 = 473KB, AWSLambda = 720KB, AmazonDynamoDB = 43KB. Fetchable live per
request; no caching/ETL infrastructure required at this scale.

**Structure**: standard AWS Price List format — `products` (SKU → attributes like `usagetype`)
+ `terms.OnDemand`/`terms.Reserved` (SKU → price dimensions → `pricePerUnit.USD`). DynamoDB's
`current/us-east-1` file has 27 products (distinct SKUs for storage, PITR backup, etc.), each
needing attribute-matching to pick the right one.

**Engineering cost: moderate, not trivial, not a big ETL project.** Not a one-line `requests.get()`
— needs (1) a `usagetype`/attribute allowlist per capability to pick the correct SKU(s) out of
several dozen candidates, and (2) an assumed usage-volume profile to turn a real per-request/
per-GB/per-hour unit price into a "$/month" figure — the same "light early-stage usage"
assumption the current hardcoded strings already make, just multiplied against a real unit price
instead of an eyeballed one. Realistic scope: one small module doing a live fetch + a
per-capability SKU-selection mapping, roughly a day of focused work, no new dependencies, no AWS
credentials anywhere in the harness's architecture.

## Recommendation

Promote to a full feature ticket, scoped to:
- A small module fetching the per-service, region-scoped Price List JSON for each of this
  harness's 13 capabilities' `aws_service` values.
- A documented `usagetype`/attribute allowlist per capability, picking the correct SKU(s) out of
  the file's many entries.
- A documented, explicit usage-volume assumption (matching today's "light early-stage usage"
  framing) to turn a real unit price into a monthly estimate.
- Keep the existing caveat language ("rough, illustrative, not a quote") — a real unit price
  multiplied by an assumed usage volume is still an estimate, just a better-grounded one.
- Graceful fallback to the current hardcoded strings if the live fetch fails (no network, AWS
  changes the file format, etc.) — never crash `describe_environment()` over a pricing lookup.

## Artifacts

- Ticket: GH-94
- Live-verified sources: `pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{AmazonS3,AmazonDynamoDB,AWSLambda}/current/us-east-1/index.json`
