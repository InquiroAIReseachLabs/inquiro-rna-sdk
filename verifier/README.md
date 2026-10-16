# Verifiers

Two independent verifiers ship with this SDK:

- **`verify.py`** — Python CLI (recommended for CI). Recomputes mock receipts and live receipts with `receipt_body` offline (needs `blake3`); for live receipts without a body (older servers) it runs a labelled server-side `verify_receipt` check.
- **`verify.js`** — JavaScript module + Node CLI. Uses `@noble/hashes` for BLAKE3 and `crypto` for SHA256.

## Canonical JSON

The attestation body includes exactly these keys (sorted when serialized):

`device_id`, `event_type`, `payload`, `signature`, `timestamp`

Serialization: UTF-8, `sort_keys=True` (Python) or lexicographic key order at every object level, no insignificant whitespace, separators `,` and `:` only.

## Input format

Any of:

- `receipt.json` written by `scripts/first_receipt.py` (live or mock)
- a mock receipt, or a raw mock JSON-RPC response (`result.receipt` with `payload`, `sha256`, `blake3`)
- a raw live JSON-RPC response (`result.receipt_hash`, with or without `result.receipt_body`)

## CLI usage

```bash
pip install blake3          # only needed for offline (mock) verification
python verifier/verify.py receipt.json
```

```bash
cd verifier && npm install && node verify.js /tmp/mock-receipt.json   # offline, mock receipts only
```

## Meaning of results

- **VERIFIED / verified: true** — offline: SHA256 and BLAKE3 match the canonical payload bytes. **VERIFIED (offline)** — a live receipt recomputes from its `receipt_body` (and binds the payload when the record has it). **VERIFIED (server-side, ...)** — older server, no body: the issuing server found the receipt on its ledger and its stored dual hash matches.
- **FAILED** — Any mismatch means the attestation body does not match the receipt (tamper or wrong merge).

See [docs/RECEIPT_ANATOMY.md](../docs/RECEIPT_ANATOMY.md).
