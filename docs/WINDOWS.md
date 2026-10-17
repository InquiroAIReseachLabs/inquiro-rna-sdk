# Windows (Git Bash or PowerShell, `py -3`)

On Windows the `python3` command is usually a Microsoft Store shortcut that does not run Python. Use `py -3`.

Prerequisites: Python 3.9+ from python.org with "Add python.exe to PATH" ticked, then `py -3 -m pip install -r requirements.txt` from the repository root. Git Bash (from Git for Windows) is recommended.

## Offline path

```bash
git clone https://github.com/InquiroAIReseachLabs/inquiro-rna-sdk && cd inquiro-rna-sdk
py -3 -m pip install -r requirements.txt

py -3 scripts/ingest_log.py payloads/tactical_uas/mission.jsonl --ledger receipts.jsonl --key signer.pem --keygen signer.pub
py -3 -m offline verify receipts.jsonl signer.pub
py -3 -m offline bundle --ledger receipts.jsonl --public signer.pub --out evaluator_bundle.zip
```

Verify the bundle, for example on a machine with networking disabled:

```bash
mkdir evalbox && cd evalbox
py -3 -m zipfile -e ../evaluator_bundle.zip .      # Git Bash has no unzip by default
cd evaluator_bundle
py -3 -I verify.py receipts.jsonl public_key.pub
sha256sum -c SHA256SUMS                            # sha256sum ships with Git Bash
```

Differences on Windows:

| Step | Windows behaviour |
|---|---|
| `signer.pem` written with mode 0600 | Does not apply: `os.chmod` on Windows only toggles the read-only attribute. Keep keys in a folder with a restrictive NTFS ACL. |
| `--payload '{"airframe_id":"UAS-DEMO-01"}'` in PowerShell | PowerShell strips the inner double quotes. Use Git Bash, or write `--payload '{\"airframe_id\":\"UAS-DEMO-01\"}'`. |
| `unzip` | Not in Git Bash by default; use `py -3 -m zipfile -e`. |
| `python3 -I` in the bundle's `README.txt` | Read as `py -3 -I`. |
| Line endings | If Git converts `receipts.jsonl` to `\r\n`, hashes still verify, but `sha256sum -c SHA256SUMS` on a converted copy fails. Verify the files from the zip. |

## Hosted sandbox path

```bash
py -3 scripts/first_receipt.py --out receipt.json
py -3 verifier/verify.py receipt.json
```
