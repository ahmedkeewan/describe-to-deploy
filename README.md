# Harness Engineering Hackathon — Research Pack

Compiled 2026-09-03 for the hackathon on Saturday 2026-09-06. Research phase only.

**Working definition (consensus across sources):** `Agent = Model + Harness`. The harness is everything around the model: system prompt, tools/skills/MCP, sandbox/filesystem, orchestration (subagents, routing), hooks/middleware (compaction, doom-loop detection, verification), memory/state across context windows, and permissions. Harness changes alone have moved Terminal-Bench 2.0 scores by 10-14 points with the same model.

---

## Tier 1 — Must read before Saturday (the canon, ~2 hrs)

| Source | Why it matters |
|---|---|
| [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (Nov 2025) | The initializer-agent + coding-agent pattern. `feature-list.json`, `init.sh`, `claude-progress.txt`, git commits and test gates as cross-session state. Reference design for anything spanning multiple context windows. |
| [OpenAI: Harness engineering — leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering) (Feb 2026, Ryan Lopopolo) | Coined the term. ~1M LOC, zero human-written lines, 3 engineers. AGENTS.md, repo-local docs as system of record, architectural constraints enforced by linters, browser validation, telemetry the agent can read. |
| [LangChain: Improving Deep Agents with harness engineering](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering) (Feb 2026) | TB2.0 52.8% → 66.5% (Top 30 → Top 5) with the same model. Three levers: self-verification prompting, environment context injection, middleware that detects doom loops. "Reasoning sandwich" (xhigh-high-xhigh). |
| [LangChain: The Anatomy of an Agent Harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) (Mar 2026, Sydney Runkle) | The cleanest taxonomy of harness components. Use this as the team's shared vocabulary. |
| [Martin Fowler / Thoughtworks: Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html) (Birgitta Böckeler) | Guides (feedforward) vs Sensors (feedback), each inferential (LLM-interpreted markdown) or computational (linters, tests, LSP, mutation testing). The "Feedback Flywheel". Best framework for deciding *what to build* in a day. |
| [Mitchell Hashimoto: My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey) (Feb 2026) | Origin of the practice: "every time the agent makes a mistake, engineer the harness so it can never make that mistake again." |

## Tier 1b — The winning edge (added 2026-09-03)

What the current top-of-leaderboard harnesses do that the Tier 1 posts don't cover. All read and distilled into VOCAB.md.

| Source | What to steal |
|---|---|
| [Anthropic: Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) (Mar 2026) | Planner → Generator → Evaluator, communicating through files not chat. GAN-style evaluator with Playwright MCP to beat *self-evaluation bias*. Sprint contracts defining "done" before coding. Context resets + handoff artifacts. Cost: solo run $9/20 min vs full harness $200/6 hr. Big lesson: **remove load-bearing components as the model improves** (sprints and resets dropped on Opus 4.6). |
| [Anthropic: Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents) (Apr 2026) | Session (append-only log) / harness (the loop) / sandbox (where code runs) as three swappable interfaces. Harnesses encode assumptions that go stale. |
| [KRAFTON Terminus-KIRA](https://github.com/krafton-ai/KIRA) + [blog](https://krafton-ai.github.io/blog/terminus_kira/) (Feb 2026) | ~75% TB2 from five cheap changes to Terminus 2: native tool calling instead of parsed JSON/XML, **marker-based polling** (`echo __CMDEND__<seq>__` to detect command completion early), 30 KB output cap, `task_complete` tool that triggers a **double-confirmation checklist** (test engineer / QA / user perspectives), prompt caching. Each one is a one-hour hackathon task. |
| [Meta-Harness TB2 artifact](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact) | Built on KIRA. Adds environment bootstrapping. 76.4% with Opus 4.6. |
| [NexAU-AHE](https://github.com/china-qijizhifeng/agentic-harness-engineering) + [paper](https://arxiv.org/abs/2604.25850) | 84.7% TB2 (#3). An *evolution agent* rewrites harness components from trace observations, starting from a bash-only seed. GPT-5.4 69.7 → 77.0 in 10 iterations. Frozen harness transfers to SWE-bench with fewer tokens. |
| [LemonHarness technical report](https://arxiv.org/abs/2606.24311) | 84.5% TB2 (#2). Three ideas: unified runtime boundary (all state changes through structured tools inside a workspace), **reusable rule knowledge base** (recurring acceptance criteria injected as priors), **time-aware execution** (assign a time tier, feed elapsed/remaining time back each turn). |
| [ForgeCode](https://forgecode.dev/blog/benchmarks-dont-matter/) | Legit ideas: flattened tool schemas with stable field order (fewer malformed calls), parallel independent tool calls (3-5x faster), recursive subagents. See caveat below. |
| [DebugML: cheating on agent benchmarks](https://debugml.github.io/cheating-agents/) | Pilot (#1) let the agent read `/tests`; ForgeCode (#2) auto-injected AGENTS.md files containing answer keys. Detected via trace clustering (Meerkat). **Lesson**: judges and reviewers read traces. Keep the sandbox clean, publish trajectories, never let task-specific hints leak into the harness. |
| [Claude Agent SDK hooks](https://platform.claude.com/docs/en/agent-sdk/hooks) + [hooks reference](https://code.claude.com/docs/en/hooks) | If building on Claude: PreToolUse / PostToolUse / Stop / SubagentStart / PreCompact hooks are the middleware surface. Fastest path to a sensor pack without writing an agent loop. |

Prior harness hackathons (winners not yet published for either):
- [Harness Engineering Hack, SF, Jun 2026](https://harness-hack.devpost.com/) — judges from Anthropic, Guild.ai, Pioneer, Composio, Nvidia, Stripe. Categories rewarded "most innovative use of agents", observability (Langfuse), and execution quality. Check `/project-gallery` for winners.
- [TrueForge Agent Harness Hackathon, Aug 2026](https://www.wemakedevs.org/hackathons/trueforge) — judged on real MCP tools, sandboxed execution, human approvals, subagents, persistent sessions. Winners due on the site and @WeMakeDevs.

## Tier 2 — Anthropic supporting posts (tool + context design)

- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (Dec 2024) — workflows vs agents, keep it simple, the base loop.
- [Writing effective tools for agents — with agents](https://www.anthropic.com/engineering/writing-tools-for-agents) (Sep 2025) — namespacing, meaningful tool responses, token-efficient outputs, use Claude to optimize its own tools via evals.
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (Sep 2025) — compaction, structured note-taking, subagent context isolation, just-in-time retrieval.
- [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) (Nov 2025) — agents write code that calls tools instead of direct tool calls; big token savings.

## Tier 3 — LangChain / Deep Agents (the most hackathon-ready stack)

Blog posts:
- [How to Build a Custom Agent Harness](https://www.langchain.com/blog/how-to-build-a-custom-agent-harness) — `create_agent` + middleware; introduces "task-harness fit".
- [How Middleware Lets You Customize Your Agent Harness](https://www.langchain.com/blog/how-middleware-lets-you-customize-your-agent-harness) (Mar 2026) — inject tools by state, swap models mid-task, mutate system prompt per step.
- [Agent Frameworks, Runtimes, and Harnesses — oh my!](https://blog.langchain.com/agent-frameworks-runtimes-and-harnesses-oh-my/) — LangChain = framework, LangGraph = runtime, DeepAgents = harness.
- [New in Deep Agents v0.6](https://www.langchain.com/blog/deep-agents-0-6) — harness profiles; gpt-5.3-codex +20% on tau2-bench, opus-4.7 +10% from harness changes alone.
- [Tuning Deep Agents to Work Well with Different Models](https://www.langchain.com/blog/tuning-deep-agents-different-models) — per-model harness profiles; notes Claude Code harness ranked last among Opus 4.6 submissions.
- [Evaluating Deep Agents CLI on Terminal Bench 2.0](https://www.langchain.com/blog/evaluating-deepagents-cli-on-terminal-bench-2-0) — how they ran Harbor + Daytona + LangSmith.

Docs and repos:
- Harness docs: https://docs.langchain.com/oss/python/deepagents/harness
- `langchain-ai/deepagents` — planning (`write_todos`), virtual FS, subagents, memory, skills, sandbox, HITL out of the box.
- `langchain-ai/deepagents-harbor` — eval harness for running deepagents against TB2.0.
- Third-party: [NVIDIA: Deep Agents harness profile for Nemotron 3 Ultra](https://developer.nvidia.com/blog/create-a-langchain-deep-agents-harness-profile-for-nvidia-nemotron-3-ultra-to-improve-performance/), [Daily Dose of DS anatomy breakdown](https://blog.dailydoseofds.com/p/the-anatomy-of-an-agent-harness), [Populix: Building an Agent Harness with Deep Agents](https://medium.com/populix-engineering/building-an-agent-harness-with-langchain-deep-agents-e0402de12a94).

## Tier 4 — SOTA / research (where the frontier is)

- **Meta-Harness** (Stanford IRIS, Lee/Finn/Khattab, [arXiv 2603.28052](https://arxiv.org/abs/2603.28052)) — outer-loop search over harness code. Repo: https://github.com/stanford-iris-lab/meta-harness. TB2 artifact (76.4% w/ Opus 4.6): https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact. Key discovered trick: **environment bootstrapping** — snapshot cwd, file tree, toolchain, package managers, memory *before* the loop starts and inject into the first prompt; saves 2-5 exploration turns. Cheap to replicate on Saturday. Applied fork: `JoelNiklaus/harness-optimization` (Harvey Legal Agent Benchmark).
- [Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses](https://arxiv.org/pdf/2604.25850) (arXiv 2604.25850) — evolve the harness from traces.
- [Natural-Language Agent Harnesses](https://arxiv.org/html/2603.25723v1) (arXiv 2603.25723).
- [Code as Agent Harness](https://arxiv.org/pdf/2605.18747).
- [CAAF: Harness as an Asset](https://arxiv.org/pdf/2604.17025) — versioned, RBAC-frozen harness across products.
- [Harnesses for Inference-Time Alignment over Execution Trajectories](https://arxiv.org/pdf/2605.21516).
- Surveys: `RUCAIBox/awesome-agent-harness` (500+ refs), `Gloriaameng/Awesome-Agent-Harness` (110+ papers, 23 systems).
- **Terminal-Bench 2.0 leaderboard** (source of truth): https://www.tbench.ai/leaderboard/terminal-bench/2.0. Top entries ~84% (NexAU-AHE, LemonHarness, Capy, ForgeCode). Terminus 2 reference agent baselines ~55-65%. Submissions via Harbor: https://huggingface.co/datasets/harborframework/terminal-bench-2-leaderboard. TB 2.1 also live (Claude Code + Claude 5 Fable 83.8%, Codex CLI + GPT-5.5 83.1%).

## Tier 5 — GitHub repos to clone / study

Reference harnesses (small enough to read in an hour):
- `SWE-agent/mini-swe-agent` — ~100-line Python agent loop, bash-only tool, >74% SWE-bench Verified. The canonical minimal harness; ideal fork base. `pip install mini-swe-agent`.
- `badlogic/pi-mono` — minimal TS terminal harness, extensions/skills/MCP. ~100k stars. `npm i -g @mariozechner/pi-coding-agent`.
- `stanford-iris-lab/meta-harness-tbench2-artifact` — see above.
- `openai/codex` — the open Apache-2 Codex harness. Read with [Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform) (Aug 2026) and the App Server post.
- `openai/symphony` — daemon that polls Linear, spawns isolated Codex per issue, delivers PRs. `SPEC.md` is language-agnostic; community ports in Go (Baton), Rust (`kumanday/OpenSymphony`), OpenCode (`skorokithakis/symphony`). Guide: https://betterstack.com/community/guides/ai/openai-symphony/
- `humanlayer/advanced-context-engineering-for-coding-agents` — ACE-FCA and the Research/Plan/Implement method; `humanlayer/12-factor-agents` (own your context window, stateless reducer).
- `clavia-labs/tardigrade` ([docs](https://tardigrade.sh/docs/why), `bunx tardie init`) — TypeScript framework for agents built on an immutable event log + Effect TS. Core claim: `behavior = f(log)`, each behavior a composable state machine. A concrete small implementation of the session-as-append-only-log idea that Anthropic's Managed Agents post (Tier 1b) argues for abstractly — worth skimming as a working example.
- Ralph Wiggum loop (Geoff Huntley): `while :; do cat PROMPT.md | claude ; done` — fresh context each iteration, git as state. See [A Brief History of Ralph](https://www.humanlayer.dev/blog/brief-history-of-ralph) and [AI That Works: Ralph under the hood](https://boundaryml.com/podcast/2025-10-28-ralph-wiggum-coding-agent-power-tools).

Sandbox and permissions layer:
- [The Agent Sandbox Taxonomy](https://georgebuilds.dev/blog/agent-sandbox-taxonomy/) (George Fahmy, Mar 2026) + repo `kajogo777/the-agent-sandbox-taxonomy` — 7 defense layers × 7 threat categories × 3 scoring dimensions, applied to 26 products (E2B, Modal, Docker Sandbox, StrongDM Leash, nono, Claude Code, Cursor, Devin). Key findings: no product covers every layer, so stack tools; VM isolation + open network + raw credentials is false confidence; sandboxing is containment, not alignment. Use the seven layers to fingerprint your own harness before Saturday.

Awesome lists (pick two, skim both):
- https://github.com/ai-boost/awesome-harness-engineering — most recently updated, broadest.
- https://github.com/Picrew/awesome-agent-harness — implementation-first, project tables.
- Also: `walkinglabs/awesome-harness-engineering`, `Jiaaqiliu/Awesome-Harness-Engineering`, `AutoJunjie/awesome-agent-harness`, `mahonzhan/awesome-agent-harness`, `RyanAlberts/best-of-Agent-Harnesses`, `bradagi/awesome-cli-coding-agents`.

## Tier 6 — Secondary explainers (skim if time)

- [Faros.ai: Harness Engineering in 2026](https://www.faros.ai/blog/harness-engineering) — the prompt → context → harness timeline.
- [codecentric: Loop, Harness, Context Engineering explained](https://www.codecentric.de/en/knowledge-hub/blog/loop-harness-context-engineering-explained) — symptom-to-layer diagnosis table.
- [Lyzr: Harness Engineering 2026 Playbook](https://www.lyzr.ai/blog/harness-engineering-for-ai-agents/), [Atlan: What is Harness Engineering](https://atlan.com/know/what-is-harness-engineering/), [Firecrawl: What is an Agent Harness](https://www.firecrawl.dev/blog/what-is-an-agent-harness), [Parallel: What is an AI harness](https://parallel.ai/articles/what-is-an-agent-harness).
- [InfoQ coverage of OpenAI post](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex/), [Addy Osmani: Long-running Agents](https://addyosmani.com/blog/long-running-agents/), [HN thread on Anthropic post](https://news.ycombinator.com/item?id=46081704).
- [Winder.ai: Comparison of AI Agent Harnesses 2026](https://winder.ai/ai-agent-harness-comparison/).
- [Thoughtworks podcast: What is harness engineering?](https://www.thoughtworks.com/en-es/insights/podcasts/technology-podcasts/what-harness-engineering) (May 2026).
- [ApexYard: AI-Governed Software Development Framework](https://apexyard.ai/) — org-level governance layer on top of a coding agent: mandatory PR gates (no direct push to main), role-based reviewer routing (20 roles / 6 departments), ~51 hooks enforcing secret-scanning and ticket linkage. Useful mainly for the **gate** concept (a sensor that blocks rather than just reports — see VOCAB.md §3); not a technique for improving a single agent loop's benchmark score.
- [ApexYard `harness-adapters/` + `docs/harnesses/`](https://github.com/me2resh/apexyard/tree/main/harness-adapters) — the framework's own answer to "how do gates survive a switch of coding-agent CLI": bash hooks stay the single source of truth, and pi/opencode/Codex/Cursor each get a thin transport adapter (declarative-generate or live-extension, per `docs/harnesses/README.md`). Live-proven (real credentialed turn blocked) for pi, opencode, and Codex as of 2026-07-09; Cursor only fails closed, not proven. Distilled into VOCAB.md §6c.
- [Simon Willison on Hashimoto's post](https://simonwillison.net/2026/Feb/5/ai-adoption-journey/).
- Prior hackathons for idea mining: [Harness Engineering Hack (SF, Jun 2026)](https://harness-hack.devpost.com/), [TrueForge Agent Harness Hackathon (Aug 2026)](https://www.wemakedevs.org/hackathons/trueforge).

---

## Layer diagnosis cheat sheet

| Symptom | Layer | Fix |
|---|---|---|
| Model misunderstands a single well-formed request | Prompt | Rewrite instructions |
| Right facts exist in the system but aren't used | Context | Retrieval, injection, compaction policy |
| Tool calls run but failures go unnoticed | Harness | Tool contracts, sensors, permissions, sandbox |
| Agent forgets progress across sessions | Harness | Durable state, checkpointing, progress artifacts |
| Doesn't know when to retry or quit | Loop | Stop rules, bounded retries, external grader |
| Works past success or stops before proof | Loop | Evidence-based terminal states |

## SOTA tips distilled (what actually moves the needle)

1. **Self-verification loops in the system prompt.** Make the agent run tests / re-read output before declaring done. Biggest single lever in LangChain's TB2 jump.
2. **Environment bootstrapping.** Inject cwd, file tree, toolchain, package managers into turn 1 (Meta-Harness). Don't make the agent discover the sandbox.
3. **Doom-loop / repeated-action detection middleware.** Hook that notices repeated identical tool calls and intervenes.
4. **External state over conversational memory.** Feature list, progress file, git commits, tests as the handoff between context windows (Anthropic). Ralph loop is the degenerate version.
5. **Guides + Sensors, prefer computational.** Markdown instructions are inferential; linters, type checks, architecture tests, LSP are deterministic and don't burn context (Thoughtworks).
6. **Repo is the system of record.** AGENTS.md / CLAUDE.md, design docs in-repo, agent-readable telemetry (OpenAI).
7. **Tool design = context design.** Namespaced, non-overlapping tools; token-lean responses; use the model to eval and rewrite its own tool descriptions (Anthropic).
8. **Per-model harness profiles.** The same harness performs differently per model; tune reasoning effort and prompts per model (Deep Agents v0.6).
9. **Trace everything.** LangSmith / Langfuse traces are what let you find the failure to harden against (Hashimoto's loop).
10. **Measure on a real benchmark.** Harbor + TB2.0 subset, or SWE-bench Lite via mini-swe-agent, so a demo has a number.

## Suggested next steps

- Read Tier 1 and skim Tier 3; agree on vocabulary (Anatomy post + guides/sensors).
- Pick a base: `deepagents` (fastest to build features) or `mini-swe-agent` (easiest to understand and benchmark).
- Set up Harbor with a 10-task TB2.0 slice so Saturday's harness changes can be scored.
- Candidate project ideas: environment-bootstrap middleware, doom-loop detector, computational sensor pack (lint/type/arch tests as hooks), cross-session progress harness a la Anthropic, or a mini Meta-Harness that mutates a prompt/tool config and re-scores.

## Caveats

Links were gathered from search results and not every page was fetched to confirm it resolves. Terminal-Bench numbers shift between snapshots, so check the official leaderboard before quoting them.
