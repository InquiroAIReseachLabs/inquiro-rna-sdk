"""Offline kit: seal, verify, tamper detection, evaluator bundle. No network."""
import base64
import json
import os
import random
import subprocess
import sys
import zipfile
from pathlib import Path

import blake3
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline.bundle import make_bundle
from offline.purepy import blake3_hex, ed25519_verify
from offline.seal import Sealer, generate_keypair, load_private_key
from offline.verify import canonical, dual_hash, load_public_key, report, verify_ledger

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def kit(tmp_path):
    generate_keypair(tmp_path / "k.pem", tmp_path / "k.pub")
    sealer = Sealer(tmp_path / "r.jsonl", load_private_key(tmp_path / "k.pem"))
    for i in range(5):
        sealer.seal("reading", payload={"n": i, "label": f"item-{i}"}, ts=f"2026-10-17T09:00:0{i}Z")
    return tmp_path, load_public_key(tmp_path / "k.pub")


def _lines(path):
    return path.read_text().splitlines()


def _write(path, receipts):
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in receipts))


# --- pure-Python fallbacks match the native libraries ---

@pytest.mark.parametrize("n", [0, 1, 63, 64, 65, 1023, 1024, 1025, 2048, 3073, 8193, 17000])
def test_pure_blake3_matches_native(n):
    data = random.Random(n).randbytes(n)
    assert blake3_hex(data) == blake3.blake3(data).hexdigest()


def test_pure_ed25519_matches_native():
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    for i in range(10):
        msg = random.Random(i).randbytes(i * 17)
        sig = key.sign(msg)
        assert ed25519_verify(pub, msg, sig)
        assert not ed25519_verify(pub, msg + b"!", sig)
        assert not ed25519_verify(pub, msg, sig[:-1] + bytes([sig[-1] ^ 1]))


# --- sealing and verification ---

def test_intact_ledger_verifies(kit):
    d, pub = kit
    result = verify_ledger(_lines(d / "r.jsonl"), pub)
    assert result["ok"], result
    assert report(result).startswith("VERIFIED: 5 receipts")


def test_sealer_resumes_an_existing_ledger(kit):
    d, pub = kit
    r = Sealer(d / "r.jsonl", load_private_key(d / "k.pem")).seal("reading", payload={"n": 5})
    assert r["seq"] == 6
    assert verify_ledger(_lines(d / "r.jsonl"), pub)["ok"]


def test_receipt_recomputes_by_hand(kit):
    d, _ = kit
    r = json.loads(_lines(d / "r.jsonl")[0])
    body = {k: v for k, v in r.items() if k not in ("receipt_hash", "signature")}
    assert dual_hash(canonical(body)) == r["receipt_hash"]
    assert r["payload_digest"] == dual_hash(canonical(r["payload"]))


@pytest.mark.parametrize("attack,expected", [
    ("edit_payload", "receipt_hash does not match"),
    ("delete_middle", "receipt(s) missing"),
    ("reorder", "out of order"),
    ("duplicate", "out of order or duplicated"),
    ("truncate_head", "chain starts at seq 2"),
    ("forge_resign_other_key", "signed by key"),
    ("edit_and_rehash", "signature does not verify"),
])
def test_tampering_is_reported(kit, attack, expected):
    d, pub = kit
    rs = [json.loads(l) for l in _lines(d / "r.jsonl")]
    if attack == "edit_payload":
        rs[2]["payload"]["n"] = 99
    elif attack == "delete_middle":
        del rs[2]
    elif attack == "reorder":
        rs[1], rs[2] = rs[2], rs[1]
    elif attack == "duplicate":
        rs.insert(3, rs[2])
    elif attack == "truncate_head":
        rs = rs[1:]
    elif attack == "forge_resign_other_key":
        other = Ed25519PrivateKey.generate()
        raw = other.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        import hashlib
        rs[2]["key_id"] = hashlib.sha256(raw).hexdigest()[:16]
    elif attack == "edit_and_rehash":
        rs[2]["payload"]["n"] = 99
        rs[2]["payload_digest"] = dual_hash(canonical(rs[2]["payload"]))
        body = {k: v for k, v in rs[2].items() if k not in ("receipt_hash", "signature")}
        rs[2]["receipt_hash"] = dual_hash(canonical(body))
    _write(d / "bad.jsonl", rs)
    result = verify_ledger(_lines(d / "bad.jsonl"), pub)
    assert not result["ok"]
    assert any(expected in i["problem"] for i in result["issues"]), result["issues"]


def test_wrong_public_key_fails(kit, tmp_path):
    d, _ = kit
    generate_keypair(tmp_path / "other.pem", tmp_path / "other.pub")
    assert not verify_ledger(_lines(d / "r.jsonl"), load_public_key(tmp_path / "other.pub"))["ok"]


def test_partial_export_verifies_with_allow_partial(kit):
    d, pub = kit
    tail = _lines(d / "r.jsonl")[2:]
    assert not verify_ledger(tail, pub)["ok"]
    assert verify_ledger(tail, pub, allow_partial=True)["ok"]


def test_digest_mode_keeps_the_payload_out(kit):
    d, pub = kit
    secret = {"position": [12.345, 67.89], "note": "stays on the device"}
    r = Sealer(d / "r.jsonl", load_private_key(d / "k.pem")).seal("reading", digest=dual_hash(canonical(secret)))
    assert "payload" not in r and r["payload_mode"] == "digest"
    assert "stays on the device" not in (d / "r.jsonl").read_text()
    assert verify_ledger(_lines(d / "r.jsonl"), pub)["ok"]
    with pytest.raises(ValueError):
        Sealer(d / "r.jsonl", load_private_key(d / "k.pem")).seal("reading", digest="not-a-digest")


def test_private_key_file_is_owner_only(tmp_path):
    generate_keypair(tmp_path / "k.pem", tmp_path / "k.pub")
    assert oct((tmp_path / "k.pem").stat().st_mode & 0o777) == "0o600"


# --- evaluator bundle ---

def _unzip(zip_path, dest):
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest)
    return dest / "evaluator_bundle"


def test_bundle_contents_and_checksums(kit):
    d, _ = kit
    summary = make_bundle(d / "r.jsonl", d / "k.pub", d / "b.zip")
    assert summary.startswith("VERIFIED")
    b = _unzip(d / "b.zip", d / "x")
    assert sorted(p.name for p in b.iterdir()) == [
        "README.txt", "SHA256SUMS", "public_key.pub", "purepy.py", "receipts.jsonl", "verify.py"]
    import hashlib
    for line in (b / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ")
        assert hashlib.sha256((b / name).read_bytes()).hexdigest() == digest
    assert "VERIFIED: 5 receipts" in (b / "README.txt").read_text()


@pytest.mark.parametrize("pure", [False, True], ids=["native", "pure-python"])
def test_bundle_verifies_in_isolation(kit, pure):
    """Run the bundled verifier as a stranger would: its own directory, isolated
    interpreter (-I: no PYTHONPATH, no user site), optionally with no crypto packages."""
    d, _ = kit
    make_bundle(d / "r.jsonl", d / "k.pub", d / "b.zip")
    b = _unzip(d / "b.zip", d / "x")
    env = {"PATH": os.environ.get("PATH", ""), **({"RNA_VERIFY_PURE": "1"} if pure else {})}
    ok = subprocess.run([sys.executable, "-I", "verify.py", "receipts.jsonl", "public_key.pub"],
                        cwd=b, env=env, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout.startswith("VERIFIED: 5 receipts")
    rs = [json.loads(l) for l in (b / "receipts.jsonl").read_text().splitlines()]
    rs[1]["payload"]["n"] = 7
    _write(b / "receipts.jsonl", rs)
    bad = subprocess.run([sys.executable, "-I", "verify.py", "receipts.jsonl", "public_key.pub"],
                         cwd=b, env=env, capture_output=True, text=True)
    assert bad.returncode == 1
    assert "edited receipt" in bad.stdout


def test_cli_end_to_end(tmp_path):
    def cli(*args):
        return subprocess.run([sys.executable, "-m", "offline", *args], cwd=ROOT, capture_output=True, text=True)
    assert cli("keygen", "--private", str(tmp_path / "s.pem"), "--public", str(tmp_path / "s.pub")).returncode == 0
    for i in range(3):
        assert cli("seal", "--ledger", str(tmp_path / "r.jsonl"), "--key", str(tmp_path / "s.pem"),
                   "--event-type", "reading", "--payload", json.dumps({"n": i})).returncode == 0
    v = cli("verify", str(tmp_path / "r.jsonl"), str(tmp_path / "s.pub"))
    assert v.returncode == 0 and v.stdout.startswith("VERIFIED: 3 receipts")
    b = cli("bundle", "--ledger", str(tmp_path / "r.jsonl"), "--public", str(tmp_path / "s.pub"),
            "--out", str(tmp_path / "b.zip"))
    assert b.returncode == 0 and (tmp_path / "b.zip").exists()
