---
title: Audience-split docs and public launch
date: 2026-09-25
status: mostly shipped — see "Status of the original ticket breakdown"; this document now also
  records a 2026-09-25 follow-up interview covering the GH-97 Pages redesign, the GH-93 research/
  restructuring, a product rename, and OSS-launch readiness
source: interview (originated from GH issue #65 and a remarketing brainstorm); follow-up interview
  same day after GH-72/73/74/75/76/92/93/97 shipped
---

# Audience-split docs and public launch

## Goal Capsule

Reposition this repo for three distinct audiences — founders/non-technical builders,
engineers/the MCP-agent-tooling ecosystem, and AI agents themselves — and take the repo public so
that positioning actually reaches anyone. What started as "split the README in two" (GH issue
#65) grew, over interview, into five separable pieces of work: a visibility prerequisite, a
three-audience README rewrite, a GitHub Pages founder-facing site, agent-facing machine-readable
docs, and a one-click installer spike. This document records the decisions from that interview so each piece
can be built and reviewed independently.

**2026-09-25 update:** all five original pieces have since shipped (see status table below). A
same-day follow-up interview reconciled what actually shipped against the original decisions
below, decided a full product rename, and added OSS-launch-readiness scope discovered by
checking this plan against current open-source/Product Hunt launch conventions. See "Follow-up
interview" near the end of this document.

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
  to the private tooling workspace this repo was built from (session history, commit messages,
  code comments) — confirmed explicitly as a required pre-check, not optional.
- As part of the same visibility change: update the GitHub repo's **About description, topics,
  and social-preview image** — first impressions should be right from day one, not a later
  afterthought.
- **Shipped as GH-72.** Repo is public; About/topics/social-preview image are set (social-preview
  image uploaded 2026-09-25, see GH-72's closing comment). Note: the social-preview image and the
  repo slug both currently say "describe-to-deploy" — see the rename decision below, which
  supersedes this.

### Decision: README stays one file, organized into audience sections — not split into separate files

- **Shipped as GH-73.** `README.md` reorganized into `## For Founders` / `## For Engineers` /
  `## For AI Agents` with a jump-links index.
- **Superseded-in-part, 2026-09-25:** the founder section has since fallen behind the Pages site
  built in GH-97 (chat mockups, live verification log, before/after comparison, benchmark stats,
  feature grid). See "Decision: bring README to parity with the Pages site" below.

### Decision: GitHub Pages is a bonus, not the primary founder surface

- Enable **GitHub Pages served from `/docs`** (not a `gh-pages` branch) — standard GitHub-native
  approach, zero extra infra.
- Relationship to the README's founder section: **the Pages site is a richer bonus for sharing
  outside GitHub; the README's founder section must stand alone and be complete on its own** for
  anyone reading natively on GitHub. Neither one is allowed to be the only place the pitch exists.
- ~~Since `/docs` already holds `agdr/`, `history/`, and `research-links.md`, enabling Pages there
  will publish that content as a rendered site too — a consequence to design around
  (Jekyll-rendered markdown), not a reason to move those files.~~ **Corrected 2026-09-25:** this
  is no longer accurate. GH-93 moved `agdr/`, `history/`, and `research-links.md` (plus
  `VOCAB.md`) out of `docs/` into a new top-level `research/` folder, specifically so `docs/`
  could stay scoped to the Pages site (`index.html`, `.nojekyll`, `assets/`, `spike-memos/`,
  `plans/`) without mixing in research content. The Jekyll-rendering concern this paragraph
  raised is moot — `.nojekyll` disables Jekyll processing for the Pages site entirely, and the
  files that would have been Jekyll-rendered no longer live under `docs/`.
- **Shipped as GH-74**, then substantially expanded by **GH-97** (see below) — the "bonus, not
  primary" framing has drifted: GH-97 invested real design effort (chat-window mockups, a live
  re-verification demo, a benchmark comparison, a feature grid) that now makes the Pages site the
  richer of the two founder surfaces, not a lightweight bonus. Resolved in the follow-up
  interview: keep both surfaces, but bring README back to parity rather than treat this as an
  intentional asymmetry.

### Decision: AGENTS.md and llms.txt live at the repo root

- Both files go at the **repo root** — the conventional location both AI crawlers and agent
  harnesses look for first — not inside `docs/`.
- **`AGENTS.md`'s content is an MCP wire-up guide** (tool list, connection config, how an AI
  coding agent actually connects to and calls this MCP server) — deliberately **not** a duplicate
  of `CONTRIBUTING.md`'s build/test/lint instructions, since that content already exists there.
- `llms.txt` covers the crawler/LLM-summary side of the "agents" audience.
- **Shipped as GH-75.** Open question below (exact spec conformance) was never resolved — carried
  forward as a new ticket.

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
- **Shipped as GH-74**, using `docs/assets/demo-events.json` captured from a real 3-capability run.
- **New nuance from GH-97, resolved 2026-09-25:** GH-97's "before/after" comparison (bare agent
  vs. this harness, same request) needed an example reply for the "without a harness" side. No
  literal quoted baseline transcript exists in `tasks/README.md` — only a description of which
  jargon terms leaked (S3, CORS, presigned URL for one task; S3/Lambda/SES for the
  resize-and-email task this comparison uses). The shipped version uses an **illustrative,
  clearly-labeled** reply built from those real named terms, not a verbatim quote. **Decided:**
  this is an acceptable, narrow exception to "genuine captured behavior, not a mockup" — it's
  honestly disclosed as illustrative and grounded in real terminology; re-running a full baseline
  agent solely to obtain a verbatim quote wasn't judged worth the cost. If a real baseline
  transcript is ever captured for this scenario, swap it in.

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
- **Shipped as a spike (GH-76)**, which found a native macOS `.pkg` GUI installer technically
  viable but expensive, and that Anthropic's own Desktop Extension format (`.mcpb`) already
  solves the MCP-wiring half of this problem for free, with no signing/notarization needed. The
  spike's disposition closed the original "bundle everything behind a GUI" idea (GH-90) in favor
  of the narrower, cheaper **GH-92** (package the MCP server as a `.mcpb` bundle) — shipped
  2026-09-25.
- **GH-92 deliberately does NOT bundle Docker/Floci** — a founder using the `.mcpb` path still
  needs `./setup.sh` in a terminal once, for Floci specifically. **Decided in the follow-up
  interview:** this is accepted as sufficient, and **treated as a settled, permanent decision, not
  a provisional one** (reframed after ce-doc-review pointed out this repo has no mechanism —
  analytics, telemetry, a feedback channel — that could ever surface "founder friction data," so a
  "revisit if the data says so" framing would never actually trigger). The original "a
  non-technical founder genuinely never sees a terminal" goal is not being pursued further — the
  cost of a full GUI installer that also bundles Docker/Floci is judged not worth it against what
  `.mcpb` + one terminal command already achieves. Not filed as an open ticket. If this needs
  revisiting later, it will be because someone notices the friction directly (a GitHub issue, a
  support conversation), not because this repo is watching for it.

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
- **Never produced.** GH-74/GH-97 shipped the scripted-replay board (a different asset — an
  HTML/JS/JSON replay, not a GIF) but the dependency-chain demo GIF itself was never made.
  **Confirmed still wanted, 2026-09-25** — for README embedding and social/Product-Hunt sharing,
  which the scripted replay can't serve (it needs a live page, not a static image). Filed as a
  new ticket below.

## Status of the original ticket breakdown

| # | Ticket | Status |
|---|---|---|
| 1 | Repo visibility prerequisite | **Shipped** — GH-72 |
| 2 | README three-audience rewrite | **Shipped** — GH-73; now needs a parity follow-up (below) |
| 3 | GitHub Pages founder site | **Shipped** — GH-74, substantially expanded by GH-97 |
| 4 | AGENTS.md + llms.txt | **Shipped** — GH-75; spec-conformance since checked and the file published (ticket 9 below) |
| 5 | [Spike] One-click macOS installer | **Shipped as spike** — GH-76, promoted to GH-92 (narrower scope than originally envisioned; accepted) |

## Follow-up interview (2026-09-25) — new decisions

Conducted after GH-93 (research/ restructuring) and GH-97 (Pages redesign) both shipped, to
reconcile the plan above against reality and decide several new items raised along the way.

### Decision: full product rename, "Describe to Deploy" → "Service Buddy"

- **Reverses an earlier explicit decision in this same session** — "Describe to Deploy" was
  chosen via its own interview (AskUserQuestion) after the repo-rename request in GH-72's epic.
  On reflection, re-decided in favor of "Service Buddy" — the name already used throughout
  `interface/design-brief.md`, `interface/founder-copy.md`, and `interface/regenerate-prompt.md`
  (an earlier, more detailed design exploration that predates the "Describe to Deploy" rename).
- **Why the full rename, not a display-name-only rebrand (added after ce-doc-review flagged the
  gap):** the interface/*.md files predate and were already superseded once by the "Describe to
  Deploy" decision — "an older file already says X" is not on its own a stronger reason than the
  deliberate interview that chose "Describe to Deploy" in the first place. The considered
  alternative was cheaper: keep the repo slug `describe-to-deploy`, keep the live Pages URL and
  the already-uploaded social-preview image, and change only the displayed product name/copy to
  "Service Buddy" everywhere. **Decided against that alternative and for the full rename anyway**
  because the repo went public and the name/image were set only hours earlier the same day
  (2026-09-25), before any meaningful external traffic, indexing, or sharing had time to
  accumulate — the same-day timing is what makes the cost of a full rename (broken URL,
  regenerated image) acceptable now in a way it would not be later. This is a one-time-only
  argument: renaming the live repo again after real external traffic exists would not carry the
  same justification.
- **Scope: full rename, including the GitHub repo itself.** New repo slug: **`service-buddy`**
  (kebab-case, matching the existing convention). This means:
  - `gh repo rename service-buddy`, then `git remote set-url origin` to match.
  - Every absolute GitHub URL hardcoded in `docs/index.html`, `README.md`, `mcpb/README.md`, and
    `harness/README.md` needs updating from `describe-to-deploy` to `service-buddy` — verified
    2026-09-25 that `AGENTS.md` and `llms.txt` currently contain no reference to the old name or
    repo URL at all, so they need no change on this front (they may still need the product-name
    pass below if they name the product elsewhere).
  - The GitHub Pages URL moves from `https://ahmedkeewan.github.io/describe-to-deploy/` to
    `https://ahmedkeewan.github.io/service-buddy/` — the old URL will 404 (GitHub does not
    redirect Pages URLs across a repo rename the way it redirects the repo itself). **Before
    renaming**, check whether anything already links to the old URL or repo slug (the closing
    comment on GH-72, any social/chat messages sent since the repo went public, the uploaded
    social-preview image's own metadata) and update or accept each one explicitly — added after
    ce-doc-review flagged that this breakage was acknowledged but never checked for real cost.
  - The social-preview image (`docs/assets/social-preview.png`, uploaded via GitHub Settings in
    GH-72) has "Describe to Deploy" baked into its design — needs regenerating and re-uploading.
  - `mcpb/manifest.json`'s `display_name` ("Describe to Deploy") and `description` need updating;
    rebuild the `.mcpb` bundle after.
  - Every H1/title/tagline across `docs/index.html`, `README.md`, `harness/README.md`,
    `mcpb/README.md`, and catalog copy that names the product needs the same pass.
- **Explicitly NOT renamed:** the internal MCP server identifier `floci-control-plane` (the name
  registered in `claude_desktop_config.json`, `.mcp.json`, and the `.mcpb` manifest's `name`
  field, as distinct from its `display_name`). This is a technical wiring identifier, not
  user-facing branding — renaming it would force anyone already connected to reconnect, for no
  user-visible benefit.
- **Filed as a new ticket** (large, cross-cutting — repo rename + regenerated social-preview image
  + copy pass across every markdown file and `docs/index.html`). Not started as of this writing.

### Decision: bring README to parity with the Pages site

- The Pages site (GH-97) now has content the README's "For Founders" section lacks: the
  benchmark numbers with real before/after context, the live-verification-log demonstration, and
  the `.mcpb` install path alongside `./setup.sh`.
- **Decided:** update README's founder section to match, rather than accept the asymmetry. This
  keeps the "neither one is allowed to be the only place the pitch exists" rule from the original
  plan intact.
- Filed as a new ticket, sequenced after the rename (so it's not done twice).

### Decision: interface/*.md — keep and rename, not archive

- `interface/design-brief.md`, `founder-copy.md`, and `regenerate-prompt.md` describe a 16-screen
  dashboard-style web-app design canvas, and (in `regenerate-prompt.md`'s case) still literally
  name the product "Service Buddy" — which turns out to now be correct again, not stale, per the
  rename decision above.
- **Decided:** keep these files in place (not archived to `research/history/` the way
  `GAME_PLAN.md`/`KICKOFF_PROMPT.md` were in GH-93) and update their content for the rename.
- **Resolved tension:** these files describe a 16-screen web app, while GH-97 established "chat
  is the front door, not a dashboard" as the current product's actual surface. **Decided: both
  are real, coexisting surfaces, not a contradiction** — chat (Claude Desktop/Code) is how
  founders use the product today; the web app in `interface/` is a legitimate, separate future
  surface sharing the same backend, not a superseding replacement for chat.
- **Filled in after ce-doc-review flagged the coexistence decision as underspecified:**
  - **Entry point:** none exists yet — the web app is design-canvas files only (`interface/`),
    never built or deployed. There is no URL, no link from chat, nothing for a founder to reach
    today. This is a design artifact for possible future work, not a shipped second surface.
  - **State model:** undecided, and deliberately left undecided — deciding how a persistent
    multi-screen web app would share session/environment state with a turn-by-turn chat interface
    is a real design question, but not one this repo needs answered until the web app is actually
    scheduled for planning. Whoever picks up `interface/` next decides it then.
  - **Founder-facing visibility:** founder-facing surfaces (README, the Pages site) will **not**
    mention or link to the web app while it stays unbuilt — it remains an internal/engineering
    artifact only. Revisit this the moment work on the web app is actually planned, not before.
  - `interface/README.md` should say all three of the above explicitly once it's updated, so a
    future reader doesn't read the two as competing visions or wonder why no link exists.

### Decision: llms.txt spec-conformance check (new ticket)

- The original plan's open question — "exact wording/length limits for llms.txt (the emerging
  spec has conventions this plan didn't pin down)" — was never resolved before GH-75 shipped.
- **Filed as a new ticket**: check the current `llms.txt` against llmstxt.org's actual published
  conventions and adjust if it's out of spec.

### Decision: dependency-chain demo GIF (new ticket, confirmed)

- Still wanted (see "Decision: new demo GIF" above, updated). Produce it from a real captured run
  against live Floci, same discipline as the scripted-replay board's `demo-events.json` — genuine
  behavior, not staged. Needed for README embedding and for Product Hunt / social assets, which
  the HTML/JS scripted replay can't serve on its own (those channels need a static image/video).

### Decision: remaining markdown files need a rename sweep, not an individual audit (new ticket)

- `catalog/README.md`, `tasks/README.md`, `harness/README.md`, `mcpb/README.md`,
  `research/VOCAB.md`, `research/research-links.md`, the four `research/agdr/AgDR-*.md` files,
  `CONTRIBUTING.md`, and `AGENTS.md` were not individually reviewed in this interview.
- **Decided:** treat the "Describe to Deploy" → "Service Buddy" rename as the reason to touch all
  of them once, in one pass (grep for the old name and the old repo URL, fix both), rather than
  auditing each file's content quality individually right now. Filed as part of the rename
  ticket above, not a separate content audit.

### New: OSS / Product Hunt launch readiness

Raised 2026-09-25 explicitly to prepare this repo for a public OSS + Product Hunt launch.
Checked against current (2026) published conventions for open-source repos and Product Hunt
launches (standard-readme spec, GitHub's own repository best-practices docs, and 2026 Product
Hunt launch checklists) rather than assumed from memory.

**Confirmed missing, as of 2026-09-25:**

- `CODE_OF_CONDUCT.md` — not present.
- `SECURITY.md` — not present.
- `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md` — no `.github/` directory
  exists at all.
- README badges (license, and whichever others apply — this repo has no CI badge to add
  truthfully since there's no CI pipeline; a license badge is honestly addable now) — none
  present.

**Already satisfied:**

- `LICENSE` (MIT) — present.
- `CONTRIBUTING.md` — present, points to `./setup.sh` and the test suite.
- README has a description, install instructions — present, though the demo GIF/screenshot gap
  above (Product Hunt checklists specifically call for a demo GIF or screenshots) is the same gap
  already tracked as its own ticket.
- GitHub About description, topics — set (GH-72).

**Not evaluated here (needs a human decision, not a docs pass):** Product Hunt's own checklist
items outside this repo's control — maker account age (30+ days), launch day/week timing (2nd–3rd
week of the month, Tuesday), gallery images/tagline/maker comment copy for the PH listing itself.
These are launch-logistics decisions for whoever runs the actual Product Hunt submission, not
something a markdown file in this repo can satisfy.

**Filed as a new ticket**: add `CODE_OF_CONDUCT.md` (a standard template, e.g. Contributor
Covenant), `SECURITY.md` (how to report a vulnerability), `.github/ISSUE_TEMPLATE/` (bug report +
feature request), `.github/PULL_REQUEST_TEMPLATE.md`, and a license badge to README. Sequence
after the rename (so these new files are written with the correct name from the start).

## New ticket breakdown (2026-09-25 follow-up)

In addition to the original five (all shipped or superseded per the status table above):

6. **Product rename to Service Buddy** — repo rename (`service-buddy`), regenerated
   social-preview image, `.mcpb` manifest update + rebuild, copy pass across `docs/index.html`,
   `README.md`, and every other markdown file that names the product or the old repo URL. Large;
   do this first among the new tickets — 7, 10, and 11 depend on it (8 and 9 are independent).
7. **README parity with the Pages site** — bring the founder section up to date with GH-97's
   content (benchmark numbers, live-verification demo, `.mcpb` install path). Sequence after 6.
8. **Dependency-chain demo GIF** — **Shipped** (PR #116), though not the way this plan
   anticipated. Screen-recording the browser proved unreliable: the board's per-event animation
   outran the screenshot round-trip, so the capture only ever caught the first and last states.
   The GIF is instead rendered by [`docs/assets/render-demo-gif.py`](../assets/render-demo-gif.py)
   from `docs/assets/demo-events.json` — the same captured events from a real run against live
   Floci that the site's board replays — using the design tokens copied from `docs/index.html`.
   The underlying run is still real; only the rendering is synthetic, and the trade is worth
   naming: the asset is now reproducible after a palette change instead of needing a re-record.
   This supersedes the resolved open question below, which committed to hand-recording.
9. **llms.txt spec-conformance check** — **Shipped**. Checked against llmstxt.org: the file is
   conformant (H1 present, blockquote summary, heading-free prose section, H2 file lists with
   `- [name](url): notes` items, `Optional` last). One real gap found and fixed — the file sat at
   the repo root and was never actually served, so a copy now lives at `docs/llms.txt` and is
   published at `https://ahmedkeewan.github.io/service-buddy/llms.txt`. A test
   (`harness/tests/test_llms_txt_published_copy.py`) fails if the two copies drift. Note for the
   record: `llms-full.txt` is a vendor convention, not part of the spec, so none is needed.
10. **OSS launch essentials** — `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/`,
    `.github/PULL_REQUEST_TEMPLATE.md`, a license badge on README. Sequence after 6 (so these are
    authored with the correct product name).
11. **interface/*.md rename + coexistence note** — update the three interface design files for
    the rename, and add an explicit note (likely in `interface/README.md`) that the 16-screen web
    app and the current chat-first product are two coexisting surfaces, not competing visions.
    Part of ticket 6's copy pass, or its own small follow-up — either is fine.

## Open questions (status of the original list, plus one new item from this follow-up)

- ~~Exact wording/length limits for `llms.txt`~~ — resolved by ticket 9 above: the spec sets no
  length limit, and the file is conformant as written.
- ~~Whether the demo GIF is hand-recorded against live Floci or produced from a scripted/staged
  run~~ — **superseded**. This was resolved as "hand-recorded against live Floci," and that is
  not what shipped; see ticket 8 above for why and what replaced it. The underlying run is still
  a real one against live Floci, so the honesty commitment behind the original decision holds —
  but the recording step does not, and this plan should not be read as if it does.
- Whether `research/agdr/` and `research/history/` need any Jekyll front-matter adjustments —
  **moot**: these no longer live under `docs/`, and `docs/.nojekyll` disables Jekyll for the
  Pages site entirely (see the corrected paragraph above).
- **New, unresolved:** exact visual design for the regenerated social-preview image under the new
  "Service Buddy" name — not decided in this interview; whoever picks up ticket 6 should design
  it fresh rather than just find-and-replace the text on the existing image, since the existing
  design was built around the "Describe to Deploy" wordmark specifically.
