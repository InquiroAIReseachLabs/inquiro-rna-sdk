# Security Review — Inquiro RNA SDK

## Scope

This document covers the public SDK components: mock MCP server, verifier, payload samples, and language examples. It does **not** cover the production RNA ledger service.

## §6 Threat Model

| Asset | Threat | Control |
|---|---|---|
| Receipt integrity | Payload tampering post-issue | Dual-hash (SHA-256 + BLAKE3); verifier detects any byte change |
| Hash algorithm weakness | Single-algorithm collision | Two independent algorithms required; both must match |
| Replay attack | Resubmitting a captured receipt | `request_id` (UUID v4) + `chain_position` must be unique per ledger |
| Mock vs production confusion | Treating mock receipts as production | Docstring and README label mock as PROTOCOL TESTING ONLY |
| Secret exposure | Internal strings in public repo | `scripts/final_audit.sh` and the October 2026 audit scan for credential-shaped strings; there is no CI secret gate yet (roadmap) |
| Dependency supply chain | Malicious `blake3` or `zeebo/blake3` update | Pin versions in requirements.txt / go.mod; review on bump |
| MCP hook injection | Malicious MCP server in cloned repo config | Users must review `.claude/settings.json` before enabling MCP servers from untrusted repos |

## §6.1 What the Mock Is Not

- **Not** an Ed25519 signer — `signature` field is the literal string `"mock_ed25519_signature"`.
- **Not** a Merkle ledger — `chain_position` is an in-process counter that resets on server restart.
- **Not** a tenant isolator — `tenant_id` echoes input; no access control is enforced.
- **Not** persistent — receipts exist only in process memory; all state is lost on restart.

## §6.2 Verifier Security Properties

The verifier (`verifier/verify.py`, `verifier/verify.js`) provides:

- **Tamper detection**: recomputes SHA-256 and BLAKE3 over canonical JSON of `payload`; any byte change to the payload produces a different hash and causes exit 1.
- **Canonical form**: `json.dumps(sort_keys=True, separators=(",", ":"))` — deterministic across all conforming Python/JS implementations.
- **No network calls** for mock receipts and for live receipts saved with `receipt_body`; a live receipt without a body falls back to a labelled server-side `verify_receipt` call.

`verifier/verify.py` does **not** verify Ed25519 signatures or chain continuity for hosted receipts (the hosted server does not sign receipts). The offline kit (`offline/`) verifies Ed25519 signatures, `seq` and `prev_hash` links; see [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for what that does and does not prove.

## §6.3 Dependency Inventory

| Dependency | Version | Purpose | Risk |
|---|---|---|---|
| `blake3` (Python) | == 1.0.8 (pinned) | BLAKE3 hashing | Low — Rust binding, no network access; pure-Python fallback in `offline/purepy.py` |
| `cryptography` (Python) | == 42.0.8 (pinned) | Ed25519 sign/verify in the offline kit | Low; pure-Python verify fallback in `offline/purepy.py` |
| `blake3` (npm) | ≥ 0.4.0 | BLAKE3 hashing in verify.js | Low |
| `github.com/zeebo/blake3` | v0.2.4 | BLAKE3 hashing in Go examples | Low |

No other third-party runtime dependencies.

## §6.4 Secrets Scanning

`scripts/final_audit.sh` and the October 2026 audit (`AUDIT_REPORT.md`) scan the repository for credential-shaped strings and private keys. The only tracked key is the published demo key in `payloads/tactical_uas/demo_key/`, which proves nothing (see its README).

## §6.5 Responsible Disclosure

Report security issues to **security@inquiroresearchlabs.ai**. Do not open a public GitHub issue for vulnerabilities.
