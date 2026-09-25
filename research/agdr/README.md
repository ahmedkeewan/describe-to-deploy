# Agent decision records (AgDRs)

Short write-ups of design decisions made while building Service Buddy's harness. Each one
records the context, the options considered, what was chosen, and what it costs. They're
written so the reasoning survives after the code changes around it.

| Record | Decision |
|---|---|
| [AgDR-0001](AgDR-0001-shared-backend-naming-scope-isolation.md) | Isolate agent environments by naming scope on one shared Floci backend, not per-environment infrastructure |
| [AgDR-0002](AgDR-0002-flock-based-state-locking.md) | Use `fcntl.flock`-based locking for cross-process state writes, since every MCP client spawns its own server process |
| [AgDR-0003](AgDR-0003-snapshot-restore-not-clone.md) | Offer snapshot/restore of an environment's recorded state, re-verified on restore, instead of cloning resources |
| [AgDR-0004](AgDR-0004-multi-founder-metadata-not-enforcement.md) | Record an optional environment `owner` as metadata only; defer real permission enforcement |
