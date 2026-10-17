#!/usr/bin/env python3
"""SWaP benchmark for the offline kit: receipts/sec, bytes/receipt, CPU and memory.

Usage:
    python3 scripts/benchmark.py [--count 5000] [--json]

Seals --count receipts shaped like the tactical UAS ai_detection event into a
temporary ledger (Ed25519-signed, hash-chained), then verifies them, and
reports throughput, ledger bytes per receipt, CPU seconds and peak resident
memory. Also times digest-only sealing and pure-Python verification (the
no-dependency path an evaluator bundle falls back to). No network.
See docs/SWAP_BENCHMARK.md for running it on ARM.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from offline.seal import Sealer, generate_keypair, load_private_key  # noqa: E402
from offline.verify import canonical, dual_hash, load_public_key, verify_ledger  # noqa: E402

PAYLOAD = {"model_id": "det-eo-small", "model_version": "2.4.1", "confidence": 0.87,
           "class": "ground_vehicle", "sensor": "eo_camera", "frame_id": 0, "bbox": [412, 220, 96, 64]}


def _cpu() -> float:
    u = resource.getrusage(resource.RUSAGE_SELF)
    return u.ru_utime + u.ru_stime


def _peak_rss_mb() -> float:
    kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return kb / 1024 / (1024 if sys.platform == "darwin" else 1)  # macOS reports bytes


def run(count: int) -> dict:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        generate_keypair(d / "k.pem", d / "k.pub")
        key, pub = load_private_key(d / "k.pem"), load_public_key(d / "k.pub")

        sealer = Sealer(d / "full.jsonl", key)
        t, c = time.perf_counter(), _cpu()
        for i in range(count):
            sealer.seal("ai_detection", payload={**PAYLOAD, "frame_id": i}, ts="2026-10-17T09:00:00.000000Z")
        seal_s, seal_cpu = time.perf_counter() - t, _cpu() - c
        size = (d / "full.jsonl").stat().st_size

        digest_sealer = Sealer(d / "digest.jsonl", key)
        t = time.perf_counter()
        for i in range(count):
            digest_sealer.seal("ai_detection", digest=dual_hash(canonical({**PAYLOAD, "frame_id": i})),
                               ts="2026-10-17T09:00:00.000000Z")
        digest_s = time.perf_counter() - t
        digest_size = (d / "digest.jsonl").stat().st_size

        lines = (d / "full.jsonl").read_text().splitlines()
        t, c = time.perf_counter(), _cpu()
        assert verify_ledger(lines, pub)["ok"]
        verify_s, verify_cpu = time.perf_counter() - t, _cpu() - c

        # Pure-Python verification of a sample, in a fresh process with RNA_VERIFY_PURE=1.
        sample = min(count, 50)
        (d / "sample.jsonl").write_text("\n".join(lines[:sample]) + "\n")
        t = time.perf_counter()
        subprocess.run([sys.executable, str(ROOT / "offline" / "verify.py"), str(d / "sample.jsonl"), str(d / "k.pub")],
                       env={**os.environ, "RNA_VERIFY_PURE": "1"}, check=True, capture_output=True)
        pure_s = time.perf_counter() - t

    return {
        "machine": platform.machine(), "python": platform.python_version(), "system": platform.system(),
        "count": count,
        "seal_receipts_per_sec": round(count / seal_s, 1),
        "seal_cpu_ms_per_receipt": round(seal_cpu / count * 1000, 3),
        "bytes_per_receipt": round(size / count, 1),
        "digest_only_receipts_per_sec": round(count / digest_s, 1),
        "digest_only_bytes_per_receipt": round(digest_size / count, 1),
        "verify_receipts_per_sec": round(count / verify_s, 1),
        "verify_cpu_ms_per_receipt": round(verify_cpu / count * 1000, 3),
        "pure_python_verify_receipts_per_sec": round(sample / pure_s, 1),
        "peak_rss_mb": round(_peak_rss_mb(), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--count", type=int, default=5000)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = run(a.count)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        width = max(map(len, r))
        print("\n".join(f"{k:<{width}}  {v}" for k, v in r.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
