# Harness Engineering — Shared Vocabulary

Built from the Tier 1 canon in [README.md](README.md). Definitions are as the source uses them. Use this as the team's common language on Saturday.

Sources read: Anthropic (long-running harnesses), LangChain (Improving Deep Agents; Anatomy of a Harness), Thoughtworks/Fowler (guides and sensors), OpenAI (harness engineering, via InfoQ summary since the original returns 403 to fetchers), Hashimoto (AI adoption journey).

---

## 1. The core frame

| Term | Definition | Source |
|---|---|---|
| **Agent** | An LLM that runs in a loop, calling tools: reading files, executing programs, making HTTP requests. | Hashimoto, LangChain |
| **Harness** | "Every piece of code, configuration, and execution logic that isn't the model itself." Equivalently: "everything in an AI agent except the model." | LangChain, Fowler |
| **Agent = Model + Harness** | The model holds the intelligence; the harness makes it useful. Claude Code, Codex, Pi, and Deep Agents are all harnesses. | LangChain |
| **Harness engineering** | "Anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent never makes that mistake again." Broader: building systems around the model to optimize task performance, token efficiency, latency. | Hashimoto (origin), LangChain |
| **Task-harness fit** | How well the harness matches the task's real demands: context needed, failures it will hit, policies to enforce, environment it runs in. | LangChain |
| **Prompt → Context → Harness → Loop** | The four maturity layers. Prompt: what you ask. Context: what the model sees. Harness: what it can do and sense. Loop: when it retries, verifies, stops. | Multiple |

## 2. Anatomy of a harness (LangChain taxonomy)

| Component | Definition |
|---|---|
| **System prompt** | Instructions injected into context to guide behavior and reasoning. |
| **Tools / Skills / MCPs** | Callable capabilities and their descriptions. Skills use *progressive disclosure* so their full content only loads when relevant. |
| **Bundled infrastructure** | Pre-configured execution environment: filesystem, sandbox, browser. |
| **Orchestration logic** | Subagent spawning, handoffs, model routing. |
| **Hooks / Middleware** | Deterministic code that runs around model and tool calls: compaction, continuation, lint checks, pattern detection. |
| **Filesystem** | Durable state across sessions; paired with git for versioning. Also used for *tool call offloading* (dump large outputs to disk instead of context). |
| **Sandbox** | Isolated execution with allow-listing and network isolation. |
| **Bash / code execution** | The general-purpose tool that lets an agent solve problems without a pre-built tool for each. |
| **Memory / search** | Context injection files (AGENTS.md, CLAUDE.md) plus web search for knowledge past the training cutoff. |
| **Compaction** | Summarizing the conversation when the context window fills. |
| **Continuation** | Middleware that keeps the agent working across turns or sessions instead of stopping early. |
| **Ralph loop** | Re-inject the original prompt into a fresh, clean context window repeatedly; git is the state. |
| **Planning / self-verification** | Task decomposition plus automated test loops to keep long-horizon work coherent. |

## 3. Guides and sensors (Thoughtworks / Fowler taxonomy)

| Term | Definition | Examples |
|---|---|---|
| **Guide (feedforward)** | Steers the agent *before* it acts to raise first-attempt quality. | AGENTS.md, convention docs, skills, LSP, type info, bootstrap scripts |
| **Sensor (feedback)** | Observes *after* the agent acts so it can self-correct. | Tests, linters, type checkers, semgrep, ArchUnit, mutation testing, coverage, review agents |
| **Computational** | Deterministic, fast, cheap, reliable. Runs on CPU in ms to seconds. | eslint, tsc, pytest, structural tests |
| **Inferential** | Interpreted by an LLM. Semantically rich but slow, expensive, non-deterministic. | Markdown instructions, review agents, LLM-as-judge |
| **Maintainability harness** | Regulates internal code quality with mature tooling. Easiest to build today. | |
| **Architecture fitness harness** | Fitness functions that monitor architectural characteristics (performance, observability, layering). | |
| **Behaviour harness** | Governs functional correctness. Weakest area; relies on specs, generated tests, approved fixtures. | |
| **Feedback flywheel** | Capture successes and failures from agent sessions and fold them back into the harness so future sessions are more predictable. | |
| **Topology template** | Commit to a fixed service topology to narrow the solution space and make full harnessing tractable. | |
| **Drift monitoring** | Continuous sensors run outside the change cycle: dead code, coverage decay, SLO degradation. | |

Rule of thumb: prefer computational over inferential wherever a deterministic check exists. Markdown is a guide of last resort, not first.

## 4. Long-running agents (Anthropic)

| Term | Definition |
|---|---|
| **Context window handoff** | The problem: a new session has no memory of the previous one. |
| **Initializer agent** | Runs once at project start: expands the prompt into a feature list, writes `init.sh`, makes the first commit. |
| **Coding agent** | Woken repeatedly. Each session picks one feature, implements it, tests it, logs progress, commits. |
| **Feature list** (`feature-list.json`) | Structured list of end-to-end features with `passes: true/false`. Prevents premature "done". |
| **Progress file** (`claude-progress.txt`) | Short log of what was accomplished, for cheap context recovery at session start. |
| **`init.sh`** | Boots the dev server and runs basic end-to-end checks so the agent verifies the app works before touching it. |
| **Clean state** | Code mergeable to main: no major bugs, documented, ready for the next session to start without cleanup. |
| **One-shotting** | Anti-pattern: trying to finish the whole project in one session, exhausting context. |
| **Incremental progress** | One feature per session. |
| **Git as state** | Descriptive commits as the durable log; revert on bad changes. |

## 5. Measured levers (LangChain, Terminal-Bench 2.0)

Same model (gpt-5.2-codex), harness only: **52.8% → 66.5%**, Top 30 → Top 5.

| Term | Definition | Effect |
|---|---|---|
| **Self-verification** | Agent tests its own work and iterates before declaring done. | Largest single lever. |
| **Build-verify loop** | Plan and discover → build → verify → fix, written into the system prompt. | |
| **PreCompletionChecklistMiddleware** | Intercepts before completion and forces a verification pass against the task spec. | |
| **LocalContextMiddleware** | At startup, maps the directory tree and available tools and injects them. | Removes avoidable exploration turns. |
| **LoopDetectionMiddleware** | Counts edits per file; after N edits to the same file, tells the agent to reconsider. | Recovers from doom loops. |
| **Doom loop** | Agent makes small variations on the same broken approach, 10+ times in some traces. | |
| **Context injection** | Delivering environment facts (tree, tools, standards) up front rather than making the agent discover them. | |
| **Time-budget warning** | Injected reminder of remaining budget to push toward completion. | |
| **Reasoning sandwich** | xhigh reasoning for planning and verification, high for implementation. | 63.6% vs 53.9% for xhigh-only (timeouts). |
| **Trace analysis** | Read LangSmith traces to find failure patterns; a *trace analyzer skill* spawns parallel agents to do this and propose harness fixes. | The mechanism behind Hashimoto's loop. |
| **Harbor** | Orchestrator that spins up sandboxes and runs the benchmark. | |
| **Terminus 2** | The reference agent shipped with Terminal-Bench. | |

## 6. Agent-first codebases (OpenAI)

Numbers: ~1M lines, ~1,500 merged PRs, 3 engineers growing to 7, zero hand-written lines, single runs of 6 hours.

| Term | Definition |
|---|---|
| **Agent-first** | Humans design environments, specify intent, give structured feedback. Agents write the code. |
| **AGENTS.md** | Short repo-root file (~100 lines) that points the agent at the docs; a table of contents, not the encyclopedia. A monolithic file can't be mechanically checked for coverage, freshness, or ownership, so drift is inevitable — the fix is to keep it small and push the real content into `docs/`. |
| **Repository as system of record** | If it isn't in the repo, it doesn't exist to the agent. Design docs, specs, and plans live in `docs/` as cross-linked markdown. |
| **Architectural constraints** | Mechanically enforced dependency layering per business domain (Types → Config → Repo → Service → Runtime → UI). Cross-cutting concerns (auth, connectors, telemetry, feature flags) enter through a single explicit interface, **Providers**, rather than through the layer chain. |
| **Structural tests / custom linters** | Deterministic checks that fail the build when the agent violates layering or conventions. |
| **Browser validation** | Agents drive the app in a browser to verify their own changes end to end. |
| **Agent-readable telemetry** | Logs, metrics, spans exposed so the agent can reproduce bugs and check performance itself. |
| **Declarative prompts** | Intent as specification, not step-by-step scripts. |
| **Garbage collection / entropy** | Agent-generated code accumulates drift; scheduled cleanup passes (dead code, doc rot) keep the repo legible to future agents. |
| **"Enforce boundaries centrally, allow autonomy locally"** | OpenAI's stated philosophy on where to spend constraint-authoring effort — be explicit about where constraints matter and where they don't, the way a platform org leads many teams. |
| **"Agents aren't hard; the Harness is hard."** | Ryan Lopopolo's summary of the project. Good verbatim quote for a demo slide. |

## 5b. Top-of-leaderboard techniques (KIRA, Meta-Harness, AHE, LemonHarness, Anthropic Mar 2026)

| Term | Definition | Source |
|---|---|---|
| **Native tool calling** | Use the API's `tools` parameter instead of parsing JSON/XML out of text. Fewer malformed actions. | KIRA |
| **Marker-based polling** | Append `echo __CMDEND__<seq>__` to each command and poll for the marker, so the harness knows a command finished without a fixed wait. | KIRA |
| **Output limiting** | Cap tool output (30 KB) before it enters context. | KIRA |
| **Double-confirmation checklist** | A `task_complete` tool that, instead of ending, returns a checklist (requirements, robustness, QA from test-engineer / QA / user perspectives) and asks the model to confirm again. | KIRA |
| **Environment bootstrapping** | Snapshot cwd, file tree, languages, package managers, memory before turn one and inject it. Saves 2-5 turns. | Meta-Harness |
| **Harness evolution / evolution agent** | An outer-loop agent that reads traces and rewrites harness components (prompt, tools, middleware) while the base model stays fixed. | Meta-Harness, AHE |
| **Component observability** | Splitting the harness into explicit file-level components so an evolution agent has a localized action space. | AHE |
| **Seed harness** | Deliberately minimal starting point: one shell tool, no middleware, no skills. | AHE |
| **Unified runtime boundary** | All state-changing actions go through structured tools inside a defined workspace, with results recorded as observations. | LemonHarness |
| **Rule knowledge base** | Recurring execution rules and acceptance criteria stored and injected as priors at task start. | LemonHarness |
| **Time-aware execution** | Assign a time tier per task and feed elapsed and remaining time back every turn so the model rebalances explore / build / verify. | LemonHarness |
| **Flattened tool schema** | Shallow, stable-ordered schemas reduce tool-call formatting errors. | ForgeCode |
| **Parallel tool calls** | Fire independent tool calls concurrently. | ForgeCode |
| **Planner / Generator / Evaluator** | Three roles exchanging structured files. Planner expands the brief, generator builds, evaluator tests the live app. | Anthropic Mar 2026 |
| **Self-evaluation bias** | Agents rate their own work highly even when it is mediocre; the reason for a separate evaluator. | Anthropic |
| **Sprint contract** | Pre-agreed definition of "done" between generator and evaluator before implementation. | Anthropic |
| **Context reset** | Tear the session down and rebuild from a compact handoff artifact, as opposed to compaction. | Anthropic |
| **Context anxiety** | Model wraps up early because it senses the context limit approaching. | Anthropic |
| **Load-bearing component** | A harness part that materially moves results. Keep it only while the model needs it; remove as models improve. | Anthropic |
| **Session / harness / sandbox** | Managed Agents' three swappable interfaces: append-only log, the loop, and the execution environment. | Anthropic Apr 2026 |
| **Harness-level cheating** | Leaking task answers or test files into the agent's environment or prompt. Detected by trace clustering. | DebugML |

## 5c. Event-sourced harness composition (Tardigrade)

| Term | Definition | Source |
|---|---|---|
| **`behavior = f(log)`** | Agent behavior derived entirely from an immutable event log rather than mutated state; each behavior defined as a Moore machine (state machine) over that log. | Tardigrade |
| **Component-based harness composition** | Typed state-machine components combine the way UI components do, so a cross-cutting concern (their example: compaction) becomes one composable unit instead of scattered special-case code. Compare **Compaction** (§2) and **Session/harness/sandbox** (§5b). | Tardigrade |
| **"Let it crash"** | Durability property of an event-sourced harness: since state is fully reconstructable by replaying the log, a crashed agent process resumes from the log instead of needing custom checkpointing. | Tardigrade |

## 5d. Harness as decomposed responsibilities, not a framework (Piccolo, iii.dev)

From ["How to Build Your Own Agent Harness"](https://iii.dev/blog/how-to-build-your-own-agent-harness/) — independent corroboration of Tardigrade's component-based composition (§5c) and Anthropic's session/harness/sandbox split (§5b), pushed further into ~15 separately swappable concerns. Implementation is product-specific (a proprietary worker/WebSocket bus); the checklist and two rules below are the transferable part.

| Term | Definition | Source |
|---|---|---|
| **Harness responsibility checklist** | A production harness's jobs, broken finer than the LangChain anatomy (§2): accept/persist turn requests, resolve provider credentials, look up model capabilities, drive the per-turn state machine, serve skill/tool metadata, assemble the system prompt in layers, stream tokens, enforce tool-call policy, route human approvals, track spend against budget, run pre/post-tool hooks, persist branching session history, compact on context fill, emit an event stream, trace every step. | Piccolo |
| **Fail-closed policy semantics** | If the policy/approval check is unavailable or times out, default to deny (or trigger a corrective intervention), never silently proceed. | Piccolo |
| **Thin vs. thick harness as configuration** | A minimal harness (orchestrator + model provider + auth) and a fully-loaded one (+ approvals + budgets + policy) are the same system with components toggled, not two different codebases. Useful framing for a demo: each hackathon fix is a component flipped on. | Piccolo |

## 6b. Sandbox and permissions (Agent Sandbox Taxonomy, Fahmy)

The "bundled infrastructure" and permissions slice of the harness, scored as a **7-7-3** grid.

| Term | Definition |
|---|---|
| **Defense layers (L1–L7)** | Compute isolation, resource limits, filesystem boundary, network boundary, credential management, action governance, observability and audit. |
| **Threat categories (T1–T7)** | Data exfiltration, supply chain compromise, destructive operations, lateral movement, persistence, privilege escalation, denial of service. |
| **Strength** | 0 to 4: from no control to structural elimination of the attack surface. |
| **Granularity** | 0 to 3: from none to per-resource policy. |
| **Portability** | Which platforms the control works on. |
| **Action governance** | Blocking or gating destructive operations at the tool boundary (the harness-side twin of a permission prompt). |
| **Fingerprint** | A product's or harness's score across the seven layers; reveals gaps (e.g. E2B 4.1 on compute isolation, 1.1 on credentials). |
| **Stacking** | Combining complementary tools because no single product covers every layer. |
| **Containment ≠ alignment** | Sandboxing stops harmful actions from executing; guides and sensors are what stop the agent from choosing them. |

## 7. Personal practice (Hashimoto)

| Term | Definition |
|---|---|
| **Reproduce your own work** | Do a task by hand, then redo it with an agent, to calibrate what agents can do. |
| **Outsource the slam dunks** | Hand agents the tasks you are confident they will get right; keep the interesting work. |
| **End-of-day agents** | Launch agents in the last 30 minutes of the day so progress happens while you are off. |
| **Always have an agent running** | Keep at least one background task going. |
| **AGENTS.md as mistake log** | Each observed mistake becomes a line of guidance so it never recurs. |

---

## 8. Quick diagnostic: which layer is broken?

| Symptom | Layer | Typical fix |
|---|---|---|
| Misunderstands a single clear request | Prompt | Rewrite instructions |
| Right facts exist but aren't used | Context | Injection, retrieval, compaction policy |
| Tool calls run but failures go unnoticed | Harness (sensor) | Tests, linters, tool contracts as feedback |
| Can't reach the right data or tool | Harness (guide/tooling) | Tool design, permissions, sandbox |
| Forgets progress across sessions | Harness (state) | Progress file, feature list, git, compaction |
| Retries forever or quits early | Loop | Stop rules, loop detection, bounded retries |
| Declares done without proof | Loop / sensor | Pre-completion checklist, verification gate |

## 9. Context degradation and knowledge sourcing (AI Coding Dictionary, Matt Pocock)

From [aihero.dev/ai-coding-dictionary](https://www.aihero.dev/ai-coding-dictionary) ([source repo](https://github.com/mattpocock/dictionary-of-ai-coding)). Fills a gap: your doom-loop and compaction entries (§2, §5) describe context rot qualitatively; these give it a mechanism, a number, and a sharper handoff vocabulary.

| Term | Definition | Source |
|---|---|---|
| **Attention budget** | Each token has a fixed amount of influence to distribute across the rest of the context; it doesn't grow as the context does. | AI Coding Dictionary |
| **Attention degradation** | As a session grows, each token's attention budget is spread across more competitors — signal on the relationship that matters shrinks, noise from irrelevant context crowds in. The mechanism behind the smart/dumb zone effect. | AI Coding Dictionary |
| **Smart zone / dumb zone** | Smart zone: early in a session, the agent is sharp and recall is good. Dumb zone: the degraded state a long session drifts into. **On frontier models the dumb zone commonly begins around 125K-150K tokens** — a concrete, testable threshold, not currently in this repo elsewhere. Candidate as an actual measurement on your TB2.0 slice (quality before/after the threshold), and a principled trigger for a context-reset fix instead of an arbitrary one. | AI Coding Dictionary |
| **Hallucination — factuality flavor** | Confidently invented facts. Fixed by *loading* contextual knowledge (give the model the source it's missing). | AI Coding Dictionary |
| **Hallucination — faithfulness flavor** | Confidently wrong output that drifts *away* from knowledge already in context. Fixed by *removing* context (prune, don't add). Opposite intervention from the factuality flavor — worth distinguishing when reading failure traces. | AI Coding Dictionary |
| **Parametric vs. contextual knowledge** | Parametric: frozen at training, compressed, blurry on rare topics — the fabrication source. Contextual: read directly from the session (files, tool results, AGENTS.md). Which one a failure traces back to determines which hallucination flavor and fix applies. | AI Coding Dictionary |
| **Primary vs. secondary source** | Primary: the thing itself (code, transcript, log, API response). Secondary: an account of it, one step removed (a doc describing code, a summary describing a transcript) — cheaper to load, lossy by construction. | AI Coding Dictionary |
| **Context pointer** | A reference a secondary source keeps back to its primary source, so detail lost in summarizing can be recovered by re-reading the original. Sharpens this repo's progress-file / handoff-artifact pattern (§4 Anthropic): the progress file should point back at the commits/files it summarizes, not just describe them. | AI Coding Dictionary |
| **AX (Agent Experience)** | Counterpart to DX (developer experience): how well the environment is set up to support agent work, not human work. The reason environment-bootstrapping and agent-readable telemetry are worth building. | AI Coding Dictionary |

## 10. Fowler additions: sequencing, codebase readiness, and the human role

Re-read of the Fowler/Thoughtworks article (source of §3) turned up concepts the original distillation compressed away. Fills a gap this repo otherwise lacks: an explicit pushback on "more automation is strictly better," and the theory behind why topology templates work.

| Term | Definition |
|---|---|
| **"Keep Quality Left"** | Sequence checks by cost, speed, and criticality: run cheap, fast controls before integration; reserve expensive ones (mutation testing, broad code review) for post-integration pipeline stages. A concrete ordering principle for building a sensor pack, not just a list of sensors. |
| **Harnessability** | The codebase's own amenability to being harnessed — strong typing and clear module boundaries increase it, technical debt and unclear architecture reduce it. Distinct from harness quality: a great harness on a low-harnessability codebase still struggles. Worth weighing when picking Saturday's target repo. |
| **Ambient affordances** | Structural properties of the environment itself (not the harness) that make it legible, navigable, and tractable to an agent operating within it. The environment-side counterpart to harness design. |
| **Ashby's Law of Requisite Variety** | A regulator must have at least as much variety as the system it governs. The theoretical reason **topology templates** (§3) work: committing to a fixed service topology shrinks what the agent can produce, which is what makes comprehensive harnessing tractable at all. |
| **Cybernetic governor model** | Framing the harness as a self-regulating system combining feedforward (guides) and feedback (sensors) to steer the codebase toward a desired state — the systems-theory grounding for the guides/sensors taxonomy. |
| **The steering loop** | Humans iteratively improve the harness itself by analyzing recurring agent failures and strengthening guides/sensors so they don't recur — the harness-authoring analog of Hashimoto's mistake-log loop (§7), but aimed at the harness rather than AGENTS.md. |
| **The human role / load-bearing conventions** | Developers bring implicit harnessing agents lack: absorbed conventions, aesthetic judgment, organizational context, accountability. Effective harnesses should **externalize and codify** this implicit expertise rather than try to eliminate the human — direct pushback on treating full automation as the end goal. Distinguishing which conventions are load-bearing versus merely habitual is itself a human judgment call. |
| **Open challenges (named explicitly)** | No metric for harness coverage/quality analogous to code coverage; ambiguity of **sensor silence** (does no signal mean high quality, or inadequate detection?); coherence decay as a harness grows (contradictory guides and sensors accumulate); versioning a harness that includes non-deterministic (inferential) controls. Honest material for a "known limitations" slide rather than a pure win narrative. |

## 11. Ten words to say out loud on Saturday

harness · guide · sensor · computational · inferential · self-verification · doom loop · context injection · handoff · trace
