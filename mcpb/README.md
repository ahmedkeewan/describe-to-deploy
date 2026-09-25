# `.mcpb` Desktop Extension bundle (GH-92)

Packages `harness/mcp_server.py` as an Anthropic Desktop Extension (`.mcpb`, formerly `.dxt`) so a
non-technical founder can install the MCP-server-wiring half of this project into Claude Desktop
with a double-click and an "Install" button — no terminal, no editing `claude_desktop_config.json`
by hand. This does **not** replace `./setup.sh`: it only replaces the "wire the MCP config" step.
Docker + Floci still need to be running first (`./setup.sh`, run once, or `floci start`).

## Building

```bash
npm install -g @anthropic-ai/mcpb   # once
./mcpb/build.sh                     # writes mcpb/describe-to-deploy.mcpb
```

`build.sh` stages a copy of the exact files `mcp_server.py` needs (mirroring the
`harness/` + `catalog/` layout its own path resolution expects) into a scratch `mcpb/.build/`
directory, then runs `mcpb pack`. Nothing under `mcpb/.build/` or the packed `.mcpb` output is
committed — `harness/*.py` stays the single source of truth; re-run `build.sh` any time those
files change.

## Installing

Double-click the built `.mcpb` file, or drag it onto the Claude Desktop app icon. Claude Desktop
shows an install dialog naming the server and its tools; click Install.

## Why `server.type: "uv"`, not `"python"`

The traditional `.mcpb` Python bundling approach (`server.type: "python"`, dependencies vendored
into `server/lib/`) cannot portably bundle **compiled** dependencies — and `mcp_server.py`'s only
external dependency, the `mcp` package, requires `pydantic_core`, which is a compiled wheel built
per platform/architecture. Vendoring one architecture's wheel into the bundle would silently break
on any other.

`server.type: "uv"` instead ships only source + a `pyproject.toml` naming `mcp` as a dependency;
`uv` (managed by the Claude Desktop host, not something the founder installs separately) resolves
and builds the right wheel for whatever machine the bundle actually runs on, the same way it would
for any other Python project. Verified locally: `uv run --directory server harness/mcp_server.py`
against the staged bundle resolves and installs `mcp` + `pydantic_core` cleanly.

This is flagged as **experimental** in `@anthropic-ai/mcpb`'s own docs (introduced in manifest
schema v0.4). The locally installed `mcpb` CLI (v2.1.2) validates a `manifest_version: "0.4"`,
`server.type: "uv"` manifest without error, and `uv run` against the staged bundle works end to
end — but this was not verified against an actual Claude Desktop install (no such app was
available in this environment). If Claude Desktop's own `.mcpb` loader doesn't yet support the
`uv` server type, the fallback in `harness/README.md`'s "Connecting to Claude Desktop" section
(manual `claude_desktop_config.json` editing, or `./setup.sh`) still works unconditionally.

## Manifest limits: no "requires Docker/Floci running" precondition

Investigated as part of this ticket's scope: the `.mcpb` manifest schema (v0.1 through v0.4, all
inspected directly from the installed `@anthropic-ai/mcpb` package) has no field for declaring an
external-runtime precondition or a pre-install health check — `compatibility` covers only
`platforms`/`runtimes`/the Claude Desktop version, and `user_config` only covers user-supplied
config values, not a live check. There is no way to make the manifest itself block installation,
or even warn, if Docker/Floci isn't running.

Conclusion: this **stays a documented prerequisite**, not something the bundle enforces. In
practice this is low-friction — the server installs either way, and the first tool call against a
capability fails with a clear connection error if Floci isn't reachable, rather than the
installation itself being blocked.

## Platform scope

`compatibility.platforms` is set to `["darwin"]` only. `.mcpb` is a Claude Desktop-specific format
(macOS and Windows); this project's own `setup.sh` treats native Windows as unsupported (WSL only)
and this bundle wasn't tested against WSL's or native Windows' Claude Desktop install. Widening
platform support is left for a follow-up if a Windows/WSL founder actually needs it.
