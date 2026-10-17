#!/usr/bin/env bash
# Final audit: extends scripts/smoke_test.sh with the offline path, the evaluator
# bundle, the known-answer vectors, the scenario demos, and claim checks on the
# live site. Written to run from Windows Git Bash (py -3) as well as Linux/macOS.
#
#   git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
#   bash scripts/final_audit.sh            # writes audit.log in the current directory
#
# The last output is the verdict: the single line READY FOR EVALUATOR, or a
# numbered list of failing items, each with its fix. Exit 0 only when nothing
# fails. FAIL means a real defect. NEEDS HUMAN CHECK items (things a script
# cannot settle: bot-blocked primary sources, mailboxes, dashboards) are listed
# above the verdict and never fail the run.
#
# Optional environment:
#   RNA_BASE_URL        another endpoint (default: rna.config.json)
#   RNA_PARTNER_KEY     pilot key (sent as X-Partner-Key, never printed)
#   WEBSITE_REPO        path to a checkout of Inquiro-Website-: crawl its links too, and run
#                       its layout and UI eval on the live site (needs node and playwright)
#   OLD_RECEIPT         a receipt.json saved before the last sandbox restart; used to
#                       show the ledger_reset answer on the live host
#   AUDIT_LOG           log path (default: ./audit.log)
#   SKIP_LIVE=1         run only the offline sections (0-4)
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
. "$ROOT/scripts/rna_env.sh" || exit 1
LOG="${AUDIT_LOG:-$PWD/audit.log}"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

TMP="$(mktemp -d)"
PASSES=0; FAILS=(); HUMANS=()
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { printf '%s | %s\n' "$(now)" "$*"; }
pass() { log "PASS $*"; PASSES=$((PASSES + 1)); }
# fail WHAT FIX: a real defect. Fails the run; listed in the verdict with its fix.
fail() { log "FAIL $1"; FAILS+=("$1 -- FIX: $2"); }
# human WHAT: a check only a person can make. Listed; does not fail the run.
human() { log "NEEDS HUMAN CHECK $1"; HUMANS+=("$1"); }
section() { echo; echo "=== $* ==="; }
redact() { sed -E 's/(X-Partner-Key: )[^ ]+/\1[REDACTED]/g; s/[A-Za-z0-9+\/]{40,}={0,2}/[REDACTED-B64]/g'; }
SITE="https://inquiroresearchlabs.ai"
OLD_HOST="https://aiflightrecorder.onrender.com"
DEPS="pip install -r requirements.txt, then rerun"

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
if rna_py tests/test_vectors.py >"$TMP/vectors.log" 2>&1; then pass "test vectors: $(tail -1 "$TMP/vectors.log")"; else fail "test vectors" "run python3 tests/test_vectors.py; the lines above name the vector that differs (a verifier regression, not a vector to regenerate)"; tail -20 "$TMP/vectors.log"; fi

section "2. Offline path (keygen, seal, verify, bundle)"
if rna_py -c 'import cryptography' 2>/dev/null; then
  OFF="$TMP/offline"; mkdir -p "$OFF"
  rna_py -m offline keygen --private "$OFF/signer.pem" --public "$OFF/signer.pub" >"$OFF/keygen.log" 2>&1 && pass "keygen" || fail "keygen: $(cat "$OFF/keygen.log")" "run python3 -m offline keygen --private k.pem --public k.pub by hand; $DEPS"
  rna_py scripts/ingest_log.py payloads/tactical_uas/mission.jsonl --ledger "$OFF/receipts.jsonl" --key "$OFF/signer.pem" >"$OFF/ingest.log" 2>&1 && pass "ingest mission.jsonl: $(tail -1 "$OFF/ingest.log")" || fail "ingest: $(cat "$OFF/ingest.log")" "run python3 scripts/ingest_log.py payloads/tactical_uas/mission.jsonl by hand and fix the error it prints"
  out=$(rna_py -m offline verify "$OFF/receipts.jsonl" "$OFF/signer.pub" 2>&1) && pass "offline verify: $out" || fail "offline verify: $out" "offline/verify.py rejects a ledger it just sealed: run python -m pytest tests/test_offline.py"
  out=$(rna_py -m offline bundle --ledger "$OFF/receipts.jsonl" --public "$OFF/signer.pub" --out "$OFF/evaluator_bundle.zip" 2>&1) && pass "bundle: $(echo "$out" | tail -1)" || fail "bundle: $out" "run python3 -m offline bundle by hand (docs/OFFLINE.md) and fix the error it prints"
  # Verify the bundle in an empty directory with an isolated interpreter (-I) and the pure-Python path forced.
  BOX="$TMP/evalbox"; mkdir -p "$BOX"; (cd "$BOX" && rna_py -m zipfile -e "$OFF/evaluator_bundle.zip" .)
  out=$(cd "$BOX/evaluator_bundle" && RNA_VERIFY_PURE=1 rna_py -I verify.py receipts.jsonl public_key.pub 2>&1) && pass "bundle verifies with python -I, pure-Python forced: $out" || fail "bundle verify (pure): $out" "offline/purepy.py disagrees with the native backend: run python -m pytest tests/test_offline.py"
  out=$(cd "$BOX/evaluator_bundle" && rna_py -I verify.py receipts.jsonl public_key.pub 2>&1) && pass "bundle verifies with python -I, default backend: $out" || fail "bundle verify: $out" "the bundled verify.py cannot verify its own ledger: run python -m pytest tests/test_offline.py"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$BOX/evaluator_bundle" && sha256sum -c SHA256SUMS >"$TMP/sums.log" 2>&1) && pass "SHA256SUMS check" || { fail "SHA256SUMS" "offline/bundle.py writes a SHA256SUMS that does not match the files (lines above)"; cat "$TMP/sums.log"; }
  else log "SKIP sha256sum not found"; fi
  rna_py - "$BOX/evaluator_bundle" <<'PY'
import json, sys
d = sys.argv[1]
L = [json.loads(l) for l in open(f"{d}/receipts.jsonl")]
open(f"{d}/deleted.jsonl", "w").write("".join(json.dumps(r, sort_keys=True) + "\n" for i, r in enumerate(L) if i != 5))
L[2]["payload"]["confidence"] = 0.99  # one value changed after sealing, not re-signed
open(f"{d}/tampered.jsonl", "w").write("".join(json.dumps(r, sort_keys=True) + "\n" for r in L))
PY
  if (cd "$BOX/evaluator_bundle" && rna_py -I verify.py tampered.jsonl public_key.pub >"$TMP/t.log" 2>&1); then fail "tampered ledger verified" "real defect: the offline verifier accepts a changed receipt; do not ship until offline/verify.py rejects it"; else pass "tampered ledger rejected: $(sed -n 2p "$TMP/t.log")"; fi
  if (cd "$BOX/evaluator_bundle" && rna_py -I verify.py deleted.jsonl public_key.pub >"$TMP/d.log" 2>&1); then fail "ledger with a deleted receipt verified" "real defect: the offline verifier misses a gap in seq/prev_hash; fix offline/verify.py"; else pass "deleted receipt detected: $(sed -n 2p "$TMP/d.log")"; fi
  if command -v unshare >/dev/null 2>&1 && unshare -rn true 2>/dev/null; then
    out=$(cd "$BOX/evaluator_bundle" && unshare -rn "${RNA_PY[@]}" -I verify.py receipts.jsonl public_key.pub 2>&1) && pass "bundle verifies inside a no-network namespace (unshare -rn)" || fail "no-network verify: $out" "the bundle reaches for the network: find the import or call in the bundled verify.py"
  else log "SKIP unshare not available here (Windows): disable the network adapter and rerun verify.py by hand to prove the offline claim"; fi
else
  fail "offline path needs the cryptography package" "$DEPS"
fi

section "3. Scenario demos reproduce byte-for-byte"
if command -v sha256sum >/dev/null 2>&1 && rna_py -c 'import cryptography' 2>/dev/null; then
  (cd payloads/tactical_uas/demos && find . -type f | sort | xargs sha256sum) > "$TMP/demos_before.txt"
  rna_py scripts/run_scenario.py demo >"$TMP/demo.log" 2>&1 || fail "run_scenario.py demo exited non-zero" "run python3 scripts/run_scenario.py demo and fix the error it prints"
  (cd payloads/tactical_uas/demos && find . -type f | sort | xargs sha256sum) > "$TMP/demos_after.txt"
  if diff "$TMP/demos_before.txt" "$TMP/demos_after.txt" >"$TMP/demos.diff"; then pass "all four demos rebuilt byte-for-byte ($(wc -l < "$TMP/demos_after.txt") files)"; else fail "demo output changed" "inspect git diff payloads/tactical_uas/demos; commit the rebuild only if the change is intended, else git checkout payloads/tactical_uas/demos"; cat "$TMP/demos.diff"; fi
  for d in intact tamper missing_event missing_event_resealed; do
    rna_py scripts/run_scenario.py check "payloads/tactical_uas/demos/$d/receipts.jsonl" payloads/tactical_uas/demo_key/demo_signer.pub >"$TMP/$d.out" 2>&1
    if diff -q "$TMP/$d.out" "payloads/tactical_uas/demos/$d/expected_output.txt" >/dev/null; then pass "demo $d matches expected_output.txt"; else fail "demo $d differs from expected_output.txt" "compare the diff above with payloads/tactical_uas/demos/$d/expected_output.txt; fix the checker, not the expected file"; diff "$TMP/$d.out" "payloads/tactical_uas/demos/$d/expected_output.txt"; fi
  done
else log "SKIP demos (needs sha256sum and cryptography)"; fi

section "4. Old host (Jay finding 1) must not be the documented host"
# These files name the retired host on purpose: the two audit scripts probe it,
# the audit records describe the finding, the link allowlist explains it and its
# test checks it. (grep: the last matching --include/--exclude wins, so the
# excludes go after the includes.)
OLD_HOST_NAMED_ON_PURPOSE=(final_audit.sh smoke_test.sh AUDIT_REPORT.md CLAIMS.md link_allowlist.json test_link_crawl.py)
grep -rIn "aiflightrecorder\.onrender\.com" --exclude-dir=.git --exclude-dir=node_modules \
  --include='*.md' --include='*.py' --include='*.sh' --include='*.json' --include='*.yml' --include='*.js' \
  "${OLD_HOST_NAMED_ON_PURPOSE[@]/#/--exclude=}" . > "$TMP/oldhost.txt" 2>/dev/null
if [ -s "$TMP/oldhost.txt" ]; then
  cat "$TMP/oldhost.txt"
  fail "old host still referenced in this repo: $(cut -d: -f1,2 "$TMP/oldhost.txt" | tr '\n' ' ')" "replace it with the host in rna.config.json (aiflightrecorder-1.onrender.com) at the file:line shown"
else pass "no reference to the old host outside the files that name it on purpose (${OLD_HOST_NAMED_ON_PURPOSE[*]})"; fi
case "$RNA_BASE_URL" in *aiflightrecorder-1.onrender.com*) pass "configured host is the new one" ;; *) log "NOTE configured host is $RNA_BASE_URL" ;; esac

live_sections() {
  code=$(curl -sS -m 30 -o /dev/null -w '%{http_code}' "$OLD_HOST/health" 2>/dev/null || echo 000)
  log "GET $OLD_HOST/health -> $code (informational: the old host is expected to be dead or suspended)"

  section "4b. Deploy freshness: /health must report persistence"
  HEALTH=$(rna_py -c 'import rna_config; print(rna_config.health_url())')
  code=$(curl -sS -m 120 -o "$TMP/health.json" -w '%{http_code}' "$HEALTH" 2>/dev/null) || code=000
  HOST_FRESH=0
  if [ "$code" != "200" ]; then
    fail "GET $HEALTH -> $code (host down or still waking)" "open $HEALTH in a browser and wait for it to answer (the free tier takes about 60 s to wake), then rerun; if it stays down, read the service logs in the Render dashboard"
  elif grep -q '"persistence"' "$TMP/health.json"; then
    HOST_FRESH=1
    pass "/health reports persistence: the live service runs the current pilot build"
    grep -q '"persistence": "ephemeral"' "$TMP/health.json" && log "NOTE /health reports persistence: ephemeral (free tier; ledger resets on restart)"
    grep -q '"persistence": "persistent"' "$TMP/health.json" && log "NOTE /health reports persistence: persistent"
  else
    log "/health answered without a persistence field :: $(head -c 200 "$TMP/health.json")"
    fail "RENDER NOT REDEPLOYED: Manual Deploy latest main, then rerun." "dashboard.render.com > flight-recorder-pilot > Manual Deploy > Deploy latest commit; wait until the deploy shows Live, then rerun this script"
  fi

  if [ "$HOST_FRESH" = 1 ]; then
    section "5. Hosted sandbox journey (smoke_test.sh)"
    SKIP_CRAWL=1 bash scripts/smoke_test.sh > "$TMP/smoke.log" 2>&1; smoke_rc=$?
    redact < "$TMP/smoke.log"
    grep -E '\| FAIL ' "$TMP/smoke.log" | sed -E 's/^.*\| FAIL //' > "$TMP/smoke_fails.txt"
    while IFS= read -r line; do fail "smoke_test.sh: $line" "run bash scripts/smoke_test.sh and read the lines above that FAIL"; done < "$TMP/smoke_fails.txt"
    if [ "$smoke_rc" -eq 0 ]; then pass "smoke_test.sh exit 0"
    elif [ ! -s "$TMP/smoke_fails.txt" ]; then fail "smoke_test.sh exit $smoke_rc with no FAIL line" "run bash scripts/smoke_test.sh by hand; it stopped before reporting"; fi

    section "6. Live host details (notice, scope, ledger reset)"
    curl -sS -m 60 -o "$TMP/init.json" -X POST "$RNA_BASE_URL" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{}}' 2>/dev/null
    grep -q 'synthetic data only' "$TMP/init.json" && pass "keyless initialize returns the sandbox notice" || fail "sandbox notice missing from initialize :: $(head -c 200 "$TMP/init.json")" "redeploy AIFlightRecorder main on Render (the notice ships in pilot/pilot_mcp_server.py)"
    curl -sS -m 60 -o "$TMP/scope.json" -X POST "$RNA_BASE_URL" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"verify_chain_segment","arguments":{}}}' 2>/dev/null
    if [ -n "${RNA_PARTNER_KEY:-}" ]; then log "NOTE pilot key set; skipping the keyless-scope check"; else
      grep -q 'pilot_key_required' "$TMP/scope.json" && pass "keyless verify_chain_segment answers -32001 pilot_key_required" || fail "keyless scope error not as documented :: $(head -c 200 "$TMP/scope.json")" "redeploy AIFlightRecorder main on Render; if it persists, compare with pilot/README.md (public sandbox scope)"; fi
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
      [ $? -eq 0 ] && pass "old receipt: server answers valid or reason ledger_reset (never a tamper verdict)" || fail "old receipt lookup gave an unexpected answer" "check ledger_was_reset in AIFlightRecorder pilot/pilot_mcp_server.py against the receipt's sealed_at"
      out=$(rna_py verifier/verify.py "$OLD_RECEIPT" 2>&1) && pass "old receipt still verifies offline from receipt_body: $out" || fail "old receipt offline verify: $out" "run python3 verifier/verify.py $OLD_RECEIPT and compare with docs/RECEIPT_ANATOMY.md"
    else
      human "ledger_reset after a fresh container: set OLD_RECEIPT=<receipt.json saved before the last restart> and rerun, or restart the Render service and look up a receipt saved before it (expected: reason ledger_reset, chain_intact null)"
    fi
  else
    log "SKIP sections 5-6: the host is not serving the current build, so their results would describe the old one"
  fi

  section "7. Live site claims (website)"
  STALE_SITE="if website main is clean (npm run check:claims), the live site is stale: GitHub > Inquiro-Website- > Actions > deploy > Run workflow on main, then rerun"
  fetch() { curl -sS -m 30 -L -o "$2" "$1" 2>/dev/null; }
  fetch "$SITE/" "$TMP/home.html"; fetch "$SITE/proving-ground/" "$TMP/pg.html"; fetch "$SITE/developers/" "$TMP/dev.html"
  fetch "$SITE/company/" "$TMP/company.html"; fetch "$SITE/llms.txt" "$TMP/llms.txt"; fetch "$SITE/llms-full.txt" "$TMP/llmsfull.txt"
  fetch "$SITE/.well-known/security.txt" "$TMP/security.txt"; fetch "$SITE/rna/" "$TMP/rna.html"; fetch "$SITE/regulatory-timeline/" "$TMP/reg.html"
  fetch "$SITE/rna/compare/" "$TMP/compare.html"; fetch "$SITE/compliance/" "$TMP/compliance.html"
  fetch "$SITE/compliance/fre-901/" "$TMP/comp_fre.html"; fetch "$SITE/compliance/dod-3000-09/" "$TMP/comp_dod.html"
  fetch "$SITE/compliance/faa-part-108/" "$TMP/comp_faa.html"; fetch "$SITE/compliance/eu-ai-act-article-12/" "$TMP/comp_eu.html"
  if [ ! -s "$TMP/pg.html" ]; then fail "could not fetch the live site" "open $SITE/proving-ground/ in a browser; if it is down, check the Cloudflare dashboard, then rerun"; else
    # "under USPTO examination" is not banned here: it is the owner-approved
    # patent sentence on /rna/ (counsel item; see counsel/COUNSEL_REVIEW.md).
    # The /compliance/ hub and its four pages are scanned like the rest: each is linked from
    # /regulatory-timeline/, and each must carry the approved sentence (docs/LEGAL_LANGUAGE.md)
    # and none of the overclaims the website claims lint bans.
    hits=0; scanned=0
    for f in home pg dev company rna reg compare compliance comp_fre comp_dod comp_faa comp_eu llms llmsfull; do
      [ -f "$TMP/$f.html" ] && page="$TMP/$f.html" || page="$TMP/$f.txt"
      scanned=$((scanned + 1))
      for phrase in "in production" "Courts admit" "court-admissible" "tamper-proof" "unhackable" "immutable" "Verify any AI output" "every claim has a demonstration" "1.6 seconds" "built to comply" "complies" "compliant" "guarantee" "certified" "constant time" "satisfy" "satisfies" "compliance challenge" "Role in compliance" "No alteration is possible" "cannot be altered"; do
        grep -qi "$phrase" "$page" && { fail "live $f still says: $phrase" "$STALE_SITE"; hits=$((hits + 1)); }; done
    done
    [ "$hits" -eq 0 ] && pass "banned phrases absent from $scanned live pages and text files (incl. /compliance/ and its four pages, llms.txt, llms-full.txt)"
    missing=0
    for f in compliance comp_fre comp_dod comp_faa comp_eu; do
      grep -q "does not by itself establish compliance or admissibility" "$TMP/$f.html" || { fail "live $f lacks the approved legal sentence" "$STALE_SITE"; missing=$((missing + 1)); }; done
    [ "$missing" -eq 0 ] && pass "approved legal sentence present on the live /compliance/ hub and its four pages"
    grep -q "aiflightrecorder-1.onrender.com" "$TMP/dev.html" && pass "live /developers/ names the new host" || fail "live /developers/ does not name the new host" "$STALE_SITE"
    grep -q '"persistence": "ephemeral"' "$TMP/dev.html" && pass "live /developers/ carries the temporary-ledger note" || log "PENDING temporary-ledger note not live yet"
    grep -qi "not production systems" "$TMP/pg.html" && pass "live proving ground says: not production systems" || fail "live proving ground lacks the status line" "$STALE_SITE"
    grep -qi "Not yet validated against real outcomes" "$TMP/pg.html" && pass "live proving ground says: Not yet validated against real outcomes" || fail "live proving ground lacks the validation disclaimer" "$STALE_SITE"
    grep -qi "patent pending\|patent-pending\|patented\|patent granted" "$TMP/rna.html" && fail "live /rna/ uses banned patent wording (patent pending / patented / patent granted)" "restore the owner-approved sentence on rna/index.html; $STALE_SITE" || pass "live /rna/ patent wording is the owner-approved phrase or absent"
    grep -qi "not production systems" "$TMP/rna.html" && pass "live /rna/ carries the status line" || fail "live /rna/ lacks the status line" "$STALE_SITE"
    grep -q 'id="status"' "$TMP/reg.html" && pass "live /regulatory-timeline/ has the status and sources section" || log "PENDING regulatory status section not live yet"
    for p in llms.txt llmsfull.txt security.txt; do [ -s "$TMP/$p" ] && pass "live $p reachable" || fail "live $p missing" "$STALE_SITE"; done
    for u in /developers/sandbox/ /receipt-experience/; do code=$(curl -sS -m 30 -o /dev/null -w '%{http_code}' "$SITE$u" 2>/dev/null || echo 000); case "$code" in 301|302|308|200) pass "$u -> $code (redirect or page, not 404)";; *) fail "$u -> $code" "restore the redirect for $u in the website _redirects file; $STALE_SITE";; esac; done
  fi

  section "7b. Layout and UI eval (live site in Chromium: Inquiro-Website- scripts/ui-eval.mjs)"
  if [ ! -s "$TMP/pg.html" ]; then
    log "SKIP UI eval: the live site did not load (section 7 already fails for that)"
  elif [ -z "${WEBSITE_REPO:-}" ] || ! command -v node >/dev/null 2>&1; then
    human "UI eval not run: it needs node and WEBSITE_REPO=../Inquiro-Website- (renders every public page at 390, 820 and 1440 px)"
  else
    (cd "$WEBSITE_REPO" && node scripts/ui-eval.mjs --base "$SITE" --out "$TMP/ui") > "$TMP/ui.log" 2>&1; ui_rc=$?
    grep -E '^(FAIL|WARN) ' "$TMP/ui.log"
    grep '^FAIL ' "$TMP/ui.log" > "$TMP/ui_fails.txt"
    while IFS= read -r line; do fail "ui: ${line#FAIL }" "fix that page's layout in Inquiro-Website- (npm run eval:ui shows it locally; screenshots in $TMP/ui); $STALE_SITE"; done < "$TMP/ui_fails.txt"
    while IFS= read -r line; do human "ui: ${line#WARN }"; done < <(grep '^WARN ' "$TMP/ui.log")
    if [ "$ui_rc" -eq 2 ]; then human "UI eval not run: in $WEBSITE_REPO run npm ci && npm i --no-save playwright@1.56.1 && npx playwright install chromium, then rerun"
    elif [ "$ui_rc" -eq 0 ]; then pass "UI eval: $(tail -1 "$TMP/ui.log" | sed 's/ Screenshots.*//') (screenshots in $TMP/ui)"
    elif [ ! -s "$TMP/ui_fails.txt" ]; then fail "ui-eval.mjs exit $ui_rc with no FAIL line" "run node scripts/ui-eval.mjs --base $SITE in $WEBSITE_REPO and read its error"; fi
  fi

  section "8. Link crawl"
  if [ -n "${WEBSITE_REPO:-}" ]; then rna_py scripts/link_crawl.py --website "$WEBSITE_REPO" > "$TMP/crawl.log" 2>&1; else rna_py scripts/link_crawl.py > "$TMP/crawl.log" 2>&1; fi
  crawl_rc=$?; grep -E "^(FAIL|NEEDS HUMAN CHECK)|^link crawl" "$TMP/crawl.log"
  grep '^FAIL' "$TMP/crawl.log" > "$TMP/crawl_fails.txt"
  while IFS= read -r line; do fail "link: ${line#FAIL  }" "fix or remove the link at the source shown; if it is deliberate or the site blocks bots, add its prefix and the reason to scripts/link_allowlist.json"; done < "$TMP/crawl_fails.txt"
  # The reason for each one is printed after "::" on its line.
  while IFS= read -r line; do human "link: ${line#NEEDS HUMAN CHECK  }"; done < <(grep '^NEEDS HUMAN CHECK' "$TMP/crawl.log")
  if [ "$crawl_rc" -eq 0 ]; then pass "link crawl: no failing URL$([ -z "${WEBSITE_REPO:-}" ] && echo ' (SDK only; set WEBSITE_REPO to include the site)')"
  elif [ ! -s "$TMP/crawl_fails.txt" ]; then fail "link_crawl.py exit $crawl_rc with no FAIL line" "run python3 scripts/link_crawl.py by hand; it stopped before reporting"; fi
}

if [ "${SKIP_LIVE:-0}" = "1" ]; then
  log "SKIP live sections 4b-8 (SKIP_LIVE=1)"
else
  live_sections
fi

section "9. Items that need a human"
human "Mailbox: send a test message to the SECURITY.md address and to the .well-known/security.txt address and confirm both are read"
human "Render dashboard: confirm the live service is the hardened pilot image and whether a persistent disk is mounted (plan, /var/data)"
human "Starcloud sibling demos (starcloud1.northstaraokeystone.com) are an external site: open each linked scenario and confirm it loads"
log "Step-by-step instructions for every human item: HUMAN_ACTIONS.md"

section "Summary: $PASSES pass, ${#FAILS[@]} fail, ${#HUMANS[@]} need a human. Temp files in $TMP (no keys written)."
if [ "${#HUMANS[@]}" -gt 0 ]; then
  echo "NEEDS HUMAN CHECK (listed for the record; these do not fail the run):"
  for h in "${HUMANS[@]}"; do echo "  - $h"; done
fi
echo "Log: $LOG"
echo
if [ "${#FAILS[@]}" -eq 0 ]; then
  if [ "${SKIP_LIVE:-0}" = "1" ]; then echo "OFFLINE SECTIONS PASS (SKIP_LIVE=1: live sections not run, so no evaluator verdict yet)"
  else echo "READY FOR EVALUATOR"; fi
  exit 0
fi
echo "NOT READY: ${#FAILS[@]} failing item(s), each with its fix:"
i=0; for f in "${FAILS[@]}"; do i=$((i + 1)); echo "$i. $f"; done
exit 1
