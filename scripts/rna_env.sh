#!/usr/bin/env bash
# Shared setup for the shell examples. Source it:  . "$ROOT/scripts/rna_env.sh"
# Sets:
#   rna_py ...        runs a real Python 3.9+ (tries python3, python, py -3)
#   RNA_BASE_URL      MCP endpoint (env override, else rna.config.json)
#   RNA_KEY_ARGS[@]   curl args for X-Partner-Key when RNA_PARTNER_KEY is set

RNA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Windows ships a "python3" alias that opens the Microsoft Store instead of
# running Python, so check each candidate actually runs a modern interpreter.
RNA_PY=()
for cand in "python3" "python" "py -3"; do
  # shellcheck disable=SC2086
  if $cand -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    read -r -a RNA_PY <<<"$cand"
    break
  fi
done
if [ "${#RNA_PY[@]}" -eq 0 ]; then
  echo "ERROR: no working Python 3.9+ found (tried python3, python, py -3)." >&2
  echo "Install Python 3.12+ from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'." >&2
  echo "On Windows, also turn off the python/python3 App execution aliases in Settings." >&2
  return 1 2>/dev/null || exit 1
fi
rna_py() { "${RNA_PY[@]}" "$@"; }

if [ -z "${RNA_BASE_URL:-}" ]; then
  RNA_BASE_URL="$(rna_py -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_url"])' "$RNA_ROOT/rna.config.json")"
fi
export RNA_BASE_URL

RNA_KEY_ARGS=()
if [ -n "${RNA_PARTNER_KEY:-}" ]; then
  RNA_KEY_ARGS=(-H "X-Partner-Key: ${RNA_PARTNER_KEY}")
fi
