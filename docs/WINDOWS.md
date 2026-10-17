# Windows (Git Bash, `py -3`)

The README's commands assume a POSIX shell and `python3`. On Windows the `python3` command is usually a Microsoft Store shortcut that does not run Python. Use `py -3` from Git Bash or PowerShell. These steps were written on Linux and checked against the scripts' code paths; they have not been run on a Windows machine. Any step that could not be made to work is marked.

Prerequisites: Git for Windows (Git Bash), Python 3.9+ from python.org with "Add python.exe to PATH" ticked, and `py -3 -m pip install -r requirements.txt` from the repo root.

## Offline path

```bash
git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
py -3 -m pip install -r requirements.txt

py -3 -m offline keygen --private signer.pem --public signer.pub
py -3 -m offline seal --ledger receipts.jsonl --key signer.pem --event-type launch --payload '{"airframe_id":"UAS-DEMO-01"}'
py -3 -m offline verify receipts.jsonl signer.pub
py -3 scripts/ingest_log.py payloads/tactical_uas/mission.jsonl --ledger mission.jsonl --key m.pem --keygen m.pub
py -3 -m offline bundle --ledger mission.jsonl --public m.pub --out evaluator_bundle.zip
```

Verify the bundle on a machine with networking disabled (turn Wi-Fi off, or disable the adapter; Windows has no `unshare`):

```bash
mkdir evalbox && cd evalbox
py -3 -m zipfile -e ../evaluator_bundle.zip .      # Git Bash has no unzip by default
cd evaluator_bundle
py -3 -I verify.py receipts.jsonl public_key.pub
sha256sum -c SHA256SUMS                            # sha256sum ships with Git Bash
```

Steps that differ or fail on Windows:

| Step | Windows behaviour |
|---|---|
| `signer.pem` written with mode 0600 | **Does not apply.** `os.chmod` on Windows only toggles the read-only attribute. The file is readable by every account that can read the folder. Keep keys in a folder with a restrictive ACL. |
| `--payload '{"airframe_id":"UAS-DEMO-01"}'` in PowerShell | PowerShell strips the inner double quotes. Use Git Bash, or in PowerShell write `--payload '{\"airframe_id\":\"UAS-DEMO-01\"}'`. |
| `unshare -rn` (no-network namespace) | **Not available.** Disable the network adapter instead, or run `tests/test_vectors.py` and `tests/test_offline.py`, which refuse any socket. |
| `unzip` | Not in Git Bash by default; use `py -3 -m zipfile -e`. |
| `python3 -I` in `README.txt` inside the bundle | Read as `py -3 -I`. |
| Line endings | The ledger is written with `\n`. If Git's `core.autocrlf` rewrites `receipts.jsonl` to `\r\n`, hashes still verify (the verifier parses each line), but `sha256sum -c SHA256SUMS` on a converted copy fails. Verify the files from the zip, not a checked-in copy. |

## Hosted sandbox path

```bash
bash scripts/warmup.sh                              # finds py -3 itself
py -3 scripts/first_receipt.py --out receipt.json
py -3 verifier/verify.py receipt.json
bash scripts/smoke_test.sh 2>&1 | tee smoke.log
bash scripts/final_audit.sh                         # writes audit.log
```

`scripts/rna_env.sh` tries `python3`, then `python`, then `py -3`, and stops with a message if none runs Python 3.9+. If `python3` opens the Store, turn off the alias under Settings, Apps, Advanced app settings, App execution aliases, or just rely on `py -3`.

## Tests

```bash
py -3 -m pip install pytest
py -3 -m pytest tests -q
py -3 -m pytest tests/test_vectors.py -q
```
