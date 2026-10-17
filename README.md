# Inquiro RNA SDK

Seal events into tamper-evident receipts and verify them, offline with your own key or against the hosted sandbox.

The hosted sandbox issues dual-hash (SHA256 + BLAKE3) receipts with a ledger sequence position and a per-tenant chain link; it does not sign receipts. The offline kit seals Ed25519-signed, hash-chained receipts with your own key. What each proves, and what neither can, is in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction.

> **Public sandbox notice.** The hosted demo endpoint is a shared public sandbox. Send **synthetic data only**: no controlled, classified, export-restricted (for example ITAR or EAR), personal or customer data. Its ledger is **temporary** and is wiped whenever the service restarts. For anything you want to keep or show someone, use the offline kit below: it runs on your machine and never touches the network.

## Offline: seal, verify, share (2 minutes)

No account and no network. Python 3.9+.

```bash
git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
pip install -r requirements.txt

# 1. Make a signing key and seal a sample mission log into a signed, hash-chained ledger
python3 scripts/ingest_log.py payloads/tactical_uas/mission.jsonl \
    --ledger receipts.jsonl --key signer.pem --keygen signer.pub

# 2. Verify it with the public key
python3 -m offline verify receipts.jsonl signer.pub

# 3. Export a bundle anyone can verify: receipts + public key + standalone verifier
python3 -m offline bundle --ledger receipts.jsonl --public signer.pub --out evaluator_bundle.zip
```

The recipient needs only Python 3.9+, no install and no network:

```bash
unzip evaluator_bundle.zip && cd evaluator_bundle
python3 verify.py receipts.jsonl public_key.pub
# VERIFIED: 9 receipts, chain intact, signed by key <your key id>
```

An edited, deleted, inserted or reordered receipt is reported. Commands, receipt format and options: [docs/OFFLINE.md](docs/OFFLINE.md).

## Hosted sandbox: your first receipt (60 seconds)

| Endpoint | What it does | Access |
|----------|--------------|--------|
| `https://aiflightrecorder-1.onrender.com/mcp` | Submit an attestation, get a dual-hash receipt, check it with `verify_receipt`. **Temporary ledger** (responses say `"persistence": "ephemeral"`). Synthetic data only. | No key: `submit_attestation`, `verify_receipt`. Pilot key (`X-Partner-Key`): also `verify_chain_segment`, `query_flight_summary`, `get_flight_health`. |
| `https://inquiroresearchlabs.ai/mcp` | Public verifier: `rna_verify` checks a signed receipt and its chain. | No account, no key. |

The default host is in [`rna.config.json`](rna.config.json); `RNA_BASE_URL` overrides it.

```bash
python3 scripts/first_receipt.py --out receipt.json
python3 verifier/verify.py receipt.json
```

`first_receipt.py` wraps [`payloads/identity_verified.json`](payloads/identity_verified.json) in the envelope the server requires (`event_type`, `device_id`, `timestamp`, `signature`, `payload`), stamps a fresh timestamp (a repeated one is rejected as a replay), submits it, and prints `accepted`, `chain_position` and `receipt_hash`. If an attestation is rejected, it prints the server's `reason` (for example `missing_fields`, `signature_invalid` or `replay`).

`verify.py` recomputes `receipt_hash` offline from the returned record (`receipt_body`) and checks that it binds your payload. Keep `receipt.json`: it still verifies offline after the sandbox resets. A lookup after a reset answers `reason: ledger_reset`, not tampering.

The public demo tenant accepts any non-empty `signature`. A pilot tenant checks a real Ed25519 signature against your registered key.

On Windows, use `py -3` in place of `python3`; see [docs/WINDOWS.md](docs/WINDOWS.md).

## Documentation

- [docs/QUICKSTART.md](docs/QUICKSTART.md): the hosted path step by step
- [docs/OFFLINE.md](docs/OFFLINE.md): offline kit commands, receipt format, signed checkpoints and key pinning
- [docs/EVENT_TYPES.md](docs/EVENT_TYPES.md): event types and payloads
- [docs/RECEIPT_ANATOMY.md](docs/RECEIPT_ANATOMY.md): what each receipt field means
- [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md): what a receipt can and cannot show
- [docs/WINDOWS.md](docs/WINDOWS.md): Windows steps

## Pilot tenant

A dedicated tenant, your Ed25519 key pair, rate limits and support terms are set up per pilot. [Contact Inquiro](https://inquiroresearchlabs.ai/contact/).

MIT License. Built by [Inquiro AI Research Labs](https://inquiroresearchlabs.ai).
