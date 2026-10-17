# Human actions

Everything left that only a person can do, as of 17 October 2026. Each item gives the exact click path or command and the result to expect. Do sections 1 to 3 first: they unblock the evaluator run. The rest can happen in any order.

Related: the legal wording rules are in [`docs/LEGAL_LANGUAGE.md`](docs/LEGAL_LANGUAGE.md); the questions for counsel are in [`counsel/COUNSEL_REVIEW.md`](counsel/COUNSEL_REVIEW.md).

## 1. Merge the close-out pull requests

- [x] **Merge the three close-out PRs** (SDK, website, AIFlightRecorder; links at the end of this file). Done 17 October, 02:02 to 02:03 UTC. The website's `deploy` workflow finished green, so the new wording and the regulatory timeline layout fix are live.
- [ ] **Merge the two follow-up PRs** (pushed after those merges landed; links at the end of this file).
  - AIFlightRecorder "ci(image): stop the persistent-ledger step failing with SIGPIPE". The `image` job's persistent-ledger step fails at random with exit code 141: it was red on the PR 53 merge and green on the PR 54 merge by chance. The fault is in the CI script, not the product.
  - inquiro-rna-sdk: this file's update.

  Click path: GitHub → the repository → Pull requests → the PR → wait until every check is green → **Merge pull request** → **Confirm merge**.
  Expected: both merged, CI green on `main`.
- [ ] **Decide on the two open dependabot PRs** in Inquiro-Website-: #418 (sharp and wrangler) and #420 (tooling group), open since September.
  Click path: Pull requests → each PR → Checks tab → if green, **Merge pull request**; if not, **Close pull request**.
  Expected: no open pull requests left in the three repositories.

## 2. Redeploy the sandbox on Render

- [ ] **Manual Deploy of latest main.**
  Click path: dashboard.render.com → service **flight-recorder-pilot** → **Manual Deploy** (top right) → **Deploy latest commit** → wait until Events shows the deploy as **Live** (a few minutes).
  Command to confirm:
  ```bash
  curl -s https://aiflightrecorder-1.onrender.com/health
  ```
  Expected: JSON that contains `"persistence"`, for example `{"status": "ok", "version": "pilot_v3", "mode": "pilot", "persistence": "ephemeral"}`. If the field is missing, the audit fails with `RENDER NOT REDEPLOYED: Manual Deploy latest main, then rerun.`
- [ ] **Record the plan and the disk.**
  Click path: flight-recorder-pilot → **Settings** → Instance Type; then **Disks** in the left menu.
  Expected: either a paid instance with a disk mounted at `/var/data` (then `/health` says `"persistence": "persistent"`), or the free plan with no disk (then it says `"ephemeral"` and the ledger resets on restart). Both are fine; the public copy already says which applies.
- [ ] **Run the scheduled live check once by hand.**
  Click path: GitHub → inquiro-rna-sdk → Actions → **Verify RNA Receipts (live API)** → **Run workflow** → branch `main` → **Run workflow**.
  Expected: green within a few minutes. Its last scheduled run (6 July) failed against the retired host; it runs daily at 06:00 UTC, and **Live health check** daily at 07:17 UTC.
- [ ] **Confirm the image is the hardened pilot build.**
  Click path: flight-recorder-pilot → **Events** → the latest deploy → it names the commit. Expected: the commit is the head of AIFlightRecorder `main` and the build used `pilot/Dockerfile`.

## 3. Rerun the audit (the evaluator command)

- [ ] From a terminal (Linux, macOS, or Windows Git Bash):
  ```bash
  git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
  git clone git@github.com:InquiroAIReseachLabs/Inquiro-Website-.git ../Inquiro-Website-
  pip install -r requirements.txt
  WEBSITE_REPO=../Inquiro-Website- bash scripts/final_audit.sh
  ```
  If you already have both clones: `git -C . pull && git -C ../Inquiro-Website- pull`, then the last command.
  Expected: the last line is `READY FOR EVALUATOR` and the exit code is 0. Lines marked `NEEDS HUMAN CHECK` (bot-blocked primary sources, mailboxes, Render, Starcloud) are listed above the verdict and do not fail the run. If it ends with a numbered list instead, do each `FIX` in order and rerun.
- [ ] Optional, the ledger-reset answer: rerun with `OLD_RECEIPT=path/to/receipt.json` (a receipt saved before the last sandbox restart). Expected: `PASS old receipt: server answers valid or reason ledger_reset`.

## 4. Mailbox tests

The repositories name two addresses: `security@inquiroresearchlabs.ai` (SDK and AIFlightRecorder `SECURITY.md`) and `contact@inquiroresearchlabs.ai` (website `.well-known/security.txt`).

- [ ] From a personal address, send subject `Mailbox test: security, 17 Oct` and body `Test, please ignore.` to security@inquiroresearchlabs.ai.
  Expected: it arrives in an inbox you read within a few minutes (check spam), with no bounce.
- [ ] Same test to contact@inquiroresearchlabs.ai. Expected: same.
- [ ] Decide whether `security.txt` should name `security@` like the two `SECURITY.md` files. If yes, it is a protected file: apply the row in section 6.

## 5. Counsel packet

- [ ] Send counsel `counsel/COUNSEL_REVIEW.md` and `docs/LEGAL_LANGUAGE.md` (both in this repository, public), plus access to the patent-review material listed in section 5 of the packet. AIFlightRecorder and Inquiro-Website- are private: add counsel as a read-only collaborator (repository → Settings → Collaborators → Add people → role **Read**) or export the named files.
  Expected: written answers to questions Q1 to Q7.
- [ ] When the answers come back: change the approved sentence, if counsel changes it, in `docs/LEGAL_LANGUAGE.md` of **both** repositories and in `data/claims-allowlist.json` of the website (the website test fails until all three match), and change "PENDING COUNSEL" to "Reviewed by counsel on <date>".

## 6. Protected website files

These files are pinned by `tests/do-not-touch.manifest.json` in Inquiro-Website-, so the close-out did not edit them. Apply each row, then regenerate the manifest:

```bash
cd Inquiro-Website-
node -e "const fs=require('fs'),c=require('crypto');const p='tests/do-not-touch.manifest.json';const m=JSON.parse(fs.readFileSync(p));for(const f of Object.keys(m.files))m.files[f]=c.createHash('sha256').update(fs.readFileSync(f)).digest('hex');fs.writeFileSync(p,JSON.stringify(m,null,2)+'\n')"
npm test
```

Expected: `npm test` passes (498 tests at the close-out). The command above rewrites only hashes; run on an unchanged tree it changes nothing.

| File:line | Before | After |
|---|---|---|
| `.well-known/rna-spec.json:5` | "...how any third party verifies it, with no trust in the issuer. ... the checks a compliant client performs." | "...how any third party verifies it, trusting only a signing key it already holds. ... the checks a conforming verifier performs." |
| `.well-known/rna-spec.json:23` | "A compliant client treats it as a string and does not assume a fixed set." | "A conforming verifier treats it as a string and does not assume a fixed set." |
| `.well-known/rna-spec.json:65` | "A compliant client performs these checks locally. None of them require trusting Inquiro." | "A conforming verifier performs these checks locally. None of them require contacting Inquiro. Authorship rests on checking signing_pubkey against a key the verifier already trusts." Then delete the "compliant client" entry from `data/claims-allowlist.json` (its stale-entry test reminds you). |
| `src/domains/actuarial/scenarios.ts:59` **and** `proving-ground/actuarial-card.js:31` (change both in one commit: the card mirrors the server byte for byte) | `outcome: 'FAA_Part_108_compliant'` | `outcome: 'FAA_Part_108_fields_recorded'` (the client-only copy in `proving-ground/demos.js:207` already says this). New actuarial demo receipts get new hashes; old receipts still verify. |
| `src/index.ts:439-440` (CTA destination allowlist; no page emits these CTAs today) | `'https://github.com/inquiroairesearchlabsinc/inquiro-rna-sdk'`, `'https://codespaces.new/inquiroairesearchlabsinc/inquiro-rna-sdk'` | `'https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk'`, `'https://codespaces.new/InquiroAIReseachLabs/inquiro-rna-sdk'` |
| `academy/codex-01/lab.js:2518`, `academy/codex-01-zh-tw/lab.js:2532` (pinned Codex) | "That is the patent-pending infrastructure Inquiro uses for autonomous systems making decisions without humans in the loop." | Wait for counsel Q4. Suggested: "That is the infrastructure Inquiro uses for autonomous systems making decisions without humans in the loop." (no patent wording in course content) |
| `.well-known/security.txt:1,8` (only if you decide so in section 4) | `contact@inquiroresearchlabs.ai` | `security@inquiroresearchlabs.ai` |
| Earlier rows | `CLAIMS.md` section 4 (17 October audit): Academy verify header, Codex "IMMUTABLE SINCE", legal pages, `shop/index.html`, `ai-catalog.json`, `agents.json` | Still open; apply with the rows above and regenerate the manifest once. |

## 7. External copy (Gumroad, LinkedIn, X, decks)

None of these is in a repository, so nothing was edited.

- [ ] Open each: the 12 Gumroad product pages (inquiro.gumroad.com, Products), the LinkedIn company page and newsletter, the X profile, and any deck you send out. Search each (Ctrl+F) for: built to comply, complies, compliant, compliance-ready, guarantee, certified, court-admissible, courts admit, in production, tamper-proof, immutable, patent pending, patent-pending.
  Expected after editing: none of those words is left, and every page that names FRE 901(b)(9), DoD 3000.09, FAA Part 108 or the EU AI Act carries the approved sentence once, verbatim.

| Before (typical) | After |
|---|---|
| "FRE 901-compliant receipts" | "Receipts designed to support FRE 901(b)(9) authentication." plus the approved sentence |
| "Court-admissible audit trail" | "A tamper-evident audit trail designed to support evidence and record-keeping requirements." plus the approved sentence |
| "Built to comply with the EU AI Act" | "Designed to support EU AI Act Article 12 record-keeping." |
| "Certified for DoD 3000.09" | "Designed to support DoD Directive 3000.09 accountability review." |
| "FAA Part 108 compliant" | "Designed to support Part 108 flight-decision records (the rule is not final; check its status)." |
| "Guaranteed tamper-proof" | "Tamper-evident: any change shows on verification." |
| "In production" | "Local verified prototypes, not production systems." |
| "Patent pending" | "Non-provisional patent under USPTO examination." (pending counsel Q4) |

The approved sentence: "Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction."

## 8. Starcloud (external site)

The site at starcloud1.northstaraokeystone.com is deployed from a separate repository and could not be loaded from the audit sandbox.

- [ ] Open https://starcloud1.northstaraokeystone.com/ in a browser. Expected: the platform page loads (not blank, not 404).
- [ ] From it, open each scenario the website links to: **Orbital compute scenario** (`#/nasa`), **Defense data scenario** (`#/usff`), **Read the doctrine** (`#/doctrine`). Expected: each view loads.
- [ ] On each view, search for the words in section 7 and for "LIVE" chips. Expected after editing: none left; apply the section 7 table in the Starcloud source repository, and add the approved sentence wherever a framework is named.
- [ ] Our own card text for those links was softened in this close-out (website `proving-ground/index.html`, defense card). Before: "Defense autonomous platforms require decision records that survive denied-environment conditions." After: "Defense autonomous platforms need decision records that survive denied-environment conditions." The orbital cards and the llms.txt link labels name no framework and were left as they were.

## 9. Bot-blocked primary sources

The audit lists these as `NEEDS HUMAN CHECK` because the sites refuse automated requests (reasons in `scripts/link_allowlist.json`).

- [ ] Open in a browser: the EU AI Act on EUR-Lex (https://eur-lex.europa.eu/eli/reg/2024/1689/oj), DoD Directive 3000.09 (https://www.esd.whs.mil/Portals/54/Documents/DD/issuances/dodd/300009p.pdf), the FAA BVLOS page (https://www.faa.gov/uas/advanced_operations/beyond_visual_line_of_sight).
  Expected: each loads the document. If one has moved, update the status table in website `regulatory-timeline/index.html` (section 04) and the prefix in `scripts/link_allowlist.json`.
- [ ] While there, check that section 04 of /regulatory-timeline/ is still true (is the Part 108 rule final? were the EU AI Act Article 113 dates amended?). Changes go through counsel Q3.

## 10. Demo partner key in the website's .env.example (report only; rotation is yours)

- **What was there:** `PARTNER_KEY_DEMO_PUBLIC=` followed by a 32-character hex value, in `.env.example` of Inquiro-Website-. The close-out replaced it with `your_demo_partner_key_here`; git history is unchanged.
- **Git history (all branches):** added to `.env.example` in `556b011` (2026-04-12, "Update demo public partner key in .env.example"); hard-coded in `receipt-experience/index.html` in `c5af28a` (2026-04-12) and removed from that file in `d714e83` the same day; carried through `dffc318` and `730d690` (history imports, June 2026). Not present anywhere in the inquiro-rna-sdk or AIFlightRecorder history. Nothing in the website code reads the variable.
- **What it could unlock:** the pilot server maps an environment variable `PARTNER_KEY_<TENANT>` to a tenant. If Render has `PARTNER_KEY_DEMO_PUBLIC` set to that value, the key selects tenant `demo_public`. No tenant file of that name exists (the public sandbox is `demo_public_001` and needs no key), so it most likely unlocks nothing beyond keyless access. The website repository is private, but the value was in served HTML for part of 12 April if that commit was deployed.
- [ ] Render: flight-recorder-pilot → **Environment** → look for `PARTNER_KEY_DEMO_PUBLIC`. Expected: absent. If present with that value: delete it, or set a new value from `python3 -c "import secrets; print(secrets.token_hex(16))"`, then **Save Changes** (Render redeploys).
- [ ] Cloudflare: Workers & Pages → the inquiroresearchlabs.ai Worker → **Settings** → **Variables and Secrets**. Expected: no variable holding that value.
- A history rewrite is not needed unless the key turns out to be live; `scripts/HISTORY_REWRITE.md` describes the steps if you decide to.

## Close-out pull requests

- inquiro-rna-sdk: https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk/pull/14 (merged)
- Inquiro-Website-: InquiroAIReseachLabs/Inquiro-Website- pull request 438 (private repository; merged)
- AIFlightRecorder: InquiroAIReseachLabs/AIFlightRecorder pull request 54 (private repository; merged)
- Follow-ups, open: the inquiro-rna-sdk PR carrying this update, and the AIFlightRecorder CI fix PR (both titled as in section 1).
