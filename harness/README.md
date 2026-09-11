# Harness

The actual harness code, built incrementally per [GAME_PLAN.md](../GAME_PLAN.md)'s build order.
Every fix here was measured against the fixed task set in [tasks/](../tasks) — see
[tasks/README.md](../tasks/README.md) for the full results and honest negative findings, not just
the wins.

## Files

| File | Fix | What it does |
|---|---|---|
| `build_prompt.py` | 1, 2 | Generates harness system prompts from `catalog/capabilities.json` — fix 1's single-agent prompt, fix 2's planner/executor role prompts. Never hand-edit the catalog content into a prompt; regenerate instead. |
| `verify_gate.py` | 4 | Computational verification gate. Zero LLM calls — reads a `stack-plan.json`, re-runs each capability's real `verify.cli` against live Floci, exits 0 only on a genuine pass. |
| `auto_wire.py` | 7 | Writes real config values into a founder's app `.env`, idempotently, only for capabilities safely derivable from the plan (never guessed). |
| `go_live_plan.py` | stretch | Reads a plan and names the real AWS equivalent per capability, using the catalog's existing `cloud_equivalent_note` — no migration performed. |
| `stack-plan.schema.json` | 2 | Schema for the intermediate plan artifact a planner produces and an executor consumes. |
| `stack-state.schema.json` / `stack-state.json` | 5 | Schema and live data for the durable, `app_context`-keyed record of what's been provisioned. |
| `mcp_server.py` | delivery | The whole harness exposed as MCP tools — see below. |

## Delivery surface: MCP server, not a bespoke frontend

Decision (2026-09-05): expose this harness as an MCP server rather than building a chat UI from
scratch. Whatever AI chat client is already driving the conversation (Claude Desktop, Claude
Code, Cursor) becomes the founder-facing interface for free.

**Architecture** mirrors fix #2's planner/executor split, now as an explicit tool contract:
- The **calling agent** (the LLM behind whatever MCP client is connected) is the planner +
  executor: it reads `list_capabilities()`, matches the founder's plain-language request to a
  capability, calls `get_provisioning_recipe()` to learn what to run, and executes those steps
  with its own tool access.
- **This server** is the gate + state: `record_provisioned()` independently re-verifies — the
  exact same check as `verify_gate.py` — before it will ever touch `stack-state.json`. State can
  only advance on a real, server-checked PASS, never on the calling agent's own claim. This makes
  fix #4's gate a structural boundary instead of a step an agent could forget to run.

**Jargon boundary**: every tool's return value is built to be founder-safe plain language, except
`whats_needed_to_go_live()`, which is explicitly the one technical/graduation report in the whole
harness and is documented as such in its own docstring.

### Running it

Prefer `./setup.sh` from the repo root — it does everything below in one pass (Docker/Colima
check-or-install via Homebrew, Floci install/start with confirmation, venv + deps, and wiring the
MCP server into Claude Desktop, Claude Code, and Cursor), and is safe to re-run. The steps below
are what it automates, useful if you want to do them by hand or understand what changed on your
machine. Pass `--start-board` to also launch the live board (in the foreground — Ctrl+C to stop)
once setup finishes; without the flag, setup only prints the command. `make setup` and `make test`
are thin aliases for `./setup.sh` and the test suite — run `make help` to see them.

`make board` runs `./setup.sh --start-board`. That flag ships in this same base branch as of the
merge of #9/#16, so `make board` works as documented.

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

`list_capabilities`, `get_app_state`, `get_provisioning_recipe`, `record_provisioned`,
`report_unsupported_request`, `check_app_readiness`, `wire_app_config`, `whats_needed_to_go_live`.
Every one was tested directly (Python function calls) and over the real MCP protocol (stdio,
`ClientSession`) against live Floci state, not just imported and assumed to work — see the
session log for the verification transcript, including a deliberate test that `record_provisioned`
correctly rejects a claim made before the underlying resource actually exists, and only updates
state after it's created for real.
