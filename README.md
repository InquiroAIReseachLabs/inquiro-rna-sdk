# Inquiro RNA SDK

Receipts-native architecture for autonomous AI systems.
Every AI decision emits a cryptographic receipt at compute-time.
Dual-hash (SHA256 + BLAKE3) receipts with a ledger sequence position; Ed25519-signed, Merkle-anchored receipts are part of the pilot production tier. Receipts may support **authentication of electronic records** (for example, Federal Rule of Evidence 901(b)(9) in U.S. federal courts) when the full production ledger, custody chain, and legal posture are in scope—**this SDK is not legal advice**, is **not** jurisdiction-specific guidance, and **does not** by itself establish admissibility.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/InquiroAIReseachLabs/inquiro-rna-sdk)
[![MIT License](https://img.shields.io/badge/license-MIT-amber)](LICENSE)

Read [`CLAUDEME.md`](CLAUDEME.md) (Inquiro execution standard) first.

---

## Endpoints

| Endpoint | What it does | Access |
|----------|--------------|--------|
| `https://aiflightrecorder-1.onrender.com/mcp` | Flight recorder demo. Submit an attestation, get a dual-hash receipt, check it with `verify_receipt`. The quickstart below runs here. Demo ledger: receipts reset when the service restarts. | No account. Public demo tenant. |
| `https://inquiroresearchlabs.ai/mcp` | Public verifier. `rna_verify` checks a signed receipt and its chain. Verify only. | No account, no key. |

The default host lives in [`rna.config.json`](rna.config.json). Every script and example reads it; set `RNA_BASE_URL` to point them somewhere else (for example the local mock, `http://localhost:8000/mcp`).

---

## Your first receipt in 60 seconds

No account. You need a clone of this repo and Python 3.9+; this step uses only the standard library.

```bash
git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
python3 scripts/first_receipt.py --out receipt.json
python3 verifier/verify.py receipt.json
```

`first_receipt.py` wraps [`payloads/identity_verified.json`](payloads/identity_verified.json) in the envelope the live server requires (`event_type`, `device_id`, `timestamp`, `signature`, `payload`), stamps a fresh timestamp (the server rejects a repeated one as a replay), submits it, and prints `accepted`, `chain_position` and `receipt_hash`. Run it twice and `chain_position` goes up.

The public demo tenant accepts any non-empty `signature`. A pilot tenant checks a real Ed25519 signature against your registered key.

`verify.py` then confirms the receipt offline: the live server returns the stored record (`receipt_body`), and `verify.py` recomputes `receipt_hash` from it and checks that it binds your payload. Against an older server that returns no body, it asks the issuing server (`verify_receipt`) instead and says so. Mock receipts are recomputed offline too. Change one character of `receipt_hash` or of the body in `receipt.json` and it fails.

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
