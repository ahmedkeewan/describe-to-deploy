# Founder Interface — Design Spec

The founder-facing surface of the infra-invisible agent. This document covers the interface
layer only — see [harness/README.md](../harness/README.md) for the harness architecture it sits
on top of.

## Status: a designed surface, not a shipped one

Read this before the rest of the document, so you don't mistake it for a description of what
exists today.

**What founders actually use right now is chat** — Claude Desktop, Claude Code, or Cursor, talking
to the MCP server in [`harness/`](../harness/). No dedicated app, no dashboard required. That is
the shipped product, and [the founder site](https://ahmedkeewan.github.io/service-buddy/) is
written around it.

**What this folder describes is a 16-screen web app** that has never been built. It's a design
exploration — a spec, a copy deck, and a canvas-regeneration prompt — kept because the thinking in
it is good, not because it's on a roadmap with a date.

The two are **not competing visions**; they're two surfaces over the same backend, at very
different stages:

- **Entry point**: none exists for the web app. There is no URL, no link from chat, nothing to
  reach. It is design-canvas files only.
- **State model**: undecided, deliberately. How a persistent multi-screen app would share
  session and environment state with a turn-by-turn chat interface is a real question, but not one
  worth answering until the app is actually scheduled for planning. Whoever picks this up decides
  it then.
- **Founder-facing visibility**: the README and the Pages site will **not** mention or link to the
  web app while it stays unbuilt. Revisit that the moment someone plans the work, not before.

Everything below is written in the present tense because it's a design spec. Read it as "this is
how it would work", not "this is how it works".

---

## In one sentence

**A non-technical founder writes what they need in plain English — "I need users to be able to
upload photos" — and the infrastructure that makes it possible is set up on Floci, verified for
real, and reported back in words they understand.**

No codebase. No cloud account. No deploy. A founder describes a product need; the infrastructure
exists a minute later, and its status is honest.

## Why an interface layer is the harness work

The measured no-harness baseline ([tasks/README.md](../tasks/README.md)) already passes 5 of 6
tasks. A capable model provisions real infrastructure without any harness at all. **So the
harness's value is not "it works vs. it doesn't"** — and claiming otherwise would be its own
credibility risk.

The baseline's two actual failures are both failures of what the user *sees*:

| Baseline failure | Measured | What the interface does |
|---|---|---|
| **Jargon leak** — Cognito, JWTs, CORS, presigned URL, `USER_PASSWORD_AUTH` surfaced to a founder who cannot parse them | 5 of 6 responses | The [two-channel event contract](#jargon-leak-prevention-is-structural-not-behavioural) makes founder-facing jargon **unrepresentable**, not merely discouraged |
| **Scope overreach** — asked for uncataloged "real-time chat," it silently built a WebSocket API Gateway v2 stack, 3 Lambdas, a DynamoDB table, and an undocumented `Host`-header workaround | t5 | The [confirmation checklist](#step-2--the-confirmation-checklist) states scope in founder language *before* provisioning. Three Lambdas cannot appear silently next to a plain-English list |

Both are now moving in the scored table:

```
                    no harness   single-agent harness (+ catalog)
  success rate      5/6          6/6
  jargon leaks      5/6          0/6
  t5 overreach      fail         fixed
  wall clock       ~1040s        ~310s
  tool calls        ~87           21
```

The interface is where those two properties are *enforced* rather than hoped for.

## What is novel here

**A failure mode made unrepresentable instead of instructed against.** The shipped single-agent
harness ([harness/build_prompt.py](../harness/build_prompt.py)) enforces the language rule by
telling the model to obey it:

> "This is the single most important rule in this prompt: a jargon leak in your final report is a
> failure even if the infrastructure itself works perfectly."

That works — 0 of 6 leaks, measured. But it is a behaviour under instruction: it holds because
the model complied, and one prompt edit, model swap, or unusual request away, it may not. The
interface removes the possibility instead. Founder-facing text is drawn only from reviewed
plain-English strings; **the model's own prose never reaches the founder pane at all.** A leak
would require committing a service name into a catalog field — a code review away, not a sampling
accident.

That is Hashimoto's rule ([README.md](../README.md) Tier 1) — *engineer the harness so the agent
can never make that mistake again* — applied to the presentation layer, which is not where it is
usually applied. It is also the same move the existing harness already makes elsewhere:
`build_prompt.py` generates the prompt *from* `capabilities.json` precisely so the two cannot
drift. This extends that principle from the prompt to the output.

**A trust vocabulary with a deliberate hole in it.** There is no status meaning "started but
unverified" ([Trust vocabulary](#trust-vocabulary)). Something created but unproven stays
`setting up…`. The verification gate cannot be quietly downgraded later because there is nowhere
in the UI to put a half-truth.

## How it maps to harness engineering

| Interface mechanism | Harness concept ([VOCAB.md](../research/VOCAB.md)) |
|---|---|
| UI reads `stack-state.json` / `events.jsonl`, never shared memory | External state as the handoff between components (§4) |
| Confirmation checklist blocks provisioning until scope is confirmed | Gate — a sensor that blocks rather than reports (§3, §6d) |
| No status for "started but unverified" | Completion gate; evidence-based terminal states (§5b) |
| Proof sentence on every row, sourced from the check that ran | Computational sensor surfaced to the human (§3) |
| `founder` / `dev` channels on every event | Guide/AX separation (§9) — the same event, two audiences |
| Fallback rule renders as a question, never an expanded plan | Advisory-vs-hard-gate distinction (§6d) |
| Append-only `events.jsonl` as the render source | Session as append-only log (Tier 1b, Managed Agents) |

## Scope

**In scope**: what the founder types, what they see while the agent works, how success and
failure are expressed, and what the harness must write for the UI to render.

**Out of scope**: hosting, deployment, cloud retargeting, accounts, multi-user, anything
persisted off the founder's machine. Local-only, deliberately, at this stage.

**Explicitly not required**: an existing project. If one happens to be in the directory the
harness was launched from, the agent can do more ([Optional: an existing
project](#optional-an-existing-project)). Everything essential works without it.

## Who this is for, and the one fact that shapes everything

A non-technical founder who knows what their product needs to do and has no way to make the
infrastructure for it exist. Their alternative today is a cloud account, IAM, and configuring
services they cannot name.

**This user cannot verify anything themselves.** They cannot read a log, judge a config, or tell
a working setup from a broken one. So the interface has one job beyond being usable: never let
them believe something works when it doesn't.

Every decision below follows from that sentence.

## What's in this folder

| | |
|---|---|
| [README.md](README.md) — this file | The design: language rule, platform, coupling, the journey, trust vocabulary, disclosure, event contract |
| [founder-copy.md](founder-copy.md) | Every word the founder can read, in one place — status words, proof sentences for all 13 capabilities, screen text, translation reference |
| [design-brief.md](design-brief.md) | The visual brief: tone, hard constraints, and the screen inventory a designer draws from |
| [regenerate-prompt.md](regenerate-prompt.md) | A self-contained prompt that rebuilds the whole 16-screen canvas, with exact tokens and copy |
| [founder-interface.html](founder-interface.html) | The 16-screen canvas, exported. Open it in a browser to pan through every screen |
| [canvas/](canvas/) | Source for that canvas — one `.dc.html` per screen, `canvas.json` for layout, `build.mjs` to regenerate them all |

Read in ~3 minutes: [In one sentence](#in-one-sentence) → [Why an interface layer is the harness
work](#why-an-interface-layer-is-the-harness-work) → [What is novel](#what-is-novel-here) →
[The journey](#the-journey) → [Trust vocabulary](#trust-vocabulary).

---

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
   ([VOCAB.md](../research/VOCAB.md) §4).

## The journey

```
   (launch)
1. what do you need?         plain English, one sentence
2. confirm the checklist     scope made visible
3. watch it get set up       and proven, one row at a time
   └ expand a row            what it does, what was checked, what to do
   └ export                  a record you can hand to anyone
```

Nothing in this requires a project, a file, or a path.

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

## Step 3 — the two panes

The app is one fixed layout, 1200 × 760 at desktop. Conversation left, product sidebar right.

```
┌──────────────────────────────────────────────────────────┐
│  ▣ Photo app ⌄                                    ⚙      │  header
├────────────────────────────────┬─────────────────────────┤
│                                │  Your product      3 …  │
│  you ▸ when someone uploads    │ ───────────────────────  │
│        a photo, email them     │  ● photo storage     ⌄  │
│        a confirmation          │    stored a test file,  │
│                                │    read it back …       │
│  Setting that up now.          │    last checked 12s ago │
│                                │ ───────────────────────  │
│                                │  ○ email             ⌄  │
│                                │    nothing arrived …    │
├────────────────────────────────┤    [try again][get help]│
│  Ask for something else…       │ ───────────────────────  │
│                                │  ↓ Export what you have │
└────────────────────────────────┴─────────────────────────┘
     conversation, ephemeral        the durable list
```

Rules:

- **The sidebar is permanent.** It is the answer to *"what do I have?"*, and the conversation
  never pushes it off screen. A founder should never have to scroll a chat log to find out what
  their product currently has.
- **Every row carries its proof sentence, always visible.** Not on hover, not behind a
  disclosure. Seeing *what was actually checked*, in words they understand, is the founder's only
  defence against false confidence. This is the product.
- **The sidebar renders `stack-state.json`, not the conversation.** An incremental request visibly
  *updates a row* rather than appending one, so state carrying over is something an audience can
  see rather than something the presenter narrates.
- **No modes, no keyboard shortcuts, no hidden panes.** Every affordance is a labelled button.
  Anything a founder must be told about is a design failure.

## Disclosure — depth without jargon

An earlier draft of this spec said the proof sentence was the whole disclosure and rows should
not expand. That was wrong, and it conflated two different rules:

```diff
- The proof sentence is the whole disclosure. No expansion.
+ Expanding a row reveals more PLAIN LANGUAGE, never more jargon.
+ Depth is fine. Changing register is not.
```

The spec's own analogy undercut it: a doctor's report *has* depth — a summary line, then what was
measured, then what to do. Refusing all detail leaves a founder unable to retry, rebuild, or
escalate, which makes the product unusable rather than honest.

An expanded row carries, in sentence-case sections:

```
What this gives you     one plain sentence
What I checked          the individual checks, each with a time
History                 set up / checked — worked, with times
                        [ check it again ]  [ remove ]
```

A failed row swaps the middle section for **What I tried** — a plain-language timeline of the
attempts — and offers three actions: `try again`, `set it up fresh`, `get help`.

### Where the technical layer surfaces

`get help` opens a modal carrying `event.dev` — real service names, commands, exit codes — under
a heading that says who it is for:

```
  Details for a developer                    [ copy ]

  You don't need to read this. If you have someone
  technical, send it to them.

  capability   send-email
  service      ses · floci 2.0.1
  check        aws ses list-identities
  result       exit 254 — could not connect
```

**This is the only place jargon is permitted**, and the language rule survives
intact because the panel is explicitly *addressed to someone else*. It is not the founder failing
to understand — it is a handoff, labelled as one. It is also the honest answer to "how does a
non-technical founder debug?" They don't. They forward.

## Export — what the founder walks away with

The sidebar's footer carries one permanent action, `Export what you have`. It resolves what a
founder is left holding when the tool is closed, and it reuses the same two-audience split as
everything else — a single checkbox, off by default, switches which one is produced.

```
  What goes in                      As
   ☑ What your product has           ● A page to share      PDF
   ☑ How the pieces fit together     ○ Just the diagram     image
   ☑ What was checked, and when      ○ A written summary    text
   ☐ Technical details               ○ Files a developer needs
```

**Plain export** — a shareable page: a diagram in the founder's own words (*someone uploads a
photo → photo storage → resizing → a confirmation email*), the capability list with its proof
sentences and dates, and a closing note that none of it is reachable from the internet yet. That
last line matters: a founder showing this to an investor needs to know what it is not.

**Technical export** — the same diagram with real resource names, a table of what verified each
capability, and the file manifest: `docker-compose.yml`, `.env`, `endpoints.json`,
`stack-plan.json`, `verification.md`.

If anything here slips, **protect the diagram**. It is the only view that shows how the pieces
connect, and it is the artifact a founder actually shows people.

## Where the board's state lives

The board renders `stack-state.json`, so that file needs a home that works when there is no
project — which is the default path.

**One Floci per machine, therefore one stack, therefore one state file.**

```
~/.floci-agent/stack-state.json     machine-level, always findable
```

All of Floci's emulated services live in a single instance sharing one set of ports and
namespaces, so two independent stacks cannot coexist regardless of where their state is filed.
The location follows the substrate.

Deliberately **not** the launch directory. In the default path `cwd` is arbitrary — a founder may
launch from anywhere — so writing there scatters files into folders unrelated to the product, and
relaunching from a different directory would silently lose everything they built.

A project, when present, does not change where the truth lives. It is recorded as a field:

```json
{
  "project": null,
  "floci_version": "2.0.1",
  "capabilities": {
    "file-storage": {
      "status": "working",
      "last_verified": "2026-09-06T10:07:44Z",
      "bucketName": "photoapp-uploads"
    }
  }
}
```

`project` tells the wiring step where to write and lets the board name what it is working on. The
board reads the same file either way.

### The state file is never trusted on startup

A file describing running services is a claim, and claims go stale — someone tears Floci down, or
reboots, and the file still says three things are working.

**Every row must be reconciled against live Floci before it renders green.**

```
on start
  read stack-state.json
  for each capability:
    re-run its check against live Floci
      passes  → ● working, "last checked just now"
      fails   → ○ not working yet
      missing → drop the row
```

This is [VOCAB.md](../research/VOCAB.md) §6d — reconcile tracked state against actual state before acting
on it — and it is the same principle as the [trust vocabulary](#trust-vocabulary) below: a row is
green because a check just passed, never because a file said so.

It is also why the default path writes **no founder-facing config file**. Such a file would be a
second claim on disk, with no reader (there is no app in this path) and no reconciliation — the
file equivalent of the "started but unverified" status this design deliberately has no room for.
The rule: *write config only where you can verify it is being used*, which is the project path
and only the project path.

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
[founder-copy.md](founder-copy.md) — status words, proof sentences for all 13 capabilities, and
all screen text. They are kept together because the language rule is only checkable when the
whole vocabulary sits side by side.

**Catalog dependency.** For the founder pane to render, `capabilities.json` needs a founder-safe
proof sentence per verify check — `verify.founder_proof`, alongside the existing `verify.cli`.
The sentences are already written in [founder-copy.md](founder-copy.md); adopting them is
roughly a 15-minute change across the 13 entries, owned by whoever owns the catalog.

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

## How this sits on the harness as it exists today

Read from [harness/build_prompt.py](../harness/build_prompt.py) at the single-agent stage
(`--mode single-agent`), so the sequencing below is what the code actually supported at that
point, not an assumption. The harness has since grown well past this point — see
[harness/README.md](../harness/README.md) for its current architecture — but the sequencing
narrative below is kept as the honest record of how the interface's own requirements were staged
against the harness as it existed at each step.

**What already lined up at the single-agent stage:**

| True at the single-agent stage | What the interface does with it |
|---|---|
| The prompt is *generated from* `capabilities.json`, so the two cannot drift | Founder-facing strings live in the same file and inherit the same guarantee — add a capability, and its plain-English wording flows through automatically |
| The fallback rule appends unmatched requests to a durable log rather than dropping them | Renders as *"I've made a note of what you asked for"* ([founder-copy.md](founder-copy.md)) — nothing new is required |
| The prompt already forbids naming services in the final report | Same intent; the interface makes it structural instead of instructed |
| `verify.cli` is run for real before anything is claimed | Becomes the proof sentence under each row — the check that ran *is* what the founder reads |

**What the interface needed that did not exist yet, at that point:**

| Needed | Depended on |
|---|---|
| `events.jsonl` with `founder` / `dev` channels | The event-log/executor work (now shipped as `harness/events.py`). At the single-agent stage the agent was Bash-only and produced one final prose report, so there was no event stream to render |
| Live board updates during a run | Same — until the event log shipped, a UI could only render the end state |
| `verify.founder_proof` in the catalog | A ~15-minute catalog change; sentences already drafted in [founder-copy.md](founder-copy.md) |

**Honest sequencing (historical).** The interface was not buildable before the event-log work
landed, and was most valuable once the verification gate (now `harness/verify_gate.py`) shipped,
since that is what gives the proof sentences something real to say. Both have since shipped; the
harness's own README documents the current tool surface.

## Implementation

```
server   the harness's existing language (Python or Node)
         + one SSE endpoint tailing events.jsonl
         + one POST for the founder's message
         + one POST for the checklist confirmation
ui       ONE static HTML file. No build step, no framework.
         The board is a list re-rendered on each event.
```

The UI is a renderer, so a single file is genuinely sufficient — and it stays easy to cut if
scope needs to shrink.

## What this looks like in a live run

The interface carries three of the demo beats in [GAME_PLAN.md](../research/history/GAME_PLAN.md#demo-5-minutes):

| Beat | What the audience sees | What it proves |
|---|---|---|
| **The ask** | A plain-English sentence typed in, and a checklist of plain-English capabilities coming back | Translation works, and scope is stated before anything runs |
| **The board filling in** | Rows moving `setting up…` → `working`, each with the sentence describing what was actually checked | Claims are backed by real checks, not the agent's say-so |
| **The failure case (t6)** | A row that says `not working yet` and stays there | The strongest moment: it declines to claim success it cannot back up |

The demo screen never shows a service name, a port, or an error code. That is checkable live —
and it is the 5/6 → 0/6 jargon result made visible rather than asserted from a table.

## What this implies for research/history/GAME_PLAN.md

1. **The demo's framing should follow the baseline data.** Lead with scope discipline (t5) and
   translation (5/6 jargon leaks), not "the baseline can't do it" — it can, and
   [tasks/README.md](../tasks/README.md) warns explicitly against overstating the gap.
2. **The checklist gate deserves its own line in the architecture table.** It is currently
   implicit in the planner, but it is the mechanism that prevents t5's overreach, and it is
   founder-visible.
3. **Auto-wiring stays optional and late.** It applies only when a project happens to be
   present, and none of `t1`–`t6` require it.

## Known limitations

Stated plainly, because a submission that hides these is easier to catch out than one that names
them. Reviewed and corrected 2026-09-11 against the code as it stands — several items below were
originally written as forward-looking design notes and have since been built; this list keeps
only what's still actually true.

- **Launching is a terminal command.** There is exactly one technical step, and the pitch should
  not claim zero. In a real product this is a downloadable app; the browser UI is unchanged.
  Running `source harness/.venv/bin/activate && python3 harness/web_server.py` (per that module's
  own docstring) is that one step today.
- **Verification strength is mixed across the catalog, not uniform.** 5 of 13 capabilities
  (`user-accounts`, `file-storage`, `structured-data`, `background-job`, `send-email` — the ones
  carrying the 2026-09-05 `hardened_note` upgrade) run a stronger check than the rest, but not
  uniformly the same check: `user-accounts`, `file-storage`, and `structured-data` do a full
  create/read-verify/delete round trip; `background-job` runs once and checks for no error;
  `send-email` sends and confirms the send succeeded (not end-to-end delivery). The remaining 7
  still run a weaker "service is up and
  answering" existence check. So the founder-facing proof sentence is honest per-capability, but
  not uniformly strong yet.
- **The UI is outside the measurement path.** Still true and still deliberate — it keeps the
  scored CLI clean. The jargon-leak metric is measured on agent response text
  ([tasks/README.md](../tasks/README.md)), not on rendered pixels.
- **Multi-product switching is built.** The live board's switcher (`interface/live.html`) lets a
  founder move between products sharing one Floci instance, keyed by `app_context` so resources
  don't collide.
- **Export is built.** The export dialog and its plain/technical page variants
  (`interface/canvas/Export*.dc.html`, wired into `live.html`) are implemented, not just
  specified.
- **`harness/stack-state.json` exists and is the board's durable source.** The feature itself is
  live: state is keyed by `app_context`, `mcp_server.py`'s `get_app_state` reads it directly, and
  `web_server.py`'s `/state` route reconciles it against live Floci before returning it to the
  board. Separately, the file was previously tracked in git holding stale demo data from a prior
  session — it's untracked now (gitignored going forward), so a fresh clone starts with no stale
  demo state.
