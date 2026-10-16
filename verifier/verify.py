"""
Verify an RNA receipt.

- Mock receipts (payload + sha256 + blake3): recompute both hashes offline.
- Live flight recorder receipts (receipt_hash only, e.g. from
  scripts/first_receipt.py): the hash also covers fields the server assigns,
  so it cannot be recomputed offline. Ask the issuing server instead
  (verify_receipt tool) and say so in the output.

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


def verify_live(doc: dict[str, Any], receipt_hash: str) -> tuple[bool, str]:
    from rna_config import base_url

    url = doc.get("endpoint") or base_url()
    body = json.dumps({"jsonrpc": "2.0", "id": "1", "method": "tools/call",
                       "params": {"name": "verify_receipt", "arguments": {"receipt_hash": receipt_hash}}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            result = json.loads(r.read()).get("result") or {}
    except (urllib.error.URLError, ValueError) as e:
        return False, f"FAIL: could not reach {url}: {e}"
    if result.get("valid") is True:
        return True, f"VERIFIED (server-side, {url}): receipt {receipt_hash[:12]}... is on the ledger and its dual hash matches"
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
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
