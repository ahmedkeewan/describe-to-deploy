# Harness

The Floci control-plane harness code. This section explains the architecture (the "why"); see
[tasks/README.md](../tasks/README.md) for the benchmark results the design decisions below were
measured against, including the honest negative findings, not just the wins.

## Files

| File | What it does |
|---|---|
| `build_prompt.py` | Generates harness system prompts from `catalog/capabilities.json`. `--mode single-agent` produces one prompt for a single planning-and-acting agent; `--mode planner-executor --role planner\|executor` produces the split-role prompt pair the harness actually runs on (see "Architecture" below). Never hand-edit the catalog content into a prompt; regenerate instead. |
| `state_lock.py` | Shared `fcntl.flock`-based cross-process locking helper. Every MCP client (each agent) runs its own `mcp_server.py` subprocess, so the plain-file state below needs a real OS-level lock, not just an in-process one — see AgDR-0002. |
| `environments_store.py` | Load/save helpers and the shared lock for `environments.json`, the sidecar file backing `create_environment`/`destroy_environment`/`list_environments` (see "Tools exposed" below). |
| `verify_gate.py` | Computational verification gate. Zero LLM calls — reads a `stack-plan.json`, re-runs each capability's real `verify.cli` against live Floci, exits 0 only on a genuine pass. |
| `auto_wire.py` | Writes real config values into a founder's app `.env`, idempotently, only for capabilities safely derivable from the plan (never guessed). |
| `go_live_plan.py` | Reads a plan and names the real AWS equivalent per capability, using the catalog's existing `cloud_equivalent_note` — no migration performed. |
| `stack-plan.schema.json` | Schema for the intermediate plan artifact a planner produces and an executor consumes. |
| `stack-state.schema.json` / `stack-state.json` | Schema and live data for the durable, `app_context`-keyed record of what's been provisioned. |
| `events.py` | Two-channel (founder/dev) event log the live board tails, `seq`-numbered and locked the same way as `stack-state.json`. |
| `mcp_server.py` | The whole harness exposed as MCP tools — see below. |

## Architecture

**Delivery surface: MCP server, not a bespoke frontend.** This harness is exposed as an MCP
server rather than a purpose-built chat UI. Whatever AI chat client is already driving the
conversation (Claude Desktop, Claude Code, Cursor) becomes the founder-facing interface for free.

**Planner/executor split, as an explicit tool contract:**
- The **calling agent** (the LLM behind whatever MCP client is connected) is the planner +
  executor: it reads `list_capabilities()`, matches the founder's plain-language request to a
  capability, calls `get_provisioning_recipe()` to learn what to run, and executes those steps
  with its own tool access.
- **This server** is the gate + state: `record_provisioned()` independently re-verifies — the
  exact same check as `verify_gate.py` — before it will ever touch `stack-state.json`. State can
  only advance on a real, server-checked PASS, never on the calling agent's own claim. This makes
  the verification gate a structural boundary instead of a step an agent could forget to run.

**Isolation model: naming-scope on one shared Floci backend, not per-environment instances.**
`create_environment`/`destroy_environment`/`list_environments` let two or more agents in
separate worktrees each provision their own infra without colliding, but they do this by
namespacing `app_context` and `resource_name` — Floci itself has no per-environment isolated
backend at this harness's level. See AgDR-0001 for the full trade-off (a per-environment backend
was considered and rejected as over-scoped for a local dev harness).

**Jargon boundary**: every tool's return value is built to be founder-safe plain language, except
five tools documented as such in their own docstrings and named in `mcp_server.py`'s module
docstring: `whats_needed_to_go_live()` (the one technical/graduation report), and
`get_provisioning_recipe()`/`create_environment()`/`destroy_environment()`/`list_environments()`
(developer/agent-facing infra detail — endpoints, credentials, app_context, board ports — never
for the founder).

### Running it

Prefer `./setup.sh` from the repo root — it does everything below in one pass (Docker/Colima
check-or-install via Homebrew, Floci install/start with confirmation, venv + deps, and wiring the
MCP server into Claude Desktop, Claude Code, and Cursor), and is safe to re-run. The steps below
are what it automates, useful if you want to do them by hand or understand what changed on your
machine. Pass `--start-board` to also launch the live board (in the foreground — Ctrl+C to stop)
once setup finishes; without the flag, setup only prints the command. `make setup` and `make test`
are thin aliases for `./setup.sh` and the test suite — run `make help` to see them.

`make down` stops Floci (`floci stop`) — a non-destructive stop that leaves the container and its
state intact, so a later `floci start` (or `make setup`) picks back up where it left off. If Floci
isn't installed or isn't currently running, `make down` prints a clear message instead of failing
noisily. This is not the benchmark-reset command — see
[tasks/README.md](../tasks/README.md) for `floci stop && docker rm -f floci`, which destroys the
container and is a separate, deliberate reset step, not a default teardown.

`make board` runs `./setup.sh --start-board`. Set `FLOCI_BOARD_PORT` to run more than one board
side by side — for example, one per environment from `create_environment` below — instead of
always binding to the default `7777`:

```bash
FLOCI_BOARD_PORT=7801 make board
```

**Platforms**: macOS and Linux are supported directly. Windows is supported via **WSL** (run
`./setup.sh` inside your WSL distro — it correctly wires Claude Desktop's config on the Windows
side, even though the script itself runs in Linux). Native Windows without WSL isn't scripted
here — install Floci with its own PowerShell installer (`irm https://floci.io/install.ps1 | iex`)
and wire the MCP server manually using the steps below.

```bash
python3 -m venv harness/.venv
source harness/.venv/bin/activate
pip install -r harness/requirements.txt
python3 harness/mcp_server.py   # runs over stdio
```

### Running the tests

`verify_gate.py` and `auto_wire.py` have unit tests covering their pure logic (no live Floci
required — `run_check`'s actual subprocess call is exercised live instead via a real scoring pass,
see [tasks/README.md](../tasks/README.md)):

```bash
python3 -m unittest discover -s harness/tests
```

### Connecting to Claude Desktop

Add to Claude Desktop's MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "floci-control-plane": {
      "command": "/absolute/path/to/harness/.venv/bin/python3",
      "args": ["/absolute/path/to/harness/mcp_server.py"]
    }
  }
}
```

Floci itself must already be running (`floci start`) — this server drives it, it doesn't launch
it.

### Connecting to Cursor

Same `mcpServers` shape as Claude Desktop, at `.cursor/mcp.json` in the repo root (project-scoped)
or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "floci-control-plane": {
      "command": "/absolute/path/to/harness/.venv/bin/python3",
      "args": ["/absolute/path/to/harness/mcp_server.py"]
    }
  }
}
```

### Tools exposed

**Founder-facing product tools**: `list_capabilities`, `get_app_state`, `get_provisioning_recipe`,
`record_provisioned`, `report_unsupported_request`, `check_app_readiness`, `wire_app_config`,
`whats_needed_to_go_live`.

`record_provisioned` accepts an optional `dry_run=True` flag: it returns the exact verify
command and success criteria a real call would use, without executing anything against live
Floci or touching `stack-state.json` — a way to double-check the invocation right before firing
it for real. A dry run can never itself produce `PASS`/`FAIL`; its `gate_result` is `NOT_RUN`.

**Environment-management tools** (for the developer running multiple agents in parallel
worktrees, not the founder):

| Tool | Purpose |
|------|---------|
| `create_environment(name)` | Mints a unique, permanently non-reused `app_context` and a free board port for one agent/worktree. Returns `{app_context, board_port}`. |
| `destroy_environment(name)` | Releases the board port and removes the environment's entries. Does not delete real backend resources — `capabilities.json` defines no teardown step for any capability (see AgDR-0001). |
| `list_environments()` | Lists every currently registered environment: name, `app_context`, board port, creation time. |

Calling `get_provisioning_recipe`/`record_provisioned` with an `app_context` from
`create_environment` enforces an extra check: `resource_name` must have the exact form
`{app_context}::{suffix}` — a `::`-delimited exact match, not a plain prefix — or the call is
rejected before any provisioning or verify command runs. Exact match matters because environment
names are free-form, so a naive prefix check can be spoofed by naming one environment after
another's full `app_context`; the `::` split closes that. This is what stops one environment from
recording a false PASS using another environment's resource.
Calling these tools the way they've always worked — with any other `app_context` string — is
unaffected.

Every tool was tested directly (Python function calls) and over the real MCP protocol (stdio,
`ClientSession`) against live Floci state, not just imported and assumed to work — see the
session log for the verification transcript, including a deliberate test that `record_provisioned`
correctly rejects a claim made before the underlying resource actually exists, and only updates
state after it's created for real.
