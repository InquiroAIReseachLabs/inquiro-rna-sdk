# SWaP benchmark

`scripts/benchmark.py` measures what sealing and verifying cost on a given machine: receipts per second, ledger bytes per receipt, CPU time per receipt and peak resident memory. It is offline and uses a temporary directory.

```bash
pip install -r requirements.txt
python3 scripts/benchmark.py --count 5000          # --json for machine-readable output
```

## Reference result

x86_64 server CPU at 2.80 GHz, 4 vCPU, Linux, Python 3.13, 5,000 receipts shaped like the `ai_detection` event:

| Metric | Value |
|---|---|
| Seal (Ed25519 sign + hash chain + append) | 9,867 receipts/s, 0.10 ms CPU each |
| Ledger size, full payload | 877 bytes/receipt |
| Seal, digest-only | 10,319 receipts/s, 696 bytes/receipt |
| Verify (native `blake3` + `cryptography`) | 5,893 receipts/s, 0.17 ms CPU each |
| Verify, pure-Python fallback | 168 receipts/s |
| Peak resident memory (whole run) | 38 MB |

Treat these as an upper bound for small ARM boards; measure on the target.

## Running on ARM (64-bit)

Prebuilt wheels for `blake3` and `cryptography` exist for Linux aarch64, so a single-board computer or embedded Linux module needs no compiler:

```bash
sudo apt-get install -y python3-venv          # apt-based images
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 scripts/benchmark.py --count 2000 --json > swap_$(uname -m).json
```

Notes:

- Pin the CPU governor for repeatable numbers: `echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`.
- Peak memory includes the Python interpreter (about 10 to 15 MB on its own).
- Without the native packages the verifier still runs (pure-Python), about 35 times slower on this x86 reference; sealing requires `cryptography`.
- 32-bit ARM: wheels may be missing; install a Rust toolchain for `blake3`, or verify with the pure-Python fallback.
- Emulation (`docker run --platform linux/arm64`) checks that it works, not how fast it is.
