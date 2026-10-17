# Receipt anatomy

## JSON-RPC envelope

HTTP responses follow JSON-RPC 2.0. For `tools/call`, the `result` object includes:

- `content`: MCP content array; `content[0].text` is a JSON string of the tool result
- The server also copies the tool fields (`receipt_hash`, `chain_position`, `accepted`) onto `result` for convenience

## submit_attestation tool result

| Field | Meaning |
|-------|---------|
| `receipt_hash` | Dual hash `sha256_hex:blake3_hex` (129 characters) over the canonical attestation body |
| `chain_position` | The receipt's position in the server's ledger. The ledger also holds the server's own records, so it can advance by more than one between your submissions. Your own count is `tenant_seq` in `receipt_body`. |
| `accepted` | Whether the attestation was accepted |
| `receipt_body` | When accepted: the stored record that `receipt_hash` covers (see below) |
| `reason`, `missing_fields` | When rejected: `missing_fields`, `invalid_fields`, `event_type_not_allowed`, `signature_invalid`, `tenant_key_not_configured`, `replay`, `daily_limit_reached` |

## verify_receipt tool result

| Field | Meaning |
|-------|---------|
| `valid` | Whether the receipt validates for the tenant / ledger |
| `chain_intact` | Chain integrity signal |
| `timestamp` | Verification timestamp |
| `receipt_type` | Receipt category (e.g. `attestation`) |

## query_flight_summary / get_flight_health

These tools (pilot tenants only) return summary metrics. `topology` is one of `open`, `closed` or `hybrid`.

## Recomputing a receipt yourself

`receipt_hash` covers fields the server assigns (receipt ID, sequence, time, tenant chain link), so it is recomputed from `receipt_body`, not from the attestation: drop `payload_hash` from the body, serialize with Python's `json.dumps(body, sort_keys=True)` (default separators `", "` and `": "`, ASCII escaping), and compare SHA256 and BLAKE3 to the two halves of `receipt_hash`. `attestation_payload_hash` in the body is the dual hash of `json.dumps(payload, sort_keys=True)`, which binds your payload. `tenant_seq` and `prev_attestation_hash` link each attestation to the tenant's previous one. `verifier/verify.py` does all of this; for a server that returns no body it falls back to the `verify_receipt` tool.

See [verifier/README.md](../verifier/README.md) for CLI usage.
