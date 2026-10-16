#!/usr/bin/env bash
# Example 01: Initialize: confirm the server is up and list available tools.
# Endpoint: RNA_BASE_URL (default: live demo, see rna.config.json; mock: http://localhost:8000/mcp).
# Run: bash examples/curl/01-initialize.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT/scripts/rna_env.sh"
BASE="$RNA_BASE_URL"

curl -s -X POST "$BASE" ${RNA_KEY_ARGS[@]+"${RNA_KEY_ARGS[@]}"} \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'
