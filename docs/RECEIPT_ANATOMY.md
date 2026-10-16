# Receipt anatomy

## JSON-RPC envelope

HTTP responses follow JSON-RPC 2.0. For `tools/call`, the `result` object includes:

- `content`: MCP content array; `content[0].text` is a JSON string of the tool result
- Lifted fields: production HTTP may duplicate tool fields (`receipt_hash`, `chain_position`, `accepted`) on `result` for convenience

## submit_attestation tool result

| Field | Meaning |
|-------|---------|
| `receipt_hash` | Dual hash `sha256_hex:blake3_hex` (129 characters) over the canonical attestation body |
| `chain_position` | Ledger sequence number (increases with each receipt; not contiguous per tenant) |
| `accepted` | Whether the attestation was accepted |
| `receipt_body` | Live server only, when accepted: the stored record that `receipt_hash` covers (see below) |
| `reason`, `missing_fields` | Live server only, when rejected: `missing_fields`, `invalid_fields`, `event_type_not_allowed`, `signature_invalid`, `tenant_key_not_configured`, `replay`, `daily_limit_reached` |

## verify_receipt tool result

| Field | Meaning |
|-------|---------|
| `valid` | Whether the receipt validates for the tenant / ledger |
| `chain_intact` | Chain integrity signal |
| `timestamp` | Verification timestamp |
| `receipt_type` | Receipt category (e.g. `attestation`) |

## query_flight_summary / get_flight_health

These tools return summary metrics. The `topology` field is a **public API enum** (`open`, `closed`, or `hybrid`) from the production sanitizer whitelist — not internal documentation.

## Canonicalization (client verification)

The attestation body hashed for `receipt_hash` is the JSON object with keys:

`device_id`, `event_type`, `payload`, `signature`, `timestamp`

serialized with **sorted keys**, **no insignificant whitespace**, UTF-8, using `separators=(',', ':')` (Python) or equivalent.

On the **mock server**, anyone with the same attestation JSON can recompute SHA256 and BLAKE3 and compare them to the receipt.

On the **live flight recorder**, `receipt_hash` also covers fields the server assigns (receipt ID, sequence, time, tenant chain link), so it is recomputed from `receipt_body`, not from the attestation: drop `payload_hash` from the body, serialize with Python's `json.dumps(body, sort_keys=True)` (default separators `", "` and `": "`, ASCII escaping), and compare SHA256 and BLAKE3 to the two halves of `receipt_hash`. `attestation_payload_hash` in the body is the dual hash of `json.dumps(payload, sort_keys=True)`, which binds your payload. `tenant_seq` and `prev_attestation_hash` link each attestation to the tenant's previous one. `verifier/verify.py` does all of this; for a server that returns no body it falls back to the `verify_receipt` tool.

See [verifier/README.md](../verifier/README.md) for CLI usage.
