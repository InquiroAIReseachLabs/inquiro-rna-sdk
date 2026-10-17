# Tactical UAS scenario pack

A training mission with synthetic data, for exercising the offline kit. It contains no weapon or engagement events.

| # | Event | What it records |
|---|---|---|
| 1 | `launch` | airframe, mission, site, operator, mode |
| 2 | `transition` | manual to autonomous waypoint flight |
| 3 | `ai_detection` | `model_id`, `model_version`, `confidence` 0.87, class, sensor frame |
| 4 | `operator_confirm` | operator confirms detection 3 |
| 5 | `ai_detection` | same model, `confidence` 0.58 |
| 6 | `operator_override` | operator overrides detection 5 (false positive) |
| 7 | `link_loss` | primary command link lost |
| 8 | `rth` | return to home on the link-loss failsafe |
| 9 | `land` | landed at the pad |

Files: one JSON file per event (`01_launch.json` …), the whole mission as a log (`mission.jsonl`, and the same as `flight_log.csv`), and a public demo key (`demo_key/`, see its README: it proves nothing).

## Demos

`python3 scripts/run_scenario.py demo` rebuilds `demos/` and prints each result. Each demo folder holds `receipts.jsonl` and the exact `expected_output.txt`:

| Demo | What was done | Result |
|---|---|---|
| `intact` | Mission sealed as logged | chain verified, mission OK |
| `tamper` | Detection 5's confidence changed from 0.58 to 0.95 after sealing | seq 5 reported as edited |
| `missing_event` | Operator override deleted from the sealed chain | gap after seq 5, and detection 5 has no operator decision |
| `missing_event_resealed` | Override left out of the log before sealing | chain verifies (it was sealed that way); the mission rules still flag detection 5 |

Check any ledger against the mission rules:

```bash
python3 scripts/run_scenario.py check receipts.jsonl signer.pub
```

Rules: the chain starts with `launch`; every `ai_detection` gets an `operator_confirm` or `operator_override` naming it before the next detection; every `link_loss` is followed by `link_restored` or `rth`.
