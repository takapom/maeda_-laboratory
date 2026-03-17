#!/usr/bin/env bash
set -euo pipefail

# show-results.sh — 完了した実行の評価結果を表示する。
#
# 使い方:
#   bash scripts/show-results.sh <run_id>
#   bash scripts/show-results.sh --latest
#
# オプション:
#   --latest    最新の実行を表示
#   --json      整形サマリーの代わりに生の JSON を出力
#   --help      このヘルプを表示
#
# 終了コード:
#   0  結果を表示
#   1  実行が見つからない

ARTIFACTS_ROOT="${ARTIFACTS_ROOT:-/tmp/drone-poc/artifacts}"
RUN_ID=""
JSON_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --latest)
      RUN_ID="$(ls -t "$ARTIFACTS_ROOT/runs/" 2>/dev/null | head -1)"
      if [[ -z "$RUN_ID" ]]; then
        echo "エラー: $ARTIFACTS_ROOT/runs/ に実行が見つかりません" >&2
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
  echo "エラー: run_id は必須です。" >&2
  echo "使い方: bash scripts/show-results.sh <run_id>" >&2
  echo "       bash scripts/show-results.sh --latest" >&2
  exit 1
fi

RUN_DIR="$ARTIFACTS_ROOT/runs/$RUN_ID"

if [[ ! -d "$RUN_DIR" ]]; then
  echo "エラー: 実行ディレクトリが見つかりません: $RUN_DIR" >&2
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
echo "  実行: $RUN_ID"
echo "============================================"
echo ""

# サマリー
if [[ -f "$RUN_DIR/summary.json" ]]; then
  STATUS="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','不明'))" < "$RUN_DIR/summary.json" 2>/dev/null || echo "不明")"
  PASSED="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('passed','N/A'))" < "$RUN_DIR/summary.json" 2>/dev/null || echo "N/A")"
  REASON="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('reason',''))" < "$RUN_DIR/summary.json" 2>/dev/null || echo "")"

  echo "  ステータス:  $STATUS"
  echo "  合否:        $PASSED"
  if [[ -n "$REASON" ]]; then
    echo "  理由:        $REASON"
  fi
  echo ""
fi

# メトリクス
if [[ -f "$RUN_DIR/metrics.json" ]]; then
  echo "--- メトリクス ---"
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
" < "$RUN_DIR/metrics.json" 2>/dev/null || echo "  （metrics.json の解析に失敗しました）"
  echo ""
fi

# エラー
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
    echo "--- エラー ---"
    echo "$ERRORS"
    echo ""
  fi
fi

echo "  アーティファクト: $RUN_DIR/"
