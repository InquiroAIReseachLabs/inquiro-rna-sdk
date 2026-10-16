#!/usr/bin/env bash
# Example 03: Verify a receipt by hash (server-side ledger lookup, live or mock).
# Run: bash examples/curl/03-verify-receipt.sh <sha256_hex>:<blake3_hex>
# If no hash is supplied, uses an intentionally unknown hash to demonstrate valid:false.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT/scripts/rna_env.sh"
BASE="$RNA_BASE_URL"
HASH="${1:-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb}"

curl -s -X POST "$BASE" ${RNA_KEY_ARGS[@]+"${RNA_KEY_ARGS[@]}"} \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\":\"tools/call\",\"params\":{\"name\":\"verify_receipt\",\"arguments\":{\"receipt_hash\":\"$HASH\"}}}"
