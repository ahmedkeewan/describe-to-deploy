---
id: AgDR-0004
timestamp: 2026-09-25T00:00:00Z
agent: Claude (build agent)
model: claude-sonnet-5
trigger: ticket-GH-69
status: executed
---

# Multi-founder / team mode: ownership metadata now, permission enforcement deferred

> In the context of [#69](https://github.com/ahmedkeewan/service-buddy/issues/69)'s request for a permissions layer so multiple founders can share one
> product, facing a harness with no authentication or identity system anywhere in its existing
> design, I decided to add an optional, purely informational `owner` field to environments
> rather than build real access control, to give visibility into who provisioned what without
> pretending to be a security boundary the harness cannot actually enforce, accepting that this
> does not solve the "founder A can't touch founder B's environment" problem [#69](https://github.com/ahmedkeewan/service-buddy/issues/69) originally
> asked for.

## Context

- This harness has no authentication anywhere. Whoever's AI chat client is connected to the MCP
  server can call any tool, including `create_environment`, `destroy_environment`, and every
  provisioning tool, for any `app_context` it knows or can guess. There is no login, no API key,
  no session concept for a human "founder" using the product today.
- `app_context` isolates *environments* from each other (AgDR-0001's shared-backend model,
  enforced by resource ownership) — it was never designed as, and does not function
  as, a *permission* boundary between people. Knowing an `app_context` string is sufficient to
  act on it; nothing checks who is asking.
- Building a real multi-founder permission model would mean adding the harness's first identity
  and authorization system: who is "logged in" as which founder, how that identity is
  established for an MCP tool call (MCP itself has no user-session concept this harness already
  uses), and how every existing tool would need to check it. That is a materially larger,
  cross-cutting change to a harness whose entire architecture assumes one trusted operator per
  MCP client connection.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Ownership metadata only, no enforcement (chosen) | Answers "who provisioned this" for a human reading `list_environments()`/`describe_environment()`; nearly free to add; doesn't claim a security property the harness can't back up. | Does not stop one founder from acting on another's environment — no actual permission check exists. |
| Real permission enforcement (an identity concept + per-tool authorization checks) | Would genuinely solve the multi-founder isolation problem [#69](https://github.com/ahmedkeewan/service-buddy/issues/69) describes. | Requires inventing an identity/session system MCP and this harness have no precedent for; touches every tool that takes an `app_context`; no demonstrated need yet (no multi-founder usage has actually been requested by a real user of this harness, per [#69](https://github.com/ahmedkeewan/service-buddy/issues/69)'s own framing as a forward-looking feature idea, not a reported problem). |
| Do nothing | Zero cost. | `list_environments()` already shows every environment to anyone connected — leaving no ownership trail at all is a worse starting point than a free metadata field, once more than one person plausibly shares a Floci instance. |

## Decision

Chosen: **add an optional `owner` string to `create_environment()`, stored in
`environments.json` and surfaced by `list_environments()`/`describe_environment()`, with no
enforcement of any kind.** This is deliberately NOT a security control. It is bookkeeping: a
human reading the environment list can see who created what, the same way a git commit records
an author without that being an access-control mechanism.

Real permission enforcement is deferred, matching AgDR-0001's own precedent for declining
over-scoped work with no demonstrated need (there, a per-environment backend; here, an identity
and authorization system). If actual multi-founder usage surfaces a real conflict (two people
provisioning against the same environment unknowingly, or a need to restrict who can destroy an
environment), that is the point to revisit this decision with a concrete requirement in hand,
not before.

## Consequences

- `owner` is optional and purely descriptive. Any connected MCP client can still act on any
  `app_context` it knows, regardless of the recorded `owner` value — this must not be
  represented to a founder or documented anywhere as an access-control feature.
- [#69](https://github.com/ahmedkeewan/service-buddy/issues/69)'s original acceptance criteria ("provisioning/verification respects who is allowed to
  act on which environment") is explicitly NOT met by this change. This AgDR is itself the
  ticket's required "decision recorded" deliverable; the "if implemented" half of the ticket's
  AC is answered "not implemented, by this decision."
- A future real permission system, if ever built, would need to introduce the identity concept
  this AgDR declines to build now, and would likely want to reuse the `owner` field this change
  adds as its starting data model.

## Artifacts

- Issue: [#69](https://github.com/ahmedkeewan/service-buddy/issues/69)
- Prior art this decision follows: AgDR-0001 (declining over-scoped work with no demonstrated
  need)
