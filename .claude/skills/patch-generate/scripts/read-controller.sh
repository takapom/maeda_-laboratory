#!/usr/bin/env bash
set -euo pipefail

# read-controller.sh — controller/ の全ソースファイルをコンテキスト付きで表示する。
#
# 使い方:
#   bash scripts/read-controller.sh
#
# 終了コード:
#   0  成功
#   1  controller/ ディレクトリが見つからない

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "エラー: git リポジトリ内ではありません。" >&2
  exit 1
}

CONTROLLER_DIR="$PROJECT_ROOT/controller"

if [[ ! -d "$CONTROLLER_DIR" ]]; then
  echo "エラー: controller/ ディレクトリが見つかりません: $CONTROLLER_DIR" >&2
  exit 1
fi

FILE_COUNT=0
for f in $(find "$CONTROLLER_DIR" -name '*.py' | sort); do
  REL="${f#$PROJECT_ROOT/}"
  echo "=== $REL ==="
  cat -n "$f"
  echo ""
  FILE_COUNT=$((FILE_COUNT + 1))
done

if [[ $FILE_COUNT -eq 0 ]]; then
  echo "controller/ に Python ファイルが見つかりませんでした。"
else
  echo "--- $FILE_COUNT 個のファイル ---"
fi
