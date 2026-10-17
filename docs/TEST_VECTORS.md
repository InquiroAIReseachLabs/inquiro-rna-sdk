# Known-answer test vectors

Published so that anyone can check that the verifiers in this repository compute the same primitives as the reference implementations. `tests/test_vectors.py` fails if `offline/verify.py`, `offline/purepy.py`, `verifier/verify.py` or `canonical_payload.py` disagree with any value below. Run it with:

```bash
python3 -m pytest tests/test_vectors.py -q      # or: python3 tests/test_vectors.py
```

All hashes are lowercase hex. Every value was recomputed on 17 October 2026 with `hashlib` (CPython 3.13), `blake3` 1.0.8 and `cryptography`, and cross-checked against the bundled pure-Python BLAKE3 and Ed25519 implementations.

## 1. SHA-256 (FIPS 180-4)

| Input | SHA-256 |
|---|---|
| `""` (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `"abc"` | `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad` |
| `"The quick brown fox jumps over the lazy dog"` | `d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592` |
| bytes `00 01 … ff` repeated 4 times (1024 bytes) | `785b0751fc2c53dc14a4ce3d800e69ef9ce1009eb327ccf458afe09c242c26c9` |
| the same pattern, first 1025 bytes | `b3981d93eeb64aa900f3e48cfcd48e9bbc89b77732c49ea201c93656c62b6a09` |

## 2. BLAKE3 (default 32-byte output, no key, no context)

| Input | BLAKE3 |
|---|---|
| `""` (empty) | `af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262` |
| `"abc"` | `6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85` |
| `"The quick brown fox jumps over the lazy dog"` | `2f1514181aadccd913abd94cfa592701a5686ab23f8df1dff1b74710febc6d4a` |
| bytes `00 01 … ff` repeated 4 times (1024 bytes, exactly one chunk) | `882179b8dbccd285cda241d968cfcccb3156c5edac2fa3761bb6eda7ff8cb172` |
| the same pattern, first 1025 bytes (crosses into a second chunk) | `3e85e5a7ffcd07c23794c079d43ebb27372d06bb1f75e4b47732fcaaf1a8cf3d` |

The 1024 and 1025 byte inputs exercise the chunk boundary and the parent-node path of the pure-Python port.

## 3. Ed25519 (RFC 8032 section 7.1)

Keys are 32 raw bytes, signatures 64 bytes, all hex. `key_id` is the first 16 hex characters of SHA-256 over the raw public key, as the offline ledger records it.

| Test | Secret key | Public key | Message | Signature | `key_id` |
|---|---|---|---|---|---|
| TEST 1 | `9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60` | `d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a` | `` (empty) | `e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b` | `21fe31dfa154a261` |
| TEST 2 | `4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb` | `3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c` | `72` | `92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00` | `39f713d0a644253f` |
| TEST 3 | `c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7` | `fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025` | `af82` | `6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a` | `dac073e0123bdea5` |

A verifier must also reject: the signature over a message with one extra byte, a signature with one flipped bit, and a signature checked against the wrong public key.

## 4. Canonical JSON

Input object (Python literal): `{"b": 1, "a": [1, 2, {"z": True, "y": None}], "c": "é", "d": 1.5, "e": "tab\there"}`

### 4a. Offline kit and mock receipts (`offline.verify.canonical`, `canonical_payload.canonical_bytes`)

Rule: keys sorted at every level, separators `,` and `:` with no spaces, non-ASCII escaped, UTF-8 (`json.dumps(obj, sort_keys=True, separators=(",", ":"))`).

Bytes: `{"a":[1,2,{"y":null,"z":true}],"b":1,"c":"é","d":1.5,"e":"tab\there"}`

| Hash | Value |
|---|---|
| SHA-256 | `6c8a3696a2a1a8b430297bbf4799dc5697f83ea0cb2a807afb8b24d7e0c23d28` |
| BLAKE3 | `7227b8a96f0b33c979a8faec1e32d835e941e33ad55478b84c579bd03535ad1c` |
| dual hash | `6c8a3696a2a1a8b430297bbf4799dc5697f83ea0cb2a807afb8b24d7e0c23d28:7227b8a96f0b33c979a8faec1e32d835e941e33ad55478b84c579bd03535ad1c` |

### 4b. Live flight-recorder `receipt_body` (`verifier/verify.py`)

Rule: keys sorted, Python's default separators `", "` and `": "`, non-ASCII escaped (`json.dumps(obj, sort_keys=True)`). The live server hashes its stored record this way; the two rules differ only in whitespace.

Bytes: `{"a": [1, 2, {"y": null, "z": true}], "b": 1, "c": "é", "d": 1.5, "e": "tab\there"}`

| Hash | Value |
|---|---|
| SHA-256 | `9b9008eb60c6234f4f61936c0ead1a5ae52c528ca2681bb78b8bc9a7355dbb0d` |
| BLAKE3 | `43b9cababb9aa6bf114c58f452647dad7ceaa8230effc00204789d87245b091d` |

## 5. Offline receipt (format v1)

Sealed with RFC 8032 TEST 1's secret key, `ts` fixed. Fields are shown in the canonical order; `receipt_hash` is the dual hash of the canonical body without `receipt_hash` and `signature`; `signature` is Ed25519 over the ASCII bytes of `receipt_hash`.

Receipt 1 (`event_type` `launch`, payload `{"airframe_id": "UAS-DEMO-01"}`, `ts` `2026-10-17T00:00:00.000000Z`):

| Field | Value |
|---|---|
| `payload_digest` | `913985f19a6b1120851ec974214a4f2feeaba4bfa02474edd34e6f0028ca44ae:36781cb8c6264efa06999206c54f7c112eccbe3661a1295a1e29c3c3e2c1fafb` |
| `prev_hash` | 64 zeros `:` 64 zeros (genesis) |
| `receipt_hash` | `a0d92eb44c50787c80175d5667dab4076da1a2f7b95b704ae505c181afe70348:9ac96a38a3697490a4e58c211709818b75d637e17ef7268f636d2af8812aab1e` |
| `signature` (base64) | `PBK1r6t/Qn3ljAL1CrVY347Z9EJv3pOEVMx0Dj6f50ZkgR0X3lh9fLtK1xYREPiB47gbwHsrSgE5bMOK2mKYAA==` |

Receipt 2 (`event_type` `land`, payload `{"pad": "A"}`, `ts` `2026-10-17T00:01:00.000000Z`):

| Field | Value |
|---|---|
| `prev_hash` | receipt 1's `receipt_hash` |
| `receipt_hash` | `4a5eda74cd732e7a78b6f4d4656f14c3ecc9087b77b782b885a97d8977b25220:bdf7074bb4577d5b5ffa2ed77618c1db6f5f52d1cf8b67099514085d8f41ac85` |
| `signature` (base64) | `DqwpzfFn8wfnvxggxDi7l/CymbMjMWdSoTnreb/zIDK7+6wKwY8yjZphxLa4tRAJbrRlRjU615k3O7DNZpUTCw==` |

A two-line ledger holding these receipts must report `VERIFIED: 2 receipts, chain intact, signed by key 21fe31dfa154a261` with the TEST 1 public key, and must fail with the TEST 2 public key.
