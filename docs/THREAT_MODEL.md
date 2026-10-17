# Threat model and limitations

What the receipts in this repository can and cannot show, and what a verifier has to trust. Written for a technical evaluator. Last reviewed 17 October 2026.

There are two receipt systems here. They have different properties, so each row below names which one it applies to.

| | Offline kit (`offline/`) | Hosted sandbox (`aiflightrecorder-1.onrender.com`) |
|---|---|---|
| Who hashes | You, on your machine | The server |
| Who signs | You, with your Ed25519 key (`signer.pem`), receipts and checkpoints | Receipts: nobody. The server does not sign receipts. Your submission carries your signature, which a pilot tenant's key verifies; the public sandbox accepts any non-empty signature. Checkpoints (`get_checkpoint`): a server key used only for checkpoints, once an operator has configured it; until then none are signed. |
| Chain link | `prev_hash` on every receipt, `seq` contiguous from 1 | `tenant_seq` and `prev_attestation_hash` on each attestation, per tenant |
| Verification | Public key + `receipts.jsonl`, no network | `receipt_body` saved from the response + the payload you sent, no network; or ask the server |
| Ledger persistence | Your file | Temporary on the free tier (`"persistence": "ephemeral"`) |
| Append-only enforced by | Sealer opens append-only and refuses a damaged or foreign ledger; verifier reports gaps | Writer opens append-only and refuses a sequence that is not last + 1; no edit or delete in the API. The storage itself is read-write. |

## 0. Two attacker classes, and what "append-only" covers

We use "append-only" in one narrow sense: **the software offers no operation that updates or deletes a ledger entry, and refuses to write anything but the next entry.** That is a statement about the application, not about the storage. Two attacker classes get different answers.

**Class 1: the application or an insider using the application.** Someone who can call the API, run the sealing command, or run the code, but cannot touch the storage or the signing key out-of-band.

| | Offline kit | Hosted service |
|---|---|---|
| Can they update or delete an entry through the product? | No. The sealer only opens the ledger in append mode and refuses a ledger whose last receipt is incomplete, unsigned or from another key. | No. No tool or HTTP verb edits a ledger entry. The writer refuses any sequence that is not last + 1. |
| Can they fork or skip a position? | No. The sealer re-reads the last receipt under a file lock. | No. The writer checks the last entry under a lock. |
| What stops them if they bypass the product (edit the file by hand)? | The verifier: any edited, deleted, inserted, duplicated or reordered receipt is reported (section 1). | `verify_chain_segment` (pilot key) checks your attestation chain. |

Within this class, append-only is **enforced by the code**, and by the verifier for anything that gets around the code.

**Class 2: the holder of storage administrator access** (or, for the offline kit, the owner of the file and the signing key). Someone who can open the ledger file, the disk or the volume directly: a cloud console user, a host root user, a disk snapshot restore, or a person holding `signer.pem`.

They can:

- cut receipts from the end (the remainder still verifies);
- replace the whole ledger with a different history. With the signing key it verifies; for the hosted service, which does not sign, a rebuilt ledger need only be self-consistent;
- delete the file.

Nothing in the product prevents this and nothing in the ledger alone reveals it. `chattr +a`, a read-only mount or WORM object storage would raise the cost, but a storage administrator can usually undo them, so they are not counted as a control here.

**What closes the gap is a reference the administrator cannot also rewrite**: the latest `seq` and `receipt_hash` (the head), or a signed checkpoint of it, stored somewhere else: a counterparty, a second key held by another person, a printed or emailed record. The verifier can then say so:

```bash
python3 -m offline verify receipts.jsonl signer.pub --checkpoint held_by_partner.ckpt
python3 -m offline verify receipts.jsonl signer.pub --head 42:<receipt_hash>
python3 -m offline verify receipts.jsonl signer.pub --against last_months_export.jsonl
python3 -m offline verify receipts.jsonl signer.pub --memory verifier_memory.json
```

They report `TRUNCATED` when receipts were cut from the end, `SPLIT_VIEW` when a receipt differs from the one recorded, `REPLACED` when the ledger was rebuilt from receipt 1, and `ROLLBACK` when the ledger is below a head the verifier remembers.

What is implemented today, and what is not:

- **Implemented:** signed checkpoints of the head (the offline kit writes one after every `seal`; the pilot signs one on request with `get_checkpoint` once its key is configured), key pinning with explicit rotation, comparison against a checkpoint, a known head, an earlier export or local verifier memory, and comparison of two holders' checkpoints.
- **Procedure, not software:** getting the checkpoint to someone other than the operator. Nothing in this repository sends it; `docs/OFFLINE.md` describes the hand-off.
- **Not implemented:** an independent timestamp of each checkpoint.

This works only if the reference was recorded at a time you trust and kept out of the administrator's reach. A run with none of these references cannot see a cut or a rewrite and prints, in every such run:

> This run had no known head, checkpoint or verifier memory, so it cannot detect rollback or truncation.

Limits of the references themselves:

- **Split view needs two holders who compare.** An operator can show one history to one holder and another to a second; only `checkpoint compare` between them, or both checking one ledger, shows it.
- **Verifier memory can be deleted.** It is a local file; delete it and the verifier forgets every head it saw.
- **Anything newer than the last stored checkpoint** can still be rewritten by the key holder without detection, until the next checkpoint reaches a holder.

## 1. What is detectable

Given a ledger (offline) or a saved `receipt_body` (hosted), a verifier detects:

- **Edited content.** Any byte change to a sealed receipt or its payload changes SHA-256 and BLAKE3 of the canonical body, so `receipt_hash` no longer matches. Offline, the signature over `receipt_hash` also fails.
- **Deleted, inserted, duplicated or reordered receipts** inside the ledger you hold (offline): `seq` must increase by exactly one and `prev_hash` must equal the previous `receipt_hash`. Hosted: `verify_chain_segment` (pilot key) checks `tenant_seq` and `prev_attestation_hash` across a segment.
- **A receipt signed by a different key** (offline): `key_id` and the Ed25519 check both fail.
- **A ledger that does not start at `seq 1`** (offline), unless you pass `--allow-partial` for an excerpt.
- **A payload that does not match its digest** (offline full mode; hosted via `attestation_payload_hash`).

## 2. What is not detectable

- **An event that was never sealed.** A log that omitted an event before sealing produces a valid chain. Only rules about what the log should contain can catch this. The verifier proves the chain is unchanged since sealing, not that sealing was complete or truthful.
- **Truncation at the tail, from the file alone.** If the last N receipts are removed, the remaining chain still verifies. Detection needs a reference point held outside the ledger: pass the head you recorded (`verify --head`) an earlier export (`verify --against`), or a signed checkpoint held by someone else.
- **Ledger rewrite by the key holder.** Anyone holding `signer.pem` can delete the ledger and seal a different history that verifies. The key proves who sealed, not that the history is the only one. Protect the private key and hand each checkpoint to someone outside your control when this matters (section 0).
- **Wrong or fabricated inputs.** A receipt binds bytes, not truth. A sensor reading sealed correctly is still a sensor reading that may be wrong.
- **Hosted ledger reset.** After a free-tier restart, the server cannot find earlier receipts and says so (`reason: ledger_reset`). That is reported as unknown (`chain_intact: null`), not as tampering, because the server no longer has evidence either way. Your saved `receipt_body` still verifies offline.
- **Hosted receipts without a saved body.** If you kept only `receipt_hash`, the only check is to ask the issuing server. That is a trust-the-server check and `verify.py` labels it as such.

## 3. Trust assumptions

- **Trusted key.** "Verifiable without trusting Inquiro" holds only when the verifier obtains the signing public key through a channel it already trusts. A key that travels with a receipt proves consistency (these receipts were signed by this key), not identity. Check `key_id` against one obtained out of band.
- **Trusted software.** The verifier you run must be the one you think it is. The evaluator bundle ships `SHA256SUMS`; compare `verify.py` and `purepy.py` against the copies in this repository.
- **Canonicalization.** Both sides must serialize identically. The hosted server uses Python's default `json.dumps` separators; the offline kit uses compact separators. Mixing them produces a false mismatch, not a false match.
- **Time.** `ts` is whatever the sealer's clock said. Nothing in the chain proves a timestamp is correct, only that it has not changed since sealing. Ordering is proved by `seq` and `prev_hash`, not by `ts`. There is no trusted timestamping authority in either system today.
- **The public sandbox tenant** accepts any non-empty signature, so a sandbox receipt proves nothing about who submitted the attestation. It demonstrates the receipt mechanics only.

## 4. Key custody

- `signer.pem` is written with mode 0600 on POSIX. On Windows `os.chmod` only clears the read-only bit; use an NTFS ACL or a protected directory.
- The private key never leaves the device in any command in this repository. Share only `signer.pub` or its `key_id`.
- Pilot tenants: the server holds only your public key. Your API key (`X-Partner-Key`) is a bearer credential; keep it secret and rotate it like one.
- There is no key rotation or revocation protocol yet. A ledger spans one key; sealing with a new key starts a new chain.

## 5. Replay

- **Hosted:** the server rejects a repeated `device_id` + `event_type` + `timestamp` (`reason: replay`). A replay with a fresh timestamp is a new attestation; the server cannot tell it from a genuine repeat. Idempotency is the client's job.
- **Offline:** replaying the same event seals a second receipt with a new `seq`. The chain is valid; de-duplication is a domain rule.
- **Verification requests** carry no secrets and can be replayed harmlessly.

## 6. Scope notes

- Nothing here is legal advice. Whether a receipt supports authentication of a record under any rule of evidence depends on the whole ledger, custody and jurisdiction.
