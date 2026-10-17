#!/usr/bin/env bash
# End-to-end smoke test of the public developer journey. Read-only and polite:
# a few requests per endpoint.
#
#   git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
#   bash scripts/smoke_test.sh 2>&1 | tee smoke.log
#
# Optional:
#   WEBSITE_REPO=../Inquiro-Website-   also crawl every URL in the website repo
#   RNA_PARTNER_KEY=...                pilot tenant key (sent as X-Partner-Key, never printed)
#   RNA_BASE_URL=...                   another endpoint (default: rna.config.json)
#   SKIP_CRAWL=1                       skip the link crawl (final_audit.sh runs it once itself)
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
. "$ROOT/scripts/rna_env.sh" || exit 1

TMP="$(mktemp -d)"
FAILS=0
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { printf '%s | %s\n' "$(now)" "$*"; }
pass() { log "PASS $*"; }
fail() { log "FAIL $*"; FAILS=$((FAILS + 1)); }

echo "=== Environment ==="
log "python: $(rna_py -c 'import sys; print(sys.executable, sys.version.split()[0])')"
log "endpoint: $RNA_BASE_URL"
HEALTH=$(rna_py -c 'import rna_config; print(rna_config.health_url())')

echo "=== 1. Health and cold start ==="
r=$(curl -sS -m 120 -o "$TMP/h.json" -w '%{http_code} %{time_total}' "$HEALTH") || r="000 0"
set -- $r
log "GET $HEALTH -> $1 in ${2}s :: $(head -c 200 "$TMP/h.json" 2>/dev/null)"
[ "$1" = "200" ] && pass "health 200" || fail "health returned $1"
rna_py -c "import sys; sys.exit(0 if float('$2') <= 10 else 1)" && pass "first request ${2}s (<= 10s)" || log "FLAG first request ${2}s (> 10s: service was asleep)"

echo "=== 2. MCP handshake ==="
for m in initialize tools/list; do
  code=$(curl -sS -m 60 -o "$TMP/m.json" -w '%{http_code}' -X POST "$RNA_BASE_URL" -H 'Content-Type: application/json' \
    ${RNA_KEY_ARGS[@]+"${RNA_KEY_ARGS[@]}"} -d "{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\":\"$m\",\"params\":{}}") || code=000
  log "POST $m -> $code :: $(head -c 160 "$TMP/m.json" 2>/dev/null)"
  [ "$code" = "200" ] && pass "$m" || fail "$m returned $code"
done

echo "=== 3. README first receipt, twice ==="
for i in 1 2; do
  if rna_py scripts/first_receipt.py --out "$TMP/receipt$i.json" >"$TMP/fr$i.log" 2>&1; then
    pass "first_receipt #$i"; else fail "first_receipt #$i"; fi
  sed 's/^/    /' "$TMP/fr$i.log"
done

echo "=== 4. verify.py on both receipts ==="
for i in 1 2; do
  out=$(rna_py verifier/verify.py "$TMP/receipt$i.json" 2>&1) && pass "verify receipt #$i :: $out" || fail "verify receipt #$i :: $out"
done

echo "=== 5. Chain position increments ==="
rna_py - "$TMP" <<'PY' && pass "chain position increments" || fail "chain position did not increment"
import json, sys
t = sys.argv[1]
p = [json.load(open(f"{t}/receipt{i}.json"))["chain_position"] for i in (1, 2)]
print(f"    chain_position: {p[0]} -> {p[1]}")
sys.exit(0 if p[1] > p[0] else 1)
PY

echo "=== 6. Tamper test (one-character change must fail) ==="
rna_py - "$TMP" <<'PY'
import json, sys
t = sys.argv[1]
d = json.load(open(f"{t}/receipt1.json"))
h = d["receipt_hash"]
d["receipt_hash"] = h[:-1] + ("0" if h[-1] != "0" else "1")
json.dump(d, open(f"{t}/tampered.json", "w"))
PY
if out=$(rna_py verifier/verify.py "$TMP/tampered.json" 2>&1); then fail "tampered receipt verified :: $out"; else pass "tampered receipt rejected :: $out"; fi

echo "=== 7. Public tenant scope (informational) ==="
code=$(curl -sS -m 60 -o "$TMP/cs.json" -w '%{http_code}' -X POST "$RNA_BASE_URL" -H 'Content-Type: application/json' \
  ${RNA_KEY_ARGS[@]+"${RNA_KEY_ARGS[@]}"} -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"verify_chain_segment","arguments":{}}}') || code=000
log "verify_chain_segment -> $code :: $(head -c 160 "$TMP/cs.json" 2>/dev/null)"

echo "=== 8. Live copy check (proving ground + developers) ==="
curl -sS -m 30 -L "https://inquiroresearchlabs.ai/proving-ground/" -o "$TMP/pg.html" || true
curl -sS -m 30 -L "https://inquiroresearchlabs.ai/developers/" -o "$TMP/dev.html" || true
if [ ! -s "$TMP/pg.html" ] || [ ! -s "$TMP/dev.html" ]; then
  fail "could not fetch the live proving ground or /developers/ page"
else
for phrase in "Receipts in production" "same code path Inquiro runs in production" "Courts admit" "Verify any AI output"; do
  grep -qi "$phrase" "$TMP/pg.html" && fail "live proving ground still says: $phrase" || pass "absent on live proving ground: $phrase"
done
for phrase in "Score any AI output" "Not yet validated against real outcomes" "not production systems"; do
  grep -qi "$phrase" "$TMP/pg.html" && pass "live proving ground says: $phrase" || log "PENDING not on live proving ground yet (deploy pending?): $phrase"
done
grep -q "aiflightrecorder-1.onrender.com" "$TMP/dev.html" && pass "live /developers/ has endpoint table" || log "PENDING /developers/ endpoint table not live yet (deploy pending?)"
fi

echo "=== 9. Link crawl ==="
if [ "${SKIP_CRAWL:-0}" = "1" ]; then
  log "SKIP link crawl (SKIP_CRAWL=1)"
elif [ -n "${WEBSITE_REPO:-}" ]; then
  rna_py scripts/link_crawl.py --website "$WEBSITE_REPO" && pass "link crawl" || fail "link crawl (see FAIL lines above)"
else
  rna_py scripts/link_crawl.py && pass "link crawl (SDK only; set WEBSITE_REPO to include the website)" || fail "link crawl (see FAIL lines above)"
fi

echo "=== Done: $FAILS failure(s). Temp files in $TMP (no keys written). ==="
[ "$FAILS" -eq 0 ]
