"""Claims lint for the SDK's reader-facing docs (docs/LEGAL_LANGUAGE.md). No network.

The banned phrases may appear only inside the approved legal sentence. Files that
quote banned phrases on purpose (the legal-language doc itself, the audit records,
the counsel packet, HUMAN_ACTIONS.md) are not scanned.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNED = ["built to comply", "complies", "compliant", "compliance-ready", "guarantee", "guaranteed", "guarantees",
          "certified", "court-admissible", "court admissible", "admissible in court", "courts admit"]
SCANNED = ["README.md", "SECURITY.md", "verifier/README.md", "mock/README.md",
           "docs/**/*.md", "examples/**/README.md", "payloads/**/README.md"]
NOT_SCANNED = {"docs/LEGAL_LANGUAGE.md"}


def approved_sentence() -> str:
    doc = (ROOT / "docs" / "LEGAL_LANGUAGE.md").read_text(encoding="utf-8")
    return re.search(r"^> (.+)$", doc, re.M).group(1)


def violations(text: str, approved: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).replace(approved, " ")
    return [m.group(0) for term in BANNED
            for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(term).replace(r"\ ", r"\s+") + r"(?![A-Za-z0-9])", text, re.I)]


def test_reader_facing_docs_carry_no_banned_claim():
    approved = approved_sentence()
    files = sorted({p for g in SCANNED for p in ROOT.glob(g)} - {ROOT / n for n in NOT_SCANNED})
    assert len(files) > 5
    found = {str(f.relative_to(ROOT)): v for f in files if (v := violations(f.read_text(encoding="utf-8"), approved))}
    assert found == {}


def test_banned_phrases_are_caught_and_the_approved_sentence_is_not():
    approved = approved_sentence()
    assert "compliance or admissibility" in approved
    assert violations(f"Intro. {approved} Outro.", approved) == []
    for claim in ["Built to comply with FRE 901(b)(9).", "It complies.", "A certified, court-admissible record.", "We guarantee it."]:
        assert violations(claim, approved), claim


def test_readme_carries_the_approved_sentence_verbatim():
    assert approved_sentence() in re.sub(r"\s+", " ", (ROOT / "README.md").read_text(encoding="utf-8"))
