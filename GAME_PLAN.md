# Hackathon Game Plan — Infra-Invisible Agent for Non-Technical Founders

Companion to [README.md](README.md) and [VOCAB.md](VOCAB.md). Hackathon date: Saturday 2026-09-06.

Supersedes the earlier TB2.0/mini-swe-agent plan and the first engineer-facing Floci plan (see
git history) — the project narrowed twice: first from "climb a public leaderboard" to "build a
harness for a real workflow," then from "help engineers pick infra" to **"let a non-technical
founder never have to know infra exists, until they've proven product-market fit."** The
harness-engineering vocabulary and judging logic carry over unchanged; the target user and the
success bar for the guide/sensor layers change a lot.

## The idea

[Floci](https://floci.io/) is a suite of local cloud emulators (AWS/Azure/GCP/OCI — real Docker,
real Postgres, real Redis, not mocks) that run entirely on a dev machine, free, no cloud account.

**Comparison point: Replit.** Replit's actual value isn't "runs your code" — it's "hides
everything you'd otherwise have to learn to run your code." This project applies that same move
to one narrower slice: **control planes and local dev infra**, not full hosting. A founder
describes their product in plain language; the agent decides, provisions, verifies, and wires up
the infra on Floci — and is honest the moment something isn't actually working, because the
founder has no way to sanity-check that themselves.

This is still a harness-engineering demo: Floci is the sandbox/execution substrate. The
interesting work is the guide/sensor/state layers around it (VOCAB §3, §4) — but the bar for each
layer is higher than an engineer-facing tool, because there is no human in the loop who can catch
a wrong or half-working setup.

## What changes for a non-technical audience

| For an engineer (prior plan) | For a non-technical founder (this plan) |
|---|---|
| Describes infra needs ("S3 + Lambda + DynamoDB") | Describes the *product* ("users sign up, upload photos, get a weekly email") — the agent does the translation |
| Can debug a wrong free-form floci-cli call | Cannot debug anything — outside the catalog, the agent falls back to the closest proven template and asks a plain-language clarifying question, never improvises silently |
| Verification gate is a nice-to-have | Verification gate is the *entire* trust mechanism — it's the only thing standing between the founder and false confidence |
| `.env` printed for them to paste in | Endpoint config is wired directly into their app's existing config file — no paste step, no concept of "endpoint" exposed |
| Local-only is the whole scope | Local-only is *this stage's* scope — the stack-plan artifact should stay cloud-provider-shaped (VOCAB §2 "unified runtime boundary" style) so it can retarget from Floci to real AWS/GCP later without a redesign, even though that retarget is out of scope for Saturday |

## Architecture

| Layer | Component | Harness role |
|---|---|---|
| Guide | **Product-capability catalog** — maps plain-language product needs ("store user uploads," "send email," "background job") to a Floci service + a pre-verified template, built from the full Floci service list | Environment bootstrap equivalent (VOCAB §5b), but the lookup key is a capability phrase, not a service name — this is the translation layer a founder needs and an engineer wouldn't |
| Guide | **Conservative fallback rule** | Outside the catalog: never freelance a floci-cli call. Offer the nearest template plus one plain-language clarifying question. Matches "advisory banner vs. hard gate" (VOCAB §6d) — a founder-facing gap in coverage should always escalate to a question, never a guess |
| Tool | **Planner** — plain-language request → structured `stack-plan.json` (services, capabilities, provider-neutral shape) | Explicit, inspectable intermediate artifact; also the thing that stays portable to a real-cloud retarget later |
| Tool | **Executor** — wraps `floci-cli` / `docker-compose` start/stop, one call per service | Unified runtime boundary (VOCAB §5b): all side effects go through one tool |
| Sensor | **Verification gate** — hits the *real* endpoint per service before declaring ready, and reports failures in plain language ("the file storage isn't responding yet"), never technical stack traces | Completion gate (VOCAB §5b/§6d) — here it's the founder's only trust signal, so false positives are the worst possible failure mode to demo |
| State | **`stack-state.json`** — durable record of what's running, read on every follow-up so "also let users upload profile pictures" is additive, not a fresh guess that might duplicate or conflict | Progress file pattern (VOCAB §4), and doubles as the artifact a future real-cloud migration path would read |
| Loop | **Failure escalation** — one retry, then stop and report in plain language, never loop silently | Doom-loop detection (VOCAB §5), scoped tighter than an engineer tool because a founder won't notice a silent retry storm |
| Guide | **Auto-wiring output** — writes the local endpoint config directly into the founder's app config/env file, no manual paste step | AX (VOCAB §9) taken further: not just legible to an agent, invisible to the human too |

## Build order

Same rhythm as before: measure before/after each fix, don't stack unmeasured changes.

| # | Fix | Est. time |
|---|---|---|
| 0 | Baseline: bare agent, bash + floci-cli docs in context, no catalog, no gate, given the *plain-language* task set directly (not pre-translated to infra terms) | 30 min |
| 1 | Product-capability catalog + conservative fallback rule | 60 min |
| 2 | Planner tool: plain-language request → `stack-plan.json` | 45 min |
| 3 | Executor tool wrapping floci-cli/docker-compose | 30 min |
| 4 | Verification gate with plain-language failure reporting | 45-60 min |
| 5 | `stack-state.json` for incremental, additive requests | 30 min |
| 6 | Failure escalation (one retry, then stop and report) | 30 min |
| 7 | Auto-wiring into the founder's app config | 30 min |

Stretch (if core lands by mid-afternoon): a one-line "what would it take to go live?" answer —
read `stack-plan.json` and name the real AWS/GCP equivalents, no migration, just proving the
artifact is retarget-shaped. Strong closer because it directly answers "what happens after PMF?"

## Scoring — task set is plain-language product asks, not infra asks

Build the fixed set before touching the harness. Every request is phrased the way a non-technical
founder would actually say it — this is the whole point, so don't write these as infra requests
in disguise:

1. "I need users to be able to sign up and log in" (single capability)
2. "Users should be able to upload a profile photo" (small stack: storage + a table)
3. "When someone uploads a photo, resize it and email them a confirmation" (dependency chain:
   storage → background job → email)
4. Follow-up on #2: "now let them upload more than one photo" (incremental, additive request
   against `stack-state.json`)
5. A request the catalog doesn't cover, e.g. "I need real-time chat" (forces the conservative
   fallback + clarifying question, not a guess)
6. An intentional failure case (ask for something that collides with what's already running, or
   an unsupported capability) — the harness must say so plainly, not hang or fake success

Run each request against **baseline (fix 0)** and again after **each subsequent fix**, same model
throughout. Record per config: success rate (verified working, judged by you, not by the agent's
own claim), time to working environment, tool calls/retries, and — new metric specific to this
framing — **whether any infra term leaked into the agent's response** to the founder (a jargon
leak is a harness failure here, not just a style nit).

Same infrastructure-noise caution as before: keep Docker/Floci state clean between runs or a
stale container from a prior run will silently inflate one config's "success."

## Demo (5 minutes)

1. One slide: the Replit comparison — "Replit hid servers so you could just build; this hides
   infra so you can build without becoming a part-time devops engineer" — plus the baseline
   number.
2. Live run: type request #3 (the dependency-chain one) in plain founder language. Show nothing
   infra-shaped on screen except the plan artifact (for you, the presenter) — the founder-facing
   output should read like a product changelog, not a deploy log.
3. Live run of the incremental follow-up (#4) to show state carrying over.
4. Trigger the failure case (#6) on stage — the strongest moment: it says plainly "that's not
   working yet" instead of confidently claiming success it can't back up.
5. If stretch landed: "what would it take to go live?" — the plan artifact naming real AWS/GCP
   equivalents, no migration performed.
6. Results table: baseline vs. final harness, plus the jargon-leak count column.

## Pair split

Person A: capability catalog, fallback rule, planner (needs floci-cli + product-translation
judgment — the parts that decide *what* founders mean).
Person B: executor, verification gate, state file, loop detection, auto-wiring (pure harness
plumbing, reusable regardless of what's in the catalog).

## Solo

Cut the multi-capability stretch and request #5 (uncataloged fallback). Ship the catalog,
planner, executor, verification gate, and one incremental request — that's the whole story:
plain language in → plan → execute → *prove it worked, honestly* → extend.

## Before Saturday (prep, ~1-2 hrs)

- [x] Install `floci-cli` / `floci-ui` locally, confirm `floci start` and one emulator
      (e.g. S3) come up and respond to a real AWS CLI call against the local endpoint —
      done 2026-09-05. Note for Saturday: on Colima (not Docker Desktop), floci needs
      `/var/run/docker.sock` symlinked to Colima's socket (`sudo ln -sf
      ~/.colima/default/docker.sock /var/run/docker.sock`) before `floci start` works —
      Colima's own forwarded socket path isn't visible inside its VM for the bind-mount
      floci needs for its Lambda emulation. `AWS_ENDPOINT_URL` and `~/.aws/config`
      `s3.addressing_style = path` are now persisted in `~/.zshrc` / `~/.aws/config`.
- [ ] Pull the full Floci service list (AWS/Azure/GCP/OCI) and draft the plain-language
      product-capability catalog on top of it — this translation table is the hardest part
      to get right and shouldn't be built live on Saturday
- [ ] Draft the 6 plain-language product requests (above) so baseline can be measured in the
      first hour, same discipline as [KICKOFF_PROMPT.md](KICKOFF_PROMPT.md)
- [ ] Confirm which agent framework/harness you're building on (Claude Agent SDK, deepagents,
      or a bare loop) — pick now, not Saturday morning
