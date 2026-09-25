---
title: Audience-split docs and public launch
date: 2026-09-25
status: requirements-only
source: interview (originated from GH issue #65 and a remarketing brainstorm)
---

# Audience-split docs and public launch

## Goal Capsule

Reposition this repo for three distinct audiences — founders/non-technical builders,
engineers/the MCP-agent-tooling ecosystem, and AI agents themselves — and take the repo public so
that positioning actually reaches anyone. What started as "split the README in two" (GH issue
#65) grew, over interview, into five separable pieces of work: a visibility prerequisite, a
three-audience README rewrite, a GitHub Pages founder-facing site, agent-facing machine-readable
docs, and a new demo asset. This document records the decisions from that interview so each piece
can be built and reviewed independently.

## Product Contract

### Audiences (three, not two)

1. **Founders / non-technical builders** — the actual end-user persona baked into the product.
   Zero infra jargon (no MCP, AWS, Floci, ARNs, planner/executor, environments).
2. **Engineers / MCP-agent-tooling ecosystem** — harness-engineering researchers and other
   Claude Code / MCP plugin authors who want architecture, design patterns, and benchmark data.
3. **AI agents** — both (a) AI crawlers/LLMs answering questions about this repo (the GEO/AEO
   angle) and (b) AI coding agents that want to actually wire up and call this MCP server as a
   tool. One audience, two jobs for its docs.

### Decision: repo visibility is a prerequisite, done first, standalone

- The repo is currently **private**. GitHub Pages only serves publicly from a **public** repo on
  the free plan — every other piece of this plan depends on that flip.
- **Before flipping to public**: run a scan for secrets, credentials, and any leaked references
  to the private ApexYard ops-fork/portfolio workflow used to build this repo (session history,
  commit messages, code comments) — confirmed explicitly as a required pre-check, not optional.
- As part of the same visibility change: update the GitHub repo's **About description, topics,
  and social-preview image** — first impressions should be right from day one, not a later
  follow-up.
- This is its own ticket, built and merged before the others below start.

### Decision: README stays one file, organized into audience sections — not split into separate files

- `README.md` keeps all the detail it needs, reorganized so **each section explicitly targets one
  audience**, not a hub-and-spoke split into three separate documents.
- Demarcation: **clear H2 headers per audience** (`## For Founders`, `## For Engineers`,
  `## For AI Agents`), with a **short jump-links list right under the title** so a reader can skip
  straight to their section. (Considered and rejected: collapsible `<details>` blocks — headers +
  jump links won over collapsing content by default.)
- The founder section must contain **zero infra jargon** — that's the one hard constraint carried
  over from the original #65 scope.

### Decision: GitHub Pages is a bonus, not the primary founder surface

- Enable **GitHub Pages served from `/docs`** (not a `gh-pages` branch) — standard GitHub-native
  approach, zero extra infra.
- Relationship to the README's founder section: **the Pages site is a richer bonus for sharing
  outside GitHub; the README's founder section must stand alone and be complete on its own** for
  anyone reading natively on GitHub. Neither one is allowed to be the only place the pitch exists.
- Since `/docs` already holds `agdr/`, `history/`, and `research-links.md`, enabling Pages there
  will publish that content as a rendered site too — a consequence to design around
  (Jekyll-rendered markdown), not a reason to move those files.

### Decision: AGENTS.md and llms.txt live at the repo root

- Both files go at the **repo root** — the conventional location both AI crawlers and agent
  harnesses look for first — not inside `docs/`.
- **`AGENTS.md`'s content is an MCP wire-up guide** (tool list, connection config, how an AI
  coding agent actually connects to and calls this MCP server) — deliberately **not** a duplicate
  of `CONTRIBUTING.md`'s build/test/lint instructions, since that content already exists there.
- `llms.txt` covers the crawler/LLM-summary side of the "agents" audience.

### Decision: the founder "try it" is a scripted replay, not a live hosted sandbox

- Floci genuinely needs Docker running locally (per AgDR-0002, "a hackathon-scale tool, not a
  production multi-tenant service") — a real live-hosted version is a much larger infra project,
  out of scope here.
- Cheaper path that still feels real: `interface/live.html` is already "ONE static HTML file...
  a list re-rendered on each event" — it does not care whether events are streamed live or
  replayed from a saved file. Record one real run against live Floci, save its `events.jsonl`,
  and build a variant of the board that plays that file back on a timer instead of tailing a live
  stream.
- This is genuine captured behavior (not a mockup), needs zero backend/Docker/hosting, and is
  itself just static HTML+JS+JSON — so it ships directly on the GitHub Pages site (ticket 3
  below).
- A real hosted live sandbox remains a legitimate future idea, explicitly deferred — not filed as
  a ticket in this plan.

### Decision: real usage still needs a one-click installer (not just better docs)

- The scripted replay (above) solves "see it work"; it does not solve "use it on my own idea."
  Actually running the harness needs Docker + a terminal (`./setup.sh`) — no amount of doc
  polish removes that, since Floci needs a real local backend.
- Considered and rejected as v1: shipping the founder page with an honest "run this one command"
  ending, or reframing so only a technical co-founder ever touches `setup.sh`. Instead: **invest
  in a real one-click packaged installer** that bundles Docker/Floci/MCP wiring behind a GUI, so
  a non-technical founder genuinely never sees a terminal.
- This is genuinely new engineering, not a docs task, and "will this work" is an open technical
  question — does it bundle Docker Desktop itself, automate driving an existing install, or use a
  lighter embedded runtime instead of Docker entirely? **File as a spike first** (time-boxed,
  answers the technical-viability question) before committing to a full build.
- **Platform: macOS only for the spike/first build** — `setup.sh` already treats macOS specially
  (Homebrew-based Docker/Colima install), making it the natural first target. Windows/WSL and
  Linux stay out of scope until the spike's findings say otherwise.

### Decision: new demo GIF, dependency-chain scenario

- The current demo materials all use the single-capability "upload a photo" example. The **new**
  GIF should show the **dependency-chain run** — a request that resolves across multiple linked
  capabilities (`depends_on`) — to visually demonstrate the harness handling real complexity, not
  just a single bucket.
- Considered and not chosen: the staged failure-detection moment (Object Lock poisoning test) and
  the side-by-side concurrent-environments demo — both are legitimate future demo assets but not
  this one.
- This asset does not exist yet; creating it is in scope for whichever ticket carries the
  founder-facing README section / Pages site (needs assignment when broken into tickets below).

## Ticket breakdown (decided: split into separate, linked tickets)

Supersede/expand GH issue #65 into the following, each independently buildable and reviewable,
in this order:

1. **Repo visibility prerequisite** — secrets/private-reference scan, flip to public, update
   About/topics/social-preview image. Blocks everything below that depends on Pages being public.
2. **README three-audience rewrite** — reorganize `README.md` into `## For Founders` /
   `## For Engineers` / `## For AI Agents` sections with a jump-links index; founder section has
   zero infra jargon and must stand alone.
3. **GitHub Pages founder site** — enable Pages from `/docs`, build the richer founder-facing
   page there, including the scripted-replay "try it" board (a variant of `interface/live.html`
   fed a saved `events.jsonl`) and the new dependency-chain demo GIF. Both can be produced from
   the *same* one real captured run — record it once, use it for both assets.
4. **AGENTS.md + llms.txt** — root-level agent-facing docs; AGENTS.md is the MCP wire-up guide.
5. **[Spike] One-click macOS installer** — time-boxed, hypothesis-driven: does bundling
   Docker/Floci/MCP wiring behind a native macOS installer actually work, and how? Disposition
   (`/spike-close`) decides whether it promotes to a full feature ticket or gets discarded with a
   memo. Independent of tickets 1-4; can start any time.

Ticket 1 must merge before tickets 3 starts (Pages needs the repo public). Tickets 2 and 4 have no
hard dependency on 1 or 3 and could proceed in parallel with them once filed. Ticket 5 is fully
independent of the rest of this plan.

## Open questions (not resolved in this interview — flag before building)

- Exact wording/length limits for `llms.txt` (the emerging spec has conventions this plan didn't
  pin down).
- Whether the demo GIF is hand-recorded against live Floci or produced from a scripted/staged run
  — an implementation detail for whichever ticket builds it.
- Whether `research/agdr/` and `research/history/` need any Jekyll front-matter adjustments to render
  cleanly once Pages is enabled — worth a quick spike before ticket 3's build starts.
