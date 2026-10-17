#!/usr/bin/env bash
# Wake the hosted sandbox and report how long /health took.
# Free instances sleep when idle; the first request after that can take ~a minute.
#   bash scripts/warmup.sh            (endpoint from rna.config.json or RNA_BASE_URL)
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/scripts/rna_env.sh" || exit 1
SLOW_SECONDS="${WARMUP_SLOW_SECONDS:-5}"
URL="$(rna_py -c 'import sys; sys.path.insert(0, sys.argv[1]); import rna_config; print(rna_config.health_url())' "$ROOT")"

out="$(curl -sS --max-time 120 -o /dev/stderr -w '%{http_code} %{time_total}' "$URL" 2>/tmp/warmup_body.$$)" || out="000 0"
code="${out% *}"; secs="${out#* }"
body="$(head -c 300 /tmp/warmup_body.$$ 2>/dev/null)"; rm -f /tmp/warmup_body.$$
echo "GET $URL -> HTTP $code in ${secs}s"
[ -n "$body" ] && echo "  $body"
if [ "$code" != "200" ]; then
  echo "ERROR: health check failed (HTTP $code)." >&2
  exit 1
fi
if rna_py -c "import sys; sys.exit(0 if float('$secs') > float('$SLOW_SECONDS') else 1)"; then
  echo "WARNING: took ${secs}s (over ${SLOW_SECONDS}s): the instance was probably asleep. It is awake now; run your demo next." >&2
fi
case "$body" in
  *'"persistence": "ephemeral"'*) echo "NOTE: sandbox ledger is ephemeral; receipts reset on restart. Keep your receipt files or export a bundle." ;;
esac
exit 0
