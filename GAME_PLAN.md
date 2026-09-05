# Hackathon Game Plan — Floci Control-Plane Agent

Companion to [README.md](README.md) and [VOCAB.md](VOCAB.md). Hackathon date: Saturday 2026-09-06.

Supersedes the earlier TB2.0/mini-swe-agent plan (see git history) — the project pivoted from
"climb a public leaderboard" to "build a useful agent harness for a real workflow." The
harness-engineering vocabulary and judging logic carry over unchanged; only the target task and
scoring method change.

## The idea

[Floci](https://floci.io/) is a suite of local cloud emulators (AWS/Azure/GCP/OCI — real Docker,
real Postgres, real Redis, not mocks) that run entirely on a dev machine. The gap: an engineer
still has to know which emulator maps to which cloud service, hand-write the compose/manifest
config, get SDK endpoint URLs right, and manually confirm things actually came up.

**Project**: an agent harness that takes a plain-language infra request ("I need S3 + a Lambda
that reads DynamoDB" / "add a Postgres instance to what's running") and turns it into a running,
*verified* local environment on Floci — then can extend or tear it down on request.

This is still a harness-engineering demo: Floci is the sandbox/execution substrate, and the
interesting work is the guide/sensor/state layers wrapped around it, per the taxonomy in
[VOCAB.md §3, §4](VOCAB.md).

## Architecture

| Layer | Component | Harness role |
|---|---|---|
| Guide | **Service catalog** — structured map of Floci services (cloud, port, floci-cli invocation, common capability → service mapping) built from `floci-cli` service list | Environment bootstrap equivalent (VOCAB §5b): the agent doesn't guess CLI flags or ports, it looks them up |
| Guide | **Stack templates** — 5-8 pre-verified common combos (S3+Lambda+DynamoDB, RDS+Redis, API Gateway+Lambda) | Cuts exploration turns for the common case; agent still free-forms outside the catalog |
| Tool | **Planner** — NL request → structured plan (`stack-plan.json`: services, ports, env vars) | Forces an explicit, inspectable intermediate artifact before anything executes |
| Tool | **Executor** — wraps `floci-cli` / `docker-compose` start/stop, one call per service, structured result back | Unified runtime boundary (VOCAB §5b): all side effects go through one tool, not raw bash |
| Sensor | **Verification gate** — after start, hits the *real* endpoint per service (`aws --endpoint-url=... s3 ls`, an actual DB connection, not "container running") before declaring ready | Completion gate (VOCAB §5b/§6d): no "done" claim without live proof |
| State | **`floci-stack.json`** — durable record of what's running, so a follow-up request ("also add Redis") is incremental, not a fresh guess | Progress file / feature list pattern (VOCAB §4), applied to infra instead of code |
| Loop | **Failure escalation** — port conflict or failed container after 1 retry stops and reports, doesn't loop silently | Doom-loop detection (VOCAB §5), scoped to infra ops where blind retry can double-provision |
| Guide | **Endpoint wiring output** — generates `.env` / SDK profile pointing at local endpoints, printed at the end | AX (VOCAB §9): the deliverable a human engineer actually pastes into their app |

## Build order

Same rhythm as before: measure before/after each fix, don't stack unmeasured changes.

| # | Fix | Est. time |
|---|---|---|
| 0 | Baseline: bare agent, bash + floci-cli --help/docs in context, no catalog, no verification gate | 30 min |
| 1 | Service catalog + stack templates (guide) | 45 min |
| 2 | Planner tool: NL request → `stack-plan.json` | 45 min |
| 3 | Executor tool wrapping floci-cli/docker-compose | 30 min |
| 4 | Verification gate: real endpoint checks per service, blocks "ready" claim | 45-60 min |
| 5 | State file for incremental requests | 30 min |
| 6 | Failure escalation / loop detection on repeated start failures | 30 min |

Stretch (if core lands by mid-afternoon): teardown command that reads the state file and cleanly
stops only what it started; or a second cloud in the same request (AWS + GCP stack) to show the
catalog generalizes past one provider.

## Scoring — no public leaderboard, so define the task set first

Build a fixed set of 6-10 requests before touching the harness, ordered easy → hard:

1. Single service ("I need an S3 bucket")
2. Small stack (S3 + Lambda)
3. Stack with a real dependency chain (Lambda reads DynamoDB, writes to S3)
4. Incremental add ("now also give me Postgres") on top of #2's running state
5. A request the catalog doesn't cover (forces free-form floci-cli use)
6. An intentional failure case (ask for a port already in use, or an unsupported service) —
   the harness should report clearly, not hang or fake success

Run each request against **baseline (fix 0)** and again after **each subsequent fix**, same model
throughout. Record per config: success rate (environment verified working, not just "agent said
done"), time to working environment, number of tool calls/retries, and whether the failure case
(#6) was reported honestly.

Same infrastructure-noise caution as before applies even though there's no shared leaderboard:
keep the machine/Docker state clean between runs (`docker ps` empty, ports free) or a stale
container from a prior run will silently inflate one config's "success."

## Demo (5 minutes)

1. One slide: the gap (Floci is powerful but manual) and the before/after numbers.
2. Live run: speak/type request #3 (the dependency-chain stack) against the finished harness —
   show the plan artifact, the executor calls, the verification gate actually hitting real
   endpoints, and the final `.env` output.
3. Live run of the incremental add (#4) to show the state file working.
4. Trigger the failure case (#6) on stage — this is the strongest "harness, not just a wrapper"
   moment: show it refusing to claim success.
5. Results table: baseline vs. final harness across the 6-10 requests.

## Pair split

Person A: catalog, templates, planner (layers that need floci-cli familiarity).
Person B: executor, verification gate, state file, loop detection (layers that are pure harness
plumbing, reusable regardless of which cloud/services get added to the catalog).

## Solo

Cut the multi-cloud stretch and request #5 (uncataloged free-form). Ship the catalog, planner,
executor, verification gate, and one incremental request — that's the whole story: plan → execute
→ *prove it worked* → extend.

## Before Saturday (prep, ~1-2 hrs)

- [ ] Install `floci-cli` / `floci-ui` locally, confirm `floci start` and one emulator
      (e.g. S3) come up and respond to a real AWS CLI call against the local endpoint
- [ ] Pull the full Floci service list (AWS/Azure/GCP/OCI) to seed the catalog — don't build
      this live on Saturday
- [ ] Draft the 6-10 request task set (above) so baseline can be measured in the first hour,
      same discipline as the original [KICKOFF_PROMPT.md](KICKOFF_PROMPT.md)
- [ ] Confirm which agent framework/harness you're building on (Claude Agent SDK, deepagents,
      or a bare loop) — pick now, not Saturday morning
