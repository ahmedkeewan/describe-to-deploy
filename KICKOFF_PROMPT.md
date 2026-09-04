# Saturday Kickoff Prompt

Paste this as the first message to Claude Code (or whatever agent you're driving the hackathon with) tomorrow morning. It only covers hour one: get a real baseline running before any harness fix is touched. See [GAME_PLAN.md](GAME_PLAN.md) for the fixes to build after this succeeds, and [VOCAB.md](VOCAB.md) for the terms it references.

---

```
You're helping me kick off a one-day harness engineering hackathon. Judging is on
measured performance gain AND a working demo — a harness demo without a
before-and-after number is worthless, so today's first hour is entirely about
getting a real, working baseline. No harness fixes yet.

Do these in order, stopping to show me output at each checkpoint rather than
plowing through silently:

1. Clone `SWE-agent/mini-swe-agent` locally. Get it running against one trivial
   task by hand (not through Harbor yet) so we know the base loop works with our
   model and API key before adding any orchestration on top.

2. Install Harbor and get it talking to the same model/API key. Confirm with a
   trivial smoke-test run, not a full slice yet.

3. Pick a 5-10 task slice of Terminal-Bench 2.0 through Harbor. Bias toward tasks
   that plausibly fail on timeouts or premature completion — those are exactly
   what today's planned fixes (completion gate, time-awareness) target, so the
   baseline needs to actually be capable of showing them fail.

4. Run the unmodified mini-swe-agent against that slice, 2 trials each, same
   model throughout. Record: pass rate, mean turns, mean wall-clock. Save this
   as the baseline row of a results table — this number is what every later fix
   gets compared against, so don't let it get overwritten.

5. Wire up whatever tracing we have keys for (LangSmith/Langfuse) and confirm at
   least one trace from the baseline run is inspectable end to end — we need to
   be able to point at a real doom loop or premature completion on stage later.

Checkpoint after each step. If anything in steps 1-2 fights you for more than
15-20 minutes (auth, sandbox quota, docker issues), stop and tell me — don't
silently burn the morning on setup. Once the baseline row exists and is saved,
stop and report the numbers back to me before we start on fix #1
(environment-bootstrap injection).
```

---

## After this succeeds

Move to the build order in [GAME_PLAN.md](GAME_PLAN.md#tailored-recommendation): environment bootstrap → output cap → completion gate → time-aware execution → loop detection, measuring the slice after each one. Don't start fix #2 until fix #1 has a recorded number next to the baseline.
