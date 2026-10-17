# Threat model and limitations

What the receipts in this repository can and cannot show, what a verifier has to trust, and what is still on the roadmap. Written for a technical evaluator. Last reviewed 17 October 2026.

There are two receipt systems here. They have different properties, so each row below names which one it applies to.

| | Offline kit (`offline/`) | Hosted sandbox (flight recorder, `aiflightrecorder-1.onrender.com`) |
|---|---|---|
| Who hashes | You, on your machine | The server |
| Who signs | You, with your Ed25519 key (`signer.pem`) | Nobody. The server does not sign receipts. Your submission carries your signature, which a pilot tenant's key verifies; the public sandbox accepts any non-empty signature. |
| Chain link | `prev_hash` on every receipt, `seq` contiguous from 1 | `tenant_seq` and `prev_attestation_hash` on each attestation, per tenant |
| Verification | Public key + `receipts.jsonl`, no network | `receipt_body` saved from the response + the payload you sent, no network; or ask the server |
| Ledger persistence | Your file | Temporary on the free tier (`"persistence": "ephemeral"`) |

## 1. What is detectable

Given a ledger (offline) or a saved `receipt_body` (hosted), a verifier detects:

- **Edited content.** Any byte change to a sealed receipt or its payload changes SHA-256 and BLAKE3 of the canonical body, so `receipt_hash` no longer matches. Offline, the signature over `receipt_hash` also fails. Demonstrated by `payloads/tactical_uas/demos/tamper`.
- **Deleted, inserted, duplicated or reordered receipts** inside the ledger you hold (offline): `seq` must increase by exactly one and `prev_hash` must equal the previous `receipt_hash`. Demonstrated by `demos/missing_event`. Hosted: `verify_chain_segment` (pilot key) checks `tenant_seq` and `prev_attestation_hash` across a segment.
- **A receipt signed by a different key** (offline): `key_id` and the Ed25519 check both fail.
- **A ledger that does not start at `seq 1`** (offline), unless you pass `--allow-partial` for an excerpt.
- **A payload that does not match its digest** (offline full mode; hosted via `attestation_payload_hash`).

## 2. What is not detectable

- **An event that was never sealed.** A log that omitted an event before sealing produces a valid chain. Only domain rules can catch this (`scripts/run_scenario.py`, `demos/missing_event_resealed`). The verifier proves the chain is unchanged since sealing, not that sealing was complete or truthful.
- **Truncation at the tail.** If the last N receipts are removed, the remaining chain still verifies. Detection needs a reference point held outside the ledger: the latest `receipt_hash` you recorded elsewhere, or a signed checkpoint (roadmap, section 6).
- **Ledger rewrite by the key holder.** Anyone holding `signer.pem` can delete the ledger and seal a different history that verifies. The key proves who sealed, not that the history is the only one. Protect the private key and anchor the chain head externally when this matters (section 6).
- **Wrong or fabricated inputs.** A receipt binds bytes, not truth. A sensor reading sealed correctly is still a sensor reading that may be wrong.
- **Hosted ledger reset.** After a free-tier restart, the server cannot find earlier receipts and says so (`reason: ledger_reset`). That is reported as unknown (`chain_intact: null`), not as tampering, because the server no longer has evidence either way. Your saved `receipt_body` still verifies offline.
- **Hosted receipts without a saved body.** If you kept only `receipt_hash`, the only check is to ask the issuing server. That is a trust-the-server check and `verify.py` labels it as such.

## 3. Trust assumptions

- **Trusted key.** "Verifiable without trusting Inquiro" holds only when the verifier obtains the signing public key through a channel it already trusts. A key that travels with a receipt proves consistency (these receipts were signed by this key), not identity. Check `key_id` against one obtained out of band.
- **Trusted software.** The verifier you run must be the one you think it is. The evaluator bundle ships `SHA256SUMS`; compare `verify.py` and `purepy.py` against the copies in this repository, and `docs/TEST_VECTORS.md` lets you confirm the primitives independently.
- **Canonicalization.** Both sides must serialize identically (`docs/TEST_VECTORS.md` section 4). The hosted server uses Python's default `json.dumps` separators; the offline kit uses compact separators. Mixing them produces a false mismatch, not a false match.
- **Time.** `ts` is whatever the sealer's clock said. Nothing in the chain proves a timestamp is correct, only that it has not changed since sealing. Ordering is proved by `seq` and `prev_hash`, not by `ts`. There is no trusted timestamping authority in either system today.
- **The public sandbox tenant** accepts any non-empty signature, so a sandbox receipt proves nothing about who submitted the attestation. It demonstrates the receipt mechanics only.

## 4. Key custody

- `signer.pem` is written with mode 0600 on POSIX. On Windows `os.chmod` only clears the read-only bit; use an NTFS ACL or a protected directory.
- The private key never leaves the device in any command in this repository. Share only `signer.pub` or its `key_id`.
- Pilot tenants: the server holds the partner's public key only (`PARTNER_PUBLIC_KEY_<TENANT>` in the deployment environment, never in the repository). The API key (`PARTNER_KEY_<TENANT>`) is a bearer credential; rotate it like one.
- There is no key rotation or revocation protocol yet. A ledger spans one key; sealing with a new key starts a new chain.

## 5. Replay

- **Hosted:** the server rejects a repeated `device_id` + `event_type` + `timestamp` (`reason: replay`). A replay with a fresh timestamp is a new attestation; the server cannot tell it from a genuine repeat. Idempotency is the client's job.
- **Offline:** replaying the same event seals a second receipt with a new `seq`. The chain is valid; de-duplication is a domain rule.
- **Verification requests** carry no secrets and can be replayed harmlessly.

## 6. Roadmap

Not implemented today. Listed so an evaluator does not infer them from the marketing surfaces.

1. **Signed checkpoints.** Periodic signed statements of (`seq`, `receipt_hash`) published outside the ledger (a second key, a transparency log, or a counterparty), so truncation and rewrite by the key holder become detectable.
2. **Server-side signatures on hosted receipts**, with a published key, so a hosted receipt can be checked for authorship as well as integrity.
3. **A hash link on every hosted ledger entry**, not only attestations (a change in the frozen core, recorded in `pilot/GAP_ANALYSIS.md` of the flight recorder repository).
4. **Trusted time**: RFC 3161 timestamps or a time-anchoring service on checkpoints.
5. **Key rotation** with a signed hand-over receipt linking the old and new keys.

## 7. Scope notes

- The mock server (`mock/`) has none of these properties: placeholder signatures, in-memory counter, no tenants, no persistence. It is for protocol testing only.
- Nothing here is legal advice. Whether a receipt supports authentication of a record under any rule of evidence depends on the whole ledger, custody and jurisdiction.
