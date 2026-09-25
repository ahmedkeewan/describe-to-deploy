# `.mcpb` Desktop Extension bundle (experimental)

Packages `harness/mcp_server.py` as an Anthropic Desktop Extension (`.mcpb`, formerly `.dxt`), so
the server can be added to Claude Desktop with a double-click and an "Install" button instead of
editing `claude_desktop_config.json` by hand.

**Status, stated plainly:**

- **Build it yourself for now.** There's no prebuilt bundle yet; one will be attached to
  [GitHub Releases](https://github.com/ahmedkeewan/service-buddy/releases) once it's been tested.
- **macOS only.**
- **Not yet verified on a real Claude Desktop install.** The manifest validates and the packaged
  server runs under `uv`, but the end-to-end install in Claude Desktop hasn't been checked (see
  below).
- **It doesn't replace `./setup.sh`.** It only replaces the "wire the MCP config" step. Docker,
  Floci, and the AWS CLI still need to be set up, so run `./setup.sh` once anyway — and answer
  **no** when it offers to wire Claude Desktop, or you'll have the server installed twice.
- **Claude Desktop needs a way to run commands.** The server doesn't provision anything itself:
  the agent runs each recipe's commands with its own tools, then the server verifies. Claude Code
  and Cursor have that built in, which is why they're the recommended clients.

## Building

Requires Node.js/npm.

```bash
npm install -g @anthropic-ai/mcpb   # once
./mcpb/build.sh                     # writes mcpb/service-buddy.mcpb
```

`build.sh` stages a copy of the exact files `mcp_server.py` needs (mirroring the
`harness/` + `catalog/` layout its own path resolution expects) into a scratch `mcpb/.build/`
directory, then runs `mcpb pack`. Nothing under `mcpb/.build/` or the packed `.mcpb` output is
committed — `harness/*.py` stays the single source of truth; re-run `build.sh` any time those
files change.

## Installing

Double-click the built `.mcpb` file, or drag it onto the Claude Desktop app icon. Claude Desktop
shows an install dialog naming the server and its tools; click Install.

**Where state lives:** the installed extension keeps its own copy of the server, so its state
(`stack-state.json`, the event log) is written inside the extension's install folder, not in
your clone of this repo. `make board` in the clone won't show what the extension has set up, and
reinstalling or updating the extension may reset that state.

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
end — but it hasn't yet been verified against an actual Claude Desktop install. If Claude
Desktop's own `.mcpb` loader doesn't support the `uv` server type, the fallback in
[`harness/README.md`](../harness/README.md#connecting-to-claude-desktop) (`./setup.sh`, or manual
`claude_desktop_config.json` editing) still works.

## Manifest limits: no "requires Docker/Floci running" precondition

The `.mcpb` manifest schema (v0.1 through v0.4, all
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
(Claude Desktop runs on macOS and Windows); this project's own `setup.sh` treats native Windows as
unsupported (WSL only), and the bundle hasn't been tested with Claude Desktop on Windows. On
Windows, use `./setup.sh` inside WSL, which wires Claude Desktop's config on the Windows side.
