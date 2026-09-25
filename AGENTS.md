# AGENTS.md

This file is for an AI coding agent (Claude Code, Cursor, or any MCP-capable client) that wants
to connect to and call this repo's MCP server. It is not a build/test/contribution guide — see
[CONTRIBUTING.md](CONTRIBUTING.md) for that.

## What this server does

`harness/mcp_server.py` is an MCP server that turns a plain-language product request into real,
verified local infrastructure on [Floci](https://floci.io/). You are the planner + executor: you
read the tool list below, match the founder's request to a capability, get the real steps from
`get_provisioning_recipe`, execute them with your own tool access, then call `record_provisioned`
— which independently re-verifies before it ever updates state. Your own belief that something
worked is never sufficient.

## Connecting

The server must already have Floci running (`floci start`) and its own dependencies installed —
run `./setup.sh` from the repo root once if you haven't. Then point your MCP client at it:

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

See [`harness/README.md`](harness/README.md)'s "Connecting to Claude Desktop" / "Connecting to
Cursor" sections for the exact config file locations on each client.

## Tool list

**Founder-facing product tools** — call these when driving the actual harness workflow:

| Tool | Purpose |
|------|---------|
| `list_capabilities()` | List every product capability this harness can build, in plain language. |
| `get_app_state(app_context)` | Look up what has already been built and verified for a given app. |
| `get_provisioning_recipe(capability_id, resource_name, app_context)` | Get the exact technical steps and verification command to actually build a capability. Returns infra detail — for your own use, never relay to the founder. |
| `record_provisioned(app_context, capability_id, resource_name)` | Call this after you've actually run the provisioning steps. Independently re-verifies before updating state. |
| `report_unsupported_request(app_context, request_text, closest_capability_id)` | Call this instead of inventing anything when a request doesn't match `list_capabilities()`. |
| `check_app_readiness(app_context)` | Re-verify, live, everything on record for this app — don't trust cached timestamps. |
| `wire_app_config(app_context, app_directory)` | Write real connection details into the founder's app config file. |
| `whats_needed_to_go_live(app_context)` | The one tool that names real cloud services — a technical migration report, not for the founder. |

**Environment-management tools** — for you, the agent, managing multiple isolated
environments (e.g. one per git worktree), not for the founder:

| Tool | Purpose |
|------|---------|
| `create_environment(name)` | Mint a new, isolated environment so your agent/worktree can provision and verify its own infra without colliding with another. |
| `destroy_environment(name)` | Release an environment's board port and remove its entries. |
| `list_environments()` | List every currently registered environment. |

## The one rule that matters

Every tool's return value is built to be founder-safe plain language, **except** the tools noted
above as returning infra detail. Never relay a service name, ARN, port, or credential to the
founder — if a tool's docstring says it's not for the founder, treat that as a hard boundary, not
a suggestion. See `harness/mcp_server.py`'s own module docstring for the complete, authoritative
list of exceptions.
