# Describe to Deploy

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

**To try it:** `./setup.sh` from the repo root gets everything running (it checks for and
installs what it needs, with your confirmation before anything gets installed). Once it's
running, just talk to it in your normal AI chat app — no commands to memorize, nothing technical
to learn first.

That's the whole idea: you describe what you want, and the harness only ever tells you it's
ready once it has actually checked.

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
