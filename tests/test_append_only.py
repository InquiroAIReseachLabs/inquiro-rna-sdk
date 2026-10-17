"""Append-only behaviour of the offline kit.

The sealer only appends and refuses a ledger it would have to repair; the verifier
reports gaps, and, given something recorded outside the file, truncation and re-signing.
What none of this can do is stop someone with write access to the file: that is stated
in docs/THREAT_MODEL.md and shown by the last tests here.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from offline.seal import LedgerRefused, Sealer, generate_keypair, load_private_key
from offline.verify import load_public_key, verify_ledger

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def kit(tmp_path):
    generate_keypair(tmp_path / "k.pem", tmp_path / "k.pub")
    key = load_private_key(tmp_path / "k.pem")
    sealer = Sealer(tmp_path / "r.jsonl", key)
    for i in range(5):
        sealer.seal("reading", payload={"n": i}, ts=f"2026-10-17T09:00:0{i}Z")
    return tmp_path, key, load_public_key(tmp_path / "k.pub")


def _lines(path):
    return path.read_text().splitlines()


def _problems(result):
    return [i["problem"] for i in result["issues"]]


# --- sealer ---------------------------------------------------------------

def test_sealing_only_adds_bytes(kit):
    d, key, _ = kit
    before = (d / "r.jsonl").read_bytes()
    Sealer(d / "r.jsonl", key).seal("reading", payload={"n": 5})
    after = (d / "r.jsonl").read_bytes()
    assert after.startswith(before) and len(after) > len(before)


def test_ledger_is_opened_append_only(kit, monkeypatch):
    d, key, _ = kit
    seen = []
    real = os.open

    def spy(path, flags, *a, **k):
        seen.append((str(path), flags))
        return real(path, flags, *a, **k)

    monkeypatch.setattr(os, "open", spy)
    Sealer(d / "r.jsonl", key).seal("reading", payload={"n": 5})
    flags = [f for p, f in seen if p.endswith("r.jsonl")]
    assert flags and all(f & os.O_APPEND and f & os.O_ACCMODE == os.O_WRONLY and not f & os.O_TRUNC for f in flags)


def test_seal_source_has_no_write_or_truncate_open():
    src = (ROOT / "offline" / "seal.py").read_text()
    assert "O_TRUNC" not in src and "O_RDWR" not in src
    # The only writes in seal.py: the key pair at keygen, and the os.open append.
    writes = re.findall(r"\.(write_text|write_bytes|unlink|truncate|rename|replace)\(", src)
    assert sorted(writes) == ["write_bytes", "write_text"], writes  # keygen: private PEM and public key


@pytest.mark.parametrize("damage, expect", [
    (lambda p: p.write_bytes(p.read_bytes()[:-20]), "complete line"),            # cut mid-receipt
    (lambda p: p.write_bytes(p.read_bytes().rstrip(b"\n")), "complete line"),     # newline lost
    (lambda p: p.write_bytes(p.read_bytes() + b"garbage\n"), "not a receipt"),
    (lambda p: p.write_bytes(p.read_bytes().replace(b'"n": 4', b'"n": 9')), "does not verify"),
])
def test_sealer_refuses_damaged_ledger_and_leaves_it_alone(kit, damage, expect):
    d, key, _ = kit
    ledger = d / "r.jsonl"
    damage(ledger)
    before = ledger.read_bytes()
    with pytest.raises(LedgerRefused, match=expect):
        Sealer(ledger, key).seal("reading", payload={"n": 5})
    assert ledger.read_bytes() == before


def test_sealer_refuses_ledger_from_another_key(kit):
    d, _, _ = kit
    generate_keypair(d / "other.pem", d / "other.pub")
    before = (d / "r.jsonl").read_bytes()
    with pytest.raises(LedgerRefused, match="spans one key"):
        Sealer(d / "r.jsonl", load_private_key(d / "other.pem"))
    assert (d / "r.jsonl").read_bytes() == before


def test_two_sealers_on_one_ledger_never_repeat_a_seq(kit):
    d, key, pub = kit
    a, b = Sealer(d / "r.jsonl", key), Sealer(d / "r.jsonl", key)  # both start at seq 5
    a.seal("x", payload={"w": "a"})
    b.seal("x", payload={"w": "b"})  # stale cached state must not fork the chain
    a.seal("x", payload={"w": "a"})
    result = verify_ledger(_lines(d / "r.jsonl"), pub)
    assert result["ok"], result
    assert result["count"] == 8


def test_cli_refuses_damaged_ledger(kit):
    d, _, _ = kit
    ledger = d / "r.jsonl"
    ledger.write_bytes(ledger.read_bytes()[:-20])
    before = ledger.read_bytes()
    r = subprocess.run([sys.executable, "-m", "offline", "seal", "--ledger", str(ledger), "--key", str(d / "k.pem"),
                        "--event-type", "x", "--payload", "{}"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2 and "refused" in r.stderr
    assert ledger.read_bytes() == before


def test_bundle_will_not_overwrite_the_ledger(kit):
    d, _, _ = kit
    before = (d / "r.jsonl").read_bytes()
    r = subprocess.run([sys.executable, "-m", "offline", "bundle", "--ledger", str(d / "r.jsonl"),
                        "--public", str(d / "k.pub"), "--out", str(d / "r.jsonl")],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2
    assert (d / "r.jsonl").read_bytes() == before


# --- verifier: gaps, truncation, re-signing --------------------------------

def test_gap_is_flagged(kit):
    d, _, pub = kit
    rows = _lines(d / "r.jsonl")
    result = verify_ledger(rows[:2] + rows[3:], pub)
    assert not result["ok"]
    assert any("seq jumps 2 -> 4: 1 receipt(s) missing" in p for p in _problems(result))


def _resign_from(d, key, start):
    """What a key holder can do: rebuild the ledger with receipt `start` altered, re-chained and re-signed."""
    rows = [json.loads(l) for l in _lines(d / "r.jsonl")]
    out = d / "rewritten.jsonl"
    keep = rows[:start - 1]
    out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in keep))
    s = Sealer(out, key)
    for r in rows[start - 1:]:
        payload = dict(r["payload"], n=r["payload"]["n"] + 100) if r["seq"] == start else r["payload"]
        s.seal(r["event_type"], payload=payload, ts=r["ts"])
    return out


def test_resigned_ledger_verifies_on_its_own(kit):
    """Documents the limit: the file alone cannot show a rewrite by the key holder."""
    d, key, pub = kit
    out = _resign_from(d, key, 3)
    assert verify_ledger(_lines(out), pub)["ok"]


def test_resigned_ledger_is_flagged_against_a_recorded_head(kit):
    d, key, pub = kit
    original = [json.loads(l) for l in _lines(d / "r.jsonl")]
    head = (original[-1]["seq"], original[-1]["receipt_hash"])
    out = _resign_from(d, key, 3)
    result = verify_ledger(_lines(out), pub, head=head)
    assert not result["ok"]
    assert any("rewritten or re-signed: seq 5" in p for p in _problems(result))


def test_resigned_ledger_is_flagged_against_an_earlier_export(kit):
    d, key, pub = kit
    earlier = _lines(d / "r.jsonl")
    out = _resign_from(d, key, 3)
    result = verify_ledger(_lines(out), pub, against=earlier)
    assert any("rewritten or re-signed: seq 3" in p and "3 receipts differ" in p for p in _problems(result))


def test_tail_truncation_is_flagged_with_head_and_against(kit):
    d, _, pub = kit
    rows = _lines(d / "r.jsonl")
    head = (5, json.loads(rows[-1])["receipt_hash"])
    cut = rows[:3]
    assert verify_ledger(cut, pub)["ok"]  # alone it still verifies
    for kwargs in ({"head": head}, {"against": rows}):
        result = verify_ledger(cut, pub, **kwargs)
        assert not result["ok"]
        assert any("truncated: ledger ends at seq 3" in p for p in _problems(result)), kwargs


def test_appended_ledger_passes_against_an_earlier_export(kit):
    d, key, pub = kit
    earlier = _lines(d / "r.jsonl")
    Sealer(d / "r.jsonl", key).seal("reading", payload={"n": 5})
    assert verify_ledger(_lines(d / "r.jsonl"), pub, against=earlier)["ok"]


def test_non_integer_seq_does_not_crash_the_verifier(kit):
    d, _, pub = kit
    rows = _lines(d / "r.jsonl")
    r = json.loads(rows[1])
    r["seq"] = "2"
    rows[1] = json.dumps(r, sort_keys=True)
    result = verify_ledger(rows, pub)
    assert not result["ok"]


def test_verify_cli_head_and_against(kit):
    d, key, _ = kit
    rows = _lines(d / "r.jsonl")
    head = f"5:{json.loads(rows[-1])['receipt_hash']}"
    out = _resign_from(d, key, 3)

    def run(*a):
        return subprocess.run([sys.executable, "-m", "offline", "verify", *a], cwd=ROOT, capture_output=True, text=True)
    assert run(str(out), str(d / "k.pub")).returncode == 0
    assert run(str(out), str(d / "k.pub"), "--head", head).returncode == 1
    r = run(str(out), str(d / "k.pub"), "--against", str(d / "r.jsonl"))
    assert r.returncode == 1 and "re-signed" in r.stdout
