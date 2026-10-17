#!/usr/bin/env python3
"""Verify an offline receipt ledger with a public key. No network, no account.

Usage:
    python3 verify.py <receipts.jsonl> <public_key.pub> [--json] [--allow-partial]
                      [--head SEQ:RECEIPT_HASH] [--against EARLIER.jsonl]

Checks every receipt:
  - receipt_hash recomputes (SHA-256 and BLAKE3 over the canonical body)
  - payload_digest matches the payload (full mode)
  - key_id matches the public key, and the Ed25519 signature verifies
  - seq increases by exactly 1 and prev_hash links to the previous receipt,
    so a deleted, inserted, reordered or edited receipt is reported
Optional comparison with something you recorded earlier, held outside this file:
  --head SEQ:RECEIPT_HASH   the chain head you noted (or a checkpoint you hold). Flags a
                            ledger that ends before SEQ (truncated) or has a different
                            receipt at SEQ (history rewritten or re-signed).
  --against EARLIER.jsonl   an earlier export of the same ledger. Flags any receipt
                            that was dropped, changed or re-signed since that copy.
Without one of these, a rewrite by someone holding the signing key, or a cut at the
end of the file, still verifies: the file cannot show it on its own.
Exit 0 when everything verifies, 1 otherwise.

Standalone by design: standard library only, using the `blake3` and
`cryptography` packages when installed and the bundled pure-Python
implementations (purepy.py) when not. Copied as-is into evaluator bundles.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from pathlib import Path

try:
    from offline.purepy import blake3_hex as _blake3_py, ed25519_verify as _ed25519_py
except ImportError:  # running from an evaluator bundle
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from purepy import blake3_hex as _blake3_py, ed25519_verify as _ed25519_py

_PURE = os.environ.get("RNA_VERIFY_PURE") == "1"  # force the no-dependency path

try:
    if _PURE:
        raise ImportError
    import blake3 as _blake3_lib
except ImportError:
    _blake3_lib = None

try:
    if _PURE:
        raise ImportError
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:
    Ed25519PublicKey = None

GENESIS = "0" * 64 + ":" + "0" * 64
FORMAT_VERSION = 1


def canonical(obj) -> bytes:
    """Sorted keys, no whitespace, ASCII-escaped, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def dual_hash(data: bytes) -> str:
    b3 = _blake3_lib.blake3(data).hexdigest() if _blake3_lib else _blake3_py(data)
    return f"{hashlib.sha256(data).hexdigest()}:{b3}"


def key_id(public_key: bytes) -> str:
    return hashlib.sha256(public_key).hexdigest()[:16]


def signature_ok(public_key: bytes, message: bytes, signature: bytes) -> bool:
    if Ed25519PublicKey is not None:
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
            return True
        except (InvalidSignature, ValueError):
            return False
    return _ed25519_py(public_key, message, signature)


def receipt_body(receipt: dict) -> dict:
    return {k: v for k, v in receipt.items() if k not in ("receipt_hash", "signature")}


def load_public_key(path) -> bytes:
    raw = base64.b64decode(Path(path).read_text().strip())
    if len(raw) != 32:
        raise ValueError("public key must be 32 raw bytes, base64-encoded")
    return raw


def _is_seq(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _compare_to_record(issues, hashes, last_seq, record, label):
    """Flag truncation or a rewritten history relative to receipts recorded elsewhere.

    record: {seq: receipt_hash} you held before. hashes: {seq: receipt_hash} in this ledger.
    """
    def add(problem):
        issues.append({"line": 0, "seq": None, "problem": problem})

    missing = [q for q in sorted(record) if q not in hashes]
    if missing and last_seq is not None and missing[0] > last_seq:
        add(f"truncated: ledger ends at seq {last_seq} but {label} reaches seq {max(record)} "
            f"({len(missing)} receipt(s) cut from the end)")
    elif missing:
        add(f"{label} has seq {missing[0]}, which is not in this ledger (excerpt or deleted receipts)")
    changed = [q for q in sorted(record) if q in hashes and hashes[q] != record[q]]
    if changed:
        add(f"history rewritten or re-signed: seq {changed[0]} has a different receipt_hash than {label}"
            + (f" ({len(changed)} receipts differ)" if len(changed) > 1 else ""))


def verify_ledger(lines, public_key: bytes, allow_partial: bool = False,
                  head=None, against=None) -> dict:
    """Return {"ok", "count", "issues": [{"line", "seq", "problem"}], "key_id"}.

    head: (seq, receipt_hash) recorded outside the ledger. against: lines of an earlier
    export of the same ledger. Either one lets truncation and re-signing be reported.
    """
    kid = key_id(public_key)
    issues = []
    prev = None
    count = 0
    hashes = {}
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        count += 1
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            issues.append({"line": n, "seq": None, "problem": "not valid JSON"})
            prev = None
            continue
        if not isinstance(r, dict):
            issues.append({"line": n, "seq": None, "problem": "line is not a receipt object"})
            prev = None
            continue
        seq = r.get("seq")
        if _is_seq(seq):
            if seq in hashes:
                issues.append({"line": n, "seq": seq, "problem": f"seq {seq} appears more than once"})
            hashes[seq] = r.get("receipt_hash")
        elif seq is not None or "seq" in r:
            issues.append({"line": n, "seq": None, "problem": f"seq {seq!r} is not an integer"})

        def bad(problem):
            issues.append({"line": n, "seq": seq, "problem": problem})

        if r.get("v") != FORMAT_VERSION:
            bad(f"unknown format version {r.get('v')!r}")
        if dual_hash(canonical(receipt_body(r))) != r.get("receipt_hash"):
            bad("receipt_hash does not match the receipt body (edited receipt)")
        if r.get("payload_mode") == "full" and dual_hash(canonical(r.get("payload"))) != r.get("payload_digest"):
            bad("payload does not match payload_digest")
        if r.get("key_id") != kid:
            bad(f"signed by key {r.get('key_id')}, not {kid}")
        try:
            sig = base64.b64decode(r.get("signature", ""), validate=True)
        except (ValueError, TypeError):
            sig = b""
        if not signature_ok(public_key, str(r.get("receipt_hash", "")).encode(), sig):
            bad("signature does not verify")

        if prev is None:
            if count == 1 and not allow_partial:
                if seq != 1:
                    bad(f"chain starts at seq {seq}, expected 1 (receipts missing before it)")
                if r.get("prev_hash") != GENESIS:
                    bad("first receipt does not link to genesis")
        elif not _is_seq(prev.get("seq")) or not _is_seq(seq):
            bad("seq is not an integer, so the chain position cannot be checked")
        else:
            if seq != prev.get("seq", 0) + 1:
                expected = prev.get("seq", 0) + 1
                if seq > expected:
                    bad(f"seq jumps {prev.get('seq')} -> {seq}: {seq - expected} receipt(s) missing")
                else:
                    bad(f"seq {seq} after {prev.get('seq')}: out of order or duplicated")
            if r.get("prev_hash") != prev.get("receipt_hash"):
                bad("prev_hash does not link to the previous receipt")
        prev = r
    if count == 0:
        issues.append({"line": 0, "seq": None, "problem": "ledger is empty"})
    last_seq = max(hashes) if hashes else None
    if head is not None:
        _compare_to_record(issues, hashes, last_seq, {head[0]: head[1]}, "the head you recorded")
    if against is not None:
        earlier = {}
        for line in against:
            if line.strip():
                try:
                    e = json.loads(line)
                    if _is_seq(e.get("seq")):
                        earlier[e["seq"]] = e.get("receipt_hash")
                except (json.JSONDecodeError, AttributeError):
                    issues.append({"line": 0, "seq": None, "problem": "the earlier ledger has an unreadable line"})
        _compare_to_record(issues, hashes, last_seq, earlier, "the earlier export")
    return {"ok": not issues, "count": count, "issues": issues, "key_id": kid}


def backend() -> str:
    return ("native" if _blake3_lib and Ed25519PublicKey else
            "pure-Python" if not (_blake3_lib or Ed25519PublicKey) else "mixed")


def report(result: dict) -> str:
    if result["ok"]:
        return f"VERIFIED: {result['count']} receipts, chain intact, signed by key {result['key_id']}"
    out = [f"FAILED: {len(result['issues'])} problem(s) in {result['count']} receipts"]
    out += [f"  line {i['line']} (seq {i['seq']}): {i['problem']}" for i in result["issues"]]
    return "\n".join(out)


def _take_value(args, flag):
    """Remove `flag VALUE` from args and return VALUE, or None if absent."""
    if flag not in args:
        return None
    i = args.index(flag)
    if i + 1 >= len(args):
        raise SystemExit(f"{flag} needs a value")
    value = args[i + 1]
    del args[i:i + 2]
    return value


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    head_arg, against_arg = _take_value(args, "--head"), _take_value(args, "--against")
    as_json = "--json" in args
    allow_partial = "--allow-partial" in args
    args = [a for a in args if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__.split("Checks")[0].strip(), file=sys.stderr)
        return 2
    head = None
    if head_arg is not None:
        seq, _, digest = head_arg.partition(":")
        if not seq.isdigit() or not digest:
            raise SystemExit("--head must be SEQ:RECEIPT_HASH, for example 42:<sha256>:<blake3>")
        head = (int(seq), digest)
    against = Path(against_arg).read_text().splitlines() if against_arg else None
    result = verify_ledger(Path(args[0]).read_text().splitlines(), load_public_key(args[1]), allow_partial,
                           head=head, against=against)
    print(json.dumps(result, indent=2) if as_json else report(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
