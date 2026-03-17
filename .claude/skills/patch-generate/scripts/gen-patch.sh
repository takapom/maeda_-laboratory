#!/usr/bin/env bash
set -euo pipefail

# gen-patch.sh — コミットされていない controller/ の変更から patch.diff を生成する。
#
# 使い方:
#   bash scripts/gen-patch.sh [--output ファイル]
#
# オプション:
#   --output ファイル   パッチの出力先（デフォルト: /tmp/drone-poc/patch.diff）
#   --help              このヘルプを表示
#
# 終了コード:
#   0  パッチ生成成功
#   1  controller/ の変更なし
#   2  無効な引数

OUTPUT="/tmp/drone-poc/patch.diff"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    --help)
      head -16 "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "エラー: 不明な引数: $1" >&2
      echo "使い方: bash scripts/gen-patch.sh [--output ファイル]" >&2
      exit 2
      ;;
  esac
done

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "エラー: git リポジトリ内ではありません。" >&2
  exit 1
}

DIFF="$(git -C "$PROJECT_ROOT" diff HEAD -- controller/)"

if [[ -z "$DIFF" ]]; then
  UNTRACKED="$(git -C "$PROJECT_ROOT" ls-files --others --exclude-standard -- controller/)"
  if [[ -z "$UNTRACKED" ]]; then
    echo "エラー: controller/ に変更が検出されませんでした。" >&2
    echo "パッチを生成する前に controller/ 配下のファイルを修正してください。" >&2
    exit 1
  fi
  DIFF="$(git -C "$PROJECT_ROOT" diff --no-index /dev/null -- $UNTRACKED 2>/dev/null || true)"
  if [[ -z "$DIFF" ]]; then
    echo "エラー: 未追跡の controller/ ファイルの差分を生成できませんでした。" >&2
    exit 1
  fi
fi

mkdir -p "$(dirname "$OUTPUT")"
echo "$DIFF" > "$OUTPUT"

LINES="$(wc -l < "$OUTPUT" | tr -d ' ')"
echo "パッチ生成完了: $OUTPUT ($LINES 行)"
