# Inquiro RNA SDK

Receipts-native architecture for autonomous AI systems.
Every AI decision emits a cryptographic receipt at compute-time.
The hosted sandbox issues dual-hash (SHA256 + BLAKE3) receipts with a ledger sequence position and a per-tenant chain link; it does not sign receipts. The offline kit seals Ed25519-signed, hash-chained receipts with your own key. What each proves, and what neither can, is in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

Receipts are designed to support evidence and record-keeping requirements, including authentication of electronic records under rules such as FRE 901(b)(9). This is not legal advice and does not by itself establish compliance or admissibility in any jurisdiction.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/InquiroAIReseachLabs/inquiro-rna-sdk)
[![MIT License](https://img.shields.io/badge/license-MIT-amber)](LICENSE)

Read [`CLAUDEME.md`](CLAUDEME.md) (Inquiro execution standard) first. Evaluators: [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) (limits and trust assumptions), [docs/TEST_VECTORS.md](docs/TEST_VECTORS.md) (known-answer vectors), [docs/WINDOWS.md](docs/WINDOWS.md) (Git Bash and `py -3` steps), `bash scripts/final_audit.sh` (end-to-end audit, writes `audit.log`, ends with `READY FOR EVALUATOR` or a numbered list of fixes), [docs/LEGAL_LANGUAGE.md](docs/LEGAL_LANGUAGE.md) (approved legal wording, pending counsel), and [HUMAN_ACTIONS.md](HUMAN_ACTIONS.md) (what only a person can do).

> **Public sandbox notice.** The hosted demo endpoint is a shared public sandbox. Send **synthetic data only**: no controlled, classified, export-restricted (for example ITAR or EAR), personal or customer data. Its ledger is **temporary** and is wiped whenever the service restarts. For anything you want to keep or show someone, use the offline kit below: it runs on your machine and never touches the network.

---

## Start here: an evaluator bundle, fully offline (2 minutes)

The primary demo needs no account and no network. You seal a mission locally, export it as one zip, and anyone can verify that zip with Python alone.

```bash
git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
pip install -r requirements.txt

# 1. Make a signing key and seal a sample mission log into a signed, hash-chained ledger
python3 scripts/ingest_log.py payloads/tactical_uas/mission.jsonl \
    --ledger receipts.jsonl --key signer.pem --keygen signer.pub

# 2. Verify it with the public key (no network)
python3 -m offline verify receipts.jsonl signer.pub

# 3. Export the evaluator bundle: receipts + public key + standalone verifier
python3 -m offline bundle --ledger receipts.jsonl --public signer.pub --out evaluator_bundle.zip
```

Send `evaluator_bundle.zip` to a reviewer. They need only Python 3.9+, no install and no network:

```bash
unzip evaluator_bundle.zip && cd evaluator_bundle
python3 verify.py receipts.jsonl public_key.pub
# VERIFIED: 9 receipts, chain intact, signed by key <your key id>
```

The verifier recomputes every SHA-256 and BLAKE3 hash, checks every Ed25519 signature, and checks the sequence and hash links, so an edited, deleted, inserted or reordered receipt is reported. It uses the `blake3` and `cryptography` packages when present and bundled pure-Python implementations when not.

See tampering and a missing operator decision caught: `python3 scripts/run_scenario.py demo` (details in [payloads/tactical_uas/](payloads/tactical_uas/README.md)). More in [docs/OFFLINE.md](docs/OFFLINE.md); performance on small hardware in [docs/SWAP_BENCHMARK.md](docs/SWAP_BENCHMARK.md).

---

## Endpoints

| Endpoint | What it does | Access |
|----------|--------------|--------|
| `https://aiflightrecorder-1.onrender.com/mcp` | Flight recorder sandbox. Submit an attestation, get a dual-hash receipt, check it with `verify_receipt`. **Temporary ledger** (responses say `"persistence": "ephemeral"`): receipts reset when the service restarts. Synthetic data only. | No key: `submit_attestation`, `verify_receipt`. Pilot key (`X-Partner-Key`): also `verify_chain_segment`, `query_flight_summary`, `get_flight_health`. |
| `https://inquiroresearchlabs.ai/mcp` | Public verifier. `rna_verify` checks a signed receipt and its chain. Verify only. | No account, no key. |

The default host lives in [`rna.config.json`](rna.config.json). Every script and example reads it; set `RNA_BASE_URL` to point them somewhere else (for example the local mock, `http://localhost:8000/mcp`).

---

## Try the hosted sandbox (60 seconds)

No account. You need a clone of this repo and Python 3.9+; this step uses only the standard library. The free instance may be asleep: `bash scripts/warmup.sh` wakes it and reports the latency.

```bash
git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
python3 scripts/first_receipt.py --out receipt.json
python3 verifier/verify.py receipt.json
```

`first_receipt.py` wraps [`payloads/identity_verified.json`](payloads/identity_verified.json) in the envelope the live server requires (`event_type`, `device_id`, `timestamp`, `signature`, `payload`), stamps a fresh timestamp (the server rejects a repeated one as a replay), submits it, and prints `accepted`, `chain_position` and `receipt_hash`. Run it twice and `chain_position` goes up, by 5 on a quiet sandbox: it is the position in the server's whole ledger, which also records each call's request and sanitization receipts ([docs/RECEIPT_ANATOMY.md](docs/RECEIPT_ANATOMY.md#why-chain_position-jumps-by-5-per-first_receiptpy-run)). Your own count is `tenant_seq` in `receipt_body`.

The public demo tenant accepts any non-empty `signature`. A pilot tenant checks a real Ed25519 signature against your registered key.

`verify.py` then confirms the receipt offline: the live server returns the stored record (`receipt_body`), and `verify.py` recomputes `receipt_hash` from it and checks that it binds your payload. Against an older server that returns no body, it asks the issuing server (`verify_receipt`) instead and says so. Mock receipts are recomputed offline too. Change one character of `receipt_hash` or of the body in `receipt.json` and it fails.

The sandbox ledger is temporary. Keep the `receipt.json` files: they verify offline from their `receipt_body` even after the sandbox resets. If you look a receipt up after a reset, the server answers with `reason: ledger_reset`, not a tamper or chain error. For evidence you want to keep or share, seal locally and export a bundle as shown above:

```bash
python3 -m offline bundle --ledger receipts.jsonl --public signer.pub --out evaluator_bundle.zip
```

If an attestation is rejected, the server says why (`reason`, for example `missing_fields`, `signature_invalid` or `replay`), and `first_receipt.py` prints it.

### Windows

Use Git Bash or PowerShell. The `python3` command on Windows is often a Microsoft Store shortcut that does not run Python; use `py -3` instead:

```powershell
py -3 scripts\first_receipt.py --out receipt.json
py -3 verifier\verify.py receipt.json
```

The shell examples find a working interpreter themselves (they try `python3`, `python`, then `py -3`) and stop with a clear message if none works. If nothing works, install Python 3.12+ from python.org with "Add python.exe to PATH" ticked.

---

## What you just received

See [docs/RECEIPT_ANATOMY.md](docs/RECEIPT_ANATOMY.md).

---

## Three ways to integrate

### 1. Run locally with the mock server (15 minutes)

Tests the MCP protocol flow without calling the live service.
The mock returns full receipts (payload + hashes) that `verify.py` recomputes offline; its signatures are placeholders.
See [mock/README.md](mock/README.md) for setup.

### 2. Open in Codespaces (2 minutes, zero local install)

Click the badge above. Full environment pre-configured.
Mock server starts automatically. First smoke test runs on open.

### 3. Hit the live API directly

See [examples/curl/](examples/curl/) for request examples (they use `RNA_BASE_URL`).
See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a step-by-step guide.
`scripts/smoke_test.sh` runs the whole journey end to end.

---

## Event types

[docs/EVENT_TYPES.md](docs/EVENT_TYPES.md)

## Receipt anatomy

[docs/RECEIPT_ANATOMY.md](docs/RECEIPT_ANATOMY.md)

## Moving to production

[docs/PRODUCTION.md](docs/PRODUCTION.md)

---

## Ready for a pilot?

Dedicated tenant. Your Ed25519 key pair. Rate limits and an SLA agreed in the pilot contract.
[Request a pilot conversation →](https://inquiroresearchlabs.ai/contact/)

---

MIT License. Built by [Inquiro AI Research Labs](https://inquiroresearchlabs.ai).
