"""Seal events into a local, signed, hash-chained JSONL ledger. No network.

Each receipt:
    v, seq, ts, event_type, payload_mode ("full" or "digest"),
    payload (full mode only), payload_digest (SHA-256:BLAKE3 of the canonical payload),
    prev_hash (previous receipt_hash, or genesis), key_id,
    receipt_hash (dual hash of everything above), signature (Ed25519 over receipt_hash)

Digest mode seals a hash the caller computed, so the payload never leaves the
device; the verifier checks the chain and signature but cannot see the payload.

The sealer only ever appends. It opens the ledger O_APPEND (never truncating),
checks the last receipt on disk before every write, and refuses if the file was
altered at its tail, belongs to another key, or no longer ends where this sealer
expects. That is a guard against mistakes and a second process, not against
someone with write access to the file: see docs/THREAT_MODEL.md.
"""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows: no advisory lock; the tail check still runs
    fcntl = None

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline.verify import FORMAT_VERSION, GENESIS, canonical, dual_hash, key_id, receipt_body, signature_ok

DIGEST_RE = re.compile(r"^[0-9a-f]{64}:[0-9a-f]{64}$")


class LedgerRefused(ValueError):
    """The sealer will not write: appending would rewrite, fork or extend a damaged ledger."""


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
    """Appends signed receipts to a ledger, continuing from its last receipt.

    Every seal() re-reads the last receipt from disk under an exclusive lock, so
    two sealers on one file cannot both write the same seq.
    """

    def __init__(self, ledger_path, private_key: Ed25519PrivateKey):
        self.ledger = Path(ledger_path)
        self._key = private_key
        self._public = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.key_id = key_id(self._public)
        self.seq, self.prev_hash = self._tail()

    def _tail(self):
        """(seq, receipt_hash) of the last receipt on disk, checked; (0, GENESIS) if none.

        Raises LedgerRefused if the file does not end in one complete, valid receipt
        signed by this key.
        """
        if not self.ledger.exists() or self.ledger.stat().st_size == 0:
            return 0, GENESIS
        with open(self.ledger, "rb") as f:
            size = f.seek(0, os.SEEK_END)
            pos, data = size, b""
            while pos > 0 and data.count(b"\n") < 2:
                pos = max(0, pos - 65536)
                f.seek(pos)
                data = f.read(size - pos)
        if not data.endswith(b"\n"):
            raise LedgerRefused(f"{self.ledger} does not end with a complete line (interrupted write or edit); "
                                "refusing to append")
        lines = data.rstrip(b"\n").split(b"\n")
        if len(lines) == 1 and pos > 0:
            raise LedgerRefused(f"last line of {self.ledger} is implausibly long; refusing to append")
        try:
            last = json.loads(lines[-1])
            seq, h = last["seq"], last["receipt_hash"]
            sig = base64.b64decode(last["signature"], validate=True)
        except (ValueError, KeyError, TypeError):
            raise LedgerRefused(f"last line of {self.ledger} is not a receipt; refusing to append")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
            raise LedgerRefused(f"last receipt in {self.ledger} has an invalid seq; refusing to append")
        if last.get("key_id") != self.key_id:
            raise LedgerRefused(f"{self.ledger} was sealed by key {last.get('key_id')}, not {self.key_id}; "
                                "a ledger spans one key, start a new ledger for a new key")
        if dual_hash(canonical(receipt_body(last))) != h or not signature_ok(self._public, h.encode(), sig):
            raise LedgerRefused(f"last receipt in {self.ledger} does not verify; refusing to append")
        return seq, h

    def seal(self, event_type: str, payload: dict | None = None, digest: str | None = None,
             ts: str | None = None) -> dict:
        if (payload is None) == (digest is None):
            raise ValueError("give exactly one of payload or digest")
        if digest is not None and not DIGEST_RE.match(digest):
            raise ValueError("digest must be sha256_hex:blake3_hex (lowercase)")
        # Append-only open: the open itself cannot shorten or rewrite the file.
        fd = os.open(self.ledger, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX)
            self.seq, self.prev_hash = self._tail()
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
            data, done = (json.dumps(receipt, sort_keys=True) + "\n").encode("utf-8"), 0
            while done < len(data):
                done += os.write(fd, data[done:])
        finally:
            os.close(fd)  # releases the lock
        self.seq, self.prev_hash = receipt["seq"], receipt_hash
        return receipt
