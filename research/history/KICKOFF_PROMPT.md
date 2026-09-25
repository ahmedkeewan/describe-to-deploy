# Kickoff Prompt (historical)

The prompt used to start the 2026-09-06 build session. Kept for reference — it documents exactly
how the baseline in [`tasks/README.md`](../../tasks/README.md) was first measured, before any harness
fix was applied. Not an active runbook; re-run it verbatim only if you want to reproduce that
baseline from scratch. See [GAME_PLAN.md](GAME_PLAN.md) for the fixes built after this succeeded,
and [VOCAB.md](../VOCAB.md) for the terms it references.

---

```
You're helping me kick off a one-day harness engineering hackathon. Judging is on
measured performance gain AND a working demo — a harness demo without a
before-and-after number is worthless, so today's first hour is entirely about
getting a real, working baseline. No harness fixes yet.

The project: an agent harness that turns a plain-language infra request into a
running, verified local environment on Floci (https://floci.io/ — local AWS/
Azure/GCP/OCI emulators, real Docker/Postgres/Redis, no cloud account needed).

Do these in order, stopping to show me output at each checkpoint rather than
plowing through silently:

1. Confirm floci-cli / floci-ui are installed and working. Run `floci start` (or
   the equivalent) for one emulator — S3 is the simplest — and confirm a real AWS
   CLI call against the local endpoint (`aws --endpoint-url=http://localhost:4566
   s3 ls` or similar) actually succeeds. We need to know the substrate works
   before wrapping an agent around it.

2. Pull the full Floci service catalog: which services exist per cloud (AWS/
   Azure/GCP/OCI), their ports, and the floci-cli invocation for each. Save this
   as a structured file (services.json or similar) — this becomes the "guide"
   layer the agent reads instead of guessing CLI flags.

3. Draft the fixed task set we'll score every harness version against: 6-10
   plain-language infra requests, easy to hard — a single service, a small
   stack, a stack with a real dependency chain (e.g. Lambda reads DynamoDB,
   writes to S3), an incremental add onto an already-running stack, a request
   outside the catalog, and one deliberate failure case (port already in use,
   or an unsupported service). Write these down now so they don't get quietly
   adjusted later to flatter a fix.

4. Run the *bare* baseline: an agent with just bash + floci-cli --help/docs in
   context, no catalog, no verification gate, against all 6-10 requests, one
   trial each, same model throughout. For each, record: did it actually produce
   a working, verified environment (check yourself, don't trust the agent's own
   "done" claim), how many tool calls/retries it took, and wall-clock time.
   Save this as the baseline row of a results table — this is what every later
   fix gets compared against, so don't let it get overwritten.

5. Wire up whatever tracing we have keys for (LangSmith/Langfuse) and confirm at
   least one trace from the baseline run is inspectable end to end — we need to
   be able to point at a real false "done" claim or wasted retry loop on stage
   later.

Checkpoint after each step. If anything in steps 1-2 fights you for more than
15-20 minutes (floci install issues, docker problems, port conflicts), stop and
tell me — don't silently burn the morning on setup. Once the baseline row exists
and is saved, stop and report the numbers back to me before we start on fix #1
(service catalog + stack templates).
```

---

## After this succeeds

Move to the build order in [GAME_PLAN.md](GAME_PLAN.md#build-order): service catalog + templates
→ planner tool → executor tool → verification gate → state file → failure escalation, measuring
the task set after each one. Don't start the next fix until the current one has a recorded number
next to the baseline.
