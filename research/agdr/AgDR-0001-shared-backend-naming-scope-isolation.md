---
id: AgDR-0001
timestamp: 2026-09-12T00:00:00Z
agent: Claude (build agent)
model: claude-sonnet-5
trigger: design-review-finding
status: executed (amended 2026-09-25)
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
  verified against this one Floci instance.
- `capabilities.json` defines `provision` and `verify` steps per capability. It defines no
  mechanism to stand up a second, independent backend instance.
- An open question going in was whether Floci supports true per-environment isolation, or only
  naming-level namespacing. Reading the code answers this directly: naming-level only.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Naming-scope isolation on one shared backend (chosen) | No new infrastructure. Matches how `app_context` already works today. Small, reviewable diff. | Resources are never truly separated. A destroyed environment's resources persist forever on the shared backend as inert capacity. |
| Per-environment Floci container or process | Genuine resource isolation. A destroyed environment leaves nothing behind. | Requires container/process orchestration this harness does not have today. Directly re-introduces the Tilt/Terraform/Docker Compose orchestration scope that was ruled out early as too heavy for a local, single-user tool. |
| Do nothing; require agents to coordinate resource names by convention | Zero engineering cost | This is today's status quo, and it is exactly the collision this feature exists to remove |

## Decision

Chosen: **naming-scope isolation on one shared Floci backend**, because it matches the harness's
existing architecture, requires no new infrastructure, and was already the direction the design
converged on once the hardcoded endpoint was read in the actual code. The control that makes this
safe despite resources never being physically separated was originally a naming rule; it is now
resource ownership — see the amendment below.

## Consequences

- No new orchestration layer, container runtime, or Terraform/Tilt dependency is introduced.
- A destroyed environment's backend resources are permanent, unreachable capacity on the shared
  backend. This is accepted, not fixed, because `capabilities.json` defines no teardown step for
  any capability — building one is a separate, larger piece of work with no demonstrated need
  yet.
- Every future MCP tool that records or restores a `resource_name` must go through the ownership
  check (`_ownership_error()`), or isolation silently breaks.

## Artifacts

- Implemented in: `harness/mcp_server.py` (`_ownership_error`), `harness/environments_store.py`
- Tests: `harness/tests/test_resource_ownership.py`
- Raised by: a design review of the isolated-per-agent-environments work, which required this
  decision be recorded before implementation started

## Amendment (2026-09-25): ownership record replaces the naming rule

The original control required every `resource_name` in a registered environment to be
`<app_context>::<name>`, with the part before `::` exactly equal to the environment's
`app_context`. No real resource could satisfy it ([#85](https://github.com/ahmedkeewan/service-buddy/issues/85)):

- `:` is illegal in S3, DynamoDB, Lambda, Secrets Manager, and Scheduler names, and the generated
  `app_context` (name, nanosecond timestamp, random suffix) was already longer than the 28
  characters a search domain name allows. So none of the six capabilities whose resources the
  agent names could be created inside an environment.
- The other five are verified against an ID AWS assigns (a Cognito pool ID, an API Gateway ID, a
  queue URL, an SNS or Step Functions ARN), which can't carry any prefix at all.

The tests never caught it because they replace the live verify step with a mock, so no name ever
reached real AWS validation. It surfaced when Claude Desktop called `create_environment` on its
own for a first "let people upload a photo" request and couldn't name the bucket.

**Now:** a resource (AWS service + the name or ID its verify check uses) belongs to the first
`app_context` that records it, read from `stack-state.json` itself so ownership can't drift from
what's recorded. Any other `app_context` is rejected by `get_provisioning_recipe` (early, before
steps are returned), `record_provisioned` (again under the state lock, so a race can't produce two
owners), and `restore_environment`. `app_context` is now `<name>-<6 hex>`, unique against every
environment, recorded app, and snapshot.

This keeps the property the naming rule was for — one environment can't record a PASS on, or
silently share, another's resource — without constraining names. It no longer enforces a naming
convention, so two environments that pick the same new name are told so when the second one tries
to use it rather than being prevented up front; the tool descriptions tell agents to name resources
after the environment to avoid that.
