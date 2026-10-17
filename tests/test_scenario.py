"""Tactical UAS scenario pack and post-flight ingest. No network."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ingest_log import ingest
from offline.seal import generate_keypair
from offline.verify import load_public_key, verify_ledger
from run_scenario import DEMO_KEY, PACK, build_demos, check, mission_issues

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = {"launch", "transition", "ai_detection", "operator_confirm", "operator_override", "link_loss", "rth"}
FORBIDDEN_WORDS = ("weapon", "release", "engage", "strike", "fire", "munition", "target")


def test_pack_covers_the_required_events():
    types = {json.loads(l)["event_type"] for l in (PACK / "mission.jsonl").read_text().splitlines()}
    assert REQUIRED <= types


def test_detections_carry_model_id_version_and_confidence():
    for line in (PACK / "mission.jsonl").read_text().splitlines():
        e = json.loads(line)
        if e["event_type"] == "ai_detection":
            assert {"model_id", "model_version", "confidence"} <= e.keys()
            assert 0.0 <= e["confidence"] <= 1.0


def test_pack_has_no_weapon_events():
    for path in PACK.rglob("*"):
        # Scenario data and demo outputs; the pack's README states the policy in words.
        if path.is_file() and path.suffix in (".json", ".jsonl", ".csv", ".txt"):
            text = path.read_text().lower()
            for word in FORBIDDEN_WORDS:
                assert word not in text, f"{path.relative_to(ROOT)} mentions {word!r}"


def test_demos_rebuild_byte_for_byte(tmp_path):
    demos = PACK / "demos"
    before = {p.relative_to(demos): p.read_bytes() for p in demos.rglob("*") if p.is_file()}
    build_demos()
    for name in ("intact", "tamper", "missing_event", "missing_event_resealed"):
        ok, out = check(demos / name / "receipts.jsonl", DEMO_KEY / "demo_signer.pub")
        (demos / name / "expected_output.txt").write_text(out + "\n")
    after = {p.relative_to(demos): p.read_bytes() for p in demos.rglob("*") if p.is_file()}
    assert after == before


@pytest.mark.parametrize("name,passes,must_contain", [
    ("intact", True, ["VERIFIED: 9 receipts", "mission: OK"]),
    ("tamper", False, ["seq 5", "edited receipt", "payload does not match"]),
    ("missing_event", False, ["seq jumps 5 -> 7", "ai_detection seq 5 has no operator decision"]),
    ("missing_event_resealed", False, ["VERIFIED: 8 receipts", "ai_detection seq 5 has no operator decision"]),
])
def test_demo_matches_expected_output(name, passes, must_contain):
    ledger = PACK / "demos" / name / "receipts.jsonl"
    ok, out = check(ledger, DEMO_KEY / "demo_signer.pub")
    assert ok is passes
    assert out + "\n" == (ledger.parent / "expected_output.txt").read_text()
    for text in must_contain:
        assert text in out


def test_link_loss_without_recovery_is_flagged():
    rs = [{"seq": 1, "event_type": "launch"}, {"seq": 2, "event_type": "link_loss"}, {"seq": 3, "event_type": "land"}]
    assert mission_issues(rs) == ["link_loss seq 2 is not followed by link_restored or rth"]


@pytest.mark.parametrize("log", ["mission.jsonl", "flight_log.csv"])
def test_ingest_seals_a_verifiable_chain(tmp_path, log):
    generate_keypair(tmp_path / "k.pem", tmp_path / "k.pub")
    receipts = ingest(PACK / log, tmp_path / "r.jsonl", tmp_path / "k.pem")
    assert len(receipts) == 9
    assert receipts[2]["payload"]["model_version"] == "2.4.1"
    assert verify_ledger((tmp_path / "r.jsonl").read_text().splitlines(), load_public_key(tmp_path / "k.pub"))["ok"]


def test_csv_and_jsonl_logs_seal_the_same_payloads(tmp_path):
    generate_keypair(tmp_path / "k.pem", tmp_path / "k.pub")
    a = ingest(PACK / "mission.jsonl", tmp_path / "a.jsonl", tmp_path / "k.pem")
    b = ingest(PACK / "flight_log.csv", tmp_path / "b.jsonl", tmp_path / "k.pem")
    assert [r["payload_digest"] for r in a] == [r["payload_digest"] for r in b]


def test_ingest_digest_only_and_sort(tmp_path):
    generate_keypair(tmp_path / "k.pem", tmp_path / "k.pub")
    lines = (PACK / "mission.jsonl").read_text().splitlines()
    (tmp_path / "shuffled.jsonl").write_text("\n".join(reversed(lines)) + "\n")
    rs = ingest(tmp_path / "shuffled.jsonl", tmp_path / "r.jsonl", tmp_path / "k.pem", sort=True, digest_only=True)
    assert rs[0]["event_type"] == "launch" and rs[-1]["event_type"] == "land"
    assert all("payload" not in r for r in rs)
    assert "det-eo-small" not in (tmp_path / "r.jsonl").read_text()


def test_ingest_cli_rejects_bad_rows_and_existing_ledger(tmp_path):
    (tmp_path / "bad.csv").write_text("timestamp,event_type\nnot-a-time,launch\n")
    run = lambda *a: subprocess.run([sys.executable, str(ROOT / "scripts" / "ingest_log.py"), *a],
                                    capture_output=True, text=True)
    r = run(str(tmp_path / "bad.csv"), "--ledger", str(tmp_path / "r.jsonl"),
            "--key", str(tmp_path / "k.pem"), "--keygen", str(tmp_path / "k.pub"))
    assert r.returncode != 0 and "not ISO 8601" in (r.stdout + r.stderr)
    (tmp_path / "exists.jsonl").write_text("")
    r = run(str(PACK / "mission.jsonl"), "--ledger", str(tmp_path / "exists.jsonl"), "--key", str(tmp_path / "k.pem"))
    assert r.returncode != 0 and "--append" in (r.stdout + r.stderr)
