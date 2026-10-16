# Local mock MCP server

- **Endpoint:** `POST http://localhost:8000/mcp` (JSON-RPC 2.0, or raw attestation JSON with `event_type`).
- **Health:** `GET http://localhost:8000/health`

**Hash values** are real cryptographic computations (SHA-256 + BLAKE3 over the same canonical JSON as the Python verifier). **Merkle chain** uses a simple in-memory counter starting at 1. **Signatures** are `mock_ed25519_signature`. **Tenant isolation** is not implemented.

For real receipts use the live demo endpoint in [rna.config.json](../rna.config.json) (see the main README).

Run (from repo root, after `pip install -r mock/requirements.txt`):

```bash
python mock/mock_server.py
```

**Bind address:** defaults to **loopback** (`127.0.0.1`). To listen on all interfaces (LAN / shared machine), set `RNA_MOCK_BIND_ALL=1` before starting.
