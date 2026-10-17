#!/usr/bin/env python3
"""Tactical UAS scenario pack: seal the mission, verify it, and run the demos. No network.

Usage:
    python3 scripts/run_scenario.py check LEDGER PUBLIC_KEY    verify chain + mission rules
    python3 scripts/run_scenario.py demo                       rebuild payloads/tactical_uas/demos/
                                                               and print each demo's output

Mission rules (on top of the cryptographic checks):
  - the chain starts with launch
  - every ai_detection gets an operator_confirm or operator_override that
    names it (detection_seq) before the next detection or the end of the chain
  - every link_loss is followed by link_restored or rth
  - only the event types below appear
The pack contains no weapon-release or engagement events.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from ingest_log import ingest  # noqa: E402
from offline.verify import load_public_key, report, verify_ledger  # noqa: E402

PACK = ROOT / "payloads" / "tactical_uas"
DEMO_KEY = PACK / "demo_key"
EVENT_TYPES = {"launch", "transition", "ai_detection", "operator_confirm", "operator_override",
               "link_loss", "link_restored", "rth", "land"}


def mission_issues(receipts: list[dict]) -> list[str]:
    issues = []
    if receipts and receipts[0].get("event_type") != "launch":
        issues.append(f"chain starts with {receipts[0].get('event_type')}, not launch")
    open_detection = None
    awaiting_recovery = None
    for r in receipts:
        et, seq, p = r.get("event_type"), r.get("seq"), r.get("payload") or {}
        if et not in EVENT_TYPES:
            issues.append(f"seq {seq}: event type {et!r} is not part of this scenario")
        if et == "ai_detection":
            if open_detection is not None:
                issues.append(f"ai_detection seq {open_detection} has no operator decision")
            open_detection = seq
        elif et in ("operator_confirm", "operator_override"):
            if p.get("detection_seq") != open_detection:
                issues.append(f"seq {seq}: {et} names detection {p.get('detection_seq')}, "
                              f"open detection is {open_detection}")
            open_detection = None
        elif et == "link_loss":
            awaiting_recovery = seq
        elif et in ("link_restored", "rth"):
            awaiting_recovery = None
    if open_detection is not None:
        issues.append(f"ai_detection seq {open_detection} has no operator decision")
    if awaiting_recovery is not None:
        issues.append(f"link_loss seq {awaiting_recovery} is not followed by link_restored or rth")
    return issues


def check(ledger: Path, public_key: Path) -> tuple[bool, str]:
    lines = ledger.read_text().splitlines()
    crypto = verify_ledger(lines, load_public_key(public_key))
    receipts = []
    for line in lines:
        try:
            receipts.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    rules = mission_issues(receipts)
    out = ["chain:   " + report(crypto).replace("\n", "\n         ")]
    out.append("mission: " + ("OK: every detection has an operator decision; link loss handled"
                              if not rules else "FAILED\n" + "\n".join(f"  {i}" for i in rules)))
    return crypto["ok"] and not rules, "\n".join(out)


def build_demos() -> dict[str, Path]:
    """Seal the mission with the demo key and derive the tamper and missing-event ledgers."""
    demos = PACK / "demos"
    shutil.rmtree(demos, ignore_errors=True)
    for name in ("intact", "tamper", "missing_event", "missing_event_resealed"):
        (demos / name).mkdir(parents=True)
    key = DEMO_KEY / "demo_signer.pem"

    intact = demos / "intact" / "receipts.jsonl"
    ingest(PACK / "mission.jsonl", intact, key)
    lines = intact.read_text().splitlines()

    # Tamper: raise the second detection's confidence after sealing, without re-signing.
    tampered = [json.loads(l) for l in lines]
    tampered[4]["payload"]["confidence"] = 0.95
    (demos / "tamper" / "receipts.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in tampered))

    # Missing event: delete the operator override receipt from the sealed chain.
    (demos / "missing_event" / "receipts.jsonl").write_text("".join(l + "\n" for i, l in enumerate(lines) if i != 5))

    # Missing event, re-sealed: a source log without the override, sealed cleanly.
    # The chain verifies; only the mission rules can see the gap.
    log = demos / "missing_event_resealed" / "mission_without_override.jsonl"
    log.write_text("".join(l + "\n" for l in (PACK / "mission.jsonl").read_text().splitlines()
                           if '"operator_override"' not in l))
    ingest(log, demos / "missing_event_resealed" / "receipts.jsonl", key)
    return {name: demos / name / "receipts.jsonl" for name in
            ("intact", "tamper", "missing_event", "missing_event_resealed")}


def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ["check"] and len(args) == 3:
        ok, out = check(Path(args[1]), Path(args[2]))
        print(out)
        return 0 if ok else 1
    if args == ["demo"]:
        for name, ledger in build_demos().items():
            ok, out = check(ledger, DEMO_KEY / "demo_signer.pub")
            (ledger.parent / "expected_output.txt").write_text(out + "\n")
            print(f"=== {name} ({'pass' if ok else 'fail, as designed' if name != 'intact' else 'FAIL'})\n{out}\n")
        return 0
    print(__doc__.split("Mission rules")[0].strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
