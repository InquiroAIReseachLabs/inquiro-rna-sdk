# Verifier

`verify.py` checks a receipt from the hosted sandbox. It recomputes `receipt_hash` offline from the returned `receipt_body` (needs `blake3`, in `requirements.txt`) and checks that it binds your payload. For a receipt without a body it runs a labelled server-side `verify_receipt` check instead.

## Input

Any of:

- `receipt.json` written by `scripts/first_receipt.py`
- a raw JSON-RPC response (`result.receipt_hash`, with or without `result.receipt_body`)

## Usage

```bash
pip install -r requirements.txt
python verifier/verify.py receipt.json
```

## Results

- **VERIFIED (offline)**: the receipt recomputes from its `receipt_body` and binds the payload.
- **VERIFIED (server-side, ...)**: no body was returned; the issuing server found the receipt and its stored dual hash matches.
- **FAILED**: the record does not match the receipt.

Field meanings: [docs/RECEIPT_ANATOMY.md](../docs/RECEIPT_ANATOMY.md). Offline ledgers sealed with the offline kit are verified with `python3 -m offline verify` instead ([docs/OFFLINE.md](../docs/OFFLINE.md)).
