# Harness Engineering Research

**To run the working demo:** `./setup.sh` from the repo root checks for Docker, installs Floci if
needed (with confirmation), sets up the harness Python environment, and wires the MCP server into
Claude Desktop and Claude Code. See [`harness/README.md`](harness/README.md) for what it does and
the manual steps it automates.

**Working definition (consensus across sources):** `Agent = Model + Harness`. The harness is everything around the model: system prompt, tools/skills/MCP, sandbox/filesystem, orchestration (subagents, routing), hooks/middleware (compaction, doom-loop detection, verification), memory/state across context windows, and permissions. Harness changes alone have moved Terminal-Bench 2.0 scores by 10-14 points with the same model.

## What's in this repo

This repo has two parts:

1. **A working demo harness** — an MCP server (`harness/`) that turns a non-technical founder's
   plain-language product request ("users should be able to upload a photo") into a verified,
   running local infra environment on [Floci](https://floci.io/), using a capability catalog
   (`catalog/`) and a fixed scoring task set (`tasks/`). See [`harness/README.md`](harness/README.md)
   to run it, and [`GAME_PLAN.md`](docs/history/GAME_PLAN.md) for the design behind it.
2. **A research reference** ([`docs/research-links.md`](docs/research-links.md) +
   [`VOCAB.md`](VOCAB.md)) — a curated link pack and shared vocabulary on harness engineering as a
   discipline.

## Project layout

| Path | What it is |
|---|---|
| `harness/` | The MCP server and its supporting scripts — the actual runnable project |
| `catalog/` | Product-capability catalog the harness reads (plain-language need → verified recipe) |
| `interface/` | Founder-facing UI design spec and canvas mockups |
| `tasks/` | Fixed scoring task set used to measure harness changes |
| `docs/research-links.md` | Curated harness-engineering research link pack (Tier 1-6) and next steps |
| `docs/history/GAME_PLAN.md` | Archived: architecture, build order, and design rationale from the original hackathon-day plan |
| `docs/history/KICKOFF_PROMPT.md` | Archived: historical record of how the baseline was first measured |
| `VOCAB.md` | Shared harness-engineering vocabulary, elaborated from the research in `docs/research-links.md` |

See [LICENSE](LICENSE) for terms.
