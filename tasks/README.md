# Scoring Task Set

The 6 fixed requests from [GAME_PLAN.md](../GAME_PLAN.md)'s Scoring section, as a runnable
artifact — see [task-set.json](task-set.json) for the exact wording and success criteria.
Written before touching the harness, per the same discipline as [KICKOFF_PROMPT.md](../KICKOFF_PROMPT.md):
don't let this get quietly adjusted later to flatter a fix.

## Ground rule

Feed `request_text` to the agent under test **verbatim**, exactly as a non-technical founder
would type or say it. Do not pre-translate it into infra language — that translation is the
capability the harness is supposed to provide, so doing it yourself before the agent sees the
request would hide the exact thing you're trying to measure.

## How to run a scoring pass (baseline or any harness config)

1. Reset state: `floci stop && docker rm -f floci`, then `floci start`, and delete any prior
   `stack-state.json` / `stack-plan.json` from the working directory. A stale bucket or table
   from a previous run will silently invalidate `t6`'s collision setup and can make `t4`'s
   "already exists" check pass for the wrong reason.
2. Run `t1`, `t2`, `t3`, `t5` — any order, note per-task time and tool-call count.
3. Immediately after `t2` (same process/session, same `stack-state.json`), run `t4`.
4. For `t6`: first create the collision out-of-band —
   ```
   aws --endpoint-url=http://localhost:4566 s3 mb s3://<expected-bucket-name>
   ```
   using whatever naming convention the harness under test actually uses (check its planner
   output from `t2`'s run to get the real name — don't guess a placeholder). Then issue `t6`'s
   `request_text` fresh, in a clean session that hasn't already provisioned this app's storage.
5. For each task, judge `success_criteria` yourself against real Floci state
   (`aws --endpoint-url=... <service> <list/describe command>`) — never accept the agent's own
   "done" claim as proof, per the verification-gate design in GAME_PLAN.md.
6. Record every response's text and scan it for infra jargon (service names, ports, ARNs,
   "endpoint," "IAM," etc.) for the jargon-leak metric.

## Results table template

One row per harness configuration (baseline, then one row per fix from GAME_PLAN.md's build
order). Fill in `t1`-`t6` as pass/fail/partial; the last three columns aggregate across all 6.

| Config | t1 | t2 | t3 | t4 | t5 | t6 | Success rate | Avg time | Avg tool calls | Jargon leaks |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 — baseline (bare agent) | | | | | | | | | | |
| 1 — + capability catalog | | | | | | | | | | |
| 2 — + planner tool | | | | | | | | | | |
| 3 — + executor tool | | | | | | | | | | |
| 4 — + verification gate | | | | | | | | | | |
| 5 — + state file | | | | | | | | | | |
| 6 — + failure escalation | | | | | | | | | | |
| 7 — + auto-wiring | | | | | | | | | | |

## What each task is actually testing

- **t1, t2** — the basic translation: plain language in, correct single capability out.
- **t3** — multi-capability dependency resolution (`depends_on` chains in
  [catalog/capabilities.json](../catalog/capabilities.json)); this is the live demo request.
- **t4** — state incrementality: does a follow-up read `stack-state.json` instead of
  re-provisioning or guessing fresh.
- **t5** — the conservative fallback rule: does the harness refuse to freelance outside the
  catalog and ask a clarifying question instead.
- **t6** — honesty under failure: the single most important task in the set for this project's
  framing, since a founder has no way to independently verify a false "done" claim.
