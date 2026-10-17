"""scripts/link_crawl.py: allowlisted URLs are NEEDS HUMAN CHECK, never FAIL. No network."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("link_crawl", ROOT / "scripts" / "link_crawl.py")
crawl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crawl)


def test_every_entry_has_a_reason():
    allow = crawl.load_allowlist()
    assert allow and all(prefix.startswith("https://") and len(reason) > 20 for prefix, reason in allow)


def test_matching_is_by_prefix_and_case_insensitive():
    allow = crawl.load_allowlist()
    assert crawl.allowlisted("https://aiflightrecorder.onrender.com/health", allow)
    assert crawl.allowlisted("https://github.com/inquiroairesearchlabsinc/inquiro-rna-sdk", allow)
    assert crawl.allowlisted("https://eur-lex.europa.eu/eli/reg/2024/1689/oj", allow)
    assert crawl.allowlisted("https://aiflightrecorder-1.onrender.com/health", allow) is None
    assert crawl.allowlisted("https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk", allow) is None


def _run(monkeypatch, capsys, urls):
    monkeypatch.setattr(crawl, "collect", lambda root, website: {u: {"x:1"} for u in urls})
    monkeypatch.setattr(crawl, "check", lambda u: ("FAIL", ["403"]))
    monkeypatch.setattr(crawl.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["link_crawl.py"])
    rc = crawl.main()
    return rc, capsys.readouterr().out


def test_allowlisted_failures_do_not_fail_the_run(monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, ["https://www.faa.gov/uas/", "https://www.esd.whs.mil/x.pdf"])
    assert rc == 0
    assert out.count("NEEDS HUMAN CHECK  403") == 2 and "bot protection" in out
    assert "NEEDS_HUMAN_CHECK=2 FAIL=0" in out


def test_other_failures_still_fail(monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, ["https://www.faa.gov/uas/", "https://inquiroresearchlabs.ai/missing/"])
    assert rc == 1
    assert "FAIL  403  https://inquiroresearchlabs.ai/missing/" in out
