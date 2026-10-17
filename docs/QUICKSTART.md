# Quickstart: hosted sandbox

## 1. Prerequisites

- A clone of this repository
- Python 3.9+ (`python3`; on Windows `py -3`, see [WINDOWS.md](WINDOWS.md))
- `pip install -r requirements.txt` (needed to verify receipts offline)

The endpoint is set once, in [rna.config.json](../rna.config.json). Override it with `RNA_BASE_URL`.

## 2. Your first receipt

From the repository root:

```bash
python3 scripts/first_receipt.py --out receipt.json
```

It wraps `payloads/identity_verified.json` in the envelope (`event_type`, `device_id`, `timestamp`, `signature`, `payload`) with a fresh timestamp, submits it, prints `accepted`, `chain_position` and `receipt_hash`, and checks the receipt with `verify_receipt`. `chain_position` is the receipt's position in the server's whole ledger, so it can jump between your submissions; your own count is `tenant_seq` in `receipt_body`.

## 3. Verify your receipt

```bash
python3 verifier/verify.py receipt.json
```

It recomputes `receipt_hash` offline from the returned `receipt_body` and checks `attestation_payload_hash` against your payload. Tamper test: change one character of `receipt_hash` in `receipt.json` and run it again; it must fail.

## 4. Other event types

The sandbox accepts `identity_verified`, `custody_transferred`, `seal_intact`, `seal_broken` and `delivery_confirmed`:

```bash
python3 scripts/first_receipt.py payloads/custody_transferred.json --out custody.json
```

`verify_chain_segment`, `query_flight_summary` and `get_flight_health` need a pilot tenant (`X-Partner-Key`).

## 5. Request a pilot tenant

[Contact Inquiro](https://inquiroresearchlabs.ai/contact/) for a dedicated tenant, Ed25519 keys and support terms.
