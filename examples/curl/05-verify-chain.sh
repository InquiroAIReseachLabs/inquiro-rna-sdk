#!/usr/bin/env bash
# Example 05: Verify a chain segment by position range (mock arguments).
# Live server: pilot tenant only (set RNA_PARTNER_KEY) and it takes
# start_hash/end_hash instead of start/end. The public demo tenant gets
# "Request blocked by security policy".
# Run: bash examples/curl/05-verify-chain.sh [start] [end]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT/scripts/rna_env.sh"
BASE="$RNA_BASE_URL"
START="${1:-1}"
END="${2:-10}"

curl -s -X POST "$BASE" ${RNA_KEY_ARGS[@]+"${RNA_KEY_ARGS[@]}"} \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\":\"tools/call\",\"params\":{\"name\":\"verify_chain_segment\",\"arguments\":{\"start\":$START,\"end\":$END}}}"
