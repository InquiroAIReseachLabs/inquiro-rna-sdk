"""python3 -m offline keygen|seal|verify|bundle|checkpoint|pin ...   (no network)

  keygen  --private signer.pem --public signer.pub
  seal    --ledger receipts.jsonl --key signer.pem --event-type TYPE (--payload JSON | --digest SHA:B3) [--ts ISO]
          [--no-checkpoint]
          (append only: refuses a ledger that is damaged, truncated at the tail or signed by another key;
           then writes a signed checkpoint to receipts.checkpoints/<seq>.ckpt)
  verify  receipts.jsonl signer.pub [--json] [--allow-partial] [--head SEQ:HASH] [--against EARLIER.jsonl]
          [--checkpoint FILE.ckpt ...] [--pins pins.json] [--memory memory.json]
  bundle  --ledger receipts.jsonl --public signer.pub --out evaluator_bundle.zip
  checkpoint make   --ledger receipts.jsonl --key signer.pem [--out FILE] [--time YYYY-MM-DDTHH:MM:SSZ]
  checkpoint verify FILE.ckpt (--public signer.pub | --pins pins.json) [--memory memory.json] [--json]
  checkpoint compare MINE.ckpt THEIRS.ckpt (--public signer.pub | --pins pins.json) [--json]
  pin add    --pins pins.json --public signer.pub [--label TEXT]
  pin list   --pins pins.json
  pin remove --pins pins.json --key-id KEY_ID
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m offline", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen")
    k.add_argument("--private", required=True)
    k.add_argument("--public", required=True)
    s = sub.add_parser("seal")
    s.add_argument("--ledger", required=True)
    s.add_argument("--key", required=True)
    s.add_argument("--event-type", required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--payload", help="JSON object")
    g.add_argument("--digest", help="sha256_hex:blake3_hex computed by the caller (payload stays local)")
    s.add_argument("--ts")
    s.add_argument("--no-checkpoint", action="store_true", help="do not write a checkpoint after sealing")
    v = sub.add_parser("verify")
    v.add_argument("rest", nargs=argparse.REMAINDER)
    b = sub.add_parser("bundle")
    b.add_argument("--ledger", required=True)
    b.add_argument("--public", required=True)
    b.add_argument("--out", default="evaluator_bundle.zip")
    c = sub.add_parser("checkpoint").add_subparsers(dest="ckpt_cmd", required=True)
    cm = c.add_parser("make")
    cm.add_argument("--ledger", required=True)
    cm.add_argument("--key", required=True)
    cm.add_argument("--out", help="write here instead of <ledger stem>.checkpoints/<seq>.ckpt")
    cm.add_argument("--time", help="checkpoint time, YYYY-MM-DDTHH:MM:SSZ (default: now, UTC)")
    cv = c.add_parser("verify")
    cv.add_argument("file")
    kg = cv.add_mutually_exclusive_group(required=True)
    kg.add_argument("--public", help="trust exactly this public key")
    kg.add_argument("--pins", help="trust the keys in this pin file")
    cv.add_argument("--memory", help="verifier memory: flag rollback, split view and resets; remember this head")
    cv.add_argument("--json", action="store_true")
    cc = c.add_parser("compare")
    cc.add_argument("mine")
    cc.add_argument("theirs")
    kc = cc.add_mutually_exclusive_group(required=True)
    kc.add_argument("--public", help="trust exactly this public key")
    kc.add_argument("--pins", help="trust the keys in this pin file")
    cc.add_argument("--json", action="store_true")
    p = sub.add_parser("pin").add_subparsers(dest="pin_cmd", required=True)
    pa = p.add_parser("add")
    pa.add_argument("--pins", required=True)
    pa.add_argument("--public", required=True)
    pa.add_argument("--label", default="")
    pl = p.add_parser("list")
    pl.add_argument("--pins", required=True)
    pr = p.add_parser("remove")
    pr.add_argument("--pins", required=True)
    pr.add_argument("--key-id", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "verify":
        from offline.verify import main as verify_main
        return verify_main(a.rest)
    if a.cmd == "keygen":
        from offline.seal import generate_keypair
        print(f"key id {generate_keypair(a.private, a.public)}: private {a.private} (keep secret), public {a.public}")
        return 0
    if a.cmd == "seal":
        from offline.seal import LedgerRefused, Sealer, load_private_key
        payload = json.loads(a.payload) if a.payload else None
        try:
            r = Sealer(a.ledger, load_private_key(a.key)).seal(a.event_type, payload=payload, digest=a.digest, ts=a.ts)
        except LedgerRefused as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        print(f"sealed seq {r['seq']} {r['event_type']} {r['receipt_hash'][:16]}...")
        return 0 if a.no_checkpoint else _auto_checkpoint(a.ledger, a.key)
    if a.cmd == "bundle":
        from offline.bundle import make_bundle
        if Path(a.out).resolve() == Path(a.ledger).resolve():
            print("refused: --out is the ledger; the bundle would overwrite it", file=sys.stderr)
            return 2
        summary = make_bundle(a.ledger, a.public, a.out)
        print(f"wrote {a.out}\n{summary}")
        return 0 if summary.startswith("VERIFIED") else 1
    if a.cmd == "checkpoint":
        return _checkpoint(a)
    if a.cmd == "pin":
        return _pin(a)
    return 2


def _auto_checkpoint(ledger, key_path) -> int:
    """After sealing: sign the new head and store it. Sealing has already succeeded."""
    from offline.checkpoint import CheckpointError, for_ledger, store
    from offline.seal import load_private_key
    try:
        path, written = store(ledger, for_ledger(ledger, load_private_key(key_path)))
    except CheckpointError as e:
        print(f"sealed, but no checkpoint: {e}", file=sys.stderr)
        return 1
    print(f"checkpoint {path}" + ("" if written else " (already present)"))
    return 0


def _checkpoint(a) -> int:
    from offline import checkpoint as ck
    if a.ckpt_cmd == "make":
        from offline.seal import load_private_key
        try:
            data = ck.for_ledger(a.ledger, load_private_key(a.key), a.time)
            if a.out:
                with open(a.out, "xb") as f:  # never overwrite a stored checkpoint
                    f.write(data)
                path, written = Path(a.out), True
            else:
                path, written = ck.store(a.ledger, data)
        except ck.CheckpointError as e:
            print(f"refused {e.code}: {e.message}", file=sys.stderr)
            return 1
        except FileExistsError:
            print(f"refused: {a.out} exists; a checkpoint file is never overwritten", file=sys.stderr)
            return 1
        c = ck.parse(data)
        print(f"checkpoint {path}{'' if written else ' (already present)'}: "
              f"{c['origin']} seq {c['seq']} head {c['head'][:16]}... key {c['key_id']}")
        return 0
    from offline.verify import STATELESS_NOTICE, load_public_key
    files = [a.file] if a.ckpt_cmd == "verify" else [a.mine, a.theirs]
    try:
        blobs = [Path(f).read_bytes() for f in files]
        pins = ck.pin_one(load_public_key(a.public)) if a.public else ck.load_pins(a.pins)
        memory = ck.load_memory(a.memory) if getattr(a, "memory", None) else None
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ck.CheckpointError as e:
        print(f"error {e.code}: {e.message}", file=sys.stderr)
        return 2
    try:
        checkpoints = [ck.verify(b, pins) for b in blobs]
    except ck.CheckpointError as e:
        return _ckpt_out(a, {"ok": False, "code": e.code, "message": e.message, "notices": []})
    if a.ckpt_cmd == "compare":
        code, message, ok = ck.compare(*checkpoints)
        return _ckpt_out(a, {"ok": ok, "code": code, "message": message, "notices": [], "checkpoints": checkpoints})
    c = checkpoints[0]
    result = {"ok": True, "code": "CKPT_OK", "checkpoint": c, "notices": []}
    if memory is None:
        result["notices"].append({"code": "NO_REFERENCE", "message": STATELESS_NOTICE})
    else:
        issues, notices = ck.origin_against_memory(memory, c["origin"])
        issues += ck.head_against_memory(memory, c["origin"], c["key_id"], c["seq"], c["head"])
        if ck.remembered(memory, c["origin"], c["key_id"]) is None and not notices:
            notices.append(("MEMORY_FIRST_SEEN", f"first time this verifier sees {c['origin']}; "
                                                 "its head is remembered for the next run"))
        result["notices"] = [{"code": k, "message": m} for k, m in notices]
        if issues:
            result.update(ok=False, code=issues[0][0], message=issues[0][1])
        else:
            ck.remember(memory, c["origin"], c["key_id"], c["seq"], c["head"])
            ck.save_memory(a.memory, memory)
    return _ckpt_out(a, result)


def _ckpt_out(a, result) -> int:
    if a.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    if result["ok"] and result["code"] == "CKPT_OK":
        c = result["checkpoint"]
        print(f"CHECKPOINT OK: {c['origin']} seq {c['seq']} head {c['head'][:16]}... "
              f"time {c['time']} key {c['key_id']}")
    elif result["ok"]:
        print(f"{result['code']}: {result['message']}")
    else:
        print(f"REJECTED {result['code']}: {result['message']}")
    for n in result["notices"]:
        print(f"NOTICE {n['code']}: {n['message']}")
    return 0 if result["ok"] else 1


def _pin(a) -> int:
    from datetime import datetime, timezone
    from offline.verify import key_id, load_public_key
    path = Path(a.pins)
    doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"v": 1, "keys": []}
    if path.exists():
        from offline.checkpoint import CheckpointError, load_pins
        try:
            load_pins(path)
        except CheckpointError as e:
            print(f"refused {e.code}: {e.message}", file=sys.stderr)
            return 1
    if a.pin_cmd == "list":
        for e in doc["keys"]:
            print(f"{e['key_id']}  added {e.get('added', '?')}  {e.get('label', '')}")
        return 0
    if a.pin_cmd == "add":
        raw = load_public_key(a.public)
        kid = key_id(raw)
        if any(e["key_id"] == kid for e in doc["keys"]):
            print(f"key {kid} is already pinned")
            return 0
        import base64
        doc["keys"].append({"key_id": kid, "public_key": base64.b64encode(raw).decode(), "label": a.label,
                            "added": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
        print(f"pinned key {kid}")
    else:
        before = len(doc["keys"])
        doc["keys"] = [e for e in doc["keys"] if e["key_id"] != a.key_id]
        if len(doc["keys"]) == before:
            print(f"key {a.key_id} is not pinned", file=sys.stderr)
            return 1
        print(f"unpinned key {a.key_id}: checkpoints signed by it will now be rejected (CKPT_KEY_UNPINNED)")
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
