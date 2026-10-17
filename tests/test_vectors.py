"""Known-answer vectors (docs/TEST_VECTORS.md). Fails if any verifier disagrees.

Runs under pytest, or directly:  python3 tests/test_vectors.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "verifier"))

from canonical_payload import canonical_bytes  # noqa: E402
from offline.purepy import blake3_hex, ed25519_verify  # noqa: E402
from offline.verify import GENESIS, canonical, dual_hash, key_id, report, signature_ok, verify_ledger  # noqa: E402
import verify as live_verifier  # noqa: E402  (verifier/verify.py; imported at collection time, before the
# no-network fixture replaces socket.socket, because it pulls in urllib and ssl)

DOC = ROOT / "docs" / "TEST_VECTORS.md"
PATTERN = bytes(range(256)) * 5

HASH_VECTORS = [  # (label, data, sha256, blake3)
    ("empty", b"",
     "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
     "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262"),
    ("abc", b"abc",
     "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
     "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85"),
    ("fox", b"The quick brown fox jumps over the lazy dog",
     "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592",
     "2f1514181aadccd913abd94cfa592701a5686ab23f8df1dff1b74710febc6d4a"),
    ("1024", PATTERN[:1024],
     "785b0751fc2c53dc14a4ce3d800e69ef9ce1009eb327ccf458afe09c242c26c9",
     "882179b8dbccd285cda241d968cfcccb3156c5edac2fa3761bb6eda7ff8cb172"),
    ("1025", PATTERN[:1025],
     "b3981d93eeb64aa900f3e48cfcd48e9bbc89b77732c49ea201c93656c62b6a09",
     "3e85e5a7ffcd07c23794c079d43ebb27372d06bb1f75e4b47732fcaaf1a8cf3d"),
]

ED25519_VECTORS = [  # RFC 8032 section 7.1: (secret, public, message, signature, key_id)
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
     "21fe31dfa154a261"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
     "39f713d0a644253f"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
     "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025", "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a",
     "dac073e0123bdea5"),
]

CANON_OBJ = {"b": 1, "a": [1, 2, {"z": True, "y": None}], "c": "é", "d": 1.5, "e": "tab\there"}
CANON_OFFLINE = b'{"a":[1,2,{"y":null,"z":true}],"b":1,"c":"\\u00e9","d":1.5,"e":"tab\\there"}'
CANON_OFFLINE_SHA = "6c8a3696a2a1a8b430297bbf4799dc5697f83ea0cb2a807afb8b24d7e0c23d28"
CANON_OFFLINE_B3 = "7227b8a96f0b33c979a8faec1e32d835e941e33ad55478b84c579bd03535ad1c"
CANON_LIVE = b'{"a": [1, 2, {"y": null, "z": true}], "b": 1, "c": "\\u00e9", "d": 1.5, "e": "tab\\there"}'
CANON_LIVE_SHA = "9b9008eb60c6234f4f61936c0ead1a5ae52c528ca2681bb78b8bc9a7355dbb0d"
CANON_LIVE_B3 = "43b9cababb9aa6bf114c58f452647dad7ceaa8230effc00204789d87245b091d"

RECEIPT_1 = {
    "event_type": "launch", "key_id": "21fe31dfa154a261", "payload": {"airframe_id": "UAS-DEMO-01"},
    "payload_digest": "913985f19a6b1120851ec974214a4f2feeaba4bfa02474edd34e6f0028ca44ae:36781cb8c6264efa06999206c54f7c112eccbe3661a1295a1e29c3c3e2c1fafb",
    "payload_mode": "full", "prev_hash": GENESIS,
    "receipt_hash": "a0d92eb44c50787c80175d5667dab4076da1a2f7b95b704ae505c181afe70348:9ac96a38a3697490a4e58c211709818b75d637e17ef7268f636d2af8812aab1e",
    "seq": 1, "signature": "PBK1r6t/Qn3ljAL1CrVY347Z9EJv3pOEVMx0Dj6f50ZkgR0X3lh9fLtK1xYREPiB47gbwHsrSgE5bMOK2mKYAA==",
    "ts": "2026-10-17T00:00:00.000000Z", "v": 1,
}
RECEIPT_2 = {
    "event_type": "land", "key_id": "21fe31dfa154a261", "payload": {"pad": "A"},
    "payload_digest": "6a6ef4622d450b11e23cb601d8e4845036ba406bf58871fa16a2b7e7cf65b8ef:2fcd1966b8c1620f21e2d0ded8dc44317d76508b61e89af3dbe9da5f288b68b5",
    "payload_mode": "full", "prev_hash": RECEIPT_1["receipt_hash"],
    "receipt_hash": "4a5eda74cd732e7a78b6f4d4656f14c3ecc9087b77b782b885a97d8977b25220:bdf7074bb4577d5b5ffa2ed77618c1db6f5f52d1cf8b67099514085d8f41ac85",
    "seq": 2, "signature": "DqwpzfFn8wfnvxggxDi7l/CymbMjMWdSoTnreb/zIDK7+6wKwY8yjZphxLa4tRAJbrRlRjU615k3O7DNZpUTCw==",
    "ts": "2026-10-17T00:01:00.000000Z", "v": 1,
}


def _flip_last_bit(b: bytes) -> bytes:
    return b[:-1] + bytes([b[-1] ^ 1])


# --- SHA-256 and BLAKE3 ---

def test_sha256_known_answers():
    for label, data, sha, _ in HASH_VECTORS:
        assert hashlib.sha256(data).hexdigest() == sha, label


def test_blake3_known_answers_native_and_pure():
    import blake3
    for label, data, _, b3 in HASH_VECTORS:
        assert blake3.blake3(data).hexdigest() == b3, f"native blake3: {label}"
        assert blake3_hex(data) == b3, f"pure-Python blake3: {label}"


def test_dual_hash_known_answers():
    for label, data, sha, b3 in HASH_VECTORS:
        assert dual_hash(data) == f"{sha}:{b3}", label


# --- Ed25519 ---

def test_ed25519_rfc8032_vectors_verify():
    for _, pk, msg, sig, kid in ED25519_VECTORS:
        pk_b, msg_b, sig_b = bytes.fromhex(pk), bytes.fromhex(msg), bytes.fromhex(sig)
        assert signature_ok(pk_b, msg_b, sig_b), pk
        assert ed25519_verify(pk_b, msg_b, sig_b), f"pure-Python: {pk}"
        assert key_id(pk_b) == kid


def test_ed25519_rfc8032_private_keys_derive_the_public_keys_and_signatures():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    for sk, pk, msg, sig, _ in ED25519_VECTORS:
        priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(sk))
        pub = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        assert pub.hex() == pk
        assert priv.sign(bytes.fromhex(msg)).hex() == sig


def test_ed25519_rejections():
    pk0 = bytes.fromhex(ED25519_VECTORS[0][1])
    for _, pk, msg, sig, _ in ED25519_VECTORS:
        pk_b, msg_b, sig_b = bytes.fromhex(pk), bytes.fromhex(msg), bytes.fromhex(sig)
        for fn in (signature_ok, ed25519_verify):
            assert not fn(pk_b, msg_b + b"\x00", sig_b), "extra message byte accepted"
            assert not fn(pk_b, msg_b, _flip_last_bit(sig_b)), "flipped signature bit accepted"
            if pk_b != pk0:
                assert not fn(pk0, msg_b, sig_b), "wrong public key accepted"


# --- Canonical JSON ---

def test_canonical_json_offline_rule():
    assert canonical(CANON_OBJ) == CANON_OFFLINE
    assert canonical_bytes(CANON_OBJ) == CANON_OFFLINE
    assert dual_hash(CANON_OFFLINE) == f"{CANON_OFFLINE_SHA}:{CANON_OFFLINE_B3}"


def test_canonical_json_live_rule():
    assert json.dumps(CANON_OBJ, sort_keys=True).encode() == CANON_LIVE
    assert live_verifier._dual_hex(CANON_LIVE.decode()) == (CANON_LIVE_SHA, CANON_LIVE_B3)


def test_live_verifier_recomputes_a_receipt_body_with_the_live_rule():
    body = dict(CANON_OBJ)
    body["payload_hash"] = f"{CANON_LIVE_SHA}:{CANON_LIVE_B3}"
    ok, msg = live_verifier.verify_live_offline({}, body["payload_hash"], body)
    assert ok, msg
    body["d"] = 1.6
    ok, _ = live_verifier.verify_live_offline({}, body["payload_hash"], body)
    assert not ok


# --- Offline receipt vector ---

def test_offline_receipt_vector_recomputes_and_verifies():
    for r in (RECEIPT_1, RECEIPT_2):
        body = {k: v for k, v in r.items() if k not in ("receipt_hash", "signature")}
        assert dual_hash(canonical(body)) == r["receipt_hash"]
        assert dual_hash(canonical(r["payload"])) == r["payload_digest"]
        pk = bytes.fromhex(ED25519_VECTORS[0][1])
        assert signature_ok(pk, r["receipt_hash"].encode(), base64.b64decode(r["signature"]))
    lines = [json.dumps(RECEIPT_1, sort_keys=True), json.dumps(RECEIPT_2, sort_keys=True)]
    result = verify_ledger(lines, bytes.fromhex(ED25519_VECTORS[0][1]))
    assert report(result) == "VERIFIED: 2 receipts, chain intact, signed by key 21fe31dfa154a261"
    wrong_key = verify_ledger(lines, bytes.fromhex(ED25519_VECTORS[1][1]))
    assert not wrong_key["ok"]


def test_offline_sealer_reproduces_the_receipt_vector(tmp_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from offline.seal import Sealer
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(ED25519_VECTORS[0][0]))
    s = Sealer(tmp_path / "r.jsonl", priv)
    r1 = s.seal("launch", payload={"airframe_id": "UAS-DEMO-01"}, ts="2026-10-17T00:00:00.000000Z")
    r2 = s.seal("land", payload={"pad": "A"}, ts="2026-10-17T00:01:00.000000Z")
    assert r1 == RECEIPT_1 and r2 == RECEIPT_2  # Ed25519 is deterministic


# --- The published document and this file agree ---

def test_every_hex_constant_in_the_doc_is_asserted_here():
    doc = DOC.read_text(encoding="utf-8")
    here = Path(__file__).read_text(encoding="utf-8")
    doc_hex = set(re.findall(r"`([0-9a-f]{16}|[0-9a-f]{64}|[0-9a-f]{128})`", doc))
    doc_hex |= set(h for pair in re.findall(r"`([0-9a-f]{64}):([0-9a-f]{64})`", doc) for h in pair)
    assert doc_hex, "no vectors found in docs/TEST_VECTORS.md"
    missing = sorted(h for h in doc_hex if h not in here and h != "0" * 64)
    assert not missing, f"docs/TEST_VECTORS.md lists values this test does not assert: {missing}"


if __name__ == "__main__":
    import inspect
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                if "tmp_path" in inspect.signature(fn).parameters:
                    import tempfile
                    fn(Path(tempfile.mkdtemp()))
                else:
                    fn()
                print(f"PASS {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {e}")
    print(f"{failures} failure(s)")
    sys.exit(1 if failures else 0)
