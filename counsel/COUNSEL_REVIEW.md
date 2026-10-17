# Counsel review packet

Prepared 17 October 2026 for outside counsel, from the main branches of the three Inquiro repositories plus the close-out pull requests of that date (inquiro-rna-sdk is public; Inquiro-Website- and AIFlightRecorder are private). Nothing here is a legal conclusion: the questions are for counsel, and the facts are what the code and copy say. File references are `file:line` in the named repository after the close-out PRs.

The approved sentence and the wording rules are in `docs/LEGAL_LANGUAGE.md` (same file in inquiro-rna-sdk and Inquiro-Website-). Steps that need a person are in `HUMAN_ACTIONS.md`.

## 1. Questions

**Q1. The approved sentence.** Is this acceptable, as is, for public pages read in the US and the EU?

> Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction.

It now appears on every surface listed in section 7 marked "approved sentence". The owner approved it; it is marked "pending counsel" everywhere it is defined.

**Q2. "Designed to support / Does not address".** The website's regulatory page now has a two-column matrix in place of check marks (Inquiro-Website- `regulatory-timeline/index.html:199-214`; the same text in `llms-full.txt:52-71`). Is each row accurate and not misleading? The rows are quoted in section 3.

**Q3. What each framework is said to ask for.** These sentences describe the frameworks themselves. They were rewritten on 17 October to stay close to the source text and to stop saying "requires" or "mandates" where the text does not. Please confirm or correct each:

| Framework | Sentence (Inquiro-Website-) | Point to check |
|---|---|---|
| FRE 901(b)(9) | `compliance/fre-901/index.html:140`: "...The key question is whether the process is one that produces accurate output, not whether the system is infallible." | An interpretation of the rule. Keep, soften, or drop? |
| DoD 3000.09 | `compliance/dod-3000-09/index.html:63, 140, 171`: "asks that autonomous and semi-autonomous weapon systems be designed to allow commanders and operators to exercise appropriate levels of human judgment over the use of force. It also sets out review and approval steps..." | Was: "mandates that decisions be traceable so that accountability can be assigned to a human". Is the new wording accurate for the January 2023 reissue? |
| FAA Part 108 | `regulatory-timeline/index.html:69, 167`: "It concerns how operators show their flights ran within approved parameters." `compliance/faa-part-108/index.html:63, 140, 172`: "Which records a final rule calls for is a question for the rule text and counsel." | The page treats Part 108 as a proposed rule (status row `regulatory-timeline/index.html:282`). Is a final rule out, and does it change the wording? The old copy said operators "must maintain records that allow the FAA, insurers, and auditors to reconstruct" each flight; that was removed. |
| EU AI Act Art. 12 | `compliance/eu-ai-act-article-12/index.html:63, 140, 178`: Article 12(2) paraphrase (events relevant to identifying risk situations or substantial modifications, post-market monitoring, monitoring of operation). `:71, 182`: "Does Article 12 require tamper-evident logs? Not in those words..." `:95, 194`: retention is set by other provisions. `:172`: high-risk classification "under the Act (Article 6 and Annexes I and III)". | Accuracy of the paraphrase; whether the Article 113 dates (status row `regulatory-timeline/index.html:283`) have been amended (a 2025 Commission "digital omnibus" proposal would delay the high-risk dates). |

**Q4. Patent wording.** See section 4.

**Q5. MIT licence and the pending patent.** See section 5.

**Q6. Patent-review material: location and visibility.** See section 6.

**Q7. Anything in section 7 (every compliance sentence, file:line) that should change.** Section 7 is generated from the files, so it is complete for the surfaces listed there.

**Q8. What a verifier can detect (EU Article 12 page and `llms-full.txt`).** Section 8 gives the new three-part statement. It follows `docs/THREAT_MODEL.md` sections 1 and 2. Is it accurate and not misleading for a regulator-facing reader, and is "designed to support Article 12 record-keeping" the right level of claim for a log whose completeness the receipt does not show?

**Q9. DoD 3000.09: V&V and T&E.** The page now says the directive "also addresses verification and validation (V&V) and test and evaluation (T&E) of such systems; read the directive for its text on those." The owner's instruction cited Section 3 of the directive for these. The reference was not checked against the primary source from the drafting environment (esd.whs.mil was unreachable), so the page does not cite a section number. Please confirm the sentence against the January 2023 reissue and say whether a section number should be added.

**Q10. "Trusting only a signing key you already hold" and "Does not address" notes.** These replace "no trust in Inquiro required" on the FRE page and hub, and are added as a note on each page (section 8). Acceptable?

## 2. What changed on 17 October

- Every surface that names one of the four frameworks or says "compliance" now carries the approved sentence once (section 7 marks them).
- Links between receipts and a framework use "designed to support". The FRE page no longer opens with "Yes, conditionally" or "The math is the proof".
- The check-mark/cross matrix ("Compliance stack", `llms-full.txt`) became "Designed to support / Does not address".
- The page formerly titled "Compliance" is now "Regulatory frameworks" (URL unchanged, `/compliance/`).
- Claims lint (website `scripts/claims-lint.mjs`) bans "built to comply", "complies", "compliant", "compliance-ready", "guarantee", "certified", "court-admissible" and "courts admit" outside the approved sentence; small equivalents scan the SDK docs and the pilot docs.
- The audit script (`scripts/final_audit.sh`, section 7) no longer bans "under USPTO examination", because that phrase is the owner-approved patent sentence on `/rna/`; it still fails on "patent pending", "patent-pending", "patented" and "patent granted".

## 3. Regulatory table with primary sources

Status as the website states it (Inquiro-Website- `regulatory-timeline/index.html:280-283`, "as of 17 October 2026"). Two of the sources block automated requests; open them in a browser.

| Framework | Status on the site | Designed to support (site) | Does not address (site) | Primary source |
|---|---|---|---|---|
| FRE 901(b)(9) | In force; a rule of evidence for US federal courts; no penalties. | Authentication of a system-produced record: a third party recomputes the receipt's hashes and checks its signature against a signing key it already trusts. | Admissibility, which a court decides on the whole record; whether the process that produced the record was accurate; custody of the record outside the receipt. | https://www.law.cornell.edu/rules/fre/rule_901 ; https://www.uscourts.gov/rules-policies/current-rules-practice-procedure/federal-rules-evidence |
| DoD Directive 3000.09 | In force as internal DoD policy on autonomy in weapon systems; no civil penalties. | A sealed record of who was Responsible, Accountable, Consulted, and Informed for a decision, and when it was sealed. | Whether the human judgment exercised was appropriate; the directive's design, review, and approval steps for weapon systems. | https://www.esd.whs.mil/Portals/54/Documents/DD/issuances/dodd/300009p.pdf (blocks bots) |
| FAA Part 108 | Rulemaking in progress: a proposed rule for routine BVLOS operations; check the Federal Register for a final rule and its effective date. | An ordered, sealed record of flight decisions from takeoff to landing that a reviewer can walk and verify. | Operator authorization, aircraft and equipment requirements, and whatever records a final rule calls for. | https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=%22Part+108%22+BVLOS ; https://www.faa.gov/uas/advanced_operations/beyond_visual_line_of_sight (blocks bots) |
| EU AI Act Article 12 | Regulation (EU) 2024/1689, in force since 1 August 2024; Article 12 applies to high-risk systems from the dates in Article 113; penalties in Article 99. | Automatic, time-stamped event records, chained so that a later change shows on verification. | Whether a system is high-risk, which events a given system must log, how long logs are kept, and the Act's other obligations. | https://eur-lex.europa.eu/eli/reg/2024/1689/oj (answers bots with a challenge page) |

## 4. Patent wording

- **Owner-approved sentence:** "Non-provisional patent under USPTO examination." It appears at Inquiro-Website- `rna/index.html:229` (status line on `/rna/`) and `llms.txt:6`, kept verbatim per the website's `docs/portfolio/OWNER_DECISIONS.md` section 2 and allowlisted in `data/claims-allowlist.json`.
- **Banned by the site's own checks:** "patent pending", "patent-pending", "patented" (audit script section 7) and "patent granted" (claims lint and audit script).
- **Still saying "patent-pending":** the pinned Academy Codex labs, `academy/codex-01/lab.js:2518` and `academy/codex-01-zh-tw/lab.js:2532`: "That is the patent-pending infrastructure Inquiro uses for autonomous systems making decisions without humans in the loop." Pinned files; the suggested change is in `HUMAN_ACTIONS.md` section 6.
- **Internal references (private repository, not served):** `.github/workflows/deploy.yml:11, 126` ("Patent Claim 11"), `.github/workflows/scripts/replay-capture.mjs:3` and `.github/workflows/scripts/entropy-gate.mjs:10` ("plurality of entropy metrics" claim).
- **Questions:** (a) Does the sentence match the filing record (application number, filing date, current status)? (b) Is "under USPTO examination" the right description at this stage of prosecution? (c) Should the Codex line be changed to the approved sentence, or should course content not mention the patent at all? (d) Should any public page give the application number?

## 5. MIT licence and the pending patent

Facts:

- inquiro-rna-sdk is public under the MIT License (`LICENSE`: "Copyright (c) 2026 Inquiro AI Research Labs Inc."). It contains the offline sealing and verification code (dual hash, Ed25519 signatures, hash chain, evaluator bundle) and the client examples.
- The website mirrors that licence at `src/sdk/LICENSE.md` ("Mirrored from inquiro-rna-sdk") and declares `"license": "MIT"` for its `verifier/` package.
- AIFlightRecorder has no LICENSE file.
- The MIT License grants the rights to "use, copy, modify, merge, publish, distribute, sublicense, and/or sell" the software. It has no express patent clause.

Questions:

- (a) Does releasing this code under MIT, by the applicant, give users an implied licence to practise any claims the code embodies, and does that matter for the pending application?
- (b) Is that acceptable as is? Or should future releases change, for example:
  - Apache-2.0, which has an express patent licence that terminates on suit;
  - a NOTICE stating that no patent rights are granted beyond the licence;
  - limiting the public SDK to verification-only code?
- (c) Is the copyright holder name ("Inquiro AI Research Labs Inc.") the correct legal entity? Agreement text elsewhere writes "Inquiro AI Research Labs, Inc.".

## 6. Patent-review material: location and visibility

Repository visibility is as reported by the GitHub API on 17 October 2026.

| Material | Location | Visibility | Served on the website? |
|---|---|---|---|
| `AI_FLIGHT_RECORDER_CODE_EXTRACTION_v1.md`: "Technical code citations for patent documentation" (line 5), "Patent-Critical Formula" (line 140), "Status: COMPLETE - Ready for Patent Attorney Review" (line 1818) | AIFlightRecorder, repository root | Private | No. The pilot Docker image includes only `pilot/` and named `src/` files (`.dockerignore`). |
| `Receipts native architecture v2.0.txt`, `CLAUDEME.md`, `sim/`, `demo/`, `benchmark_pitch.py` (design and planning material) | AIFlightRecorder, repository root | Private | No |
| `legal/attorney-report-2026-05-07.md` (earlier attorney report, pinned) | Inquiro-Website- | Private | No: `.assetsignore` excludes it, although the rest of `legal/` is served |
| `docs/portfolio/OWNER_DECISIONS.md`, `docs/portfolio/LEGAL_PROPOSALS.md` | Inquiro-Website- | Private | No: `docs/` is excluded from assets |
| `AUDIT_REPORT.md`, `CLAIMS.md` (they describe that the material above exists and quote "Ready for Patent Attorney Review") | inquiro-rna-sdk | **Public** | No (GitHub only) |

Questions:

- (a) `CLAIMS.md` (16 October) describes AIFlightRecorder as "a public repository". Was it ever public, and if so from when to when? This matters for any public-disclosure analysis.
- (b) Should the public SDK's audit documents mention the existence of patent-review material at all?
- (c) Should the patent-review files leave AIFlightRecorder for a separate private repository with narrower access?

## 7. Every compliance sentence, file:line

Generated on 17 October 2026 from the close-out branches. It covers reader-facing copy only:

- **Inquiro-Website-:** served HTML and text pages, the `.well-known` JSON files, and the demo scripts.
- **inquiro-rna-sdk:** reader-facing Markdown.
- **AIFlightRecorder:** `pilot/*.md` and `SECURITY.md`.

It does not cover pinned legal pages or agreements, internal docs, tests, or code comments. A line is listed if it names one of the four frameworks in a sentence, or uses compliance, admissibility, guarantee, certification or court language. Lines that only name a framework (topic lists, breadcrumbs, URLs) are left out.

The approved sentence is marked; every other sentence is for Q2, Q3 or Q7.

### Inquiro-Website-

| file:line | sentence | note |
|---|---|---|
| `.well-known/rna-spec.json:5` | What a conforming RNA receipt looks like and how any third party verifies it, with no trust in the issuer. This is an integration and verification profile, not an implementation specification. It defines the receipt envelope a verifier reads and the checks a compliant client performs. It deliberately does not specify receipt construction internals. | protected file: before/after in HUMAN_ACTIONS.md |
| `.well-known/rna-spec.json:23` | An opaque category label. A compliant client treats it as a string and does not assume a fixed set. | protected file: before/after in HUMAN_ACTIONS.md |
| `.well-known/rna-spec.json:65` | A compliant client performs these checks locally. None of them require trusting Inquiro. | protected file: before/after in HUMAN_ACTIONS.md |
| `company/index.html:167` | One receipt format designed to support record-keeping under four frameworks: FRE 901(b)(9), DoD 3000.09, FAA Part 108, and EU AI Act Article 12, with status on the regulatory landscape . Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `compliance/dod-3000-09/index.html:6` | DoD Directive 3000.09 and Inquiro Receipts / Inquiro AI Research Labs |  |
| `compliance/dod-3000-09/index.html:32` | {"@type": "ListItem", "position": 3, "name": "DoD Directive 3000.09", "item": "https://inquiroresearchlabs.ai/compliance/dod-3000-09/"} |  |
| `compliance/dod-3000-09/index.html:43` | DoD Directive 3000.09 concerns appropriate levels of human judgment over the use of force in autonomous weapon systems. Inquiro receipts are designed to support accountability review with a RACI binding and a signed timestamp on each decision. |  |
| `compliance/dod-3000-09/index.html:50` | "keywords": "DoD Directive 3000.09, autonomous weapons, human judgment, RACI, decision provenance, Ed25519, chain intact |  |
| `compliance/dod-3000-09/index.html:63` | DoD Directive 3000.09 asks that autonomous and semi-autonomous weapon systems be designed to allow commanders and operators to exercise appropriate levels of human judgment over the use of force. It also sets out review and approval steps for such systems; read the directive for those. Receipts are designed to support the record a reviewer uses to see who was assigned accountability for a decision. |  |
| `compliance/dod-3000-09/index.html:76` | Which receipt fields are designed to support DoD 3000.09 accountability review? |  |
| `compliance/dod-3000-09/index.html:136` | DoD Directive 3000.09 asks that autonomous and semi-autonomous weapon systems be designed so commanders and operators can exercise appropriate levels of human judgment over the use of force. Inquiro receipts are designed to support accountability review: each decision is recorded with a RACI binding (Responsible, Accountable, Consulted, Informed) and a signed timestamp, so a reviewer can reconstruct who was assigned accountability for an engagement and when, and verify the record independently. |  |
| `compliance/dod-3000-09/index.html:137` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `compliance/dod-3000-09/index.html:140` | DoD Directive 3000.09 sets policy for autonomous and semi-autonomous weapon systems. It asks that such systems be designed to allow commanders and operators to exercise appropriate levels of human judgment over the use of force, and it sets out review and approval steps; read the directive for those. Which records a program keeps for later review is for the program and its counsel to decide. |  |
| `compliance/dod-3000-09/index.html:171` | DoD Directive 3000.09 asks that autonomous and semi-autonomous weapon systems be designed to allow commanders and operators to exercise appropriate levels of human judgment over the use of force. It also sets out review and approval steps for such systems; read the directive for those. Receipts are designed to support the record a reviewer uses to see who was assigned accountability for a decision. |  |
| `compliance/dod-3000-09/index.html:178` | Which receipt fields are designed to support DoD 3000.09 accountability review? |  |
| `compliance/eu-ai-act-article-12/index.html:6` | EU AI Act Article 12 and Inquiro Receipts / Inquiro AI Research Labs |  |
| `compliance/eu-ai-act-article-12/index.html:32` | {"@type": "ListItem", "position": 3, "name": "EU AI Act Article 12", "item": "https://inquiroresearchlabs.ai/compliance/eu-ai-act-article-12/"} |  |
| `compliance/eu-ai-act-article-12/index.html:42` | EU AI Act Article 12 and Inquiro Receipts |  |
| `compliance/eu-ai-act-article-12/index.html:43` | EU AI Act Article 12 requires high-risk AI systems to allow the automatic recording of events over their lifetime. Inquiro receipts are designed to support that record-keeping with tamper-evident, independently verifiable entries sealed when each event happens. |  |
| `compliance/eu-ai-act-article-12/index.html:50` | "keywords": "EU AI Act, Article 12, high-risk AI, logging, traceability, tamper-evident, Ed25519, dual hash, chain intact |  |
| `compliance/eu-ai-act-article-12/index.html:60` | What does EU AI Act Article 12 require? |  |
| `compliance/eu-ai-act-article-12/index.html:133` | Regulatory frameworks / EU AI Act Article 12 |  |
| `compliance/eu-ai-act-article-12/index.html:136` | EU AI Act Article 12 requires high-risk AI systems to allow the automatic recording of events over their lifetime, for traceability. Inquiro receipts are designed to support that record-keeping with tamper-evident, independently verifiable entries: each event is sealed at the moment it happens and chained to the one before it, so any change to a sealed receipt breaks its hashes and signature and shows to anyone who runs verification. |  |
| `compliance/eu-ai-act-article-12/index.html:137` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `compliance/eu-ai-act-article-12/index.html:140` | Article 12 of the EU AI Act requires that high-risk AI systems technically allow the automatic recording of events (logs) over the lifetime of the system. The logging is to enable the recording of events relevant to identifying situations that may present a risk or involve a substantial modification, to post-market monitoring, and to monitoring the system's operation. |  |
| `compliance/eu-ai-act-article-12/index.html:172` | Inquiro does not provide legal advice. Article 12 obligations depend on whether a system qualifies as high-risk under the Act (Article 6 and Annexes I and III) and on the provider's or deployer's role. Counsel familiar with the EU AI Act should advise on classification and retention requirements. |  |
| `compliance/eu-ai-act-article-12/index.html:177` | What does EU AI Act Article 12 require? |  |
| `compliance/faa-part-108/index.html:6` | FAA Part 108 BVLOS and Inquiro Receipts / Inquiro AI Research Labs |  |
| `compliance/faa-part-108/index.html:32` | {"@type": "ListItem", "position": 3, "name": "FAA Part 108 (BVLOS)", "item": "https://inquiroresearchlabs.ai/compliance/faa-part-108/"} |  |
| `compliance/faa-part-108/index.html:43` | FAA Part 108 is the FAA rulemaking for BVLOS drone operations. Inquiro receipts are designed to support an operator's record of what the aircraft decided and on whose authority, sealed into a chain an auditor can verify offline. |  |
| `compliance/faa-part-108/index.html:50` | "keywords": "FAA Part 108, BVLOS, drone operations, flight decision record, Ed25519, dual hash, chain intact, underwriter |  |
| `compliance/faa-part-108/index.html:63` | FAA Part 108 is the FAA rulemaking for routine beyond visual line of sight (BVLOS) drone operations; its status and primary sources are on the regulatory landscape page. Which records a final rule calls for is a question for the rule text and counsel. Receipts are designed to support an operator's own record of what the aircraft decided and on whose authority. |  |
| `compliance/faa-part-108/index.html:136` | FAA Part 108 is the FAA rulemaking for routine BVLOS drone operations. Inquiro receipts are designed to support an operator's record of what the aircraft decided and on whose authority: each flight-decision record from takeoff to landing is sealed into a chain an underwriter or auditor can verify offline, by recomputing the dual hash and checking the signature, without relying on the operator's logs. |  |
| `compliance/faa-part-108/index.html:137` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `compliance/faa-part-108/index.html:140` | FAA Part 108 is the FAA's rulemaking for beyond visual line of sight (BVLOS) unmanned aircraft operations; its current status is noted on the regulatory landscape page. Because the operator cannot see the aircraft throughout the flight, more of each flight rests on automated decisions and on the records those systems keep. Which records a final rule calls for is a question for the rule text and counsel; insurers and auditors may ask for their own. |  |
| `compliance/faa-part-108/index.html:172` | FAA Part 108 is the FAA rulemaking for routine beyond visual line of sight (BVLOS) drone operations; its status and primary sources are on the regulatory landscape page. Which records a final rule calls for is a question for the rule text and counsel. Receipts are designed to support an operator's own record of what the aircraft decided and on whose authority. |  |
| `compliance/fre-901/index.html:6` | FRE 901(b)(9) and Inquiro Receipts / Inquiro AI Research Labs |  |
| `compliance/fre-901/index.html:32` | {"@type": "ListItem", "position": 3, "name": "FRE 901(b)(9)", "item": "https://inquiroresearchlabs.ai/compliance/fre-901/"} |  |
| `compliance/fre-901/index.html:43` | FRE 901(b)(9) allows a record to be authenticated by describing a process that produces an accurate result. Inquiro receipts are designed to support that kind of authentication: a third party recomputes the dual hash and checks the Ed25519 signature with no call to Inquiro required. |  |
| `compliance/fre-901/index.html:50` | "keywords": "FRE 901, FRE 901(b)(9), authentication, evidence, cryptographic receipt, Ed25519, dual hash |  |
| `compliance/fre-901/index.html:63` | FRE 901(b)(9) permits authentication by evidence describing a process or system and showing that it produces an accurate result. The offering party must describe the process with enough specificity that the court can assess reliability; the trier of fact then weighs the evidence. |  |
| `compliance/fre-901/index.html:68` | Which receipt fields does a verifier use to support FRE 901(b)(9) authentication? |  |
| `compliance/fre-901/index.html:84` | Does a receipt alone establish admissibility? |  |
| `compliance/fre-901/index.html:87` | No. A receipt is one artifact in a broader admissibility determination. Your full ledger, custody chain, and counsel determine admissibility. Inquiro does not provide legal advice. |  |
| `compliance/fre-901/index.html:136` | FRE 901(b)(9) allows a record to be authenticated by describing a process or system and showing that it produces an accurate result. Inquiro receipts are designed to support that kind of authentication: a third party recomputes the receipt's dual hash and checks the Ed25519 signature against a signing key the verifier already trusts, with no call to Inquiro required. A receipt alone does not establish admissibility; your full ledger, custody chain, and counsel decide that. |  |
| `compliance/fre-901/index.html:137` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `compliance/fre-901/index.html:140` | Rule 901(b)(9) permits authentication by evidence describing a process or system and showing that it produces an accurate result. The rule is not limited to electronic records; it applies to any output of a system or process. The offering party describes the process with enough specificity that the court can assess reliability, and the trier of fact weighs the evidence. The key question is whether the process is one that produces accurate output, not whether the system is infallible. |  |
| `compliance/fre-901/index.html:164` | Inquiro does not provide legal advice. A receipt is a technical artifact designed to support an authentication argument, not a legal opinion. Admissibility is determined by your full ledger, custody chain, opposing counsel, and the court. |  |
| `compliance/fre-901/index.html:170` | FRE 901(b)(9) permits authentication by evidence describing a process or system and showing that it produces an accurate result. The offering party must describe the process with enough specificity that the court can assess reliability; the trier of fact then weighs the evidence. |  |
| `compliance/fre-901/index.html:173` | Which receipt fields does a verifier use to support FRE 901(b)(9) authentication? |  |
| `compliance/fre-901/index.html:181` | Does a receipt alone establish admissibility? |  |
| `compliance/fre-901/index.html:182` | No. A receipt is one artifact in a broader admissibility determination. Your full ledger, custody chain, and counsel determine admissibility. Inquiro does not provide legal advice. |  |
| `compliance/index.html:49` | "keywords": "regulatory frameworks, cryptographic decision provenance, FRE 901, DoD 3000.09, FAA Part 108, EU AI Act Article 12 |  |
| `compliance/index.html:84` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `llms-full.txt:18` | - High-risk AI systems under EU AI Act Article 12 |  |
| `llms-full.txt:34` | - One foundation designed to support FRE 901(b)(9), DoD 3000.09, FAA Part 108, and EU AI Act Article 12 record-keeping |  |
| `llms-full.txt:42` | 1. FRE 901(b)(9): evidence produced by a process or system can be authenticated by |  |
| `llms-full.txt:45` | 2. DoD Directive 3000.09: autonomous and semi-autonomous weapon systems are to allow |  |
| `llms-full.txt:48` | 3. FAA Part 108: FAA rulemaking for routine beyond-visual-line-of-sight drone operations. |  |
| `llms-full.txt:50` | 4. EU AI Act Article 12: high-risk AI systems are to allow automatic recording of events |  |
| `llms-full.txt:55` | - FRE 901(b)(9). Designed to support: authentication of a system-produced record; a |  |
| `llms-full.txt:57` | already trusts. Does not address: admissibility, which a court decides on the whole |  |
| `llms-full.txt:59` | - DoD Directive 3000.09. Designed to support: a sealed record of who was Responsible, |  |
| `llms-full.txt:63` | - FAA Part 108. Designed to support: an ordered, sealed record of flight decisions from |  |
| `llms-full.txt:66` | - EU AI Act Article 12. Designed to support: automatic, time-stamped event records, |  |
| `llms-full.txt:71` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `llms-full.txt:95` | - Zone 01, How does AI actually think? Five foundational questions anyone should ask |  |
| `llms-full.txt:193` | A: Record-keeping under FRE 901(b)(9) for U.S. evidence, DoD 3000.09 for autonomous |  |
| `llms-full.txt:194` | weapons, FAA Part 108 for commercial BVLOS drone operations, and EU AI Act Article 12 for |  |
| `llms-full.txt:195` | high-risk AI traceability. Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `llms.txt:13` | - [Receipts-Native Architecture](https://inquiroresearchlabs.ai/rna/): The receipts-native model in plain language and why it is defensible, dual-hash SHA-256 + BLAKE3, Merkle chain, Ed25519 signing, and export designed to support FRE 901(b)(9) authentication. |  |
| `llms.txt:48` | RNA is not an audit framework. It is a substrate that produces evidence designed to support record-keeping and authentication arguments under FRE 901(b)(9), DoD 3000.09, FAA Part 108, and EU AI Act Article 12. Not legal advice. |  |
| `llms.txt:59` | - Evidence designed to support FRE 901(b)(9) authentication (not legal advice) |  |
| `llms.txt:63` | - FRE 901(b)(9): Federal Rules of Evidence, authentication of system-produced records. |  |
| `llms.txt:64` | - DoD 3000.09: Autonomous and semi-autonomous weapons systems. |  |
| `llms.txt:66` | - EU AI Act Article 12: High-risk AI logging. |  |
| `llms.txt:68` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `proving-ground/actuarial-card.js:31` | { action: 'REGULATORY CHECK', outcome: 'FAA_Part_108_compliant' }, | mirrors the protected src/domains/actuarial/scenarios.ts byte for byte; change both (HUMAN_ACTIONS.md section 6) |
| `proving-ground/demos.js:207` | { id: 'regulatory', t: 'T+1.5', sec: 19.5, type: 'REGULATORY CHECK', outcome: 'FAA_Part_108_fields_recorded' }, |  |
| `regulatory-timeline/index.html:69` | Part 108 is the FAA rulemaking for routine beyond-visual-line-of-sight operation of unmanned aircraft. It concerns how operators show their flights ran within approved parameters. |  |
| `regulatory-timeline/index.html:74` | What does EU AI Act Article 12 ask for? |  |
| `regulatory-timeline/index.html:100` | Regulatory landscape: FRE 901(b)(9), DoD 3000.09, FAA Part 108, EU AI Act Article 12 |  |
| `regulatory-timeline/index.html:101` | What FRE 901(b)(9), DoD 3000.09, FAA Part 108, and EU AI Act Article 12 ask for, and what receipts are designed to support under each. |  |
| `regulatory-timeline/index.html:118` | "keywords": "FRE 901(b)(9), DoD 3000.09, FAA Part 108, EU AI Act Article 12, autonomous systems, BVLOS, receipts-native architecture |  |
| `regulatory-timeline/index.html:167` | What it asks for. Part 108 is the FAA rulemaking for routine beyond-visual-line-of-sight operation of unmanned aircraft. It concerns how operators show their flights ran within approved parameters. |  |
| `regulatory-timeline/index.html:201` | Admissibility, which a court decides on the whole record; whether the process that produced the record was accurate; custody of the record outside the receipt. |  |
| `regulatory-timeline/index.html:221` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `regulatory-timeline/index.html:280` | FRE 901(b)(9) In force. A rule of evidence for United States federal courts; it carries no penalties. Rule 901, Cornell LII |  |
| `regulatory-timeline/index.html:281` | DoD Directive 3000.09 In force as internal Department of Defense policy on autonomy in weapon systems; it carries no civil penalties. DoDD 3000.09, esd.whs.mil |  |
| `regulatory-timeline/index.html:282` | FAA Part 108 Rulemaking in progress: a proposed rule for routine BVLOS operations. Check the Federal Register for whether a final rule has been published and its effective date. Federal Register search , FAA BVLOS page |  |
| `regulatory-timeline/index.html:283` | EU AI Act Article 12 Regulation (EU) 2024/1689, in force since 1 August 2024. Article 12 applies to high-risk systems from the dates in Article 113; check the current text for any amendment to those dates. Penalties are set in Article 99. EUR-Lex, Regulation (EU) 2024/1689 |  |
| `rna/compare/index.html:105` | Designed to support FRE 901(b)(9), DoD 3000.09, FAA Part 108, and EU AI Act Article 12 record-keeping in one record |  |
| `rna/compare/index.html:111` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `rna/index.html:207` | Federal Rule of Evidence 901(b)(9) allows authentication of evidence by describing a process or system and showing it produces an accurate result. Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `rna/index.html:226` | Exports in a form designed to support FRE 901(b)(9) authentication. |  |
| `src/domains/actuarial/scenarios.ts:59` | { action: 'REGULATORY CHECK', outcome: 'FAA_Part_108_compliant' }, | protected file: before/after in HUMAN_ACTIONS.md |

96 line(s).

### inquiro-rna-sdk

| file:line | sentence | note |
|---|---|---|
| `README.md:7` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |
| `docs/EVENT_TYPES.md:29` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |

2 line(s).

### AIFlightRecorder

| file:line | sentence | note |
|---|---|---|
| `pilot/README.md:17` | Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction. | approved sentence |

1 line(s).

## 8. Second pass, 17 October 2026: the regulatory framework pages

The hub and four pages were already reworded in the first pass (section 2). The second pass, Inquiro-Website- pull request from branch `claude/eager-dirac-2n94d5`, removed what was left. Line numbers are in that branch. Section 7 above lists these pages at their first-pass lines; where a sentence below differs from section 7, this section is current.

| Page (Inquiro-Website-) | Before | After |
|---|---|---|
| `compliance/eu-ai-act-article-12/index.html:152-158` | "Any change to a sealed receipt breaks its hashes and signature, so alteration is detectable by anyone who runs verification." / "This is designed to support the Article 12 traceability requirement ... tamper-evident (any post-hoc change is detectable)" | Three bullets: any change to a sealed receipt breaks its hashes and signature; deletion or reordering is detectable by a verifier holding the chain or a prior head; a wholesale rewrite by someone with write access to the whole ledger is detectable only against a previously stored head or checkpoint. Then "designed to support Article 12 record-keeping", "does not show that every event was sealed or that a recorded event was correct", link to `docs/THREAT_MODEL.md`. |
| same, `:159` | (none) | Note: "Designed to support: tamper-evident, independently verifiable event records. Does not address: whether a system is high-risk under the Act, whether its logging meets Article 12, retention periods, or whether every event was recorded." |
| same, `:84`, `:203` | (none) | New FAQ "What changes to a log can a verifier detect?" with the three-part answer. `chain_intact` described as confirming "the chain the verifier holds has no gap or mismatched reference" (was "the full log is unbroken"). |
| `compliance/dod-3000-09/index.html:63, 140, 172` | "It also sets out review and approval steps for such systems; read the directive for those." | "It also addresses verification and validation (V&V) and test and evaluation (T&E) of such systems; read the directive for its text on those." (Q9) |
| same, throughout | "an engagement" (lede, `parent_receipts` row, verification steps, closing paragraph) | "a decision". "Rules of engagement" is kept where the page says a receipt does not replace them. |
| same, `:166` | (none) | Note: "Designed to support: a signed, timestamped record of who was assigned each RACI role for a decision. Does not address: whether the human judgment exercised was appropriate, whether a system meets the directive, or command authority and legal accountability." |
| same | "The Accountable entry identifies the human in the chain of command who owned the decision." "confirm the record has not been altered". "confirm the entire lineage is unaltered." | "records the human who was assigned ownership of the decision". "has not changed since it was sealed". "the chain it holds has no gap or mismatched reference". |
| `compliance/fre-901/index.html:15, 43, 136, 95, 187` | "a third party recomputes the dual hash and checks the Ed25519 signature against a signing key the verifier already trusts, with no call to Inquiro required" | "you recompute the dual hash and check the Ed25519 signature, trusting only a signing key you already hold" (Q10). "A valid signature proves the body was signed by the holder of the private key" became "shows ... Whether that key belongs to the party it claims is checked against a key you already hold." |
| same, `:165` | (none) | Note: "Designed to support: authentication of a system-produced record by a verifier who holds the signing key. Does not address: whether the recorded event was correct, whether the process that produced it was accurate, or admissibility, which a court decides on the whole record." |
| `compliance/index.html:92, 109` | FRE row: "against a signing key it already trusts, with no call to Inquiro required" | "trusting only a signing key you already hold". New note: "Does not address: whether the recorded event was correct, whether a process was accurate, whether a system is lawful, or whether any framework applies to a given system. Those questions are for counsel." |
| the three field tables | Column header "Role in authentication" / "Role in accountability review" / "Role in Article 12 logging" | "Designed to support" |
| `llms-full.txt:24-30, 42-70, 188` | "any alteration to a sealed record is detectable when the chain is verified"; "the directive's design, review, and approval steps"; "a third party recomputes the hashes ... a signing key it already trusts"; "Tampering is detectable by verifying the chain." | The same three-part statement; V&V and T&E; "trusting only a signing key you already hold". |

Phrases from the audit list that were already gone before this pass (removed in section 2): "satisfy" / "satisfies", "Role in compliance", "How chained receipts satisfy the requirement" (now "are designed to support it"), "Yes, conditionally.", "The math is the proof", "compliance challenge", "No alteration is possible after sealing without detection", "This satisfies the Article 12 traceability requirement". The claims lint now bans "satisfy", "satisfies", "compliance challenge", "Role in compliance" and "No alteration is possible" (it already banned "cannot be altered"), scans the hub and the four pages, and `scripts/final_audit.sh` section 7 checks the live copies of all five for the same phrases and for the approved sentence.

Not changed, for the owner or counsel: `rna/index.html:129, 254` ("It proves the action happened when it says it did and has not been altered since"; `docs/THREAT_MODEL.md` section 3 says nothing in the chain proves a timestamp is correct); `regulatory-timeline/index.html:177` and `rna/index.html:145, 262` ("any change ... is detectable by anyone who runs verification", accurate for a changed receipt, silent on deletion and rewrite); `compliance/faa-part-108/index.html:71, 176` ("any alteration breaks the chain and is detectable"); `.well-known/rna-spec.json:5, 65` ("with no trust in the issuer", "None of them require trusting Inquiro"; protected file).
