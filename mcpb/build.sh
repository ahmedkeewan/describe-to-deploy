#!/usr/bin/env bash
# Builds the .mcpb Desktop Extension bundle for the floci-control-plane MCP server (GH-92).
#
# harness/*.py stays the single source of truth -- this script stages a COPY of the files the
# server actually needs (mirroring the harness/ + catalog/ layout mcp_server.py's own REPO_ROOT
# resolution expects) into a scratch build directory, then packs that with `mcpb pack`. Nothing
# under mcpb/server/ is committed; it's a build artifact, regenerated on every run.
#
# Requires the mcpb CLI (npm install -g @anthropic-ai/mcpb) on PATH. Does NOT require uv locally
# to build -- uv is a runtime dependency for whoever installs the resulting .mcpb into Claude
# Desktop, not for building it.
#
# Usage: ./mcpb/build.sh [output-path]
#   output-path   where to write the .mcpb file (default: mcpb/describe-to-deploy.mcpb)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCPB_DIR="$REPO_ROOT/mcpb"
BUILD_DIR="$MCPB_DIR/.build"
OUTPUT="${1:-$MCPB_DIR/describe-to-deploy.mcpb}"

if ! command -v mcpb >/dev/null 2>&1; then
  echo "mcpb CLI not found on PATH. Install it with: npm install -g @anthropic-ai/mcpb" >&2
  exit 1
fi

echo "== Staging bundle contents =="
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/server/harness" "$BUILD_DIR/server/catalog"

cp "$MCPB_DIR/manifest.json" "$BUILD_DIR/manifest.json"
cp "$MCPB_DIR/pyproject.toml" "$BUILD_DIR/server/pyproject.toml"

# Only the modules mcp_server.py imports directly, or invokes via subprocess -- not the test
# suite, not the .venv, not runtime state files (stack-state.json, events.jsonl, environments.json,
# environment-snapshots.json, .*.lock) which are per-machine data, not server code.
HARNESS_FILES=(
  mcp_server.py
  environments_store.py
  events.py
  auto_wire.py
  go_live_plan.py
  build_prompt.py
  verify_gate.py
  snapshots_store.py
  state_lock.py
  pricing.py
  stack-plan.schema.json
  stack-state.schema.json
)
for f in "${HARNESS_FILES[@]}"; do
  cp "$REPO_ROOT/harness/$f" "$BUILD_DIR/server/harness/$f"
done
cp "$REPO_ROOT/catalog/capabilities.json" "$BUILD_DIR/server/catalog/capabilities.json"

echo "== Validating manifest =="
mcpb validate "$BUILD_DIR/manifest.json"

echo "== Packing =="
mkdir -p "$(dirname "$OUTPUT")"
mcpb pack "$BUILD_DIR" "$OUTPUT"

echo ""
echo "Built: $OUTPUT"
echo "Install it by double-clicking the file (or dragging it onto Claude Desktop) and clicking Install."
