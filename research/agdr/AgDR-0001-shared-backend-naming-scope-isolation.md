---
id: AgDR-0001
timestamp: 2026-09-12T00:00:00Z
agent: Hisham (Tech Lead)
model: claude-sonnet-5
trigger: design-review-finding
status: executed
---

# Isolation model: naming-scope on a shared Floci backend

> In the context of adding isolated per-agent environments to the Floci MCP harness, facing a
> hardcoded single Floci endpoint with no per-instance provisioning support, I decided to isolate
> environments by namespacing `app_context` and `resource_name` on one shared backend, to achieve
> concurrent-agent safety without new infrastructure, accepting that backend resources are never
> truly separated and can only be kept apart by naming discipline.

## Context

- `harness/mcp_server.py` and `harness/verify_gate.py` both hardcode
  `AWS_ENDPOINT_URL=http://localhost:4566`. Every capability, for every app, is provisioned and
  verified against this one LocalStack/Floci instance.
- `capabilities.json` defines `provision` and `verify` steps per capability. It defines no
  mechanism to stand up a second, independent backend instance.
- The PRD's own Open Question 1 asked whether Floci supports true per-environment isolation, or
  only naming-level namespacing. Reading the code answers this directly: naming-level only.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Naming-scope isolation on one shared backend (chosen) | No new infrastructure. Matches how `app_context` already works today. Small, reviewable diff. | Resources are never truly separated. A destroyed environment's resources persist forever on the shared backend as inert capacity. |
| Per-environment LocalStack/Floci container or process | Genuine resource isolation. A destroyed environment leaves nothing behind. | Requires container/process orchestration this harness does not have today. Directly re-introduces the Tilt/Terraform/Docker Compose scope this idea's own validation explicitly rejected as over-scoped (see IDEA-001 validation, Q3). |
| Do nothing; require agents to coordinate resource names by convention | Zero engineering cost | This is today's status quo, and it is exactly the collision this feature exists to remove |

## Decision

Chosen: **naming-scope isolation on one shared Floci backend**, because it matches the harness's
existing architecture, requires no new infrastructure, and was already the direction the
technical design converged on once the hardcoded endpoint was read in the actual code. The
resource-name-to-environment binding (see the technical design's Data Flow step 6) is the
control that makes this safe despite resources never being physically separated.

## Consequences

- No new orchestration layer, container runtime, or Terraform/Tilt dependency is introduced.
- A destroyed environment's backend resources are permanent, unreachable capacity on the shared
  backend. This is accepted, not fixed, because `capabilities.json` defines no teardown step for
  any capability — building one is a separate, larger piece of work with no demonstrated need
  yet.
- Every future MCP tool that touches `resource_name` must respect the environment-prefix binding
  this decision implies, or isolation silently breaks.

## Artifacts

- Technical design: `projects/harness-engineering-research/technical-designs/isolated-per-agent-environments.md` (ops-fork/portfolio repo)
- PRD: `projects/harness-engineering-research/prds/isolated-per-agent-environments.md`
- Design review (Tariq, doc-only, CHANGES REQUESTED — finding B1 required this record)
