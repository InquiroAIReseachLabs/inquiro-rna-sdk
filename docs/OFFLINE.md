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
python3 -m offline verify receipts.jsonl signer.pub --head 42:<receipt_hash>   # truncation, re-signing
python3 -m offline verify receipts.jsonl signer.pub --against earlier.jsonl     # same, against an earlier export
python3 -m offline bundle --ledger receipts.jsonl --public signer.pub --out evaluator_bundle.zip
python3 scripts/ingest_log.py flight_log.csv --ledger receipts.jsonl --key signer.pem   # post-flight
```

`seal` only appends. It opens the ledger append-only, and before each write checks the last receipt on disk: it refuses (exit 2, ledger untouched) if the file ends mid-line, the last receipt does not verify, or it was sealed by another key. There is no command that rewrites or truncates a ledger; to start over, move the file yourself. `bundle` refuses to write over the ledger. These guard against mistakes and concurrent sealers, not against someone with write access to the file, who can still edit it with any tool.

`signer.pem` is written with mode 0600. Keep it on the device; share only `signer.pub` or its key id.

## Checkpoints and pinned keys

A checkpoint is one small signed file that states the head of a ledger at a moment: `origin` (which ledger), `seq` (how far it reached), `head` (its last `receipt_hash`), `time` (when, by the signer's clock) and `key_id` (who signed). It exists so the head can be held by someone other than the operator; see [THREAT_MODEL.md](THREAT_MODEL.md) section 0 for why that matters.

```bash
python3 -m offline seal ...                         # also writes receipts.checkpoints/<seq>.ckpt
python3 -m offline checkpoint make --ledger receipts.jsonl --key signer.pem       # on demand
python3 -m offline checkpoint verify receipts.checkpoints/000000000042.ckpt --public signer.pub
python3 -m offline checkpoint verify receipts.checkpoints/000000000042.ckpt --pins pins.json --json
```

- **Format.** Plain JSON under the canonical rule above, plus `checkpoint_hash` (dual hash of the other fields) and `signature` (Ed25519 over `checkpoint_hash`, hex). The stored file is exactly the canonical JSON and one LF, about 560 bytes. Any other byte form is rejected, so do not re-indent or re-save it in an editor; attach the file as it is. `.gitattributes` keeps Git from changing its line endings.
- **Origin.** `offline/<key_id>/<instance>`, where the instance is the first 16 hex characters of receipt 1's hash. A ledger rebuilt from scratch, even with the same key, has a different origin.
- **When.** `seal` and `scripts/ingest_log.py` write a checkpoint after their last receipt (`--no-checkpoint` to skip). A checkpoint is signed only after the whole ledger verifies, and a checkpoint file is never rewritten: one already stored for that `seq` with the same head is kept, and one with a different head makes the command refuse (`CKPT_CONFLICT`).
- **Time.** `time` is the signer's clock. It proves nothing about when; an independent timestamp is a separate, later step.

Outcome codes from `checkpoint verify` (exit 0 only for `CKPT_OK`):

| Code | Meaning |
|---|---|
| `CKPT_OK` | Canonical, intact, signed by a pinned key |
| `CKPT_MALFORMED` | Not a checkpoint: bad JSON, a missing or extra field, a float, a bad value |
| `CKPT_VERSION` | Unknown format version |
| `CKPT_NOT_CANONICAL` | The bytes are not the one canonical form (re-indented, CRLF, missing final LF) |
| `CKPT_HASH_MISMATCH` | A field was changed after signing |
| `CKPT_KEY_UNPINNED` | Signed by a key you have not pinned. Never accepted silently. |
| `CKPT_SIGNATURE_INVALID` | The signature does not verify for the pinned key |
| `PIN_INVALID` | A pin file entry whose `key_id` does not match its key |

**Pinning.** A verifier trusts a checkpoint only if its `key_id` is pinned: either the one key you name with `--public`, or a key in a pin file. Get the key, or at least its `key_id`, through a channel you already trust, not from the checkpoint or the ledger.

```bash
python3 -m offline pin add --pins pins.json --public signer.pub --label "field unit 3"
python3 -m offline pin list --pins pins.json
python3 -m offline pin remove --pins pins.json --key-id 21fe31dfa154a261
```

**Rotating a key** is explicit; nothing rotates on its own:

1. Generate the new key pair and send the new `key_id` to every holder through a trusted channel.
2. Each holder runs `pin add` for the new key. Keep the old key pinned so old checkpoints still verify.
3. Start a new ledger with the new key (a ledger spans one key). Seal a last receipt in the old ledger that names the new `key_id`, so the hand-over is on record.
4. Remove the old pin only if the old key is compromised. From then on its checkpoints are rejected with `CKPT_KEY_UNPINNED`, which is the intended result.

## What the verifier proves, and what it does not

It reports any receipt that was edited, deleted, inserted, duplicated or reordered after sealing, any receipt not signed by the given key, and a ledger that does not start at `seq 1` (use `--allow-partial` for an excerpt). It also reports a repeated or non-integer `seq`.

Given something recorded outside the ledger, it reports more; see the next section. Without any such reference, a tail cut or a rewrite by someone holding the signing key still verifies, and every such run prints:

> This run had no known head, checkpoint or verifier memory, so it cannot detect rollback or truncation.

(`NOTICE NO_REFERENCE`, and `{"code": "NO_REFERENCE"}` under `notices` with `--json`). See [THREAT_MODEL.md](THREAT_MODEL.md) section 0.

Every problem carries a stable code; `--json` gives `issues` (each with `code`, `line`, `seq`, `problem`), `notices`, the ledger's `origin` and `head`, and the `references` it compared against. Exit 0 when nothing is wrong (notices never fail a run), 1 when anything is, 2 for a usage error.

| Code | Meaning |
|---|---|
| `RECEIPT_EDITED`, `PAYLOAD_MISMATCH` | A receipt or its payload changed after sealing |
| `WRONG_KEY`, `SIGNATURE_INVALID` | A receipt is not signed by the given key |
| `SEQ_GAP`, `SEQ_ORDER`, `SEQ_DUPLICATE`, `SEQ_NOT_INTEGER`, `CHAIN_LINK`, `CHAIN_START` | Receipts deleted, inserted, reordered or duplicated, or the ledger does not start at seq 1 |
| `NOT_JSON`, `NOT_RECEIPT`, `RECEIPT_VERSION`, `LEDGER_EMPTY` | Not a ledger this verifier can read |
| `TRUNCATED` | The ledger ends before a checkpoint, known head or earlier export |
| `SPLIT_VIEW` | A different hash at the same seq: the history was rewritten (re-signed) or two histories exist |
| `REPLACED` | Same key, different receipt 1: the whole ledger was rebuilt |
| `ROLLBACK` | Below the highest head this verifier has already seen |
| `ORIGIN_MISMATCH` | A checkpoint of a different ledger |
| `NOT_COVERED` | A reference names a seq outside this excerpt |
| `CKPT_*`, `PIN_INVALID` | The checkpoint itself was rejected (table above) |

It cannot tell you an event was never sealed: a log that omitted an event before sealing produces a valid chain. Only rules about what the log should contain can catch that. Anyone holding the private key can produce a valid chain, so protect the key and check the key id out of band.

## Checking against a reference: checkpoints, known heads, memory

```bash
python3 -m offline verify receipts.jsonl signer.pub --checkpoint held_by_partner.ckpt     # repeatable
python3 -m offline verify receipts.jsonl signer.pub --head 42:<receipt_hash>               # noted by hand
python3 -m offline verify receipts.jsonl signer.pub --against earlier.jsonl                # an earlier export
python3 -m offline verify receipts.jsonl signer.pub --memory ~/.rna/verifier_memory.json   # remembered heads
```

- **Checkpoint or known head.** A ledger shorter than the checkpoint's `seq` is `TRUNCATED`. A different hash at that `seq` is `SPLIT_VIEW`. A checkpoint whose origin names a different receipt 1 under the same key is `REPLACED`. A checkpoint is trusted only if its key is pinned (`--pins pins.json`, else the public key given).
- **Memory.** Optional local state: the highest head seen per origin and key. A ledger or checkpoint below it is `ROLLBACK`; the same `seq` with a different hash is `SPLIT_VIEW`. A clean run records the new head; a failed run records nothing. The first run for an origin only records it (`NOTICE MEMORY_FIRST_SEEN`), so it cannot detect anything yet. Memory is a file on your machine: anyone who deletes it makes the verifier forget.
- **Checkpoints on their own** (for example from the hosted pilot, where you do not hold the ledger): `checkpoint verify FILE.ckpt --pins pins.json --memory memory.json` applies the same rollback and split-view rules. A pilot checkpoint from a new instance of an ephemeral ledger is `NOTICE LEDGER_RESET`, never rollback or tamper; a deployment remembered as persistent that suddenly presents an ephemeral origin is `PERSISTENCE_DOWNGRADE`.

### Handing the head to someone else

At the end of every run (or every flight), give the latest checkpoint to someone who does not control your ledger. That is what makes truncation and replacement detectable later.

1. `python3 -m offline checkpoint make --ledger receipts.jsonl --key signer.pem` (or use the one `seal` just wrote in `receipts.checkpoints/`). It is about 560 bytes.
2. Send the `.ckpt` file as an email attachment, or paste its single line into the email body. Send the `key_id` separately the first time.
3. The holder pins your key once (`pin add`), then stores each file unchanged, never re-saved in an editor, in a folder you cannot write to, and runs `checkpoint verify FILE.ckpt --pins pins.json --memory memory.json` on arrival.
4. To check the ledger later, the holder runs `verify receipts.jsonl signer.pub --checkpoint their_copy.ckpt`.
5. Two holders compare what they were given: `checkpoint compare mine.ckpt theirs.ckpt --pins pins.json`. `CONSISTENT` means the same head at the same `seq`; `SPLIT_VIEW` means the operator showed them different histories; `SEQ_DIFFERS` means different points of one ledger, which `verify --checkpoint` with both files settles.

Nothing here sends anything: there is no webhook, no mail sending and no hosted service in the kit. Getting the file to the holder is your step.

## Hash-only (digest) mode

`--digest` (or `ingest_log.py --digest-only`) seals the SHA-256:BLAKE3 digest of a payload you computed yourself. The payload never enters the ledger; the chain, order and signatures still verify. Later, you can prove a disclosed payload matches by hashing it the same way and comparing it to `payload_digest`.

## Running with networking disabled

The kit makes no network calls. To see that for yourself on Linux, run any command inside an empty network namespace:

```bash
unshare -rn python3 -m offline verify receipts.jsonl signer.pub
```
