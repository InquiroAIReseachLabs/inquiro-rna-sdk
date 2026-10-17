# Legal language

**Status: PENDING COUNSEL.** The owner approved the sentence below for use now. Counsel has not reviewed it yet; the questions for counsel are in `counsel/COUNSEL_REVIEW.md` in the inquiro-rna-sdk repository. This file is kept word for word at `docs/LEGAL_LANGUAGE.md` in both inquiro-rna-sdk and Inquiro-Website-; the website's claims lint test checks the sentence against its copy. Change both copies together.

## The approved sentence

> Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction.

Use it verbatim, as one paragraph. Do not shorten it, split it, or add to it.

## Where it goes

Every surface that names FRE 901(b)(9), DoD Directive 3000.09, FAA Part 108 or the EU AI Act, or that says "compliance", carries the approved sentence once, near the first such mention. As of 17 October 2026:

| Repository | Surface |
|---|---|
| Inquiro-Website- | `regulatory-timeline/index.html` (under the matrix), `compliance/index.html` and the four pages under `compliance/`, `rna/compare/index.html`, `company/index.html`, `rna/index.html`, `llms.txt`, `llms-full.txt` |
| inquiro-rna-sdk | `README.md`, `docs/EVENT_TYPES.md` |
| AIFlightRecorder | `pilot/README.md` |

Surfaces that cannot be edited from these repositories (the protected website files, Gumroad, LinkedIn, X, decks, the Starcloud site) have before/after text in `HUMAN_ACTIONS.md` in inquiro-rna-sdk.

## How to word everything else

1. **Link a receipt to a framework only with "designed to support".** "Receipts are designed to support FRE 901(b)(9) authentication", not "receipts satisfy", "meet", "map to", "cover" or "answer" a framework.
2. **Tables use two columns: "Designed to support" and "Does not address".** No check marks, crosses, Yes/No or traffic lights against a framework.
3. **Say what a framework asks for in neutral words close to its text, and link the primary source.** Do not write "requires" or "mandates" unless the text says so. Questions about what a text says go to counsel.
4. **State rulemaking status with the date it was checked.** No deadlines and no penalty amounts on public pages.
5. **A receipt shows integrity and, given a trusted key, authorship.** It does not show that the recorded event was correct, that a process was accurate, or that a system is lawful.

## Banned outside the approved sentence

`built to comply`, `complies`, `compliant`, `compliance-ready`, `guarantee` (and `guaranteed`, `guarantees`), `certified`, `court-admissible` (and `court admissible`, `admissible in court`), `courts admit`.

Also banned, because they tie a receipt to a framework as if it met it or overstate what a seal shows: `satisfy`, `satisfies`, `compliance challenge`, `Role in compliance`, `No alteration is possible`, `cannot be altered`. Say what a verifier can detect as `docs/THREAT_MODEL.md` (inquiro-rna-sdk) states it: any change to a sealed receipt breaks its hashes and signature; deletion or reordering is detectable by a verifier holding the chain or a prior head; a wholesale rewrite by someone with write access to the whole ledger is detectable only against a previously stored head or checkpoint.

"Compliance" itself is not banned: the approved sentence uses it, and the `/compliance/` URLs stay. Do not use it as a claim ("compliance solution", "assess compliance with receipts").

Enforced by:

- **Website:** `scripts/claims-lint.mjs` (`npm run check:claims`; also `tests/claims_lint.test.ts`, run in preflight). One temporary exception: "compliant client" in the protected `.well-known/rna-spec.json`, until Matthew applies the before/after in `HUMAN_ACTIONS.md`; the editable `/spec/` page now says "conforming client".
- **SDK:** `tests/test_claims_copy.py` scans `README.md` and the docs.
- **Pilot:** `tests/test_claims_copy.py` in AIFlightRecorder scans `pilot/*.md` and `SECURITY.md`.

Files that quote banned phrases on purpose (this file, the audit records, the counsel packet, `HUMAN_ACTIONS.md`) are excluded from those scans by name.
