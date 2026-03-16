#!/usr/bin/env bash
set -euo pipefail

# show-results.sh — Display evaluation results for a completed run.
#
# Usage:
#   bash scripts/show-results.sh <run_id>
#   bash scripts/show-results.sh --latest
#
# Options:
#   --latest    Show the most recent run
#   --json      Output raw JSON instead of formatted summary
#   --help      Show this help
#
# Exit codes:
#   0  Results displayed
#   1  Run not found

ARTIFACTS_ROOT="${ARTIFACTS_ROOT:-/tmp/drone-poc/artifacts}"
RUN_ID=""
JSON_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --latest)
      RUN_ID="$(ls -t "$ARTIFACTS_ROOT/runs/" 2>/dev/null | head -1)"
      if [[ -z "$RUN_ID" ]]; then
        echo "Error: No runs found in $ARTIFACTS_ROOT/runs/" >&2
        exit 1
      fi
      shift
      ;;
    --json)
      JSON_MODE=true
      shift
      ;;
    --help)
      head -16 "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *)
      RUN_ID="$1"
      shift
      ;;
  esac
done

if [[ -z "$RUN_ID" ]]; then
  echo "Error: run_id is required." >&2
  echo "Usage: bash scripts/show-results.sh <run_id>" >&2
  echo "       bash scripts/show-results.sh --latest" >&2
  exit 1
fi

RUN_DIR="$ARTIFACTS_ROOT/runs/$RUN_ID"

if [[ ! -d "$RUN_DIR" ]]; then
  echo "Error: Run directory not found: $RUN_DIR" >&2
  exit 1
fi

if $JSON_MODE; then
  echo '{'
  echo '  "run_id": "'"$RUN_ID"'",'
  echo '  "metrics": '
  cat "$RUN_DIR/metrics.json" 2>/dev/null || echo 'null'
  echo ','
  echo '  "summary": '
  cat "$RUN_DIR/summary.json" 2>/dev/null || echo 'null'
  echo '}'
  exit 0
fi

echo "============================================"
echo "  Run: $RUN_ID"
echo "============================================"
echo ""

# Summary
if [[ -f "$RUN_DIR/summary.json" ]]; then
  STATUS="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','unknown'))" < "$RUN_DIR/summary.json" 2>/dev/null || echo "unknown")"
  PASSED="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('passed','N/A'))" < "$RUN_DIR/summary.json" 2>/dev/null || echo "N/A")"
  REASON="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('reason',''))" < "$RUN_DIR/summary.json" 2>/dev/null || echo "")"

  echo "  Status:  $STATUS"
  echo "  Passed:  $PASSED"
  if [[ -n "$REASON" ]]; then
    echo "  Reason:  $REASON"
  fi
  echo ""
fi

# Metrics
if [[ -f "$RUN_DIR/metrics.json" ]]; then
  echo "--- Metrics ---"
  python3 -c "
import json, sys
d = json.load(sys.stdin)
for side in ('baseline', 'candidate'):
    m = d.get(side)
    if m:
        print(f'  {side}:')
        for k, v in m.items():
            print(f'    {k}: {v}')
delta = d.get('delta')
if delta:
    print('  delta:')
    for k, v in delta.items():
        print(f'    {k}: {v}')
" < "$RUN_DIR/metrics.json" 2>/dev/null || echo "  (could not parse metrics.json)"
  echo ""
fi

# Errors
if [[ -f "$RUN_DIR/metrics.json" ]]; then
  ERRORS="$(python3 -c "
import json, sys
d = json.load(sys.stdin)
errs = d.get('errors', [])
if errs:
    for e in errs:
        print(f\"  [{e.get('code','?')}] {e.get('message','')}\")
" < "$RUN_DIR/metrics.json" 2>/dev/null)"
  if [[ -n "$ERRORS" ]]; then
    echo "--- Errors ---"
    echo "$ERRORS"
    echo ""
  fi
fi

echo "  Artifacts: $RUN_DIR/"
