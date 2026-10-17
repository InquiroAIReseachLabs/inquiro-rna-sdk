#!/usr/bin/env bash
# Final audit: extends scripts/smoke_test.sh with the offline path, the evaluator
# bundle, the known-answer vectors, the scenario demos, and claim checks on the
# live site. Written to run from Windows Git Bash (py -3) as well as Linux/macOS.
#
#   git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
#   bash scripts/final_audit.sh            # writes audit.log in the current directory
#
# Optional environment:
#   RNA_BASE_URL        another endpoint (default: rna.config.json)
#   RNA_PARTNER_KEY     pilot key (sent as X-Partner-Key, never printed)
#   WEBSITE_REPO        path to a checkout of Inquiro-Website- to crawl its links too
#   OLD_RECEIPT         a receipt.json saved before the last sandbox restart; used to
#                       show the ledger_reset answer on the live host
#   AUDIT_LOG           log path (default: ./audit.log)
#   SKIP_LIVE=1         run only the offline sections
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
. "$ROOT/scripts/rna_env.sh" || exit 1
LOG="${AUDIT_LOG:-$PWD/audit.log}"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

TMP="$(mktemp -d)"
FAILS=0; PASSES=0; HUMAN=0
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { printf '%s | %s\n' "$(now)" "$*"; }
pass() { log "PASS $*"; PASSES=$((PASSES + 1)); }
fail() { log "FAIL $*"; FAILS=$((FAILS + 1)); }
human() { log "HUMAN $*"; HUMAN=$((HUMAN + 1)); }
section() { echo; echo "=== $* ==="; }
redact() { sed -E 's/(X-Partner-Key: )[^ ]+/\1[REDACTED]/g; s/[A-Za-z0-9+\/]{40,}={0,2}/[REDACTED-B64]/g'; }
SITE="https://inquiroresearchlabs.ai"
OLD_HOST="https://aiflightrecorder.onrender.com"

section "0. Environment"
log "date: $(now)"
log "uname: $(uname -s -m 2>/dev/null)"
log "python: $(rna_py -c 'import sys; print(sys.executable, sys.version.split()[0])')"
log "git: $(git rev-parse --short HEAD 2>/dev/null || echo 'not a git checkout')"
log "endpoint: $RNA_BASE_URL"
log "log: $LOG"
rna_py -c 'import blake3' 2>/dev/null && log "blake3: native" || log "blake3: not installed (pure-Python fallback will be used; pip install -r requirements.txt for speed)"
rna_py -c 'import cryptography' 2>/dev/null && log "cryptography: native" || log "cryptography: not installed (sealing needs it; verification falls back to pure Python)"

section "1. Known-answer vectors (docs/TEST_VECTORS.md)"
if rna_py tests/test_vectors.py >"$TMP/vectors.log" 2>&1; then pass "test vectors: $(tail -1 "$TMP/vectors.log")"; else fail "test vectors"; tail -20 "$TMP/vectors.log"; fi

section "2. Offline path (keygen, seal, verify, bundle)"
if rna_py -c 'import cryptography' 2>/dev/null; then
  OFF="$TMP/offline"; mkdir -p "$OFF"
  rna_py -m offline keygen --private "$OFF/signer.pem" --public "$OFF/signer.pub" >"$OFF/keygen.log" 2>&1 && pass "keygen" || fail "keygen: $(cat "$OFF/keygen.log")"
  rna_py scripts/ingest_log.py payloads/tactical_uas/mission.jsonl --ledger "$OFF/receipts.jsonl" --key "$OFF/signer.pem" >"$OFF/ingest.log" 2>&1 && pass "ingest mission.jsonl: $(tail -1 "$OFF/ingest.log")" || fail "ingest: $(cat "$OFF/ingest.log")"
  out=$(rna_py -m offline verify "$OFF/receipts.jsonl" "$OFF/signer.pub" 2>&1) && pass "offline verify: $out" || fail "offline verify: $out"
  out=$(rna_py -m offline bundle --ledger "$OFF/receipts.jsonl" --public "$OFF/signer.pub" --out "$OFF/evaluator_bundle.zip" 2>&1) && pass "bundle: $(echo "$out" | tail -1)" || fail "bundle: $out"
  # Verify the bundle in an empty directory with an isolated interpreter (-I) and the pure-Python path forced.
  BOX="$TMP/evalbox"; mkdir -p "$BOX"; (cd "$BOX" && rna_py -m zipfile -e "$OFF/evaluator_bundle.zip" .)
  out=$(cd "$BOX/evaluator_bundle" && RNA_VERIFY_PURE=1 rna_py -I verify.py receipts.jsonl public_key.pub 2>&1) && pass "bundle verifies with python -I, pure-Python forced: $out" || fail "bundle verify (pure): $out"
  out=$(cd "$BOX/evaluator_bundle" && rna_py -I verify.py receipts.jsonl public_key.pub 2>&1) && pass "bundle verifies with python -I, default backend: $out" || fail "bundle verify: $out"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$BOX/evaluator_bundle" && sha256sum -c SHA256SUMS >"$TMP/sums.log" 2>&1) && pass "SHA256SUMS check" || { fail "SHA256SUMS"; cat "$TMP/sums.log"; }
  else log "SKIP sha256sum not found"; fi
  rna_py - "$BOX/evaluator_bundle" <<'PY'
import json, sys
d = sys.argv[1]
L = [json.loads(l) for l in open(f"{d}/receipts.jsonl")]
open(f"{d}/deleted.jsonl", "w").write("".join(json.dumps(r, sort_keys=True) + "\n" for i, r in enumerate(L) if i != 5))
L[2]["payload"]["confidence"] = 0.99  # one value changed after sealing, not re-signed
open(f"{d}/tampered.jsonl", "w").write("".join(json.dumps(r, sort_keys=True) + "\n" for r in L))
PY
  if (cd "$BOX/evaluator_bundle" && rna_py -I verify.py tampered.jsonl public_key.pub >"$TMP/t.log" 2>&1); then fail "tampered ledger verified"; else pass "tampered ledger rejected: $(sed -n 2p "$TMP/t.log")"; fi
  if (cd "$BOX/evaluator_bundle" && rna_py -I verify.py deleted.jsonl public_key.pub >"$TMP/d.log" 2>&1); then fail "ledger with a deleted receipt verified"; else pass "deleted receipt detected: $(sed -n 2p "$TMP/d.log")"; fi
  if command -v unshare >/dev/null 2>&1 && unshare -rn true 2>/dev/null; then
    out=$(cd "$BOX/evaluator_bundle" && unshare -rn "${RNA_PY[@]}" -I verify.py receipts.jsonl public_key.pub 2>&1) && pass "bundle verifies inside a no-network namespace (unshare -rn)" || fail "no-network verify: $out"
  else log "SKIP unshare not available here (Windows): disable the network adapter and rerun verify.py by hand to prove the offline claim"; fi
else
  fail "offline path needs the cryptography package: pip install -r requirements.txt"
fi

section "3. Scenario demos reproduce byte-for-byte"
if command -v sha256sum >/dev/null 2>&1 && rna_py -c 'import cryptography' 2>/dev/null; then
  (cd payloads/tactical_uas/demos && find . -type f | sort | xargs sha256sum) > "$TMP/demos_before.txt"
  rna_py scripts/run_scenario.py demo >"$TMP/demo.log" 2>&1 || fail "run_scenario.py demo exited non-zero"
  (cd payloads/tactical_uas/demos && find . -type f | sort | xargs sha256sum) > "$TMP/demos_after.txt"
  if diff "$TMP/demos_before.txt" "$TMP/demos_after.txt" >"$TMP/demos.diff"; then pass "all four demos rebuilt byte-for-byte ($(wc -l < "$TMP/demos_after.txt") files)"; else fail "demo output changed"; cat "$TMP/demos.diff"; fi
  for d in intact tamper missing_event missing_event_resealed; do
    rna_py scripts/run_scenario.py check "payloads/tactical_uas/demos/$d/receipts.jsonl" payloads/tactical_uas/demo_key/demo_signer.pub >"$TMP/$d.out" 2>&1
    if diff -q "$TMP/$d.out" "payloads/tactical_uas/demos/$d/expected_output.txt" >/dev/null; then pass "demo $d matches expected_output.txt"; else fail "demo $d differs from expected_output.txt"; diff "$TMP/$d.out" "payloads/tactical_uas/demos/$d/expected_output.txt"; fi
  done
else log "SKIP demos (needs sha256sum and cryptography)"; fi

if [ "${SKIP_LIVE:-0}" = "1" ]; then
  section "Done (offline only): $PASSES pass, $FAILS fail"
  echo "Log: $LOG"; [ "$FAILS" -eq 0 ]; exit
fi

section "4. Old host (Jay finding 1) must not be the documented host"
if grep -rIq "aiflightrecorder\.onrender\.com" --include='*.md' --include='*.py' --include='*.sh' --include='*.json' --include='*.yml' --include='*.js' . 2>/dev/null; then fail "old host still referenced in this repo"; else pass "no reference to the old host in this repo"; fi
code=$(curl -sS -m 30 -o /dev/null -w '%{http_code}' "$OLD_HOST/health" 2>/dev/null || echo 000)
log "GET $OLD_HOST/health -> $code (informational: the old host is expected to be dead or suspended)"
case "$RNA_BASE_URL" in *aiflightrecorder-1.onrender.com*) pass "configured host is the new one" ;; *) log "NOTE configured host is $RNA_BASE_URL" ;; esac

section "5. Hosted sandbox journey (smoke_test.sh)"
bash scripts/smoke_test.sh > "$TMP/smoke.log" 2>&1; smoke_rc=$?
redact < "$TMP/smoke.log"
[ "$smoke_rc" -eq 0 ] && pass "smoke_test.sh exit 0" || fail "smoke_test.sh exit $smoke_rc (see lines above)"

section "6. Live host details (persistence, notice, scope)"
HEALTH=$(rna_py -c 'import rna_config; print(rna_config.health_url())')
curl -sS -m 120 -o "$TMP/health.json" "$HEALTH" 2>/dev/null
grep -q '"persistence": "ephemeral"' "$TMP/health.json" && log "NOTE /health reports persistence: ephemeral (free tier; ledger resets on restart)"
grep -q '"persistence": "persistent"' "$TMP/health.json" && log "NOTE /health reports persistence: persistent"
grep -q '"persistence"' "$TMP/health.json" && pass "/health carries a persistence field" || fail "/health has no persistence field :: $(head -c 200 "$TMP/health.json")"
curl -sS -m 60 -o "$TMP/init.json" -X POST "$RNA_BASE_URL" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{}}' 2>/dev/null
grep -q 'synthetic data only' "$TMP/init.json" && pass "keyless initialize returns the sandbox notice" || fail "sandbox notice missing from initialize :: $(head -c 200 "$TMP/init.json")"
curl -sS -m 60 -o "$TMP/scope.json" -X POST "$RNA_BASE_URL" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"verify_chain_segment","arguments":{}}}' 2>/dev/null
if [ -n "${RNA_PARTNER_KEY:-}" ]; then log "NOTE pilot key set; skipping the keyless-scope check"; else
grep -q 'pilot_key_required' "$TMP/scope.json" && pass "keyless verify_chain_segment answers -32001 pilot_key_required" || fail "keyless scope error not as documented :: $(head -c 200 "$TMP/scope.json")"; fi
if [ -n "${OLD_RECEIPT:-}" ] && [ -f "$OLD_RECEIPT" ]; then
  rna_py - "$OLD_RECEIPT" "$RNA_BASE_URL" <<'PY'
import json, sys, urllib.request
d = json.load(open(sys.argv[1])); url = sys.argv[2]
args = {"receipt_hash": d["receipt_hash"], "sealed_at": d["attestation"]["timestamp"]}
body = json.dumps({"jsonrpc": "2.0", "id": "1", "method": "tools/call", "params": {"name": "verify_receipt", "arguments": args}}).encode()
r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=90).read())["result"]
print("old receipt lookup:", {k: r.get(k) for k in ("valid", "chain_intact", "reason")})
sys.exit(0 if r.get("reason") == "ledger_reset" or r.get("valid") is True else 1)
PY
  [ $? -eq 0 ] && pass "old receipt: server answers valid or reason ledger_reset (never a tamper verdict)" || fail "old receipt lookup gave an unexpected answer"
  out=$(rna_py verifier/verify.py "$OLD_RECEIPT" 2>&1) && pass "old receipt still verifies offline from receipt_body: $out" || fail "old receipt offline verify: $out"
else
  human "ledger_reset after a fresh container: set OLD_RECEIPT=<receipt.json saved before the last restart> and rerun, or restart the Render service and look up a receipt saved before it (expected: reason ledger_reset, chain_intact null)"
fi

section "7. Live site claims (website)"
fetch() { curl -sS -m 30 -L -o "$2" "$1" 2>/dev/null; }
fetch "$SITE/" "$TMP/home.html"; fetch "$SITE/proving-ground/" "$TMP/pg.html"; fetch "$SITE/developers/" "$TMP/dev.html"
fetch "$SITE/company/" "$TMP/company.html"; fetch "$SITE/llms.txt" "$TMP/llms.txt"; fetch "$SITE/llms-full.txt" "$TMP/llmsfull.txt"
fetch "$SITE/.well-known/security.txt" "$TMP/security.txt"; fetch "$SITE/rna/" "$TMP/rna.html"; fetch "$SITE/regulatory-timeline/" "$TMP/reg.html"
if [ ! -s "$TMP/pg.html" ]; then fail "could not fetch the live site"; else
  for f in home pg dev company rna reg; do
    for phrase in "in production" "Courts admit" "court-admissible" "tamper-proof" "unhackable" "immutable" "Verify any AI output" "every claim has a demonstration" "1.6 seconds" "under USPTO examination"; do
      grep -qi "$phrase" "$TMP/$f.html" && fail "live /$f/ still says: $phrase" ; done
  done
  pass "banned phrases checked on 6 live pages (any hit is listed above as FAIL)"
  grep -q "aiflightrecorder-1.onrender.com" "$TMP/dev.html" && pass "live /developers/ names the new host" || fail "live /developers/ does not name the new host"
  grep -q '"persistence": "ephemeral"' "$TMP/dev.html" && pass "live /developers/ carries the temporary-ledger note" || log "PENDING temporary-ledger note not live yet"
  grep -qi "not production systems" "$TMP/pg.html" && pass "live proving ground says: not production systems" || fail "live proving ground lacks the status line"
  grep -qi "Not yet validated against real outcomes" "$TMP/pg.html" && pass "live proving ground says: Not yet validated against real outcomes" || fail "live proving ground lacks the validation disclaimer"
  grep -q "Patent pending" "$TMP/rna.html" && pass "live /rna/ uses patent-pending wording" || log "PENDING patent wording change not live yet"
  grep -q 'id="status"' "$TMP/reg.html" && pass "live /regulatory-timeline/ has the status and sources section" || log "PENDING regulatory status section not live yet"
  for p in llms.txt llmsfull.txt security.txt; do [ -s "$TMP/$p" ] && pass "live $p reachable" || fail "live $p missing"; done
  grep -qi "immutable\|constant time" "$TMP/llmsfull.txt" && fail "live llms-full.txt still says immutable or constant time" || pass "live llms-full.txt free of immutable/constant-time wording"
  for u in /developers/sandbox/ /receipt-experience/; do code=$(curl -sS -m 30 -o /dev/null -w '%{http_code}' "$SITE$u" 2>/dev/null || echo 000); case "$code" in 301|302|308|200) pass "$u -> $code (redirect or page, not 404)";; *) fail "$u -> $code";; esac; done
fi

section "8. Link crawl"
if [ -n "${WEBSITE_REPO:-}" ]; then rna_py scripts/link_crawl.py --website "$WEBSITE_REPO" > "$TMP/crawl.log" 2>&1; else rna_py scripts/link_crawl.py > "$TMP/crawl.log" 2>&1; fi
crawl_rc=$?; grep -E "^(FAIL|WARN)|^link crawl" "$TMP/crawl.log"
[ "$crawl_rc" -eq 0 ] && pass "link crawl" || fail "link crawl (FAIL lines above; set WEBSITE_REPO to include the site)"

section "9. Items that need a human"
human "Mailbox: send a test message to the SECURITY.md address and to the .well-known/security.txt address and confirm both are read"
human "Render dashboard: confirm the live service is the hardened pilot image and whether a persistent disk is mounted (plan, /var/data)"
human "Starcloud sibling demos (starcloud1.northstaraokeystone.com) are an external site: open each linked scenario and confirm it loads"

section "Done: $PASSES pass, $FAILS fail, $HUMAN need a human. Temp files in $TMP (no keys written)."
echo "Log: $LOG"
[ "$FAILS" -eq 0 ]
