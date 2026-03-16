#!/usr/bin/env bash
set -euo pipefail

# list-past-goals.sh — List goals and status from previous evaluation runs.
#
# Usage:
#   bash scripts/list-past-goals.sh [--limit N]
#
# Options:
#   --limit N   Show last N runs (default: 10)
#   --help      Show this help
#
# Exit codes:
#   0  Success
#   1  No runs found

ARTIFACTS_ROOT="${ARTIFACTS_ROOT:-/tmp/drone-poc/artifacts}"
LIMIT=10

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --help)
      head -14 "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

RUNS_DIR="$ARTIFACTS_ROOT/runs"

if [[ ! -d "$RUNS_DIR" ]]; then
  echo "No runs found in $RUNS_DIR"
  exit 1
fi

RUNS="$(ls -t "$RUNS_DIR" 2>/dev/null | head -"$LIMIT")"

if [[ -z "$RUNS" ]]; then
  echo "No runs found."
  exit 1
fi

printf "%-28s %-12s %-6s %s\n" "RUN_ID" "STATUS" "PASS" "GOAL"
printf "%-28s %-12s %-6s %s\n" "---" "---" "---" "---"

for run_id in $RUNS; do
  RUN_DIR="$RUNS_DIR/$run_id"

  GOAL="$(python3 -c "
import json, sys
try:
    d = json.load(open('$RUN_DIR/request.json'))
    print(d.get('goal', 'N/A')[:60])
except: print('N/A')
" 2>/dev/null)"

  STATUS="$(python3 -c "
import json, sys
try:
    d = json.load(open('$RUN_DIR/summary.json'))
    print(d.get('status', '?'))
except: print('?')
" 2>/dev/null)"

  PASSED="$(python3 -c "
import json, sys
try:
    d = json.load(open('$RUN_DIR/summary.json'))
    print(d.get('passed', 'N/A'))
except: print('?')
" 2>/dev/null)"

  printf "%-28s %-12s %-6s %s\n" "$run_id" "$STATUS" "$PASSED" "$GOAL"
done
