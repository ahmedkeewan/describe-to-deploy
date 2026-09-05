# Founder Interface Design — Floci Infra-Invisible Agent

Design spec for the founder-facing interface described in [GAME_PLAN.md](../GAME_PLAN.md).
Written 2026-09-05, the evening before the hackathon. Companion to
[catalog/README.md](../catalog/README.md) (what the agent can provision) and
[tasks/README.md](../tasks/README.md) (how it is scored).

## The product in one sentence

**A founder writes what they need in plain English — "I need users to be able to upload photos" —
and the services that makes possible are set up on Floci, verified for real, and reported back in
words they understand.**

No codebase required. No account, no cloud, no deploy. The founder describes a product need; the
infrastructure to support it exists a minute later, and its status is honest.

## Scope

**In scope**: what the founder types, what they see while the agent works, how success and
failure are expressed, and what the harness must write for the UI to render.

**Out of scope**: hosting, deployment, cloud retargeting, accounts, multi-user, anything
persisted off the founder's machine. Local-only, deliberately, at this stage.

**Explicitly not required**: an existing project. If the founder happens to have one in the
directory they launched from, the agent can do more (see [Optional: an existing
project](#optional-an-existing-project)). Everything essential works without it.

## Who this is for, and the one fact that shapes everything

A non-technical founder who knows what their product needs to do and has no way to make the
infrastructure for it exist. Their alternative today is a cloud account, IAM, and configuring
services they cannot name.

**This user cannot verify anything themselves.** They cannot read a log, judge a config, or tell
a working setup from a broken one. So the interface has one job beyond being usable: never let
them believe something works when it doesn't.

## What the baseline run says the interface is actually for

The fix-0 baseline recorded in [tasks/README.md](../tasks/README.md) on 2026-09-05 passed
5 of 6 tasks. A capable model provisions and verifies real infrastructure without any harness at
all, and its honesty under genuine failure (t6) was accurate down to the error string.

Two gaps remained, and **both are interface problems**:

| Baseline failure | What the interface does about it |
|---|---|
| **Jargon leak, 5 of 6 responses** — Cognito, JWTs, CORS, presigned URL, `USER_PASSWORD_AUTH` surfaced to the founder | The two-channel event contract makes founder-facing jargon *unrepresentable*, not merely discouraged. See [Jargon leak prevention](#jargon-leak-prevention-is-structural-not-behavioural). |
| **t5 overreach** — asked for uncataloged "real-time chat," it silently built a WebSocket API Gateway v2 stack, 3 Lambdas, a DynamoDB table, and an undocumented `Host`-header workaround | The confirmation checklist makes scope *visible in founder language* before anything is provisioned. Three Lambdas cannot appear silently when the founder is looking at a list of plain-English capabilities. |

This is the honest framing for the demo: the baseline is not incompetent, and overstating that
gap is a credibility risk. The interface is where scope discipline and translation are enforced.

## The language rule

**Every word the founder reads must be understandable by someone who has never heard of cloud
infrastructure. Zero technical jargon, without exception.** This is not a style preference — the
baseline leaked infra terms in 5 of 6 responses, and it is one of the two measured failures this
interface exists to fix.

Never appears in front of the founder:

```
  service names      S3, Cognito, DynamoDB, Lambda, SES, RDS, Redis
  infra nouns        bucket, table, instance, container, endpoint, port,
                     region, ARN, IAM, role, policy, queue, trigger
  protocol/format    JWT, CORS, presigned URL, API, SDK, JSON, YAML, env var
  ops verbs          provision, deploy, configure, spin up, boot, mount
  error surfaces     exit codes, stack traces, exception names,
                     AccessDenied, NotAuthorizedException
  file paths         .env, docker-compose.yml, ~/.aws/config
```

Say instead:

| Instead of | Say |
|---|---|
| "Provisioned an S3 bucket" | "a place to store photos" |
| "Configured a Cognito user pool" | "a way for people to sign up and log in" |
| "Created a DynamoDB table" | "somewhere to keep your information" |
| "Deployed a Lambda function" | "something that runs when a photo arrives" |
| "SES email delivery configured" | "a way to send email" |
| "Verified the endpoint responds" | "stored a test file and read it back" |
| "AccessDenied: object is protected" | "I can't change these older photos" |
| "Wrote AWS_ENDPOINT_URL to .env" | "connected it to your app" |

Three rules for writing any founder-facing string:

1. **Describe what it does for their product, never what it is.** A founder cares that people can
   upload photos, not that object storage exists.
2. **Use the words they used.** If they said "photos," the row says photos — not "files," not
   "objects," not "media assets."
3. **A sentence that needs a follow-up explanation has failed.** There is no tooltip, no
   drill-down, no "learn more." One plain sentence or it goes back to the catalog author.

Enforcement is structural, not editorial — see [Jargon leak prevention](#jargon-leak-prevention-is-structural-not-behavioural).
Every founder-facing string lives in [capabilities.json](../catalog/capabilities.json) and
is reviewed once, rather than being generated fresh on every run and hoped over.

## Platform

A **local web app**. The harness runs as a local process and serves a single-page UI in the
browser.

```
  harness process (local)          browser
  ├─ agent + tools            ──▶  localhost:7777
  ├─ writes the artifacts          chat + capability board
  └─ serves the UI                 reads events.jsonl over SSE
```

| Rejected | Why |
|---|---|
| CLI / TUI | A founder who cannot debug will not work in a terminal. Also weak for live status and a clickable checklist. |
| Desktop app (Electron/Tauri) | Right for a real product — proper icon, no localhost. A packaging project this build has no time for. |
| Inside an existing agent client | Cannot control founder-facing rendering, which is the distinctive part of this project. |

Precedent: Floci already ships `floci-ui` as a local web UI, so a Floci user is already in this
pattern.

**Honest caveat.** Launching the process is a terminal command. Do not claim "zero technical
steps" — there is exactly one. If asked: in a real product this is a downloadable app, and the
browser UI is unchanged.

## Coupling: the UI is a pure renderer

The UI has no logic and cannot provision anything. The harness writes artifacts; the UI draws
them.

```
harness (CLI, scoreable)          ui (disposable)
  stack-plan.json      ─────────▶  the checklist
  stack-state.json     ─────────▶  the board
  events.jsonl         ─────────▶  live progress
```

1. **Scoring stays intact.** [tasks/task-set.json](../tasks/task-set.json) measures the
   CLI. The UI sits outside the measurement path and cannot contaminate the before/after numbers.
2. **It is cuttable.** If the UI does not land, the demo degrades to a terminal run rather than
   collapsing.
3. **It matches the harness vocabulary** — external state as the handoff between components
   ([VOCAB.md](../VOCAB.md) §4).

## The journey

```
   (launch)
1. what do you need?         plain English, one sentence
2. confirm the checklist     scope made visible
3. watch it get set up       and proven, one row at a time
```

Three steps. Nothing in them requires a project, a file, or a path.

## Step 1 — the ask

The opening screen asks one question and offers examples in the founder's own register, not
infrastructure examples:

```
  What do you need your product to do?

  ▸ _

  for example:
    "I need users to be able to sign up and log in"
    "users should be able to upload a profile photo"
    "when someone uploads a photo, email them a confirmation"
```

The examples are the plain-language phrasings from
[tasks/task-set.json](../tasks/task-set.json), so what a founder is nudged toward typing is
exactly what the harness is scored against.

Nothing is asked about projects, folders, languages, or files.

## Step 2 — the confirmation checklist

The checklist is the gate, and it is the interface's answer to the baseline's t5 overreach.
Everything arrives pre-checked; the founder unchecks anything they did not ask for.

```
  Here's what I'll set up for that:

    ☑ a place to store photos
    ☑ something to resize them
    ☑ a way to send email

    [ set these up ]
```

They cannot judge infrastructure, but they can judge *"I never asked for email."* That is the
whole point: scope stated in terms the founder can actually evaluate, before any side effect.

`depends_on` in [capabilities.json](../catalog/capabilities.json) makes unchecking safe:

```
    ☐ a place to store photos
    ☒ something to resize them   ← auto-unchecked
      "this needs somewhere to put the photos first"
```

**When the request falls outside the catalog**, the conservative fallback rule fires here rather
than producing a checklist — the founder sees a plain-language question, never a silently
expanded plan:

```
  I can give you a place to store and look up
  messages, but not live chat yet.

  [ that works ]   [ no, I need live chat ]
```

## Step 3 — the board

```
┌──────────────────────────────────────────────┐
│  you ▸ when someone uploads a photo,         │  ← conversation
│        email them a confirmation             │    ephemeral
│                                              │
│  Setting that up now.                        │
├──────────────────────────────────────────────┤
│  YOUR PRODUCT                                │
│                                              │  ← board
│  ● photo storage       working               │    persistent
│    stored a test file and read it back       │    = stack-state
│    last checked 12s ago                      │
│                                              │
│  ● accounts            working               │
│    created a test account and signed in      │
│    last checked 1m ago                       │
│                                              │
│  ○ email               not working yet       │
│    nothing arrived when I sent a test        │
└──────────────────────────────────────────────┘
```

Rules:

- **Every row carries its proof sentence, always visible.** Not on hover, not behind a
  disclosure. Seeing *what was actually checked*, in words they understand, is the founder's only
  defence against false confidence. This is the product.
- **The board renders `stack-state.json`, not the conversation.** An incremental request visibly
  *updates a row* rather than appending one, so state carrying over is something an audience can
  see rather than something the presenter narrates.
- **No modes, no keyboard shortcuts, no hidden panes.** Every affordance is a labelled button.
  Anything a founder must be told about is a design failure.
- **Rows are not clickable.** The proof sentence is the whole disclosure. Anything needing more
  explanation is a catalog-writing failure, not a missing affordance.

## Trust vocabulary

Five states the founder can ever see:

```
  ◐  setting up…               working on it
  ●  working                   + proof sentence, always shown
  ○  not working yet           honest failure
  ⊘  stopped — needs a person  escalated after one retry
  ?  waiting on your answer    fallback rule fired
```

**There is deliberately no state meaning "started but unverified."** A container that is up but
has not passed its check stays `setting up…` — it never gets to look like success. That single
omission is the trust thesis expressed as a state machine, and it is why the verification gate
cannot be quietly downgraded later: there is nowhere in the UI to put a half-truth.

- **No percentage bars, no ETAs.** Nothing here has a knowable duration, and a stalled 80% is a
  lie.
- **Every `working` row shows "last checked N ago."** Proof has a shelf life. On incremental
  requests the board visibly re-checks existing rows.

## Failure presentation

```
  ○ email                 not working yet
    nothing arrived when I sent a test

    Your photo storage still works — this
    one piece isn't ready.

    [ try again ]
```

1. **Name it in product terms, then say what it means for them.** "Email isn't working" is half
   of what a founder needs; "your photo storage still works" is the other half.
2. **Exactly one primary action.** Never a menu of recovery options.
3. **A partial run never reads as success.** If any row is red, the summary line is neutral or
   negative. No "Done! (2 of 3)".
4. **No stack traces, exit codes, or service names** in the founder pane, under any condition.
   Failure detail goes to `event.dev`.

## Jargon leak prevention is structural, not behavioural

Everything the UI renders comes from `events.jsonl`, append-only. **Every event carries two
channels:**

```json
{
  "seq": 17,
  "t": "2026-09-06T10:04:12Z",
  "kind": "verify.pass",
  "capability": "file-storage",

  "founder": {
    "label":  "a place to store photos",
    "status": "proven",
    "proof":  "stored a test file and read it back"
  },

  "dev": {
    "service":  "s3",
    "endpoint": "http://localhost:4566",
    "cmd":      "aws s3api put-object --bucket test ...",
    "exit":     0,
    "ms":       412
  }
}
```

The founder pane renders `event.founder` and nothing else. The model never writes into
`founder` — those strings come from [capabilities.json](../catalog/capabilities.json).

This turns the game plan's **jargon-leak metric from a behaviour we hope for into a property of
the interface**. Given the baseline leaked infra terms in 5 of 6 responses, this is the single
highest-value structural change in the design. A leak would require a service name to be
committed into a catalog field — a code review away, not a sampling accident. It is Hashimoto's
rule ([README.md](../README.md) Tier 1) applied to the UI layer: engineer the harness so
the mistake cannot happen again.

Event kinds:

```
plan.proposed      question.asked      provision.start
plan.approved      escalate.stop       provision.ok/fail
                                       verify.start
                                       verify.pass/fail
```

**Where the strings live.** Every founder-facing string is drafted in
[founder-copy.md](founder-copy.md) — status words, proof sentences for all 12 capabilities, and
all screen text. They are kept together because the language rule is only checkable when the
whole vocabulary sits side by side.

**Catalog dependency.** For the founder pane to render, `capabilities.json` needs a founder-safe
proof sentence per verify check — `verify.founder_proof`, alongside the existing `verify.cli`.
The sentences are already written in [founder-copy.md](founder-copy.md); adopting them is
roughly a 15-minute change across the 12 entries, owned by whoever owns the catalog.

## Optional: an existing project

If the directory the harness was launched from happens to contain a project, the agent can do
more. Nothing here is required, nothing is asked of the founder, and the concept is never raised
if no project is present.

```
launch
  │
  ├── no project (default) ──▶ provision + verify services
  │                            board goes green
  │                            config written to the launch directory
  │
  └── project detected ──────▶ same, plus:
                               wire config into it
                               verify through the app where possible
```

The only visible difference is the strength of the proof sentence:

```
no project    ● photo storage    working
                "stored a test file and read it back"

with project  ● photo uploads    working
                "uploaded a photo through your app and loaded it back"
```

The second is the honest one — it proves what the founder cares about rather than what the
harness provisioned. It also catches the false-confidence case where an app constructs a client
with an explicit cloud endpoint, ignores the local wiring, and fails while the emulator check
still passes.

Build the default path first. The project path is a bonus and stays cuttable; auto-wiring
remains late in the build order, where the game plan already has it.

## Implementation

```
server   the harness's existing language (Python or Node)
         + one SSE endpoint tailing events.jsonl
         + one POST for the founder's message
         + one POST for the checklist confirmation
ui       ONE static HTML file. No build step, no framework.
         The board is a list re-rendered on each event.
```

The UI is a renderer, so a single file is genuinely sufficient — and it stays cuttable if the day
runs short.

## What this implies for GAME_PLAN.md

1. **The demo's framing should follow the baseline data.** Lead with scope discipline (t5) and
   translation (5/6 jargon leaks), not "the baseline can't do it" — it can, and
   [tasks/README.md](../tasks/README.md) warns explicitly against overstating the gap.
2. **The checklist gate deserves its own line in the architecture table.** It is currently
   implicit in the planner, but it is the mechanism that prevents t5's overreach, and it is
   founder-visible.
3. **Auto-wiring (fix #7) stays optional and late.** It applies only when a project happens to be
   present, and none of `t1`–`t6` require it.

## Open question

- Does the "no project" path need to leave anything behind on disk — a config file in the launch
  directory — or is the green board with its proof sentences the whole deliverable? Every scored
  task in `t1`–`t6` judges success by querying Floci directly, so nothing currently depends on a
  written artifact.
