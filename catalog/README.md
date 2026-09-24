# Product-Capability Catalog

The "guide" layer from [GAME_PLAN.md](../GAME_PLAN.md)'s architecture table: maps a
non-technical founder's plain-language product description to a Floci AWS service, a
provisioning recipe, and a real verification check — without the founder ever needing to name
a cloud service themselves.

Currently AWS-only (Floci's `az`/`gcp`/`oci` emulators are separate containers not started for
this catalog — extend later if a request needs them). All 12 entries were spot-verified
against a running `floci/floci` server v2.0.1: every `verify.cli` command in
[capabilities.json](capabilities.json) was run for real against
`aws --endpoint-url=http://localhost:4566` with dummy `test`/`test` credentials and returned a
clean, empty result — not just copied from AWS docs.

## Schema (per capability entry)

| Field | Purpose |
|---|---|
| `phrases` | Example plain-language ways a founder might ask for this. Not exhaustive — the planner tool should match by meaning, not string-match this list. |
| `founder_description` | What to say back to the founder. Never mentions the AWS service name — that's the whole point of this catalog. |
| `aws_service` / `floci_services_flag` | The real service name, for the executor tool only. Never surfaced to the founder. |
| `depends_on` | Other capability ids this one needs already provisioned (e.g. `background-job` needs `file-storage` for its S3 trigger). The planner must resolve these before provisioning, and the state file must already have them recorded. |
| `provision.steps` | What the executor actually runs, in order. |
| `provision.state_fields` | What gets written into `stack-state.json` for this capability so a later incremental request can find and reuse it. |
| `verify` | The real check the verification gate runs before claiming "done." This is the trust mechanism — never skip it, never accept the executor's own exit code as sufficient proof. |
| `wiring.env_vars` | What gets auto-written into the founder's app config. Names only — values come from `provision` output at runtime. |
| `cloud_equivalent_note` | One-liner for the stretch-goal "what would it take to go live?" answer — confirms the plan artifact stays retargetable to real AWS. |

## The fallback rule (non-negotiable for this project)

If a request doesn't clearly match a capability's `phrases`/meaning:

1. **Never** invent a floci-cli invocation outside this catalog.
2. Pick the closest existing capability and offer it, in plain language, as a question —
   e.g. "I can give you a place to store and look up messages, but not live chat yet — want
   that instead?"
3. If nothing here is close, say so plainly and stop. Log the request text somewhere durable
   (not silently dropped) so it becomes the next entry added to this catalog.

See `explicitly_not_covered` in [capabilities.json](capabilities.json) for known gaps —
these are exactly what request #5 in GAME_PLAN.md's task set is designed to trigger.

## Coverage vs. the GAME_PLAN.md task set

| Task set request | Capabilities exercised |
|---|---|
| 1. "sign up and log in" | `user-accounts` |
| 2. "upload a profile photo" | `file-storage` |
| 3. "resize photo + email confirmation" | `file-storage` → `background-job` → `send-email` |
| 4. "upload more than one photo" (follow-up on #2) | `file-storage` (incremental, reads existing state) |
| 5. "real-time chat" | intentionally **not covered** — exercises the fallback rule |
| 6. failure case | any capability, provisioned against a deliberately conflicting state |

## Known gaps to fill

- No entry yet for a plain "just give me a working backend with a database and an API" request
  that spans `structured-data` + `backend-api` in one ask — likely how a real founder would
  actually phrase request #3's shape. Consider adding a composite/starter-stack entry if the
  planner tool doesn't handle multi-capability matching well enough on its own.
- `search` and `app-settings` aren't exercised by any task-set request — kept in for catalog
  breadth, but untested end-to-end.
