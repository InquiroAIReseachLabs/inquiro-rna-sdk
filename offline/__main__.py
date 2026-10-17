"""python3 -m offline keygen|seal|verify|bundle ...   (no network)

  keygen  --private signer.pem --public signer.pub
  seal    --ledger receipts.jsonl --key signer.pem --event-type TYPE (--payload JSON | --digest SHA:B3) [--ts ISO]
          (append only: refuses a ledger that is damaged, truncated at the tail or signed by another key)
  verify  receipts.jsonl signer.pub [--json] [--allow-partial] [--head SEQ:HASH] [--against EARLIER.jsonl]
  bundle  --ledger receipts.jsonl --public signer.pub --out evaluator_bundle.zip
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
    v = sub.add_parser("verify")
    v.add_argument("rest", nargs=argparse.REMAINDER)
    b = sub.add_parser("bundle")
    b.add_argument("--ledger", required=True)
    b.add_argument("--public", required=True)
    b.add_argument("--out", default="evaluator_bundle.zip")
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
        return 0
    if a.cmd == "bundle":
        from offline.bundle import make_bundle
        if Path(a.out).resolve() == Path(a.ledger).resolve():
            print("refused: --out is the ledger; the bundle would overwrite it", file=sys.stderr)
            return 2
        summary = make_bundle(a.ledger, a.public, a.out)
        print(f"wrote {a.out}\n{summary}")
        return 0 if summary.startswith("VERIFIED") else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
