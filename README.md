# Service Buddy

This repo has two parts: a working demo harness (an MCP server that turns a plain-language
product request into real, verified infrastructure) and a research reference on harness
engineering as a discipline.

Jump to the section that's for you:

- [For Founders](#for-founders) — you want to try the demo or use the harness on your own idea
- [For Engineers](#for-engineers) — you want to understand or extend the harness
- [For AI Agents](#for-ai-agents) — you're an AI coding agent working with this repo

## For Founders

Describe what you want in plain English — "let people sign up," "store the photos users
upload," "run something on a schedule" — and the harness sets it up for you, then checks that it
actually works before ever telling you it's done. If something isn't working yet, it says so
plainly instead of pretending.

There's no new tool to learn and no form to fill in. You type into the same chat window you
already have open, the way you'd ask a person, and you get an answer back in the same plain
language: "Done and verified — people can upload a photo and get it back later." There are 13
things it knows how to set up today, and if you ask for something outside that list it tells you
so rather than guessing.

### The numbers

We put it on a fixed set of six founder requests and measured what changed against the same
agent with no harness at all:

- Tech-speak in the replies: 0 out of 6 requests leaked it, down from 5 out of 6 without the
  harness. No server names or acronyms when all you asked for was a straight answer.
- Speed: about 3.4× faster end to end — roughly 310 seconds total across all six requests,
  versus roughly 1,040 seconds without the harness.
- Wasted motion: about 4× less — 21 steps total versus roughly 87. Fewer dead ends, not just
  less typing.

[`tasks/README.md`](tasks/README.md) has the full writeup, including the honest misses.

Benchmarks are one kind of proof. Here's another: the three most common requests were run again
for real against a live machine, each one set up and then independently re-checked from
scratch. All 3 passed on the first try, averaging about 0.78 seconds each, with zero internal
names or tech-speak in any of the replies a founder would see.

### Getting it running

Two paths, both a few minutes:

- **Claude Desktop, no terminal.** Grab the ready-made bundle from
  [`mcpb/`](mcpb/README.md), double-click it (or drag it onto Claude Desktop), and click
  Install.
- **Claude Code or Cursor.** Clone the repo and run `./setup.sh` from the root. One command
  checks for and installs everything it needs and wires itself into your chat app — asking your
  confirmation before anything gets installed.

Either way, `./setup.sh` needs to run once on the machine, so the harness has something real and
local to set things up on. After that there are no commands to memorize — you just describe what
you want.

### Once you're in

- **A live dashboard, if you want one.** `make board` opens a board in your browser that updates
  in real time as things get set up, side by side with the chat. You don't need it to get
  started.
- **Real cost answers.** Ask what something will cost and it pulls live numbers from the
  provider's own published price list rather than guessing. As of 2026-09-25, 5GB of file storage
  priced out at $0.11/month. 6 of the 13 capabilities get live-fetched pricing; the rest fall back
  to a clearly labelled estimate, never a silent guess.
- **Setup that asks first.** `./setup.sh` never installs anything without your yes, is safe to
  run again any time, and works on macOS, Linux, and Windows via WSL.

That's the whole idea: you describe what you want, and the harness only ever tells you it's
ready once it has actually checked.

There's a fuller walkthrough, with a real recorded conversation and the live verification log,
at [ahmedkeewan.github.io/service-buddy](https://ahmedkeewan.github.io/service-buddy/).

## For Engineers

**Working definition (consensus across sources):** `Agent = Model + Harness`. The harness is
everything around the model: system prompt, tools/skills/MCP, sandbox/filesystem, orchestration
(subagents, routing), hooks/middleware (compaction, doom-loop detection, verification),
memory/state across context windows, and permissions. Harness changes alone have moved
Terminal-Bench 2.0 scores by 10-14 points with the same model.

This repo's demo harness is an MCP server (`harness/`) that turns a non-technical founder's
plain-language product request ("users should be able to upload a photo") into a verified,
running local infra environment on [Floci](https://floci.io/), using a capability catalog
(`catalog/`) and a fixed scoring task set (`tasks/`). See [`harness/README.md`](harness/README.md)
to run it, and [`GAME_PLAN.md`](research/history/GAME_PLAN.md) for the design behind it.

**Design patterns worth stealing**, independent of this specific product:

- [AgDR-0001](research/agdr/AgDR-0001-shared-backend-naming-scope-isolation.md) — isolating multiple
  agents on one shared backend via naming scope, not per-agent infrastructure instances.
- [AgDR-0002](research/agdr/AgDR-0002-flock-based-state-locking.md) — `fcntl.flock`-based
  cross-process state locking for an MCP server where every client spawns its own subprocess.

**The benchmark data is real, including the negative results.** [`tasks/README.md`](tasks/README.md)
tracks before/after numbers across every harness change — including the one deliberate negative
finding (a baseline agent asked to build "real-time chat," an uncataloged capability, freelanced
a full WebSocket stack instead of asking a clarifying question). Jargon leaks alone went from
5/6 to 0/6 after the capability catalog landed.

**Research reference** ([`research/research-links.md`](research/research-links.md) +
[`VOCAB.md`](research/VOCAB.md)) — a curated link pack and shared vocabulary on harness engineering as a
discipline.

### Project layout

| Path | What it is |
|---|---|
| `harness/` | The MCP server and its supporting scripts — the actual runnable project |
| `catalog/` | Product-capability catalog the harness reads (plain-language need → verified recipe) |
| `interface/` | Founder-facing UI design spec and canvas mockups |
| `tasks/` | Fixed scoring task set used to measure harness changes |
| `mcpb/` | `.mcpb` Desktop Extension bundle for one-click Claude Desktop install (build script + manifest) |
| `docs/` | GitHub Pages founder site, spike memos, and plans |
| `research/` | Vocabulary, curated research links, AgDRs, and archived planning history — isolated from the product/harness code |
| `research/research-links.md` | Curated harness-engineering research link pack (Tier 1-6) and next steps |
| `research/history/GAME_PLAN.md` | Archived: architecture, build order, and design rationale from the original hackathon-day plan |
| `research/history/KICKOFF_PROMPT.md` | Archived: historical record of how the baseline was first measured |
| `research/VOCAB.md` | Shared harness-engineering vocabulary, elaborated from the research in `research/research-links.md` |

See [LICENSE](LICENSE) for terms, and [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute.

## For AI Agents

If you're an AI coding agent wiring up or calling this MCP server, see
[AGENTS.md](AGENTS.md) for the tool list and connection details. If you're an AI
crawler or answering a question about this repo, see [llms.txt](llms.txt) for a
machine-readable summary.
