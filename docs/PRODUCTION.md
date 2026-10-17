# Production

## What changes from demo to production

- **Dedicated tenant** with a unique `receipt_namespace` and isolation flags
- **Your Ed25519 key pair** for partner signatures (generate securely; never commit private keys)
- **Rate limits** — per-minute and per-day caps per tenant configuration
- **Persistent ledger** — backed by a mounted disk (not the temporary free-tier container). Hosted receipts are dual-hashed and chain-linked per tenant; they are not server-signed today (see [THREAT_MODEL.md](THREAT_MODEL.md))
- **Support terms** — availability and support as agreed in the pilot contract

## How to request production / pilot

Use the [contact form](https://inquiroresearchlabs.ai/contact/) to start a pilot conversation. A tenant, keys, and limits are provisioned out-of-band.

## Operational checklist

- Store merged verification JSON or full RPC responses according to your retention policy
- Run the verifier steps of [../.github/workflows/ci.yml](../.github/workflows/ci.yml) (or equivalent) on every release branch
- Monitor the scheduled [../.github/workflows/verify-receipts-live-cron.yml](../.github/workflows/verify-receipts-live-cron.yml) for live API health
