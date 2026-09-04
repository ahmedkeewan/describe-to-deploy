# Hackathon Game Plan

Companion to [README.md](README.md). Hackathon date: Saturday 2026-09-06.

## Event profile (confirmed 2026-09-03)

Internal event, no public rubric. Any stack. Judged on **measured performance gain AND a working demo**. One day, solo or pair.

## Tailored recommendation

**Base**: `mini-swe-agent`. Tiny loop, one bash tool, model-agnostic, and Harbor already supports it, so the baseline is a one-liner. A pair can hold the whole codebase in their heads, which matters when you are patching the loop live.

**Project**: "Five fixes, one number." Stack the cheapest leaderboard-proven changes onto the seed harness and show the score climbing after each one. This satisfies both judging axes at once: the score is the measured gain, and the running agent with traces on screen is the demo.

Build order, each one measured before the next starts:

| # | Fix | Where in mini-swe-agent | Est. time |
|---|---|---|---|
| 1 | Environment bootstrap injected into first user turn | prompt template / run script | 45 min |
| 2 | Output cap (30 KB) on tool results | environment class | 20 min |
| 3 | Completion gate: agent's "done" returns a checklist and requires a second confirm | agent loop, intercept the submit action | 60 min |
| 4 | Time-aware execution: elapsed and remaining time appended to each observation | agent loop | 45 min |
| 5 | Loop detection: same command or same file edited N times triggers an intervention message | agent loop | 45 min |

Stretch (only if all five are measured by mid-afternoon): a one-iteration **evolution loop**. A second agent reads the failing traces from the slice, proposes one prompt or tool change, you apply it and re-run. Showing the harness improve itself on stage is the strongest possible closer for a demo-judged room.

**Scoring**: 10-task Terminal-Bench 2.0 slice through Harbor, 2 trials each, same model throughout. Pick tasks where the baseline fails on timeouts or premature completion, since fixes 3 and 4 target exactly those. Record pass rate, mean turns, and mean wall-clock per config.

**Demo (5 minutes)**:
1. One slide: Agent = Model + Harness, and the baseline number.
2. Live run of one task on the final harness with the trace viewer open. Point at the bootstrap block, the time counter, and the completion checklist firing.
3. The results table, one row per fix. Same model, five harness changes, score climbed from X to Y.
4. If stretch landed: the evolution agent's proposed diff and the re-run number.

**Pair split**: Person A owns Harbor, the slice, the baseline, and the results table. Person B owns the harness patches. Swap for review before each measurement run.

**Solo**: drop fix 5 and the stretch. Four fixes measured beats six unmeasured.

## Before Saturday (2 to 3 hours total)

1. **Read the Tier 1 canon.** Anthropic's long-running harness post, LangChain's Deep Agents post, and the Fowler guides-vs-sensors article. Those three give you the vocabulary and the three biggest levers.
2. **Pick your base now, not on Saturday.** Recommendation: `SWE-agent/mini-swe-agent`. It is about 100 lines, model-agnostic, and already scores well on SWE-bench, so every change you make is visible and attributable. Use `langchain-ai/deepagents` instead only if the hackathon rewards feature breadth over measurable gains.
3. **Get a scoreboard running.** Install Harbor and run a 5 to 10 task slice of Terminal-Bench 2.0 against the unmodified base. Save the baseline number. This is the single highest-value prep task: a harness demo without a before-and-after number is just a prompt.
4. **Set up tracing.** LangSmith or Langfuse, whichever you already have keys for. Hashimoto's loop ("engineer away every observed mistake") only works if you can see where the agent failed.
5. **Confirm API keys and sandbox.** Daytona, Docker, or whatever Harbor needs. Do not lose the first hour of the hackathon to setup.

Prep checklist:
- [x] Tier 1 articles read (vocabulary distilled in [VOCAB.md](VOCAB.md))
- [ ] Base repo cloned and running locally
- [ ] Harbor installed, TB2.0 slice chosen (5 to 10 tasks)
- [ ] Baseline score recorded
- [ ] Tracing wired and verified
- [ ] API keys and sandbox working

## On Saturday

Pick one narrow idea and measure it. Strongest candidates from the research, roughly in order of payoff per hour:

1. **Environment bootstrapping middleware.** Snapshot the working directory, file tree, toolchain, and package managers before turn one and inject it into the prompt. Meta-Harness found this saves 2 to 5 exploration turns. Small patch, easy to demo.
2. **Self-verification gate.** Force the agent to run tests or re-inspect output before it may declare done. This was LangChain's biggest single lever on Terminal-Bench.
3. **Doom-loop detector.** A hook that notices repeated identical tool calls and injects a corrective message or escalates. Easy to build, visible in traces.
4. **Computational sensor pack.** Linters, type checks, and architecture tests wired in as post-edit hooks so failures reach the agent as feedback rather than reaching the reviewer.

### Day shape

| Time | Activity |
|---|---|
| First hour | Re-run baseline, confirm traces flow, agree on the one idea |
| Hours 2 to 5 | Build the change, run the slice after each meaningful edit |
| Hour 6 | Look at traces for the tasks that still fail and harden one more thing |
| Last hour | Freeze, write the before-and-after table, prepare the demo |

### How to actually win (from the leaderboard and prior hackathons)

What separates the top harnesses from the middle is a stack of small deterministic fixes, each individually cheap. A winning day is three or four of these on top of a measured baseline, not one big idea:

1. **Environment bootstrap** (Meta-Harness): file tree, toolchain, package managers injected at turn one.
2. **Completion gate** (KIRA + LangChain): `task_complete` returns a checklist instead of ending; the agent must confirm twice.
3. **Time-aware execution** (LemonHarness): inject elapsed and remaining time each turn. Directly attacks timeout failures, which are a large share of TB2 misses.
4. **Loop detection** (LangChain): per-file edit counter with an intervention message.
5. **Output cap + marker polling** (KIRA): 30 KB cap and `__CMDEND__` markers so waits and context bloat drop.

Stretch, if the first four are measured by hour 5: a **mini evolution loop** (AHE / Meta-Harness). Run the slice, have a second agent read the failing traces and propose one harness edit, re-run. Even one iteration on stage is a strong demo because it shows the harness improving itself.

Judging signals seen in prior harness hackathons: observability and traces on screen, real sandboxed execution, a human approval gate on irreversible actions, subagents used for a reason, and a before-and-after number. Judges from Anthropic and Langfuse were on the SF panel; they read traces.

Do not: let test files, answer keys, or task-specific AGENTS.md hints into the agent's environment. Two of the top three TB2 harnesses were caught doing exactly this via trace analysis.

### Demo story

Same model, same tasks, one harness change, and a number that moved. Resist adding a second idea until the first one has a measured result.

Results table template:

| Config | Tasks | Pass rate | Avg turns | Notes |
|---|---|---|---|---|
| Baseline | | | | |
| + harness change | | | | |
