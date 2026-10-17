# Demo signing key: public, for the scenario demos only

This key pair is committed on purpose so the demo ledgers and their expected
outputs are reproducible byte for byte. Anyone can sign with it, so a receipt
signed by this key proves nothing. Never use it for real data; create your own
with `python3 -m offline keygen`.
