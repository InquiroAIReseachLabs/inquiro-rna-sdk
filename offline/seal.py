"""Seal events into a local, signed, hash-chained JSONL ledger. No network.

Each receipt:
    v, seq, ts, event_type, payload_mode ("full" or "digest"),
    payload (full mode only), payload_digest (SHA-256:BLAKE3 of the canonical payload),
    prev_hash (previous receipt_hash, or genesis), key_id,
    receipt_hash (dual hash of everything above), signature (Ed25519 over receipt_hash)

Digest mode seals a hash the caller computed, so the payload never leaves the
device; the verifier checks the chain and signature but cannot see the payload.
"""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline.verify import FORMAT_VERSION, GENESIS, canonical, dual_hash, key_id

DIGEST_RE = re.compile(r"^[0-9a-f]{64}:[0-9a-f]{64}$")


def generate_keypair(private_path, public_path) -> str:
    """Write a new Ed25519 key pair (private PEM 0600, public base64). Returns key_id."""
    key = Ed25519PrivateKey.generate()
    private_path, public_path = Path(private_path), Path(public_path)
    private_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    os.chmod(private_path, 0o600)
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    public_path.write_text(base64.b64encode(raw).decode() + "\n")
    return key_id(raw)


def load_private_key(path) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(Path(path).read_bytes(), password=None)


class Sealer:
    """Appends signed receipts to a ledger, continuing from its last receipt."""

    def __init__(self, ledger_path, private_key: Ed25519PrivateKey):
        self.ledger = Path(ledger_path)
        self._key = private_key
        raw = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.key_id = key_id(raw)
        self.seq, self.prev_hash = 0, GENESIS
        if self.ledger.exists():
            for line in self.ledger.read_text().splitlines():
                if line.strip():
                    last = json.loads(line)
                    self.seq, self.prev_hash = last["seq"], last["receipt_hash"]

    def seal(self, event_type: str, payload: dict | None = None, digest: str | None = None,
             ts: str | None = None) -> dict:
        if (payload is None) == (digest is None):
            raise ValueError("give exactly one of payload or digest")
        if digest is not None and not DIGEST_RE.match(digest):
            raise ValueError("digest must be sha256_hex:blake3_hex (lowercase)")
        body = {
            "v": FORMAT_VERSION,
            "seq": self.seq + 1,
            "ts": ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "event_type": event_type,
            "payload_mode": "full" if payload is not None else "digest",
            "payload_digest": dual_hash(canonical(payload)) if payload is not None else digest,
            "prev_hash": self.prev_hash,
            "key_id": self.key_id,
        }
        if payload is not None:
            body["payload"] = payload
        receipt_hash = dual_hash(canonical(body))
        receipt = {**body, "receipt_hash": receipt_hash,
                   "signature": base64.b64encode(self._key.sign(receipt_hash.encode())).decode()}
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, sort_keys=True) + "\n")
        self.seq, self.prev_hash = receipt["seq"], receipt_hash
        return receipt
