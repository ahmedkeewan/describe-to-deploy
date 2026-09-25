# Founder Interface — Design Spec

The full design for the founder-facing interface. Start with [README.md](README.md): it says
which parts are built (the live board, `live.html`) and which exist only as design. This spec is
written in the present tense throughout. Read the unbuilt parts as "this is how it would work".

Founder-facing wording lives in [founder-copy.md](founder-copy.md); the language rule and trust
vocabulary are summarised in the [README](README.md#the-language-rule).

## Scope

**In scope**: what the founder types, what they see while the agent works, how success and
failure are expressed, and what the harness must write for the UI to render.

**Out of scope**: hosting, deployment, cloud retargeting, accounts, multi-user, anything
persisted off the founder's machine. Local-only, deliberately, at this stage.

**Explicitly not required**: an existing project. If one happens to be in the directory the
harness was launched from, the agent can do more ([Optional: an existing
project](#optional-an-existing-project)). Everything essential works without it.

## Platform

A **local web app**: the harness runs as a local process and serves a single-page UI in the
browser.

```
  harness process (local)          browser
  ├─ MCP server + tools       ──▶  localhost:7777
  ├─ writes the artifacts          chat + capability board
  └─ serves the UI                 reads events.jsonl over SSE
```

| Rejected | Why |
|---|---|
| CLI / TUI | A founder who cannot debug will not work in a terminal. Also weak for live status and a clickable checklist. |
| Desktop app (Electron/Tauri) | Right for a real product — proper icon, no localhost — but a packaging project of its own. |

**Superseded in part.** This spec originally also rejected running "inside an existing agent
client", because that gives up control of founder-facing rendering. The shipped product does
exactly that: it runs inside the founder's chat client over MCP, and the board is an optional
companion. The jargon boundary moved into the MCP tools' own return values
(`founder_message`), so it holds in chat too.

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
2. **It is cuttable.** If the UI does not land, the product degrades to a terminal run rather than
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
  defence against false confidence.
- **The sidebar renders `stack-state.json`, not the conversation.** An incremental request visibly
  *updates a row* rather than appending one, so state carrying over is visible on screen rather
  than something the founder has to be told about.
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

The board renders `harness/stack-state.json`, keyed by `app_context`, so several products can
share one Floci instance without colliding. The switcher picks which `app_context` the board
shows. A project, when present, doesn't change where the truth lives.

(An earlier draft put a single machine-level file at `~/.floci-agent/stack-state.json`, on the
reasoning that one Floci per machine means one stack. Keying by `app_context` replaced that once
several products needed to coexist on one Floci.)

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
on it — and it is the same principle as the [trust vocabulary](README.md#trust-vocabulary): a row is
green because a check just passed, never because a file said so.

It is also why the default path writes **no founder-facing config file**. Such a file would be a
second claim on disk, with no reader (there is no app in this path) and no reconciliation — the
file equivalent of the "started but unverified" status this design deliberately has no room for.
The rule: *write config only where you can verify it is being used*, which is the project path
and only the project path.

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

This turns the **jargon-leak metric from a behaviour we hope for into a property of the
interface**. Given the baseline leaked infra terms in 5 of 6 responses, this is the single
highest-value structural change in the design. A leak would require a service name to be
committed into a catalog field — a code review away, not a sampling accident. It is Hashimoto's
rule ([research-links.md](../research/research-links.md#tier-1--the-canon-2-hrs)) applied to the UI layer: engineer the harness so
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

**Catalog fields.** Every catalog entry carries a founder-safe `verify.founder_proof` alongside
its `verify.cli`, and the board renders it under each row.

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

The default path comes first. The project path is a bonus: `wire_app_config` writes the
connection details when a project directory is given, and the stronger through-the-app check is
design only.

## Implementation

```
server   harness/web_server.py (Starlette)
           GET  /         the board (live.html)
           GET  /state    stack-state.json, reconciled against live Floci
           GET  /events   server-sent events tailing events.jsonl
           POST /chat     a one-shot Claude Code run against the MCP server
ui       interface/live.html: ONE static HTML file. No build step, no framework.
         The board is a list re-rendered on each event.
```

The UI is a renderer, so a single file is enough, and it stays easy to cut if scope needs to
shrink.
