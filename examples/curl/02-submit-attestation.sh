#!/usr/bin/env bash
# Example 02: Submit an attestation and verify the receipt.
# Run: bash examples/curl/02-submit-attestation.sh
# Endpoint: RNA_BASE_URL (default: live demo, see rna.config.json; mock: http://localhost:8000/mcp).
# The live server needs an envelope (event_type, device_id, timestamp, signature,
# payload) with a fresh timestamp each run; the mock accepts the same envelope.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT/scripts/rna_env.sh"
BASE="$RNA_BASE_URL"
OUT="${RNA_RECEIPT_OUT:-${TMPDIR:-/tmp}/receipt.json}"

BODY=$(rna_py -c 'import json,sys; sys.path.insert(0, sys.argv[1]); from scripts.first_receipt import build_attestation; doc=json.load(open(sys.argv[2])); print(json.dumps({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"submit_attestation","arguments":build_attestation(doc)}}))' "$ROOT" "$ROOT/payloads/identity_verified.json")

curl -s -X POST "$BASE" ${RNA_KEY_ARGS[@]+"${RNA_KEY_ARGS[@]}"} \
  -H "Content-Type: application/json" \
  -d "$BODY" \
  -o "$OUT"

echo "Receipt saved to $OUT"
rna_py "$ROOT/verifier/verify.py" "$OUT"
