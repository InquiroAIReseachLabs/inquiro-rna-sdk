# Final independent audit, 17 October 2026

**Scope.** `inquiro-rna-sdk`, `AIFlightRecorder` (pilot only; core `src/` read-only) and `Inquiro-Website-`, audited after PRs inquiro-rna-sdk#9, #10, #11, AIFlightRecorder#52 and Inquiro-Website-#436 merged (all five confirmed merged on GitHub; audited at `main` = `728ad44`, `5c018a5`, `a095b66`). Branch `audit/final-oct16` in each repository carries the fixes. Nothing was pushed to `main`.

**Method.** Fresh clones from GitHub into an empty directory. Every claim in the PR descriptions was re-run rather than read. Live hosts (`aiflightrecorder-1.onrender.com`, `inquiroresearchlabs.ai`, the old Render host, Starcloud, every regulatory primary source) were **unreachable from the audit sandbox** (egress proxy denies them), and there is **no Docker daemon** here. Where that blocks a check, the row says so and `scripts/final_audit.sh` carries the check for Matthew to run from Windows Git Bash. A separate fresh subagent re-verified the PASS rows below (its discrepancies are folded in). Keys are redacted throughout.

**Companion files.** `CLAIMS.md` (claims audit), `docs/THREAT_MODEL.md`, `docs/TEST_VECTORS.md` + `tests/test_vectors.py`, `docs/WINDOWS.md`, `scripts/final_audit.sh` (this repository); `docs/CLAIMS_INVENTORY_2026_10_17.md`, `scripts/claims-lint.mjs`, `data/claims-allowlist.json` (website); `SECURITY.md`, `.dockerignore` (flight recorder).

---

## Part 1. Fix verification

Mapping assumptions (the brief's labels are not in the repositories): "Jay findings 1-3" are the three findings named in the description of inquiro-rna-sdk#9; "Patches A-E" are that PR's five change bullets; "Phase 1 gaps a-e" are the rows of `pilot/GAP_ANALYSIS.md` and "f-i" the four further commits of AIFlightRecorder#51; "Phase 2 items 1-7" are the seven bullets of inquiro-rna-sdk#11; "free-tier items" are the four bullets of AIFlightRecorder#52 plus its CI image assertion.

| Item | Expected | Found | Evidence (command, output) | Result |
|---|---|---|---|---|
| **Jay 1** old host 503 | No reference to `aiflightrecorder.onrender.com`; default host in one place | One reference left, in the pinned attorney report (`Inquiro-Website-/legal/attorney-report-2026-05-07.md`, a historical document). Default host in `rna.config.json`; 8 references all to `aiflightrecorder-1` | `grep -rIn "aiflightrecorder\.onrender\.com" --exclude-dir=.git .` → 4 hits, all `legal/attorney-report-2026-05-07.md`; `grep -rIoh "https\?://[a-z0-9.-]*onrender\.com" \| sort \| uniq -c` → `8 aiflightrecorder-1.onrender.com/mcp`, `1 aiflightrecorder.onrender.com/mcp` (the report) | PASS (repo). Live 503 not retestable here: `final_audit.sh` section 4 |
| **Jay 2** 404s | No dead links | Internal: 392 links resolve (now 393). Found dead: `docs/PRODUCTION.md:18` → `.github/workflows/verify-receipts.yml` (file absent); `regulatory-timeline` TOC `#status` with no section; `docs/email/post-pilot.md` → `/developers/sandbox/` (route removed, 301 only). External URLs: 257 of 285 blocked by the sandbox proxy, 12 pass (github.com) | `npm run check:dead-links` → `PASS: 392 internal links`; `python3 scripts/link_crawl.py --website ../Inquiro-Website-` → `PASS=12 WARN=0 BLOCKED=0 FAIL=257` (every FAIL is `Tunnel connection failed: 403`); `ls .github/workflows/` → `ci.yml health-check.yml verify-receipts-live-cron.yml` | FAIL (3 found, all fixed on branch). External crawl: `final_audit.sh` section 8 |
| **Jay 3** overclaiming | README hedged; website no "in production", "courts admit", "verify any AI output" | SDK README hedge present. Website proving ground carries "not production systems" and the validation disclaimer on 4 of 7 cards. Residual overclaims found: "every claim has a demonstration", "In 1.6 seconds", LIVE chips on an external site, "immutable by construction", "constant time", "Zero data retention", "no trust required", "AI Output Verification", "pilot production tier" signed receipts (SDK), "immutable audit trail" (pilot README), "commercial products" (Academy FAQ), capstones "signed ... verify independently" (HMAC, not a signature) | `grep -rIn -i -E "receipts in production\|courts admit\|verify any AI output\|tamper-proof"` on public files → none outside docs/tests; the residuals are rows W2-W8, W12-W22, S6, F1-F2 of `CLAIMS.md` with file:line | FAIL (residuals; all fixed on branch except protected files, listed in `CLAIMS.md` section 4) |
| **Patch A** one endpoint setting | `rna.config.json` + `RNA_BASE_URL` honoured everywhere | `rna_config.py`, `rna_env.sh`, `first_receipt.py`, `verify.py`, curl examples, Node example, devcontainer, both workflows read it | `grep -rln "rna_config\|RNA_BASE_URL\|rna.config.json"` → 14 files; `RNA_BASE_URL=http://127.0.0.1:18080/mcp python3 scripts/first_receipt.py` → `Endpoint: http://127.0.0.1:18080/mcp` | PASS |
| **Patch B** working quickstart | `first_receipt.py` wraps the payload, fresh timestamp, `accepted: true`, position increases | Against a locally run pilot server: `accepted: True`, `chain_position: 10` then `15`, `verify_receipt: valid=True` | Part 2b transcript | PASS (local server; live host via `final_audit.sh` section 5) |
| **Patch C** `verify.py` | Offline recompute from `receipt_body`; labelled server check without a body; mock recompute | `VERIFIED (offline): ... binds the payload`; body stripped → `NOT ON LEDGER (server-side, ...)` after reset, `VERIFIED (server-side ...)` before; CI mock steps unchanged | Part 2b; `tests/test_vectors.py::test_live_verifier_recomputes_a_receipt_body_with_the_live_rule` | PASS |
| **Patch D** cross-platform Python | `rna_env.sh` tries `python3`, `python`, `py -3`; Windows note | Code does so; README has the note. Not executed on Windows. The 0600 private-key claim does not hold on Windows | `sed -n 12,24p scripts/rna_env.sh`; `docs/WINDOWS.md` (new) | PASS by inspection, UNTESTED on Windows |
| **Patch E** docs and CI | Endpoint table, dead badge gone, daily `health-check.yml`, live cron with tamper test, smoke test, link crawler | All present; `health-check.yml` fails on non-200; cron submits five event types and runs a one-character tamper test | `cat .github/workflows/health-check.yml` (exit 1 on `code != 200`); `verify-receipts-live-cron.yml` lines 38-56; `bash scripts/smoke_test.sh` sections 1-7 PASS against the local server | PASS |
| **Phase 1 a** rejection reasons | `reason` + `missing_fields` | Present and whitelisted by the sanitizer | `pytest pilot/test_harness/test_gap_fixes.py::TestRejectionReasons` 4 passed; local server returned `missing_fields` | PASS |
| **Phase 1 b** ledger lost on restart | Persistent disk path; writable check; loud fallback | `RECEIPTS_FILE=/var/data/receipts.jsonl`, `LEDGER_REQUIRES_MOUNT=1`; fallback warning observed | Server log: `WARNING: ledger ... is ephemeral ... Mount a persistent disk`; `render.yaml` disk block | PASS (code). Disk on the live service: human check |
| **Phase 1 c** offline recompute | `receipt_body`, `attestation_payload_hash` | Both present; tamper to hash, body or payload each fails | `TestReceiptBody` 4 passed; Part 2b b.4 | PASS |
| **Phase 1 d** deleted/reordered receipts | `tenant_seq`, `prev_attestation_hash`, segment check | Detects delete, reorder, rewrite within a segment; tail truncation not detectable (documented) | `TestTenantChain` 5 passed | PASS |
| **Phase 1 e** public tenant blocked by generic error | `-32001` with `pilot_key_required` | Observed | Part 2b b.5: `{"code": -32001, "data": {"reason": "pilot_key_required"}}` | PASS |
| **Phase 1 f** persistent ledger path, restart-safe segments | Boot receipts under other tenants are infrastructure | `test_ledger_persistence.py` passes | `pytest pilot/test_harness -q` → 150 passed | PASS |
| **Phase 1 g** explicit public sandbox tenant, file-name check | `demo_public_001` marked `public_sandbox`; tenant id must match file name | Both enforced | `TestPublicSandbox` 6 passed; `TestTenantFileName` 1 passed | PASS |
| **Phase 1 h** tenant template, `new_tenant.sh`, ONBOARDING | New tenant passes with no code change | 411 passed, 13 skipped (Docker-only) with `audit_check_001` | Part 2d | PASS |
| **Phase 1 i** placeholder-key warnings, every tenant runs the suite | No break on `CONFIGURE_BEFORE_PILOT` | `TestNewTenantScript` 5 passed; suite iterates tenants | `pytest pilot/test_harness/test_tenant_onboarding.py` | PASS |
| **Phase 2 (1)** offline kit | Seal, chain, sign, verify with no network | Done under `unshare -rn` | Part 2a | PASS |
| **Phase 2 (2)** evaluator bundle | One zip, standalone verifier, pure-Python fallback, `SHA256SUMS` | Verified with `python3 -I`, `RNA_VERIFY_PURE=1`; sums check | Part 2a | PASS |
| **Phase 2 (3)** scenario pack | Nine events, no weapon events, four demos with expected outputs | Present; demos byte-for-byte | Part 2c; `grep -il "weapon\|engag" payloads/tactical_uas/*.json` → none | PASS |
| **Phase 2 (4)** post-flight ingest | CSV or JSONL to sealed chain | `ingest_log.py mission.jsonl` → 9 receipts; CSV path covered by `tests/test_scenario.py` | Part 2a | PASS |
| **Phase 2 (5)** SWaP benchmark | Numbers reproducible in order of magnitude | 7,073 seal/s, 5,287 verify/s, 132 pure-Python verify/s, 32.7 MB here vs 9,867 / 5,893 / 168 / 38 MB in the doc | `python3 scripts/benchmark.py --count 2000` | PASS (different CPU; doc says measure on target) |
| **Phase 2 (6)** offline bundle is the primary demo | README leads with it | It does (README.md:19) | `sed -n 19,45p README.md` | PASS |
| **Phase 2 (7)** sandbox hardening | Notice in README, `sealed_at` sent, `warmup.sh` | All three observed | `grep -n sealed_at verifier/verify.py` → line 114; `bash scripts/warmup.sh` output | PASS |
| **Free tier 1** reset-aware lookups | `reason: ledger_reset`, `chain_intact: null`, never tamper | Observed with and without `sealed_at`, and after new traffic | Part 2b b.7 | PASS |
| **Free tier 2** persistence field | On `/health` and public tool responses | On `/health` and `verify_receipt`; not on `initialize` (documented as "sandbox tool responses") | Part 2b b.1, b.1b | PASS |
| **Free tier 3** sandbox notice | In keyless `initialize` `instructions`, README, ONBOARDING | Present | Part 2b b.1b; `grep -n "synthetic data" pilot/README.md pilot/ONBOARDING.md` | PASS |
| **Free tier 4** hash-only finding | Documented, no native digest submission | `pilot/HASH_ONLY_MODE.md` present; not implemented (proposal) | file read | PASS (as documented; feature is ROADMAP) |
| **Free tier 5** CI image job asserts `persistent` on a volume | Docker job | Workflow present; cannot run here | `.github/workflows/ci.yml` lines 48-72 | UNVERIFIED (no Docker daemon); rerun in Actions |

## Part 2. End-to-end runs, clean room

Fresh clones (`git clone` from GitHub into an empty scratch directory), no caches, `pip install -r requirements.txt` only.

**a. Offline path, networking disabled (Linux).** Inside `unshare -rn` (a socket to 1.1.1.1:53 fails with `Network is unreachable`): `keygen` → key id written; two `seal`s; `verify` → `VERIFIED: 2 receipts, chain intact`; `bundle` → zip; README path `ingest_log.py mission.jsonl --keygen` → `sealed 9 receipts (seq 1-9)`; bundle extracted into an empty directory and verified with `python3 -I` and `RNA_VERIFY_PURE=1` (backend reported `pure-Python`) → `VERIFIED: 9 receipts`; `sha256sum -c SHA256SUMS` → 5 OK; one value changed after sealing → `FAILED: 2 problem(s)` naming seq 3. Windows steps and the steps that fail: `docs/WINDOWS.md` (0600 key permission does not apply; no `unshare`; no `unzip`; PowerShell quoting). Not executed on Windows.

**b. Hosted sandbox (local pilot server standing in for the unreachable Render host).** `pilot_mcp_server.py --http --port 18080` with `LEDGER_REQUIRES_MOUNT=1`: `warmup.sh` → `HTTP 200 in 0.001s`, persistence `ephemeral`, note printed; keyless `initialize` → sandbox notice; `first_receipt.py` twice → `chain_position 10 → 15`, `verify_receipt valid=True`; `verify.py` → `VERIFIED (offline) ... binds the payload`; one-byte tamper of hash, of body, of payload → three `FAILED (offline)`; `verify_chain_segment` keyless → `-32001 pilot_key_required`; server-side `verify_receipt` → `valid: true, chain_intact: true`. Fresh container: server killed, ledger file deleted, server restarted; lookup of the earlier receipt → `valid: false, chain_intact: null, reason: ledger_reset` with and without `sealed_at`, and still after a new receipt was sealed; the saved file still `VERIFIED (offline)`; with `receipt_body` stripped, `verify.py` → `NOT ON LEDGER (server-side ...) Not a sign of tampering`, exit 1. `smoke_test.sh` sections 1-7 all PASS; sections 8-9 fail only because the website and external hosts are unreachable from here.

**c. Scenario demos.** `sha256sum` of the 9 files under `payloads/tactical_uas/demos/` before and after `run_scenario.py demo`: identical. Each demo's `check` output equals its `expected_output.txt`.

**d. New tenant from `_template.json`.** `bash pilot/scripts/new_tenant.sh audit_check_001 "Audit Check"` → file created, env var names printed, no key material; `pytest pilot/tests pilot/test_harness -q` → `411 passed, 13 skipped` (the 13 need Docker); 45 tests ran against the new tenant specifically.

**e. Container audit (static; no daemon).** Simulating Docker's `.dockerignore` rules on the repository: the build context held **94 files**, including `pilot/tests/` (deleted later by the Dockerfile), `pilot/test_harness/` (14 files, shipped in the image), `pilot/output/partner_kit.zip`, `pilot/GAP_ANALYSIS.md`, `pilot/HASH_ONLY_MODE.md` and local `__pycache__`. No credential-shaped string, private key or `.env` in the context (`grep` over 14 patterns). The nine approved `src/` modules are copied and compiled to `.pyc`, then the `.py` files are deleted: "no core source" is true of source text, not of core code (bytecode is in the image). `.dockerignore` tightened on the branch: **40 files**; `pilot/tests/test_container_audit.py` 23 passed, 13 skipped. `pilot/internal/pilot_config.json` names a tenant `pilot_walling_001`: if that is a real partner identifier it is in the public repository and the image (human check). The root `docker-compose.yml` / `Dockerfile.edge` / `Dockerfile.ground` share this `.dockerignore` and so cannot see the files they `COPY` (pre-existing; outside pilot scope).

**f. Known-answer vectors.** `docs/TEST_VECTORS.md`: SHA-256 and BLAKE3 for five inputs (empty, `abc`, the fox sentence, 1024 and 1025 bytes to cross the BLAKE3 chunk boundary), the three RFC 8032 Ed25519 vectors with the derived `key_id`, both canonical-JSON rules on one object, and a deterministic two-receipt offline ledger. `tests/test_vectors.py`: 12 pass natively and with `RNA_VERIFY_PURE=1`; a copy with one BLAKE3 digit changed fails 3 tests; a test also fails if the document lists a hex value the test file does not assert.

**g. `scripts/final_audit.sh`.** Extends `smoke_test.sh`: environment, vectors, offline path, bundle under `python -I` + pure backend, tamper and deletion, `unshare` when available, demos byte-for-byte, old-host check, `smoke_test.sh`, live-host persistence/notice/scope, `OLD_RECEIPT` reset probe, live-site phrase checks, link crawl, and a HUMAN list; writes `audit.log`, redacts keys. Offline sections run here: `16 pass, 0 fail`. Live sections await a machine that can reach the hosts. Git Bash notes: uses `mktemp`, `sha256sum`, `python -m zipfile`; skips `unshare` with a note.

## Part 3. Claims audit

See `CLAIMS.md` (47 classified rows across the three repositories, protected-surface before/after table, external list) and the website's `docs/CLAIMS_INVENTORY_2026_10_17.md` (409 occurrences, 19 cross-surface inconsistencies).

**b. Wording fixed on `audit/final-oct16`** (website unless noted): prototype vs production (llms.txt status line; "Live work", "LIVE" chips, "commercial products"); legal/compliance hedges (llms.txt, llms-full.txt, company, compliance hub, `index.html` JSON-LD "DoD 3000.09 Compliance"; FAA Part 108 as rulemaking); append-only/tamper claims ("immutable by construction", "constant time", "breaks the chain instantly", pilot README "immutable audit trail"); "verify" on scoring demos (renamed to scoring; disclaimer on all seven cards); hard-coded verdicts (genesis stamp and fake BLAKE3 row, Academy receipt banner/anchor, deploy header, two Inquiry simulations labelled); "without trusting Inquiro" (trusted-key caveat on every editable occurrence, 17 edits); unsupported specifics ("1.6 seconds" twice, "every claim has a demonstration" twice, "three verticals", "four cross-site Live Demonstrations", "in the browser"); SDK README "pilot production tier" signing claim, stale SECURITY_REVIEW rows, dead workflow link, removed sandbox route in the email template. **Everything legal/compliance is marked for counsel review** in `CLAIMS.md`.

**c. Not edited (protected or external):** `tests/do-not-touch.manifest.json` files (`.well-known/*.json`, `security.txt`, `academy/agreement/*`, Codex labs and `codex.html`, `legal/*`, Worker `src/*`, `verifier/*`, `verify/*.js`), CODEOWNERS files, `shop/index.html` (unlisted, Gumroad-linked), the pinned attorney report, Gumroad/LinkedIn/X/decks, Starcloud. Exact before/after text: `CLAIMS.md` section 4. One edit I had made to `.well-known/rna-spec.json` was reverted when the manifest test caught it. Patent wording was left verbatim per `docs/portfolio/OWNER_DECISIONS.md` section 2 (the site also bans "patent pending"); it is a counsel item.

**d. Regulatory dates and penalties, as of 17 October 2026.** No primary source was reachable from the sandbox (DNS blocked), so every row is NEEDS HUMAN CHECK; the statements below are from the auditor's knowledge and must be confirmed against the URL before any date or penalty appears on a public surface. The site states no deadlines or penalty amounts; the new status section on `/regulatory-timeline/#status` links these sources and says so.

| Framework | Statement to confirm | Primary source | Status |
|---|---|---|---|
| FRE 901(b)(9) | In force; rule of evidence (restyled 2011); no penalties | https://www.law.cornell.edu/rules/fre/rule_901 and https://www.uscourts.gov/rules-policies/current-rules-practice-procedure/federal-rules-evidence | NEEDS HUMAN CHECK |
| DoD Directive 3000.09 | "Autonomy in Weapon Systems", reissued 25 January 2023; internal policy, no civil penalties | https://www.esd.whs.mil/Portals/54/Documents/DD/issuances/dodd/300009p.pdf | NEEDS HUMAN CHECK |
| FAA Part 108 | Proposed rule (NPRM, Federal Register, August 2025) for routine BVLOS; **whether a final rule has published, and its effective date, is unknown to this audit** | https://www.federalregister.gov/ (search "Part 108" BVLOS); https://www.faa.gov/uas/advanced_operations/beyond_visual_line_of_sight | NEEDS HUMAN CHECK (highest priority: the compliance page previously said Part 108 "governs") |
| EU AI Act Article 12 | Regulation (EU) 2024/1689; in force 1 August 2024; high-risk obligations (Annex III) apply from 2 August 2026 per Article 113 unless amended (a 2025 "digital omnibus" proposal to delay was under discussion); penalties Article 99: up to EUR 35 million or 7 % of worldwide turnover for prohibited practices, up to EUR 15 million or 3 % for other obligations | https://eur-lex.europa.eu/eli/reg/2024/1689/oj | NEEDS HUMAN CHECK (confirm whether the Article 113 dates were amended) |

**e. Claims lint in website CI.** `scripts/claims-lint.mjs` fails on banned phrases ("in production", "courts admit", "court-admissible", "guarantee", "compliant" unless allowlisted, "immutable", "tamper-proof", "constant time", "every claim has a demonstration", "SLA", "no trust required" and others) and on hard-coded verdict literals in static copy (`CHAIN VERIFIED`, `VERIFIED`, `chain_intact … true`, `"valid": true`, `signature_valid`, `GREEN/YELLOW/RED`, `PASS/INTACT`). Allowlist `data/claims-allowlist.json` (file-scoped verdict entries, a reason on every line, stale entries fail a test). Wired into `npm test` (`tests/claims_lint.test.ts`), `npm run check:claims`, the `preflight` script and `.github/workflows/preflight.yml` with a fix-guidance comment. Result on the branch: clean across 58 files; `npm test` 497/497; `check:standards`, `check:dead-links`, `typecheck`, `wrangler deploy --dry-run` pass.

## Part 4. Evaluator readiness

- **Threat model and limitations:** `docs/THREAT_MODEL.md` (detectable vs not; trusted key, software, canonicalization, time; key custody; replay; ledger-rewrite caveat; roadmap for signed checkpoints, server-side signatures, hosted hash links, trusted time, key rotation). Linked from the README.
- **Pinned dependencies and lockfiles:** SDK `requirements.txt` now `blake3==1.0.8`, `cryptography==42.0.8`; `examples/python/requirements.txt` pinned; `mock/requirements.txt` already pinned; `verifier/package-lock.json` and `examples/go/go.sum` present; `examples/nodejs/package.json` uses `^1.3.3` with no lockfile (LOW). Flight recorder: `pilot/requirements.txt` fully pinned; root `requirements.txt` now pinned. Website: `package-lock.json` present, `npm ci` used in CI; `package.json` ranges are caret (normal with a lockfile); workflow actions are tag-pinned (`@v7`), not SHA-pinned, and `trufflesecurity/trufflehog@main` is unpinned (LOW). SDK and flight recorder workflows are SHA-pinned.
- **Public-repo hygiene scan** (14 secret patterns, private-key files, profanity, phone numbers and personal mailboxes, company names, internal notes): no credentials, no profanity, no personal data. Findings: `Inquiro-Website-/.env.example` contains `PARTNER_KEY_DEMO_PUBLIC=a8b8…f0ff` (32 hex, key-shaped, committed 2026-06-24). The pilot server reads every `PARTNER_KEY_*` variable and derives the tenant id from the suffix (`pilot/config_loader.py:428-433`), so if this value were set on a deployment it would be accepted as a key for a tenant `demo_public` that has no config file; rotate it if it was ever live. Redacted here, left in place for the owner to decide. `Inquiro-Website-/scripts/indexnow-submit.mjs:40` holds a 32-hex IndexNow key (`f5d5…e2bc`), public by design (served at `/<key>.txt`) but a scanner will flag it; `tests/geo_probe.test.ts:103` holds an obviously fake key; the SDK tracks `payloads/tactical_uas/demo_key/demo_signer.pem` by design (its README says it proves nothing). `AIFlightRecorder` is a public repository whose root holds `AI_FLIGHT_RECORDER_CODE_EXTRACTION_v1.md` ("Ready for Patent Attorney Review"), `Receipts native architecture v2.0.txt`, `spec.md`, `CLAUDEME.md`, `sim/`, `demo/` and `benchmark_pitch.py`, and `pilot/internal/pilot_config.json` names `pilot_walling_001`: counsel and owner decision. Website `schema_diagram.html` (Academy KV schema) is publicly served with no `noindex`. Defense-contractor names in the gov-os demo are synthetic scenario vendors (`src/domains/gov-os/scenarios.ts`), labelled as such.
- **SECURITY.md contact:** the SDK says `security@inquiroresearchlabs.ai`; `.well-known/security.txt`, `agents.json`, `ai-catalog.json` and the legal pages say `contact@`; `academy/genesis` says `inquiro@`. The flight recorder had no `SECURITY.md` (added, same address as the SDK). **Whether any of the three mailboxes is read could not be tested from here** (no DNS, no SMTP): human check.
- **License posture:** SDK is MIT (`LICENSE`, 2026, Inquiro AI Research Labs Inc.); the website states a non-provisional patent under USPTO examination and the flight recorder repository publishes patent-extraction material. An MIT grant covers copyright, not patents, and the SDK offline kit implements the receipt scheme the patent describes. **Flagged for counsel; not changed.**

## Findings

| # | Item | Severity | Status | Evidence |
|---|---|---|---|---|
| 1 | Hosted sandbox receipts are not signed; SDK README said signed/Merkle-anchored receipts are a "pilot production tier" | HIGH (claims) | Fixed (README, PRODUCTION.md, THREAT_MODEL.md) | `src/core.py` `emit_receipt` has no signature path; response carries `receipt_hash`/`receipt_body` only |
| 2 | Website trust claims ("without trusting Inquiro", 21 places) lacked the trusted-key caveat | HIGH (claims) | Fixed on 17 editable occurrences; 4 protected (before/after given) | `CLAIMS.md` W6 |
| 3 | Hard-coded verdicts: genesis "CHAIN INTACT" + SHA-256 shown as BLAKE3; Academy receipt banner/"Anchored ✓"; deploy header "VERIFIED"; Inquiry simulations | HIGH (claims) | Fixed; `shop` and agreement/verify protected (before/after given) | `CLAIMS.md` W12-W15; `academy/genesis/genesis.js:131-136` |
| 4 | FAA Part 108 described as a framework in force; no regulatory status or sources; TOC anchor to a missing section | HIGH (legal) | Fixed wording and section; dates NEEDS HUMAN CHECK | Part 3d |
| 5 | Container build context shipped test harness, partner kit zip and working notes; "no core source" is bytecode-only | MEDIUM | `.dockerignore` fixed (94 → 40 files); wording clarified | Part 2e |
| 6 | Dead links: SDK `PRODUCTION.md` workflow, email template sandbox route, regulatory `#status` | MEDIUM | Fixed | Part 1 Jay 2 |
| 7 | `SECURITY_REVIEW.md` stale (said no Ed25519 verification, old pins, missing workflow) | MEDIUM | Fixed | `CLAIMS.md` S8-S9 |
| 8 | "Zero data retention" / "No KV write" vs receipts retrievable by id | MEDIUM | Wording fixed where editable; Worker behaviour NEEDS HUMAN CHECK; `ai-catalog.json` protected | `CLAIMS.md` W17 |
| 9 | `legal/cookies` "CURRENT TRACKING: NONE" while pages load `tracking.js` and beta posts telemetry | MEDIUM (legal) | Not edited (pinned); counsel | `CLAIMS.md` W26 |
| 10 | Academy capstones described as "signed ... verify independently" but sealed with HMAC | MEDIUM | Fixed (`academy/index.html`) | `src/academy.ts:2731` |
| 11 | Three contact mailboxes across surfaces; none verifiable | MEDIUM | Flight recorder SECURITY.md added; mailbox test is human | Part 4 |
| 12 | Key-shaped value in website `.env.example` (the server would honour it as a `PARTNER_KEY_*`); public IndexNow key in `scripts/indexnow-submit.mjs` | MEDIUM (hygiene) | Not changed; rotate or delete the former | Part 4 |
| 13 | Public flight-recorder repository carries patent-review and internal planning material | MEDIUM (counsel) | Not changed | Part 4 |
| 14 | Patent status wording unverifiable; "patent pending" banned by the site's own gate | MEDIUM (counsel) | Left verbatim; allowlisted in the claims lint with the reason | `CLAIMS.md` W11 |
| 15 | Canonical receipt envelope differs between the profile, the anatomy page, the catalogs and the compliance pages (`raci_binding`) | LOW | Not changed; owner decision | `CLAIMS.md` W24 |
| 16 | Live hosts, external sites, regulatory sources and Docker unreachable from the audit sandbox | INFO | `final_audit.sh` carries the live checks | throughout |
| 17 | `examples/nodejs` unpinned without lockfile; website actions tag-pinned, trufflehog `@main` | LOW | Not changed | Part 4 |
| 18 | `tests/do-not-touch.manifest.json` caught an audit edit to `rna-spec.json` | INFO (control works) | Reverted | Part 3c |

## Verification pass (fresh subagent, no shared context)

Every mechanically checkable PASS reproduced: test counts (57, 12, 366/411, 23), the negative control (3 failed), all vectors recomputed independently including the RFC 8032 keys, the offline path and bundle under `unshare -rn` and `python3 -I`, demo hashes, the 40-file build context by an independent simulation of Docker's rule order, the local-server journey including `ledger_reset`, the website gates (497/497), the do-not-touch manifest (34 changed files, none pinned), and the regulatory status section. Eight discrepancies were found, all in the claims layer, and all are fixed in the final commits:

| # | Discrepancy | Fix |
|---|---|---|
| D1 | Proving Ground JSON-LD (`:56`, `:107`) still said "AI output verification" | Renamed to scoring |
| D2 | `academy/receipt.html:320` runtime text "CHAIN VERIFIED · IMMUTABLE SINCE" in an editable file | Now "SEALED"; the claims lint scans static copy only, a stated limit |
| D3 | IndexNow key in `scripts/indexnow-submit.mjs` missed by the hygiene scan | Recorded (public by design) |
| D4 | Report said the `.env.example` key name matches no server variable; `config_loader.py` reads every `PARTNER_KEY_*` | Reasoning corrected above |
| D5 | The audit's own rewording of `pilot/README.md` overstated: tail truncation is not detectable, and only attestation receipts carry the tenant link | Reworded again, citing GAP_ANALYSIS.md |
| D6 | `SECURITY_REVIEW.md:16` still claimed a CI secret gate | Now stated as roadmap |
| D7 | `docs/EVENT_TYPES.md` said "Immutable" and that `receipt_hash` binds the five attestation fields | Tamper-evident with legal hedge; hash described correctly (row S18 in `CLAIMS.md`) |
| D8 | `final_audit.sh` passed when the live site said "patent pending", which the site's gate bans | Check inverted; status-line check added |

## Every FAIL

1. Jay 2 (404s): three dead links in the repositories. Fixed on the branches. External crawl not possible here.
2. Jay 3 (overclaiming): residual overclaims on 25 surfaces (`CLAIMS.md` rows marked UNSUPPORTED). Fixed where editable; 10 protected or external rows need Matthew.
3. Container audit (Part 2e): build context included files that do not belong in the image. Fixed.
4. Regulatory TOC anchor `#status` pointed at nothing. Fixed.
5. `scripts/final_audit.sh` live sections, `smoke_test.sh` sections 8-9, `link_crawl.py` external URLs, CI Docker job, Windows execution: **could not be run here** (not failures of the code; unverified).

## Needs human action

**Hosting (Matthew).** Run `bash scripts/final_audit.sh` from Git Bash against the live host and site and attach `audit.log`; confirm in the Render dashboard that the service runs the hardened image and whether a disk is mounted at `/var/data` (free tier means `"persistence": "ephemeral"`, which the copy now states); rerun the GitHub Actions `image` job; open the three Starcloud scenario links; send a test message to `security@`, `contact@` and `inquiro@inquiroresearchlabs.ai` and confirm each is read; decide whether `PARTNER_KEY_DEMO_PUBLIC` in `.env.example` was ever live and rotate it if so.

**Legal (counsel).** Every compliance and FRE 901(b)(9) sentence on the website and in the SDK README (`CLAIMS.md` W8, S7); the regulatory table in Part 3d, especially FAA Part 108 status and the EU AI Act application dates; patent status wording (W11) and whether the public `AIFlightRecorder` root material should stay public; MIT licence versus the patent position; the cookies page accuracy (W26); the Academy "sealed receipts are permanent" and consent-record language (inventory rows 21, 187-193).

**External copy (Matthew).** Apply the before/after table in `CLAIMS.md` section 4 to the protected website files (after regenerating the do-not-touch manifest) and to Gumroad, LinkedIn/X and any deck.

## Go / no-go for a rigorous technical evaluator

**GO, with conditions, for the SDK offline path and evaluator bundle.** From a fresh clone with networking disabled the kit does exactly what it says: seals, chains, signs, detects edits/deletions/reordering, exports a bundle that verifies with Python alone, reproduces the demos byte-for-byte, and now ships known-answer vectors and a threat model that states what it cannot detect. An evaluator who reads `docs/THREAT_MODEL.md` first will not be surprised.

**HOLD for the hosted sandbox and the website until three things are true:** (1) the `audit/final-oct16` PRs are merged and deployed, because the live site still carries the "1.6 seconds", "LIVE", "immutable" and unhedged trust wording until then; (2) `scripts/final_audit.sh` passes against the live host and site from Matthew's machine (this audit could not reach them); (3) counsel has signed off on the compliance and patent sentences, or they are removed. The flight recorder is fit to show as a free-tier demo with a temporary ledger, and nothing more, which is what the copy now says.

## Close-out addendum, 17 October 2026 (after the live run of `a79748c`)

The live run of `scripts/final_audit.sh` at `a79748c` gave 33 pass and 4 fail. All four were defects in the audit scripts, not the product. They are fixed in the close-out PR:

- Section 4 matched its own file and the audit records. Files that name the retired host on purpose are now excluded by name, and the grep's last-match `--include`/`--exclude` order is fixed.
- The link crawl failed on the retired host, the old GitHub org slug and three primary sources that block bots. These are now `NEEDS HUMAN CHECK` with a reason each (`scripts/link_allowlist.json`), and they no longer fail the run.
- Section 7 banned "under USPTO examination", which is the owner-approved patent sentence on `/rna/`. That ban is removed; the other patent bans stay.
- `smoke_test.sh` failed through the same crawl. The audit now runs the crawl once (`SKIP_CRAWL=1` for the smoke test).

New behaviour:

- **Verdict line:** the script now ends with `READY FOR EVALUATOR`, or a numbered list of failing items, each with its fix. `NEEDS HUMAN CHECK` items are listed but never fail the run.
- **Deploy freshness:** a `/health` without `persistence` fails with `RENDER NOT REDEPLOYED: Manual Deploy latest main, then rerun.`
- **Layout and UI eval:** section 7b renders the live site in Chromium (website `scripts/ui-eval.mjs`). The eval found the `/regulatory-timeline/` defect in the screenshot Matthew sent: the status section sat in the table-of-contents column, and phone tables hid their last column. Both are fixed in the website close-out PR.

Corrections to this report:

- `CLAIMS.md` row "AIFlightRecorder root" calls that repository public. The GitHub API reports it private as of 17 October 2026; whether it was ever public is counsel question Q6(a).
- Legal wording now follows `docs/LEGAL_LANGUAGE.md` (the approved sentence, pending counsel).
- The open legal questions are in `counsel/COUNSEL_REVIEW.md`. Everything that needs a person, with click paths and expected results, is in `HUMAN_ACTIONS.md`.
