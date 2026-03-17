#!/usr/bin/env bash
set -euo pipefail

# validate-patch.sh — パッチ生成前に controller/ の変更を検証する。
#
# 使い方:
#   bash scripts/validate-patch.sh
#
# チェック項目:
#   1. controller/ にコミットされていない変更がある
#   2. 変更が controller/ のみに限定されている
#   3. 修正された Python ファイルのシンタックスが正しい
#   4. 差分のプレビュー
#
# 終了コード:
#   0  全チェック合格
#   1  検証失敗

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "エラー: git リポジトリ内ではありません。" >&2
  exit 1
}

ERRORS=0

echo "==> controller/ の変更を確認中 ..."
DIFF="$(git -C "$PROJECT_ROOT" diff HEAD -- controller/)"
if [[ -z "$DIFF" ]]; then
  echo "  失敗: controller/ に変更が検出されません" >&2
  ERRORS=$((ERRORS + 1))
else
  LINES="$(echo "$DIFF" | wc -l | tr -d ' ')"
  echo "  OK: controller/ に $LINES 行の差分"
fi

echo ""
echo "==> controller/ 外の変更を確認中 ..."
OTHER_DIFF="$(git -C "$PROJECT_ROOT" diff HEAD -- ':!controller/' ':!.claude/')"
if [[ -n "$OTHER_DIFF" ]]; then
  CHANGED_FILES="$(git -C "$PROJECT_ROOT" diff HEAD --name-only -- ':!controller/' ':!.claude/')"
  echo "  警告: controller/ 外で変更が検出されました:" >&2
  echo "$CHANGED_FILES" | sed 's/^/    /' >&2
  echo "  これらの変更はパッチに含まれません。" >&2
else
  echo "  OK: controller/ 外に変更なし"
fi

echo ""
echo "==> 修正された Python ファイルのシンタックスチェック中 ..."
MODIFIED="$(git -C "$PROJECT_ROOT" diff HEAD --name-only -- 'controller/*.py' 2>/dev/null || true)"
if [[ -n "$MODIFIED" ]]; then
  for f in $MODIFIED; do
    FULL="$PROJECT_ROOT/$f"
    if [[ -f "$FULL" ]]; then
      if python3 -c "import py_compile; py_compile.compile('$FULL', doraise=True)" 2>/dev/null; then
        echo "  OK: $f"
      else
        echo "  失敗: $f にシンタックスエラーがあります" >&2
        ERRORS=$((ERRORS + 1))
      fi
    fi
  done
else
  echo "  （修正された .py ファイルなし）"
fi

echo ""
echo "==> 差分プレビュー ..."
if [[ -n "$DIFF" ]]; then
  echo "$DIFF" | head -40
  TOTAL="$(echo "$DIFF" | wc -l | tr -d ' ')"
  if [[ $TOTAL -gt 40 ]]; then
    echo "  ... （残り $((TOTAL - 40)) 行）"
  fi
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "結果: 検証失敗（$ERRORS 件のエラー）"
  exit 1
else
  echo "結果: 検証合格"
  exit 0
fi
