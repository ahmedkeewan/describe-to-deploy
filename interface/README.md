# Founder Interface

The founder-facing surface of Service Buddy: what a non-technical founder sees while the harness
sets things up, and the rules that keep it honest and jargon-free. This folder holds the live
board, its design spec, and the copy deck. See [harness/README.md](../harness/README.md) for the
MCP server underneath.

## Status: what's built and what's design

**The main way founders use Service Buddy is chat.** Claude Desktop, Claude Code, or Cursor talks
to the MCP server in [`harness/`](../harness/). No extra app is needed.

**The live board is an optional companion,** built and shipped as [`live.html`](live.html). Start
it with `make board` and open http://localhost:7777. It follows the same MCP state as the chat.

| Part of the design | Status |
|---|---|
| Product sidebar: one row per capability, proof sentence always visible, "last checked" time | Built (`live.html`) |
| Live updates as things get set up (reads `events.jsonl` over server-sent events) | Built (`harness/web_server.py`) |
| Board state re-checked against live Floci before a row renders green | Built (`/state` route) |
| Expandable rows with more plain-language detail | Built |
| Product switcher (several apps side by side, keyed by `app_context`) | Built |
| Export (plain page or developer files) | Built |
| Chat box in the board (runs a one-shot Claude Code session against the MCP server) | Built; needs a logged-in `claude` CLI |
| Confirmation checklist before anything is set up | Design only |
| Failure actions (`try again`, `set it up fresh`, `get help`) and the developer-details modal | Design only |
| `stopped — needs a person` and `waiting on your answer` statuses | Design only |

The full 16-screen design is in [spec.md](spec.md) and on the canvas
([founder-interface.html](founder-interface.html)). Anything marked "design only" above is
described there in the present tense, but it isn't built yet.

## The design in one paragraph

A founder writes what they need in plain English, like "I need users to be able to upload
photos". The infrastructure is set up on Floci, checked for real, and reported back in words they
understand. The founder can't verify anything themselves: they can't read a log or tell a working
setup from a broken one. So beyond being usable, the interface has one job. It must never let
them believe something works when it doesn't.

## Why the interface matters

The bare-agent baseline in [tasks/README.md](../tasks/README.md) already passes 5 of 6 tasks, so
the harness's value isn't "it works vs. it doesn't". The baseline's two real failures are both
about what the founder sees:

| Baseline failure | Measured | What the interface does |
|---|---|---|
| **Jargon leak.** Cognito, JWTs, CORS, and presigned URLs shown to a founder who can't parse them | 5 of 6 responses | Founder-facing text comes only from reviewed catalog strings, so jargon can't reach the founder pane |
| **Scope overreach.** Asked for uncataloged "real-time chat", it silently built a WebSocket stack, 3 functions, and a table | t5 | The confirmation checklist (design) states scope in founder language before anything is set up |

The single-agent harness fixes jargon by *instructing* the model (0 of 6 leaks, measured). The
interface goes further and makes a leak structurally impossible. Every event carries a `founder`
channel and a `dev` channel. The founder pane renders only `founder`, and those strings come from
[capabilities.json](../catalog/capabilities.json), never from the model's own prose. A leak would
need a service name committed into a catalog field, which a code review catches. That is
Hashimoto's rule ([research-links.md](../research/research-links.md#tier-1--the-canon-2-hrs))
applied to the presentation layer: engineer the harness so the agent can never make that mistake
again.

## The language rule

**Every word the founder reads must make sense to someone who has never heard of cloud
infrastructure.** No exceptions.

Never shown to the founder:

```
  service names      S3, Cognito, DynamoDB, Lambda, SES, RDS, Redis
  infra nouns        bucket, table, instance, container, endpoint, port,
                     region, ARN, IAM, role, policy, queue, trigger
  protocol/format    JWT, CORS, presigned URL, API, SDK, JSON, YAML, env var
  ops verbs          provision, deploy, configure, spin up, boot, mount
  error surfaces     exit codes, stack traces, exception names
  file paths         .env, docker-compose.yml, ~/.aws/config
```

The translation table and the rules for writing new strings are in
[founder-copy.md](founder-copy.md). The one place jargon is allowed is a panel explicitly
addressed to a developer; see [Disclosure](spec.md#disclosure--depth-without-jargon).

## Trust vocabulary

The complete set of statuses a founder can see:

```
  ◐  setting up…               working on it
  ●  working                   + proof sentence, always shown
  ○  not working yet           honest failure
  ⊘  stopped — needs a person  (design only)
  ?  waiting on your answer    (design only)
```

**There is deliberately no status meaning "started but unverified."** Something created but not
yet proven stays `setting up…`. The verification gate can't be quietly weakened later, because
the UI has no status that could show a half-truth.

## How it maps to harness engineering

| Interface mechanism | Harness concept ([VOCAB.md](../research/VOCAB.md)) |
|---|---|
| UI reads `stack-state.json` / `events.jsonl`, never shared memory | External state as the handoff between components (§4) |
| Confirmation checklist blocks setup until scope is confirmed | Gate: a sensor that blocks rather than reports (§3, §12) |
| No status for "started but unverified" | Completion gate; evidence-based terminal states (§7) |
| Proof sentence on every row, sourced from the check that ran | Computational sensor surfaced to the human (§3) |
| `founder` / `dev` channels on every event | Guide/AX separation (§17): the same event, two audiences |
| Fallback rule renders as a question, never an expanded plan | Advisory-vs-hard-gate distinction (§12) |
| Append-only `events.jsonl` as the render source | Session as append-only log (Managed Agents, [research-links.md](../research/research-links.md#tier-1b--the-winning-edge)) |

## What's in this folder

| | |
|---|---|
| [live.html](live.html) | The live board, served by `harness/web_server.py` (`make board`) |
| [spec.md](spec.md) | The full design spec: the journey, the two panes, disclosure, export, state, failure presentation, the event contract |
| [founder-copy.md](founder-copy.md) | Every founder-facing string in one place: status words, proof sentences for all 13 capabilities, screen text, translation reference |
| [regenerate-prompt.md](regenerate-prompt.md) | A self-contained prompt that rebuilds the 16-screen design canvas, with exact tokens and copy |
| [founder-interface.html](founder-interface.html) | The 16-screen canvas, exported. Open it in a browser to pan through every screen |
| [canvas/](canvas/) | Source for that canvas: one `.dc.html` per screen, `canvas.json` for layout, `build.mjs` to regenerate them all |

The original visual brief is archived at
[research/history/design-brief.md](../research/history/design-brief.md). It has been superseded by
this folder.

## Known limitations

- **Starting the board is a terminal command** (`make board`). The chat path needs no board at
  all.
- **Verification strength varies across the catalog.** 6 of 13 capabilities run a real
  functional check. `user-accounts`, `file-storage`, and `structured-data` do a full
  create/read/delete round trip. `background-job` runs once and checks for no error. `send-email`
  confirms the send succeeded (not end-to-end delivery). `multi-step-workflow` runs the workflow
  once and waits for it to finish. The other 7 run an "up and answering" existence check. Each
  proof sentence is honest about which kind of check ran.
- **The UI is outside the measurement path.** This is deliberate, so the scored runs stay clean.
  The jargon-leak metric is measured on agent response text ([tasks/README.md](../tasks/README.md)),
  not on rendered pixels.
