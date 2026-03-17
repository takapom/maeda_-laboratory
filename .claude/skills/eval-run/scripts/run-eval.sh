#!/usr/bin/env bash
set -euo pipefail

# run-eval.sh — controller/ の変更からパッチを生成し、評価を実行する。
#
# 使い方:
#   bash scripts/run-eval.sh --goal "最適化の目標" [オプション]
#
# オプション:
#   --goal テキスト         必須。評価の最適化目標。
#   --constraints テキスト  任意。パッチの制約条件。
#   --patch-file ファイル   任意。生成する代わりに既存のパッチを使用。
#   --help                  このヘルプを表示。
#
# 環境変数:
#   ARTIFACTS_ROOT       デフォルト: /tmp/drone-poc/artifacts
#   WORKSPACE_ROOT       デフォルト: /tmp/drone-poc/workspace
#   COPPELIASIM_HOST     デフォルト: 127.0.0.1
#   COPPELIASIM_PORT     デフォルト: 23000
#
# 終了コード:
#   0  評価が正常に完了
#   1  評価が失敗
#   2  無効な引数

GOAL=""
CONSTRAINTS=""
PATCH_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --goal)
      GOAL="$2"
      shift 2
      ;;
    --constraints)
      CONSTRAINTS="$2"
      shift 2
      ;;
    --patch-file)
      PATCH_FILE="$2"
      shift 2
      ;;
    --help)
      head -24 "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "エラー: 不明な引数: $1" >&2
      echo "--help で使い方を確認してください。" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$GOAL" ]]; then
  echo "エラー: --goal は必須です。" >&2
  echo "使い方: bash scripts/run-eval.sh --goal \"最適化の目標\"" >&2
  exit 2
fi

# プロジェクトルートを検出
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "エラー: git リポジトリ内ではありません。" >&2
  exit 1
}

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# デフォルト値
export ARTIFACTS_ROOT="${ARTIFACTS_ROOT:-/tmp/drone-poc/artifacts}"
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-/tmp/drone-poc/workspace}"
export REPO_URL="${REPO_URL:-$PROJECT_ROOT}"
export BASE_REF="${BASE_REF:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"

# 仮想環境が利用可能なら有効化
if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.venv/bin/activate"
fi

# パッチが未指定なら生成
if [[ -z "$PATCH_FILE" ]]; then
  echo "==> controller/ の変更からパッチを生成中 ..."
  PATCH_FILE="/tmp/drone-poc/patch.diff"
  bash "$SKILL_DIR/scripts/gen-patch.sh" --output "$PATCH_FILE"
else
  if [[ ! -f "$PATCH_FILE" ]]; then
    echo "エラー: パッチファイルが見つかりません: $PATCH_FILE" >&2
    exit 1
  fi
  echo "==> 指定されたパッチを使用: $PATCH_FILE"
fi

export PATCH_FILE

# CLI 引数を構築
CLI_ARGS=(
  --goal "$GOAL"
  --patch-file "$PATCH_FILE"
)
if [[ -n "$CONSTRAINTS" ]]; then
  CLI_ARGS+=(--constraints "$CONSTRAINTS")
fi

# 評価を実行
echo "==> 評価実行を開始 ..."
echo "    REPO_URL=$REPO_URL"
echo "    BASE_REF=$BASE_REF"
echo "    ARTIFACTS_ROOT=$ARTIFACTS_ROOT"
echo ""

if python -m agent_runner.cli "${CLI_ARGS[@]}"; then
  echo ""
  echo "==> 評価が正常に完了しました。"

  # 最新の実行を検索してサマリーを表示
  LATEST_RUN="$(ls -t "$ARTIFACTS_ROOT/runs/" 2>/dev/null | head -1)"
  if [[ -n "$LATEST_RUN" ]]; then
    echo ""
    bash "$SKILL_DIR/scripts/show-results.sh" "$LATEST_RUN"
  fi
else
  RC=$?
  echo "" >&2
  echo "==> 評価が失敗しました（終了コード $RC）。" >&2

  LATEST_RUN="$(ls -t "$ARTIFACTS_ROOT/runs/" 2>/dev/null | head -1)"
  if [[ -n "$LATEST_RUN" ]]; then
    echo "    アーティファクト: $ARTIFACTS_ROOT/runs/$LATEST_RUN/" >&2
    STDERR_LOG="$ARTIFACTS_ROOT/runs/$LATEST_RUN/stderr.log"
    if [[ -f "$STDERR_LOG" && -s "$STDERR_LOG" ]]; then
      echo "" >&2
      echo "--- stderr.log ---" >&2
      tail -20 "$STDERR_LOG" >&2
    fi
  fi
  exit $RC
fi
