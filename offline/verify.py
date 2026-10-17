#!/usr/bin/env python3
"""Verify an offline receipt ledger with a public key. No network, no account.

Usage:
    python3 verify.py <receipts.jsonl> <public_key.pub> [--json] [--allow-partial]
                      [--head SEQ:RECEIPT_HASH] [--against EARLIER.jsonl]
                      [--checkpoint FILE.ckpt ...] [--pins pins.json] [--memory memory.json]

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
  --checkpoint FILE.ckpt    a signed checkpoint (repeatable), trusted only if its key is
                            pinned (--pins, else the public key given). Flags truncation
                            (TRUNCATED), a different head (SPLIT_VIEW) and a rebuilt
                            ledger (REPLACED).
  --memory memory.json      local memory of the highest head seen per origin and key.
                            Flags a ledger below it (ROLLBACK) or contradicting it
                            (SPLIT_VIEW); remembers the new head after a clean run.
Without one of these, a rewrite by someone holding the signing key, or a cut at the
end of the file, still verifies: the file cannot show it on its own, and the output
says so (NO_REFERENCE).
Every problem carries a stable code (--json for machine-readable output).
Exit 0 when everything verifies, 1 otherwise, 2 for a usage error.

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


# Outcome codes for ledger problems. Stable: scripts and tests match on them.
# Checkpoint and memory codes (CKPT_*, ROLLBACK, SPLIT_VIEW, ...) are in checkpoint.py.
NOT_JSON = "NOT_JSON"
NOT_RECEIPT = "NOT_RECEIPT"
RECEIPT_VERSION = "RECEIPT_VERSION"
RECEIPT_EDITED = "RECEIPT_EDITED"
PAYLOAD_MISMATCH = "PAYLOAD_MISMATCH"
WRONG_KEY = "WRONG_KEY"
SIGNATURE_INVALID = "SIGNATURE_INVALID"
SEQ_NOT_INTEGER = "SEQ_NOT_INTEGER"
SEQ_DUPLICATE = "SEQ_DUPLICATE"
SEQ_GAP = "SEQ_GAP"
SEQ_ORDER = "SEQ_ORDER"
CHAIN_LINK = "CHAIN_LINK"
CHAIN_START = "CHAIN_START"
LEDGER_EMPTY = "LEDGER_EMPTY"
TRUNCATED = "TRUNCATED"
SPLIT_VIEW = "SPLIT_VIEW"
NOT_COVERED = "NOT_COVERED"
REFERENCE_UNREADABLE = "REFERENCE_UNREADABLE"
NO_REFERENCE = "NO_REFERENCE"

# Printed by every run that had nothing to compare against; docs/OFFLINE.md and
# docs/THREAT_MODEL.md carry the same sentence.
STATELESS_NOTICE = ("This run had no known head, checkpoint or verifier memory, "
                    "so it cannot detect rollback or truncation.")


def _is_seq(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _issue(issues, line, seq, code, problem):
    issues.append({"line": line, "seq": seq, "code": code, "problem": problem})


def _compare_to_record(issues, hashes, last_seq, record, label):
    """Flag truncation or a rewritten history relative to receipts recorded elsewhere.

    record: {seq: receipt_hash} you held before. hashes: {seq: receipt_hash} in this ledger.
    """
    missing = [q for q in sorted(record) if q not in hashes]
    if missing and last_seq is not None and missing[0] > last_seq:
        _issue(issues, 0, None, TRUNCATED,
               f"truncated: ledger ends at seq {last_seq} but {label} reaches seq {max(record)} "
               f"({len(missing)} receipt(s) cut from the end)")
    elif missing:
        _issue(issues, 0, None, NOT_COVERED,
               f"{label} has seq {missing[0]}, which is not in this ledger (excerpt or deleted receipts)")
    changed = [q for q in sorted(record) if q in hashes and hashes[q] != record[q]]
    if changed:
        _issue(issues, 0, None, SPLIT_VIEW,
               f"history rewritten or re-signed: seq {changed[0]} has a different receipt_hash than {label}"
               + (f" ({len(changed)} receipts differ)" if len(changed) > 1 else ""))


def ledger_origin(kid: str, genesis_receipt_hash) -> str | None:
    """offline/<key_id>/<instance>: the instance is the first 16 hex of receipt 1's hash."""
    if not isinstance(genesis_receipt_hash, str) or ":" not in genesis_receipt_hash:
        return None
    return f"offline/{kid}/{genesis_receipt_hash.split(':')[0][:16]}"


def verify_ledger(lines, public_key: bytes, allow_partial: bool = False,
                  head=None, against=None, checkpoints=None, pins=None, memory=None) -> dict:
    """Verify a ledger, then compare it with whatever was recorded outside it.

    head: (seq, receipt_hash) noted by hand. against: lines of an earlier export.
    checkpoints: [(label, stored bytes)] checked with `pins` ({key_id: public key}).
    memory: a verifier memory dict (checkpoint.load_memory); compared, not changed.

    Returns {"ok", "count", "issues": [{"line", "seq", "code", "problem"}],
    "notices": [{"code", "message"}], "key_id", "origin", "head", "references", "remember"}.
    Notices never fail a run; issues always do.
    """
    kid = key_id(public_key)
    issues, notices, references, remember = [], [], [], []
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
            _issue(issues, n, None, NOT_JSON, "not valid JSON")
            prev = None
            continue
        if not isinstance(r, dict):
            _issue(issues, n, None, NOT_RECEIPT, "line is not a receipt object")
            prev = None
            continue
        seq = r.get("seq")
        if _is_seq(seq):
            if seq in hashes:
                _issue(issues, n, seq, SEQ_DUPLICATE, f"seq {seq} appears more than once")
            hashes[seq] = r.get("receipt_hash")
        elif seq is not None or "seq" in r:
            _issue(issues, n, None, SEQ_NOT_INTEGER, f"seq {seq!r} is not an integer")

        def bad(code, problem):
            _issue(issues, n, seq, code, problem)

        if r.get("v") != FORMAT_VERSION:
            bad(RECEIPT_VERSION, f"unknown format version {r.get('v')!r}")
        if dual_hash(canonical(receipt_body(r))) != r.get("receipt_hash"):
            bad(RECEIPT_EDITED, "receipt_hash does not match the receipt body (edited receipt)")
        if r.get("payload_mode") == "full" and dual_hash(canonical(r.get("payload"))) != r.get("payload_digest"):
            bad(PAYLOAD_MISMATCH, "payload does not match payload_digest")
        if r.get("key_id") != kid:
            bad(WRONG_KEY, f"signed by key {r.get('key_id')}, not {kid}")
        try:
            sig = base64.b64decode(r.get("signature", ""), validate=True)
        except (ValueError, TypeError):
            sig = b""
        if not signature_ok(public_key, str(r.get("receipt_hash", "")).encode(), sig):
            bad(SIGNATURE_INVALID, "signature does not verify")

        if prev is None:
            if count == 1 and not allow_partial:
                if seq != 1:
                    bad(CHAIN_START, f"chain starts at seq {seq}, expected 1 (receipts missing before it)")
                if r.get("prev_hash") != GENESIS:
                    bad(CHAIN_START, "first receipt does not link to genesis")
        elif not _is_seq(prev.get("seq")) or not _is_seq(seq):
            bad(SEQ_NOT_INTEGER, "seq is not an integer, so the chain position cannot be checked")
        else:
            if seq != prev.get("seq", 0) + 1:
                expected = prev.get("seq", 0) + 1
                if seq > expected:
                    bad(SEQ_GAP, f"seq jumps {prev.get('seq')} -> {seq}: {seq - expected} receipt(s) missing")
                else:
                    bad(SEQ_ORDER, f"seq {seq} after {prev.get('seq')}: out of order or duplicated")
            if r.get("prev_hash") != prev.get("receipt_hash"):
                bad(CHAIN_LINK, "prev_hash does not link to the previous receipt")
        prev = r
    if count == 0:
        _issue(issues, 0, None, LEDGER_EMPTY, "ledger is empty")
    last_seq = max(hashes) if hashes else None
    origin = ledger_origin(kid, hashes.get(1))

    if head is not None:
        references.append("known head")
        _compare_to_record(issues, hashes, last_seq, {head[0]: head[1]}, "the head you recorded")
    if against is not None:
        references.append("earlier export")
        earlier = {}
        for line in against:
            if line.strip():
                try:
                    e = json.loads(line)
                    if _is_seq(e.get("seq")):
                        earlier[e["seq"]] = e.get("receipt_hash")
                except (json.JSONDecodeError, AttributeError):
                    _issue(issues, 0, None, REFERENCE_UNREADABLE, "the earlier ledger has an unreadable line")
        _compare_to_record(issues, hashes, last_seq, earlier, "the earlier export")

    if checkpoints or memory is not None:
        try:
            from offline import checkpoint as ck
        except ImportError:  # running from an evaluator bundle
            import checkpoint as ck
    for label, data in checkpoints or []:
        references.append(f"checkpoint {label}")
        try:
            c = ck.verify(data, pins if pins is not None else ck.pin_one(public_key))
        except ck.CheckpointError as e:
            _issue(issues, 0, None, e.code, f"checkpoint {label}: {e.message}")
            continue
        if origin is None:
            notices.append({"code": "ORIGIN_UNKNOWN", "message": f"checkpoint {label}: this excerpt has no receipt 1, "
                            "so its origin cannot be confirmed; compared by seq only"})
        elif c["origin"] != origin:
            parts = c["origin"].split("/")
            if parts[0] == "offline" and parts[1] == kid:
                _issue(issues, 0, None, ck.REPLACED,
                       f"replaced: checkpoint {label} is for {c['origin']}, but this ledger begins with a different "
                       f"receipt 1 ({origin}): the whole ledger was rebuilt")
            else:
                _issue(issues, 0, None, ck.ORIGIN_MISMATCH,
                       f"checkpoint {label} is for {c['origin']}, not this ledger ({origin})")
            continue
        _compare_to_record(issues, hashes, last_seq, {c["seq"]: c["head"]}, f"checkpoint {label}")
        remember.append((c["origin"], c["key_id"], c["seq"], c["head"]))

    if memory is not None and origin is not None:
        held = ck.remembered(memory, origin, kid)
        if held is not None:
            references.append("verifier memory")
            if last_seq is not None and last_seq < held["seq"]:
                _issue(issues, 0, None, ck.ROLLBACK,
                       f"rollback: ledger ends at seq {last_seq}, but this verifier already saw seq {held['seq']} "
                       f"of {origin} (on {held.get('seen', '?')})")
            elif hashes.get(held["seq"]) != held["head"]:
                _issue(issues, 0, None, ck.SPLIT_VIEW,
                       f"split view: seq {held['seq']} has a different receipt_hash than the one this verifier saw "
                       f"before for {origin}; two different histories exist")
        else:
            notices.append({"code": "MEMORY_FIRST_SEEN", "message": f"first time this verifier sees {origin}; "
                            "its head is remembered for the next run"})
    if not references:
        notices.append({"code": NO_REFERENCE, "message": STATELESS_NOTICE})
    if origin is not None and last_seq is not None:
        remember.append((origin, kid, last_seq, hashes[last_seq]))
    return {"ok": not issues, "count": count, "issues": issues, "notices": notices, "key_id": kid,
            "origin": origin, "head": {"seq": last_seq, "receipt_hash": hashes.get(last_seq)},
            "references": references, "remember": remember}


def backend() -> str:
    return ("native" if _blake3_lib and Ed25519PublicKey else
            "pure-Python" if not (_blake3_lib or Ed25519PublicKey) else "mixed")


def report(result: dict) -> str:
    if result["ok"]:
        out = [f"VERIFIED: {result['count']} receipts, chain intact, signed by key {result['key_id']}"]
    else:
        out = [f"FAILED: {len(result['issues'])} problem(s) in {result['count']} receipts"]
        out += [f"  line {i['line']} (seq {i['seq']}) {i.get('code', '')}: {i['problem']}" for i in result["issues"]]
    out += [f"NOTICE {n['code']}: {n['message']}" for n in result.get("notices", [])]
    return "\n".join(out)


def _take_values(args, flag):
    """Remove every `flag VALUE` from args and return the VALUEs."""
    values = []
    while flag in args:
        i = args.index(flag)
        if i + 1 >= len(args):
            raise SystemExit(f"{flag} needs a value")
        values.append(args[i + 1])
        del args[i:i + 2]
    return values


def _take_value(args, flag):
    values = _take_values(args, flag)
    return values[-1] if values else None


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    head_arg, against_arg = _take_value(args, "--head"), _take_value(args, "--against")
    checkpoint_args, pins_arg = _take_values(args, "--checkpoint"), _take_value(args, "--pins")
    memory_arg = _take_value(args, "--memory")
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
    public_key = load_public_key(args[1])
    pins = memory = None
    if checkpoint_args or memory_arg or pins_arg:
        try:
            from offline import checkpoint as ck
        except ImportError:  # running from an evaluator bundle
            import checkpoint as ck
        try:
            pins = ck.load_pins(pins_arg) if pins_arg else None
            memory = ck.load_memory(memory_arg) if memory_arg else None
        except ck.CheckpointError as e:
            print(f"error {e.code}: {e.message}", file=sys.stderr)
            return 2
    checkpoints = [(c, Path(c).read_bytes()) for c in checkpoint_args]
    result = verify_ledger(Path(args[0]).read_text().splitlines(), public_key, allow_partial,
                           head=head, against=against, checkpoints=checkpoints, pins=pins, memory=memory)
    if result["ok"] and memory is not None:
        for origin, kid, seq, h in result["remember"]:
            ck.remember(memory, origin, kid, seq, h)
        ck.save_memory(memory_arg, memory)
    print(json.dumps(result, indent=2) if as_json else report(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
