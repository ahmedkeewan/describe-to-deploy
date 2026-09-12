#!/usr/bin/env bash
# Sets up this repo end to end: checks for Docker, checks/installs Floci, creates the harness
# venv, and wires the MCP server into Claude Desktop and Claude Code. Safe to re-run -- every
# step is idempotent and skips work that's already done. Never silently installs software or
# starts containers; each such step asks for confirmation first.
#
# Usage: ./setup.sh [--start-board]
#   --start-board   after setup finishes, also start the live board (harness/web_server.py) in
#                   the foreground. Without this flag (the default), setup only prints the
#                   command -- it never launches a long-running process on its own.
set -euo pipefail

START_BOARD=false
for arg in "$@"; do
  case "$arg" in
    --start-board) START_BOARD=true ;;
    *)
      echo "Unknown argument: $arg (supported: --start-board)" >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_ROOT/harness/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
MCP_SERVER="$REPO_ROOT/harness/mcp_server.py"
WEB_SERVER="$REPO_ROOT/harness/web_server.py"

say() { printf '%s\n' "$*"; }
step() { printf '\n== %s ==\n' "$*"; }
confirm() {
  # $1 = prompt text. Returns 0 (yes) only on an explicit y/Y answer.
  local reply
  read -r -p "$1 [y/N] " reply || true
  [[ "$reply" =~ ^[Yy]$ ]]
}

# --- 1. Platform check --------------------------------------------------------------------
step "Checking platform"
platform="$(uname -s)"
is_wsl=false
case "$platform" in
  Darwin)
    say "Detected $platform -- supported."
    ;;
  Linux)
    if [ -n "${WSL_DISTRO_NAME:-}" ] || grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
      is_wsl=true
      say "Detected Linux under WSL -- supported. Note: Claude Desktop runs on the Windows side,"
      say "not inside WSL, so its config path is resolved differently below."
    else
      say "Detected $platform -- supported."
    fi
    ;;
  *)
    say "This script supports macOS, Linux, and WSL only (detected: $platform)."
    say "Native Windows without WSL isn't scripted here -- Floci has its own PowerShell"
    say "installer (irm https://floci.io/install.ps1 | iex); wire the MCP server manually"
    say "afterwards per harness/README.md, or install WSL and re-run this script inside it."
    exit 1
    ;;
esac

# --- 2. Docker check -----------------------------------------------------------------------
step "Checking Docker"
if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  say "Docker isn't installed or isn't running. Floci needs Docker to run its emulators."
  say "Install/start Docker (https://docs.docker.com/get-docker/), then re-run this script."
  exit 1
fi
say "Docker is running."

# --- 3. Floci check + optional install ------------------------------------------------------
step "Checking Floci"
FLOCI_BIN=""
if command -v floci >/dev/null 2>&1; then
  FLOCI_BIN="floci"
elif command -v floci-cli >/dev/null 2>&1; then
  FLOCI_BIN="floci-cli"
fi

if [ -z "$FLOCI_BIN" ]; then
  say "Floci isn't installed. Official install command:"
  say ""
  say "    curl -fsSL https://floci.io/install.sh | sh"
  say ""
  if confirm "Run this now to install Floci?"; then
    curl -fsSL https://floci.io/install.sh | sh
    if command -v floci >/dev/null 2>&1; then
      FLOCI_BIN="floci"
    elif command -v floci-cli >/dev/null 2>&1; then
      FLOCI_BIN="floci-cli"
    else
      say "Install finished but no 'floci' or 'floci-cli' binary was found on PATH."
      say "Open a new shell (PATH may need to reload) and re-run this script."
      exit 1
    fi
    say "Floci installed."
  else
    say "Skipping install. Run the command above yourself, then re-run ./setup.sh."
    exit 0
  fi
else
  say "Floci is already installed ($FLOCI_BIN)."
fi

# --- 4. Start Floci if not already running ---------------------------------------------------
step "Checking whether Floci is running"
if "$FLOCI_BIN" doctor >/dev/null 2>&1; then
  say "Floci is already running."
else
  if confirm "Floci doesn't look like it's running. Start it now (floci start)?"; then
    "$FLOCI_BIN" start
    say "Floci started."
  else
    say "Skipping. You'll need to run '$FLOCI_BIN start' yourself before using the MCP server."
  fi
fi

# --- 5. Python venv + deps -------------------------------------------------------------------
step "Setting up the harness Python environment"
if [ ! -x "$VENV_PYTHON" ]; then
  python3 -m venv "$VENV_DIR"
  say "Created venv at $VENV_DIR"
else
  say "venv already exists at $VENV_DIR"
fi
"$VENV_PYTHON" -m pip install -q --upgrade pip
"$VENV_PYTHON" -m pip install -q -r "$REPO_ROOT/harness/requirements.txt"
say "Dependencies installed."

# --- 6/7. Wire MCP config into Claude Desktop + Claude Code ----------------------------------
merge_mcp_config() {
  # $1 = target config path, $2 = human label for logging
  local target="$1"
  local label="$2"
  mkdir -p "$(dirname "$target")"
  "$VENV_PYTHON" - "$target" "$VENV_PYTHON" "$MCP_SERVER" <<'PYEOF'
import json
import sys
from pathlib import Path

target_path, python_bin, mcp_server = sys.argv[1:4]
path = Path(target_path)

if path.exists():
    try:
        config = json.loads(path.read_text())
    except json.JSONDecodeError:
        print(f"  ! {path} is not valid JSON -- leaving it untouched. Wire it in by hand.")
        sys.exit(1)
else:
    config = {}

config.setdefault("mcpServers", {})
config["mcpServers"]["floci-control-plane"] = {
    "command": python_bin,
    "args": [mcp_server],
}
path.write_text(json.dumps(config, indent=2) + "\n")
print(f"  wired floci-control-plane into {path}")
PYEOF
}

step "Wiring Claude Desktop"
claude_desktop_config=""
if [ "$is_wsl" = true ]; then
  # Claude Desktop is a native Windows app -- its config lives on the Windows filesystem, not
  # in WSL's own $HOME. Resolve the real path via the Windows-side %APPDATA% env var.
  if command -v cmd.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
    win_appdata="$(cmd.exe /c 'echo %APPDATA%' 2>/dev/null | tr -d '\r\n')"
    if [ -n "$win_appdata" ]; then
      claude_desktop_config="$(wslpath "$win_appdata")/Claude/claude_desktop_config.json"
    fi
  fi
  if [ -z "$claude_desktop_config" ]; then
    say "Couldn't resolve the Windows-side Claude Desktop config path (cmd.exe/wslpath"
    say "unavailable or %APPDATA% empty). Wire it manually -- see harness/README.md."
  fi
else
  case "$platform" in
    Darwin) claude_desktop_config="$HOME/Library/Application Support/Claude/claude_desktop_config.json" ;;
    Linux)  claude_desktop_config="$HOME/.config/Claude/claude_desktop_config.json" ;;
  esac
fi
if [ -n "$claude_desktop_config" ]; then
  merge_mcp_config "$claude_desktop_config" "Claude Desktop" || say "  (skipped -- fix the file above and re-run)"
fi

step "Wiring Claude Code (project-scoped)"
merge_mcp_config "$REPO_ROOT/.mcp.json" "Claude Code" || say "  (skipped -- fix the file above and re-run)"

# --- 8. Summary --------------------------------------------------------------------------
step "Setup complete"
say "Next steps:"
say "  - Claude Desktop and Claude Code are wired to the floci-control-plane MCP server."
say "    Restart Claude Desktop (or start a new Claude Code session in this repo) to pick it up."
if [ "$START_BOARD" = false ]; then
  say "  - To start the live board:"
  say "      $VENV_PYTHON harness/web_server.py"
  say "    then open http://localhost:7777"
fi

# --- 9. Optionally start the live board (--start-board) ------------------------------------
if [ "$START_BOARD" = true ]; then
  step "Starting the live board"
  say "Open http://localhost:7777 -- press Ctrl+C here to stop it."
  exec "$VENV_PYTHON" "$WEB_SERVER"
fi
