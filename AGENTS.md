# AGENTS.md

This file is for an AI coding agent (Claude Code, Cursor, or any MCP-capable client) that wants
to connect to and call Service Buddy's MCP server. It is not a build/test/contribution guide; see
[CONTRIBUTING.md](CONTRIBUTING.md) for that.

## What this server does

`harness/mcp_server.py` is an MCP server that turns a plain-language product request into real,
verified local infrastructure on [Floci](https://floci.io/), a free AWS emulator that runs in
Docker on the user's machine. You are the planner and executor: read the tool list below, match
the founder's request to a capability, get the real steps from `get_provisioning_recipe`, run them
with your own shell access, then call `record_provisioned`, which independently re-verifies before
it ever updates state. Your own belief that something worked is never sufficient.

The server does not run provisioning commands itself, so your client needs a way to run shell
commands (Claude Code and Cursor have one). Those commands, and every verification check, use the
AWS CLI against Floci on `http://localhost:4566`.

## Connecting

Floci must be running (`floci start`) and the server's dependencies installed. Run `./setup.sh`
from the repo root once if you haven't; it writes the client configs below for you. The server
registers as `floci-control-plane`.

**Claude Code.** `./setup.sh` writes a project-scoped `.mcp.json` at the repo root, so the server
is available when `claude` is started from the repo folder (Claude Code asks you to approve it on
first launch). To make it available from any folder:

```bash
claude mcp add --scope user floci-control-plane -- \
  /absolute/path/to/harness/.venv/bin/python3 /absolute/path/to/harness/mcp_server.py
```

**Cursor and Claude Desktop.** Both use the same JSON shape:

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

| Client | Config file |
|---|---|
| Claude Code | `.mcp.json` at the repo root (project scope), or `claude mcp add --scope user` |
| Cursor | `.cursor/mcp.json` in the project, or `~/.cursor/mcp.json` for every project |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |

Restart the client after changing its config. See [`harness/README.md`](harness/README.md) for
more on running the server.

## Tool list

The **Founder-safe?** column tells you whether a tool's return value can be relayed to the
founder. "No" means never relay it. "Yes, except …" means the named field is for you only.

**Product tools.** Call these to drive the founder's request:

| Tool | Purpose | Founder-safe? |
|------|---------|---------------|
| `list_capabilities()` | List every product capability this server can build, in plain language. | Yes |
| `get_app_state(app_context)` | Look up what has already been built and verified for an app. `app_context` is the stable identifier for the founder's app (the value from `create_environment`, or any consistent slug you choose for the app). | Yes |
| `get_provisioning_recipe(capability_id, resource_name, app_context=None)` | Get the exact technical steps and verification command to build a capability. | **No**: infra detail for your own use |
| `record_provisioned(app_context, capability_id, resource_name, dry_run=False)` | Call after you've actually run the provisioning steps. Re-verifies live before updating state. `dry_run=True` previews the exact check it would run, without running it or recording anything. | Yes, except `_diagnostic_for_you_the_calling_agent` (present on FAIL and on `dry_run=True`) |
| `report_unsupported_request(app_context, request_text, closest_capability_id=None)` | Call this instead of inventing anything when a request doesn't match `list_capabilities()`. | Yes |
| `check_app_readiness(app_context)` | Re-verify, live, everything on record for this app. Don't trust cached timestamps. | Yes |
| `wire_app_config(app_context, app_directory)` | Write real connection details into the founder's app config file. | Yes, except `_diagnostic_for_you_the_calling_agent` (present on failure) |
| `whats_needed_to_go_live(app_context)` | Technical report naming the real cloud service behind each verified capability and what changes in production. For an engineer or investor, only when explicitly asked. | **No** |

**Environment tools.** For you, the agent, managing isolated environments (for example one per git
worktree). None of these are founder-facing:

| Tool | Purpose | Founder-safe? |
|------|---------|---------------|
| `create_environment(name, owner=None)` | Mint a new, isolated environment so your agent or worktree can provision and verify its own infra without colliding with another. `owner` is optional metadata, not access control. | **No** |
| `destroy_environment(name)` | Release an environment's board port and remove its entries. | **No** |
| `list_environments()` | List every registered environment: name, app_context, board port, created time, and owner. | **No** |
| `describe_environment(name)` | List an environment's capabilities with monthly real-AWS cost estimates (live AWS pricing for 6 capabilities, labelled estimates for the rest). Names AWS services. | **No** |
| `snapshot_environment(name)` | Save a point-in-time copy of an environment's recorded capabilities (recorded state, not the infrastructure itself). Returns a `snapshot_id`. | **No** |
| `restore_environment(name, snapshot_id)` | Restore a snapshot into the same environment. Each capability is re-verified live first; ones that fail are skipped, not restored. | **No** |
| `get_verification_history(app_context=None, capability_id=None, since=None, until=None)` | Query the event log for what changed and when. Filters combine with AND; `since`/`until` are ISO-8601 timestamps. Each event's `dev` field has raw commands and service names; relay only its `founder` field. | **No** |

## The one rule that matters

Everything a founder-safe tool returns is plain language you can relay as-is. Never relay a
service name, ARN, port, or credential to the founder. If a tool or field is marked "No" or "for
you only" above, or its description says it's not for the founder, treat that as a hard boundary,
not a suggestion.
