#!/usr/bin/env python3
"""Turn a post-flight log (CSV or JSONL) into a sealed, signed receipt chain. No network.

Usage:
    python3 scripts/ingest_log.py LOG --ledger receipts.jsonl --key signer.pem
                                  [--keygen signer.pub] [--sort] [--digest-only] [--append]

Each row becomes one receipt, in file order (or time order with --sort).
  timestamp   "timestamp", "ts" or "time" (ISO 8601, required)
  event_type  "event_type" (required)
  payload     every other column; a "detail" column holding a JSON object is
              merged in; numeric strings in CSV become numbers
--digest-only seals only the SHA-256:BLAKE3 digest of each payload, so the
log contents never enter the ledger. --keygen creates the key pair first.
Then verify:  python3 -m offline verify receipts.jsonl signer.pub
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from offline.seal import Sealer, generate_keypair, load_private_key  # noqa: E402
from offline.verify import canonical, dual_hash  # noqa: E402

TS_KEYS = ("timestamp", "ts", "time")


def _number(v: str):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return v


def read_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            return [{k: _number(v) if v != "" else None for k, v in row.items()} for row in csv.DictReader(f)]
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"FAIL: {path}:{n} is not JSON ({e.msg})")
    return rows


def to_event(row: dict, n: int) -> tuple[str, str, dict]:
    ts = next((str(row[k]) for k in TS_KEYS if row.get(k) not in (None, "")), None)
    event_type = row.get("event_type")
    if not ts or not event_type:
        raise SystemExit(f"FAIL: row {n} needs a timestamp and an event_type")
    try:
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        raise SystemExit(f"FAIL: row {n} timestamp {ts!r} is not ISO 8601")
    payload = {k: v for k, v in row.items() if k not in TS_KEYS + ("event_type", "detail") and v is not None}
    detail = row.get("detail")
    if detail not in (None, ""):
        extra = json.loads(detail) if isinstance(detail, str) else detail
        if not isinstance(extra, dict):
            raise SystemExit(f"FAIL: row {n} detail must be a JSON object")
        payload.update(extra)
    return ts, str(event_type), payload


def ingest(log, ledger, key_path, sort=False, digest_only=False) -> list[dict]:
    events = [to_event(row, n) for n, row in enumerate(read_rows(Path(log)), 1)]
    if sort:
        events.sort(key=lambda e: e[0])
    sealer = Sealer(ledger, load_private_key(key_path))
    out = []
    for ts, event_type, payload in events:
        if digest_only:
            out.append(sealer.seal(event_type, digest=dual_hash(canonical(payload)), ts=ts))
        else:
            out.append(sealer.seal(event_type, payload=payload, ts=ts))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("log")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--key", required=True, help="Ed25519 private key (PEM)")
    ap.add_argument("--keygen", metavar="PUBLIC", help="create the key pair first, writing the public key here")
    ap.add_argument("--sort", action="store_true", help="seal in timestamp order instead of file order")
    ap.add_argument("--digest-only", action="store_true", help="seal payload digests, not payloads")
    ap.add_argument("--append", action="store_true", help="continue an existing ledger")
    a = ap.parse_args()
    if Path(a.ledger).exists() and not a.append:
        raise SystemExit(f"FAIL: {a.ledger} exists; pass --append to continue it")
    if a.keygen:
        generate_keypair(a.key, a.keygen)
    receipts = ingest(a.log, a.ledger, a.key, sort=a.sort, digest_only=a.digest_only)
    print(f"sealed {len(receipts)} receipts into {a.ledger} "
          f"(seq {receipts[0]['seq']}-{receipts[-1]['seq']}, key {receipts[0]['key_id']})" if receipts
          else "no rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
