#!/usr/bin/env bash
set -euo pipefail

# list-past-goals.sh — 過去の評価実行の目標とステータスを一覧表示する。
#
# 使い方:
#   bash scripts/list-past-goals.sh [--limit N]
#
# オプション:
#   --limit N   直近 N 件の実行を表示（デフォルト: 10）
#   --help      このヘルプを表示
#
# 終了コード:
#   0  成功
#   1  実行が見つからない

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
      echo "エラー: 不明な引数: $1" >&2
      exit 1
      ;;
  esac
done

RUNS_DIR="$ARTIFACTS_ROOT/runs"

if [[ ! -d "$RUNS_DIR" ]]; then
  echo "$RUNS_DIR に実行が見つかりません"
  exit 1
fi

RUNS="$(ls -t "$RUNS_DIR" 2>/dev/null | head -"$LIMIT")"

if [[ -z "$RUNS" ]]; then
  echo "実行が見つかりませんでした。"
  exit 1
fi

printf "%-28s %-12s %-6s %s\n" "実行ID" "ステータス" "合否" "目標"
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
