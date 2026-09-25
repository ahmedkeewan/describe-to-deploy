---
id: AgDR-0002
timestamp: 2026-09-12T00:00:00Z
agent: Hisham (Tech Lead)
model: claude-sonnet-5
trigger: design-review-finding
status: executed
---

# Concurrency control: flock-based file locking over stack-state.json and events.jsonl

> In the context of multiple agent processes now writing to `stack-state.json` and
> `events.jsonl` concurrently, facing an existing read-modify-write pattern with no cross-process
> locking, I decided to wrap both files' read-modify-write cycles in a POSIX `flock`-based
> locking helper, to close the race with the smallest possible change, accepting that this
> approach does not scale past a handful of concurrent environments.

## Context

- `harness/mcp_server.py`'s `_load_state()` / `_save_state()` do a plain
  read-then-write of `stack-state.json`, with no lock. Each MCP client (each agent) runs its own
  `mcp_server.py` subprocess over stdio, so two agents calling `record_provisioned` at once can
  already silently clobber each other's state today, independent of the environments feature.
- `harness/events.py`'s `_next_seq()` has the identical shape: it reads the whole file and
  computes `last + 1`. Its `threading.Lock` only serializes writes within one process. It does
  nothing across the multiple processes this harness actually runs.
- The repo's own documented platform support is macOS and Linux directly, Windows via WSL —
  all POSIX, so `fcntl.flock` is available everywhere this harness is documented to run.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| `fcntl.flock`-based locking helper around both files' read-modify-write cycles (chosen) | Minimal diff. No new dependency. Fixes both files with one mechanism. Matches the harness's small-script style. | Serializes all state writes across every concurrent agent. A slow verify call (up to a 30s timeout) held inside the lock would block every other agent's writes; the design keeps verification outside the locked section to avoid this. |
| Migrate `stack-state.json` and `events.jsonl` to SQLite (WAL mode) | Real concurrent-write support at scale. Removes the read-whole-file-every-time pattern in `_next_seq()`. | Bigger diff. New dependency and query surface for a harness that is otherwise plain JSON files read by a browser (`interface/live.html` reads `events.jsonl` directly). No demonstrated need yet — the harness is a single-user local tool, not a production multi-tenant service. |
| Leave both files unlocked; document the race as a known limitation | Zero engineering cost | Directly breaks the feature's own goal. Concurrent agents are the whole point of this design, and the race is exactly the kind of state corruption the feature exists to prevent. |

## Decision

Chosen: **`fcntl.flock`-based locking**, because it is the smallest change that actually closes
the race for both files, requires no new dependency, and fits this harness's plain-file
architecture. The SQLite alternative is rejected for now for lack of a demonstrated need at this
scale — this is the same "no dependency without demonstrated need" discipline the technical
design already applied elsewhere (declining a per-environment backend, declining a Belt-style
generator layer).

## Consequences

- Target state, once every ticket in the epic lands: every state write across
  `stack-state.json` and `environments.json` goes through one locked read-modify-write helper,
  and `events.jsonl`'s `emit()` and `_next_seq()` use the same helper.
- Current state as of GH-24 (this decision's first landing): the shared helper
  (`harness/state_lock.py`) exists and is applied to `stack-state.json` only. `environments.json`
  does not exist yet (pending GH-25). `events.py`'s `_next_seq()` still uses only its
  in-process `threading.Lock`, unchanged, and remains exposed to the cross-process race described
  in Context until GH-31 lands. Do not read this record as saying that race is already closed.
- Verification (`_run_verify`, up to a 30s subprocess timeout) stays outside the locked section,
  matching today's ordering in `record_provisioned` where verification runs before the state
  write. This is a stated constraint on the helper, not an incidental property.
- If environment count grows past a handful, or write contention becomes noticeable, this
  decision should be revisited — flagged as an open question in the technical design, not a
  silent limitation.

## Artifacts

- Implemented in: `harness/state_lock.py`, used by `harness/events.py`,
  `harness/environments_store.py`, and `harness/snapshots_store.py`
- Raised by: a design review of the isolated-per-agent-environments work, which required this
  decision be recorded before implementation started
