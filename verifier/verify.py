"""
Verify an RNA receipt.

- Mock receipts (payload + sha256 + blake3): recompute both hashes offline.
- Live flight recorder receipts with receipt_body (servers from October 2026):
  recompute receipt_hash offline from the stored record,
  dual_hash(json.dumps(body minus "payload_hash", sort_keys=True)), and check
  attestation_payload_hash against the submitted payload when it is present.
- Live receipts without a body (older servers): the hash covers fields the
  server assigns, so ask the issuing server (verify_receipt) and say so.

Usage: python verifier/verify.py <receipt.json|api-response.json>
Exit 0 on success, 1 on failure.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from canonical_payload import canonical_bytes  # noqa: E402


def _load_doc(raw: str) -> dict[str, Any]:
    doc = json.loads(raw)
    if not isinstance(doc, dict):
        raise ValueError("Top-level JSON must be an object")
    return doc


def _extract_receipt(doc: dict[str, Any]) -> dict[str, Any]:
    if "receipt" in doc and isinstance(doc["receipt"], dict):
        return doc["receipt"]
    r = doc.get("result")
    if isinstance(r, dict) and "receipt" in r and isinstance(r["receipt"], dict):
        return r["receipt"]
    if "sha256" in doc and "blake3" in doc and "payload" in doc:
        return doc
    if (
        "result" in doc
        and isinstance(doc["result"], dict)
        and "sha256" in doc["result"]
        and "payload" in doc["result"]
    ):
        return doc["result"]
    raise ValueError("Could not find receipt object (expected receipt.payload, result.receipt, or inline sha256/blake3/payload)")


def verify_receipt_data(receipt: dict[str, Any]) -> tuple[bool, str]:
    pl = receipt.get("payload")
    if not isinstance(pl, dict):
        return False, "receipt missing dict payload"
    expected_sha = receipt.get("sha256")
    expected_b3 = receipt.get("blake3")
    if not isinstance(expected_sha, str) or not isinstance(expected_b3, str):
        return False, "receipt missing sha256 or blake3 string fields"
    import blake3

    data = canonical_bytes(pl)
    got_sha = hashlib.sha256(data).hexdigest()
    got_b3 = blake3.blake3(data).hexdigest()
    if got_sha == expected_sha and got_b3 == expected_b3:
        return True, f"VERIFIED: dual hash matches (sha256={got_sha[:12]}...)"
    parts = []
    if got_sha != expected_sha:
        parts.append(f"SHA256 mismatch (expected {expected_sha}, got {got_sha})")
    if got_b3 != expected_b3:
        parts.append(f"BLAKE3 mismatch (expected {expected_b3}, got {got_b3})")
    return False, "FAILED: " + "; ".join(parts)


def _live_hash(doc: dict[str, Any]) -> str | None:
    """receipt_hash of a live receipt record or thin JSON-RPC response, else None."""
    for src in (doc, doc.get("result") if isinstance(doc.get("result"), dict) else {}):
        rh = src.get("receipt_hash")
        if isinstance(rh, str) and rh and "sha256" not in src and "receipt" not in src:
            return rh
    return None


def _dual_hex(text: str) -> tuple[str, str]:
    import blake3

    data = text.encode("utf-8")
    return hashlib.sha256(data).hexdigest(), blake3.blake3(data).hexdigest()


def _receipt_body(doc: dict[str, Any]) -> dict[str, Any] | None:
    for src in (doc, doc.get("result") if isinstance(doc.get("result"), dict) else {}):
        if isinstance(src.get("receipt_body"), dict):
            return src["receipt_body"]
    return None


def verify_live_offline(doc: dict[str, Any], receipt_hash: str, body: dict[str, Any]) -> tuple[bool, str]:
    """Recompute a live receipt from its stored record. The server hashes
    json.dumps(record, sort_keys=True) with Python's default separators."""
    unhashed = {k: v for k, v in body.items() if k != "payload_hash"}
    sha, b3 = _dual_hex(json.dumps(unhashed, sort_keys=True))
    want_sha, _, want_b3 = receipt_hash.partition(":")
    if (sha, b3) != (want_sha, want_b3) or body.get("payload_hash") != receipt_hash:
        return False, f"FAILED (offline): receipt body does not hash to {receipt_hash[:12]}... (tampered body or hash)"
    payload = (doc.get("attestation") or {}).get("payload")
    bound = body.get("attestation_payload_hash")
    if isinstance(payload, dict) and bound:
        if ":".join(_dual_hex(json.dumps(payload, sort_keys=True))) != bound:
            return False, "FAILED (offline): payload does not match attestation_payload_hash in the receipt"
        return True, f"VERIFIED (offline): receipt {receipt_hash[:12]}... recomputes from its body and binds the payload"
    return True, f"VERIFIED (offline): receipt {receipt_hash[:12]}... recomputes from its body"


def verify_live(doc: dict[str, Any], receipt_hash: str) -> tuple[bool, str]:
    body = _receipt_body(doc)
    if body is not None:
        return verify_live_offline(doc, receipt_hash, body)

    from rna_config import base_url

    url = doc.get("endpoint") or base_url()
    args = {"receipt_hash": receipt_hash}
    sealed_at = (doc.get("attestation") or {}).get("timestamp")
    if sealed_at:
        args["sealed_at"] = sealed_at  # lets the server tell a reset ledger from a miss
    body = json.dumps({"jsonrpc": "2.0", "id": "1", "method": "tools/call",
                       "params": {"name": "verify_receipt", "arguments": args}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            result = json.loads(r.read()).get("result") or {}
    except (urllib.error.URLError, ValueError) as e:
        return False, f"FAIL: could not reach {url}: {e}"
    if result.get("valid") is True:
        return True, f"VERIFIED (server-side, {url}): receipt {receipt_hash[:12]}... is on the ledger and its dual hash matches"
    if result.get("reason") == "ledger_reset":
        return False, (f"NOT ON LEDGER (server-side, {url}): the server's ledger was reset after this receipt "
                       f"was sealed. Not a sign of tampering. Verify offline from a receipt_body or an "
                       f"exported bundle, or seal the event again.")
    return False, f"FAILED (server-side, {url}): receipt {receipt_hash[:12]}... not found or hash mismatch"


def main() -> int:
    argv = [a for a in sys.argv[1:] if a not in ("--all",)]
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: python verifier/verify.py <receipt.json>", file=sys.stderr)
        return 1
    path = Path(argv[0])
    if not path.is_file():
        print(f"FAIL: not a file: {path}", file=sys.stderr)
        return 1
    try:
        doc = _load_doc(path.read_text(encoding="utf-8"))
        live = _live_hash(doc)
        if live:
            ok, msg = verify_live(doc, live)
            print(msg)
            return 0 if ok else 1
        receipt = _extract_receipt(doc)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    ok, msg = verify_receipt_data(receipt)
    # A saved record also states receipt_hash; it must name this receipt.
    claimed = doc.get("receipt_hash")
    if ok and isinstance(claimed, str) and claimed != f"{receipt.get('sha256')}:{receipt.get('blake3')}":
        ok, msg = False, "FAILED: receipt_hash in the record does not match the receipt's sha256:blake3"
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
