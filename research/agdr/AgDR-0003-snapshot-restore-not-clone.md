---
id: AgDR-0003
timestamp: 2026-09-25T00:00:00Z
agent: Claude (build agent)
model: claude-sonnet-5
trigger: ticket-GH-67
status: executed
---

# Environment lifecycle: snapshot/restore of recorded state, not clone of resources

> In the context of adding an environment-lifecycle feature beyond create/destroy ([#67](https://github.com/ahmedkeewan/service-buddy/issues/67)), facing
> AgDR-0001's naming-scope isolation on one shared Floci backend, I decided to implement
> snapshot/restore of an environment's recorded stack-state.json entries rather than a true
> `clone_environment` that duplicates provisioned resources under a new `app_context`, to give
> agents an undo-style safety net without violating the resource-name-to-environment binding,
> accepting that a restored capability is only re-admitted to state after a fresh live
> re-verification, not blindly copied.

## Context

- [#67](https://github.com/ahmedkeewan/service-buddy/issues/67)'s original framing asked for a `clone_environment(name, new_name)` tool "to fork an
  existing environment's provisioned state for a new agent," or a snapshot/restore pair.
- AgDR-0001 already established that Floci is one shared backend with no per-environment
  isolation; environments are kept apart only by naming discipline — `app_context` prefixes on
  `resource_name`, enforced by the exact `::`-delimited binding check in
  `_resource_name_binding_error()`.
- A literal clone (copy every `stack-state.json` entry from `app_context` A to a new
  `app_context` B) would produce state entries whose `resource_name` values are still prefixed
  with A, not B. Any later call through B would fail the binding check [#29](https://github.com/ahmedkeewan/service-buddy/issues/29) built specifically
  to prevent one environment from claiming another's resources — the clone would either be
  rejected outright, or (if the binding check were loosened to allow it) would let two
  environments believe they own the same real bucket/table/etc., which is the exact
  false-provenance failure AgDR-0001's binding control exists to close.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Snapshot/restore of recorded state, re-verified on restore (chosen) | Never violates the resource-name binding — restore only ever writes state under the *same* `app_context` it was snapshotted from. Re-verification on restore keeps the harness's core "never trust an unchecked claim" guarantee intact even when reintroducing older state. | Not a true fork — doesn't help two *different* agents share a starting point, only lets one environment roll its own recorded state back to an earlier point. |
| True clone_environment(name, new_name), copying resource_name as-is | Matches the literal ticket wording; gives a new environment head-start state. | Breaks the resource-name-to-environment binding ([#29](https://github.com/ahmedkeewan/service-buddy/issues/29)) the moment the clone's `app_context` differs from the original's. Either the binding check has to be weakened (reopening the false-PASS vulnerability that check was built to close), or the clone's copied entries are permanently unusable through any tool that enforces the binding. |
| True clone_environment that also re-provisions real resources under the new app_context | Gives a genuinely independent working copy with valid bindings. | This is not a clone, it's a full re-provision — the same cost as building from scratch, defeating the "quick fork" motivation. No demonstrated need for this heavier feature yet. |

## Decision

Chosen: **snapshot/restore of recorded state, scoped to a single environment's own
`app_context`, with restore forcing a fresh live re-verification per capability before it's
written back to `stack-state.json`.** This is the only option that doesn't require touching or
weakening the resource-name binding, and it keeps the "state can only advance on a genuine,
freshly-checked PASS" contract (`record_provisioned()`'s existing guarantee) true for restored
state as well as newly-provisioned state.

## Consequences

- `snapshot_environment(name)` and `restore_environment(name, snapshot_id)` operate on one
  environment's own recorded state — they are not a mechanism for seeding a *second*,
  independent environment with a head start. A future ticket could revisit true multi-agent
  forking, but it would need to solve the resource-name-binding problem above first (most likely
  via the heavier "clone that re-provisions" option this AgDR rejected as premature).
- A capability present in a snapshot but no longer verifying live (the real resource was deleted,
  or Floci was reset) is silently excluded from what `restore_environment` writes back, with the
  skip reported in the response — restore never resurrects a false claim.
- Snapshots are stored durably (`harness/environment-snapshots.json`, locked the same way as
  `stack-state.json` and `environments.json`) so they survive process restarts, matching this
  harness's existing durability pattern for `app_context`-scoped state.

## Artifacts

- Issue: [#67](https://github.com/ahmedkeewan/service-buddy/issues/67)
- Prior art this decision extends: AgDR-0001 (shared-backend naming-scope isolation), AgDR-0002
  (flock-based state locking)
