#!/usr/bin/env python3
"""Submit one attestation to the live flight recorder and check the receipt.

Usage:
    python3 scripts/first_receipt.py [payloads/identity_verified.json] [--out receipt.json]

Standard library only. Endpoint: RNA_BASE_URL, else rna.config.json.

The live server takes an attestation envelope, not the bare payload file:
    event_type, device_id, timestamp, signature, payload (object)
A fresh UTC timestamp is stamped on every run because the server rejects a
repeated device_id + event_type + timestamp as a replay. The public demo tenant
accepts any non-empty signature; a pilot tenant needs a real Ed25519 signature.

Exit 0 when the receipt is accepted and verify_receipt reports valid: true.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rna_config import base_url  # noqa: E402

LIVE_EVENT_TYPES = {"identity_verified", "custody_transferred", "seal_intact", "seal_broken", "delivery_confirmed"}
DEMO_SIGNATURE = base64.b64encode(b"demo-signature-not-ed25519").decode()


def rpc(url: str, method: str, params: dict, rid: str) -> dict:
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("RNA_PARTNER_KEY")
    if key:
        headers["X-Partner-Key"] = key
    body = json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        # Generous timeout: a sleeping free-tier instance can take ~60 s to wake.
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: HTTP {e.code} from {url}: {e.read()[:200]!r}")
    except urllib.error.URLError as e:
        sys.exit(f"FAIL: cannot reach {url}: {e.reason}")


def build_attestation(doc: dict) -> dict:
    """Wrap a payloads/*.json file in the envelope the live server requires."""
    return {
        "event_type": doc.get("event_type", "identity_verified"),
        "device_id": doc.get("device_id", "DEV-001"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "signature": DEMO_SIGNATURE,
        "payload": doc,
    }


def lift(response: dict) -> dict:
    """Tool result fields, from result or from content[0].text."""
    result = response.get("result") or {}
    out = dict(result)
    try:
        out.update(json.loads(result["content"][0]["text"]))
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("payload", nargs="?", default=str(ROOT / "payloads" / "identity_verified.json"))
    ap.add_argument("--out", default="receipt.json", help="where to save the receipt (default: receipt.json)")
    args = ap.parse_args()

    url = base_url()
    doc = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    att = build_attestation(doc)
    if att["event_type"] not in LIVE_EVENT_TYPES:
        print(f"WARN: event_type {att['event_type']!r} is not accepted by the flight recorder "
              f"(accepts: {', '.join(sorted(LIVE_EVENT_TYPES))}).", file=sys.stderr)

    print(f"Endpoint: {url}")
    resp = rpc(url, "tools/call", {"name": "submit_attestation", "arguments": att}, "1")
    if "error" in resp:
        sys.exit(f"FAIL: server error {resp['error']}")
    res = lift(resp)

    # Some servers return the full receipt; the hosted sandbox returns receipt_hash only.
    full_receipt = res.get("receipt") if isinstance(res.get("receipt"), dict) else None
    if full_receipt:
        receipt_hash = f"{full_receipt['sha256']}:{full_receipt['blake3']}"
        accepted, position = True, full_receipt.get("chain_position")
    else:
        receipt_hash = res.get("receipt_hash") or ""
        accepted, position = bool(res.get("accepted")), res.get("chain_position")

    print(f"accepted:       {accepted}")
    print(f"chain_position: {position}")
    print(f"receipt_hash:   {receipt_hash or '(none)'}")
    if not accepted:
        if res.get("reason"):
            missing = f" ({', '.join(res['missing_fields'])})" if res.get("missing_fields") else ""
            print(f"FAIL: attestation rejected: {res['reason']}{missing}", file=sys.stderr)
        else:
            print("FAIL: attestation rejected (this server version gives no reason); usual causes:\n"
                  "  - event_type not allowed for your tenant (see WARN above)\n"
                  "  - same device_id + event_type + timestamp sent twice (replay)\n"
                  "  - missing signature, or a pilot tenant whose Ed25519 key does not match", file=sys.stderr)
        return 1

    record = {"endpoint": url, "attestation": att, "receipt_hash": receipt_hash,
              "chain_position": position, "accepted": accepted}
    if full_receipt:
        record["receipt"] = full_receipt
    if isinstance(res.get("receipt_body"), dict):
        # The stored record: verify.py recomputes receipt_hash from it offline.
        record["receipt_body"] = res["receipt_body"]
    Path(args.out).write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Saved:          {args.out}")

    check = lift(rpc(url, "tools/call", {"name": "verify_receipt", "arguments": {"receipt_hash": receipt_hash}}, "2"))
    print(f"verify_receipt: valid={check.get('valid')}")
    if res.get("persistence") == "ephemeral" or check.get("persistence") == "ephemeral":
        print("NOTE: this sandbox ledger is ephemeral and resets on restart. Keep "
              f"{args.out}: it verifies offline from its receipt_body.")
    if check.get("valid") is not True:
        print("FAIL: server could not verify the receipt it just issued", file=sys.stderr)
        return 1
    print(f"Next: python3 verifier/verify.py {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
