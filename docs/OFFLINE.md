# Offline kit

Seal events on the device, verify them anywhere, with no network and no account.

## Receipt format (v1)

One JSON object per line in `receipts.jsonl`:

| Field | Meaning |
|---|---|
| `v` | Format version (`1`) |
| `seq` | 1, 2, 3, … with no gaps |
| `ts` | When the event happened (ISO 8601) |
| `event_type` | Free-form type, for example `ai_detection` |
| `payload_mode` | `full` (payload included) or `digest` (only its hash) |
| `payload` | The event data (full mode only) |
| `payload_digest` | `sha256_hex:blake3_hex` of the canonical payload |
| `prev_hash` | `receipt_hash` of the previous receipt; 64 zeros `:` 64 zeros for the first |
| `key_id` | First 16 hex characters of SHA-256 of the signer's public key |
| `receipt_hash` | `sha256_hex:blake3_hex` of the canonical receipt without `receipt_hash` and `signature` |
| `signature` | Ed25519 signature over the ASCII bytes of `receipt_hash`, base64 |

Canonical JSON: keys sorted at every level, separators `,` and `:` with no spaces, non-ASCII escaped (`json.dumps(obj, sort_keys=True, separators=(",", ":"))`).

## Commands

```bash
python3 -m offline keygen --private signer.pem --public signer.pub
python3 -m offline seal --ledger receipts.jsonl --key signer.pem --event-type launch --payload '{"airframe_id":"UAS-DEMO-01"}'
python3 -m offline seal --ledger receipts.jsonl --key signer.pem --event-type ai_detection --digest <sha256>:<blake3>
python3 -m offline verify receipts.jsonl signer.pub            # --json for machine output
python3 -m offline bundle --ledger receipts.jsonl --public signer.pub --out evaluator_bundle.zip
python3 scripts/ingest_log.py flight_log.csv --ledger receipts.jsonl --key signer.pem   # post-flight
```

`signer.pem` is written with mode 0600. Keep it on the device; share only `signer.pub` or its key id.

## What the verifier proves, and what it does not

It reports any receipt that was edited, deleted, inserted, duplicated or reordered after sealing, any receipt not signed by the given key, and a ledger that does not start at `seq 1` (use `--allow-partial` for an excerpt).

It cannot tell you an event was never sealed: a log that omitted an event before sealing produces a valid chain. Domain rules catch that; see `scripts/run_scenario.py` and the `missing_event_resealed` demo. Anyone holding the private key can produce a valid chain, so protect the key and check the key id out of band.

## Hash-only (digest) mode

`--digest` (or `ingest_log.py --digest-only`) seals the SHA-256:BLAKE3 digest of a payload you computed yourself. The payload never enters the ledger; the chain, order and signatures still verify. Later, you can prove a disclosed payload matches by hashing it the same way and comparing it to `payload_digest`.

## Running with networking disabled

The test suite proves the kit needs no network: every test fails if it opens a socket, and CI runs the suite inside `unshare -rn` (an empty network namespace):

```bash
unshare -rn python3 -m pytest tests -q
```
