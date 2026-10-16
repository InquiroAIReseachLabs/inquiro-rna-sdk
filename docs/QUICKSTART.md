# Quickstart

## 1. Prerequisites

- A clone of this repo
- Python 3.9+ (`python3`; on Windows use `py -3`, see the README's Windows note)
- `curl` and `bash` for `examples/curl/` (Git Bash on Windows)
- Optional: `pip install -r requirements.txt` (blake3) to verify mock receipts offline; Go 1.22+ for `examples/go`, Node.js 18+ for `examples/nodejs`

The endpoint is set once, in [rna.config.json](../rna.config.json) (the live flight recorder demo). Override it with `RNA_BASE_URL`, for example `export RNA_BASE_URL=http://localhost:8000/mcp` for the mock.

## 2. Your first receipt

From the repo root:

```bash
python3 scripts/first_receipt.py --out receipt.json
```

It wraps `payloads/identity_verified.json` in the live envelope (`event_type`, `device_id`, `timestamp`, `signature`, `payload`) with a fresh timestamp, submits it, prints `accepted`, `chain_position` and `receipt_hash`, and checks the receipt with `verify_receipt`. Run it again: `chain_position` increases.

## 3. Verify your receipt

```bash
python3 verifier/verify.py receipt.json
```

For a live receipt this is a server-side check (the hash covers server-assigned fields, so it cannot be recomputed offline). For a mock receipt it recomputes SHA256 and BLAKE3 offline. Tamper test: change one character of `receipt_hash` in `receipt.json` and run it again; it must fail.

## 4. Try other event types

The flight recorder accepts `identity_verified`, `custody_transferred`, `seal_intact`, `seal_broken` and `delivery_confirmed`:

```bash
python3 scripts/first_receipt.py payloads/custody_transferred.json --out custody.json
bash examples/curl/02-submit-attestation.sh
```

`examples/curl/04` and `05` need a pilot tenant on the live server (`RNA_PARTNER_KEY`); the public demo tenant gets "Request blocked by security policy". The mock answers all five.

## 5. Integrate into your CI

Copy [.github/workflows/verify-receipts-live-cron.yml](../.github/workflows/verify-receipts-live-cron.yml) into your repository. It submits each live event type, verifies every receipt server-side, and runs a tamper test.

## 6. Run locally with the mock server

See [mock/README.md](../mock/README.md). Start the mock, set `RNA_BASE_URL=http://localhost:8000/mcp`, and run `examples/curl/*.sh`.

## 7. Request a pilot tenant

[Contact Inquiro](https://inquiroresearchlabs.ai/contact/) for a dedicated tenant, Ed25519 keys, and an SLA.
