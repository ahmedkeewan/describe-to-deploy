#!/usr/bin/env bash
# Sets up this repo end to end: checks for Docker, checks/installs Floci and the AWS CLI,
# creates the harness venv (Python 3.11+), and wires the MCP server into Claude Desktop, Claude
# Code, and Cursor. Safe to re-run -- every step is idempotent and skips work that's already
# done. Never silently installs system software, starts containers, or edits Claude Desktop's
# global config; each such step asks for confirmation first. (Python packages go into the
# repo-local venv at harness/.venv without a prompt.)
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

# --- 2. Docker check, with an offer to install Colima via Homebrew if nothing is present ----
step "Checking Docker"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  say "Docker is running."
elif command -v docker >/dev/null 2>&1; then
  # The CLI is present, so a runtime is installed -- it just isn't answering. Offering to
  # install Colima here would be wrong for a Docker Desktop user whose app is simply closed.
  say "Docker is installed but isn't running (or this user can't reach it)."
  say "  - Docker Desktop: open the Docker app and wait until it says it's running."
  say "  - Colima: run 'colima start'."
  say "  - Linux: start the daemon (sudo systemctl start docker) and make sure your user is in"
  say "    the 'docker' group."
  say "Then re-run ./setup.sh."
  exit 1
else
  say "Docker isn't installed. Floci needs Docker (or Colima, a lightweight Docker-compatible"
  say "runtime) to run its emulators."

  if ! command -v brew >/dev/null 2>&1; then
    say ""
    say "Homebrew isn't installed. Official install command:"
    say ""
    say '    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    say ""
    if confirm "Run this now to install Homebrew?"; then
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      if ! command -v brew >/dev/null 2>&1; then
        say "Homebrew install finished but 'brew' isn't on PATH yet."
        say "Open a new shell (PATH may need to reload) and re-run this script."
        exit 1
      fi
    else
      say "Skipping. Install Docker (https://docs.docker.com/get-docker/) or Homebrew + Colima"
      say "yourself, then re-run ./setup.sh."
      exit 1
    fi
  fi

  say ""
  say "Colima (a lightweight Docker-compatible runtime) can be installed via Homebrew:"
  say ""
  say "    brew install colima docker"
  say ""
  if confirm "Install Colima + the docker CLI now?"; then
    brew install colima docker
    say "Colima installed."
  else
    say "Skipping. Install Docker or Colima yourself, then re-run ./setup.sh."
    exit 1
  fi

  if confirm "Start Colima now (colima start)?"; then
    colima start
    say "Colima started."
  else
    say "Skipping. Run 'colima start' yourself before using the MCP server."
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    say "Docker still isn't responding after installing/starting Colima -- check 'colima status'"
    say "and re-run this script."
    exit 1
  fi
  say "Docker is running (via Colima)."
fi

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
    exit 1
  fi
else
  say "Floci is already installed ($FLOCI_BIN)."
fi

# --- 4. Start Floci if not already running ---------------------------------------------------
step "Checking whether Floci is running"
# 'status' answers exactly "is it up?"; 'doctor' runs a full environment diagnostic and can
# fail for unrelated reasons.
if "$FLOCI_BIN" status >/dev/null 2>&1; then
  say "Floci is already running."
else
  if confirm "Floci doesn't look like it's running. Start it now (floci start)?"; then
    "$FLOCI_BIN" start
    say "Floci started."
  else
    say "Skipping. You'll need to run '$FLOCI_BIN start' yourself before using the MCP server."
  fi
fi

# --- 5. AWS CLI check + optional install -----------------------------------------------------
# Every capability's verification check is an 'aws ...' command pointed at the local Floci
# endpoint, so the CLI is required even though no AWS account is ever used.
step "Checking the AWS CLI"
if command -v aws >/dev/null 2>&1; then
  say "AWS CLI is installed ($(aws --version 2>&1 | cut -d' ' -f1))."
else
  say "The AWS CLI isn't installed. It's used only to talk to the local Floci emulator -- no AWS"
  say "account or credentials are needed."
  if command -v brew >/dev/null 2>&1; then
    say ""
    say "    brew install awscli"
    say ""
    if confirm "Install the AWS CLI via Homebrew now?"; then
      brew install awscli
      say "AWS CLI installed."
    else
      say "Skipping. Install it yourself (see above), then re-run ./setup.sh."
      exit 1
    fi
  else
    say "Install it from https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    say "then re-run ./setup.sh."
    exit 1
  fi
fi

# --- 6. Python venv + deps -------------------------------------------------------------------
step "Setting up the harness Python environment"
if [ ! -x "$VENV_PYTHON" ]; then
  # Pinned dependencies (e.g. rpds-py) need Python 3.11+; on an older interpreter pip fails
  # with an unhelpful resolver error, so check up front.
  if ! command -v python3 >/dev/null 2>&1; then
    say "python3 isn't installed. Install Python 3.11 or newer, then re-run ./setup.sh."
    exit 1
  fi
  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    say "Python 3.11 or newer is required (found $(python3 -V 2>&1))."
    say "  - macOS: brew install python@3.12"
    say "  - Linux/WSL: install python3.11+ and its venv package from your package manager."
    say "Then re-run ./setup.sh."
    exit 1
  fi
  python3 -m venv "$VENV_DIR"
  say "Created venv at $VENV_DIR"
else
  say "venv already exists at $VENV_DIR"
fi
"$VENV_PYTHON" -m pip install -q --upgrade pip
"$VENV_PYTHON" -m pip install -q -r "$REPO_ROOT/harness/requirements.txt"
say "Dependencies installed."

# --- 7. Wire MCP config into Claude Desktop, Claude Code, and Cursor --------------------------
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
desktop_wired=false
if [ -n "$claude_desktop_config" ]; then
  # Claude Desktop's config is global to this user, so ask before touching it -- and skip it
  # entirely if you installed the .mcpb bundle instead, or you'd have the server twice.
  say "This adds the floci-control-plane server to Claude Desktop's config:"
  say "    $claude_desktop_config"
  say "(Skip this if you installed the Service Buddy .mcpb bundle in Claude Desktop.)"
  if confirm "Wire Claude Desktop now?"; then
    if [ -f "$claude_desktop_config" ]; then
      cp "$claude_desktop_config" "$claude_desktop_config.bak"
      say "  backed up the existing config to $claude_desktop_config.bak"
    fi
    if merge_mcp_config "$claude_desktop_config" "Claude Desktop"; then
      desktop_wired=true
    else
      say "  (skipped -- fix the file above and re-run)"
    fi
  else
    say "  Skipped Claude Desktop."
  fi
fi

step "Wiring Claude Code (project-scoped)"
merge_mcp_config "$REPO_ROOT/.mcp.json" "Claude Code" || say "  (skipped -- fix the file above and re-run)"

step "Wiring Cursor (project-scoped)"
merge_mcp_config "$REPO_ROOT/.cursor/mcp.json" "Cursor" || say "  (skipped -- fix the file above and re-run)"

# --- 8. Summary --------------------------------------------------------------------------
step "Setup complete"
say "Next steps:"
say "  - Claude Code: start 'claude' from inside $REPO_ROOT and approve the"
say "    floci-control-plane server when asked. To use it from any folder instead:"
say "      claude mcp add --scope user floci-control-plane -- \"$VENV_PYTHON\" \"$MCP_SERVER\""
say "  - Cursor: open $REPO_ROOT and enable floci-control-plane under Settings -> MCP."
if [ "$desktop_wired" = true ]; then
  say "  - Claude Desktop: quit and reopen it to pick up the server."
fi
say "  - Then ask, in plain words: \"What can you set up for me?\""
if [ "$START_BOARD" = false ]; then
  say "  - To start the live board (optional):"
  say "      $VENV_PYTHON $WEB_SERVER"
  say "    then open http://localhost:7777"
fi

# --- 9. Optionally start the live board (--start-board) ------------------------------------
if [ "$START_BOARD" = true ]; then
  step "Starting the live board"
  say "Open http://localhost:7777 -- press Ctrl+C here to stop it."
  exec "$VENV_PYTHON" "$WEB_SERVER"
fi
