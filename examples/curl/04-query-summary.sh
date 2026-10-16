#!/usr/bin/env bash
# Example 04: Query the flight summary.
# Live server: pilot tenant only (set RNA_PARTNER_KEY). The public demo tenant
# gets "Request blocked by security policy". The mock answers without a key.
# Run: bash examples/curl/04-query-summary.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT/scripts/rna_env.sh"
BASE="$RNA_BASE_URL"

curl -s -X POST "$BASE" ${RNA_KEY_ARGS[@]+"${RNA_KEY_ARGS[@]}"} \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"query_flight_summary","arguments":{}}}'
