"""Evaluator bundle: one zip holding receipts, public key and a standalone verifier.

The recipient needs only Python 3.9+:  unzip, then  python3 verify.py receipts.jsonl public_key.pub
"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from offline.verify import load_public_key, report, verify_ledger

HERE = Path(__file__).resolve().parent

README = """Offline receipt bundle
======================

Contents
  receipts.jsonl   signed, hash-chained receipts, one per line
  public_key.pub   Ed25519 public key (base64) that signed them, key id {key_id}
  verify.py        standalone verifier (Python 3.9+, no network, no install)
  purepy.py        pure-Python BLAKE3 and Ed25519 used when the blake3 or
                   cryptography packages are not installed
  SHA256SUMS       checksums of the files above

Verify (works with networking disabled):
  python3 verify.py receipts.jsonl public_key.pub

Expected output for this bundle:
  {expected}

The verifier recomputes every receipt hash (SHA-256 and BLAKE3), checks every
Ed25519 signature, and checks that sequence numbers and hash links are
unbroken, so an edited, deleted, inserted or reordered receipt is reported.
Check the key id against one obtained from the issuer out of band.
"""


def make_bundle(ledger, public_key_path, out_zip) -> str:
    """Write the zip and return the verifier's report for its contents."""
    ledger, public_key_path, out_zip = Path(ledger), Path(public_key_path), Path(out_zip)
    public_key = load_public_key(public_key_path)
    result = verify_ledger(ledger.read_text().splitlines(), public_key)
    summary = report(result)
    files = {
        "receipts.jsonl": ledger.read_bytes(),
        "public_key.pub": public_key_path.read_bytes(),
        "verify.py": (HERE / "verify.py").read_bytes(),
        "purepy.py": (HERE / "purepy.py").read_bytes(),
    }
    files["README.txt"] = README.format(key_id=result["key_id"], expected=summary.splitlines()[0]).encode()
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in files.items()).encode()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(f"evaluator_bundle/{name}", data)
    return summary
