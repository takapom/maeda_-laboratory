#!/usr/bin/env bash
set -euo pipefail

# run-eval.sh — Generate patch from controller/ changes and run evaluation.
#
# Usage:
#   bash scripts/run-eval.sh --goal "Optimization goal" [OPTIONS]
#
# Options:
#   --goal TEXT          Required. Optimization goal for the evaluation.
#   --constraints TEXT   Optional. Constraints for the patch.
#   --patch-file FILE    Optional. Use an existing patch instead of generating one.
#   --help               Show this help.
#
# Environment:
#   ARTIFACTS_ROOT       Default: /tmp/drone-poc/artifacts
#   WORKSPACE_ROOT       Default: /tmp/drone-poc/workspace
#   COPPELIASIM_HOST     Default: 127.0.0.1
#   COPPELIASIM_PORT     Default: 23000
#
# Exit codes:
#   0  Evaluation completed successfully
#   1  Evaluation failed
#   2  Invalid arguments

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
      echo "Error: Unknown argument: $1" >&2
      echo "Run with --help for usage." >&2
      exit 2
      ;;
  esac
done

if [[ -z "$GOAL" ]]; then
  echo "Error: --goal is required." >&2
  echo "Usage: bash scripts/run-eval.sh --goal \"Optimization goal\"" >&2
  exit 2
fi

# Resolve project root
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: Not inside a git repository." >&2
  exit 1
}

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Defaults
export ARTIFACTS_ROOT="${ARTIFACTS_ROOT:-/tmp/drone-poc/artifacts}"
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-/tmp/drone-poc/workspace}"
export REPO_URL="${REPO_URL:-$PROJECT_ROOT}"
export BASE_REF="${BASE_REF:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"

# Activate venv if available
if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Generate patch if not provided
if [[ -z "$PATCH_FILE" ]]; then
  echo "==> Generating patch from controller/ changes ..."
  PATCH_FILE="/tmp/drone-poc/patch.diff"
  bash "$SKILL_DIR/scripts/gen-patch.sh" --output "$PATCH_FILE"
else
  if [[ ! -f "$PATCH_FILE" ]]; then
    echo "Error: Patch file not found: $PATCH_FILE" >&2
    exit 1
  fi
  echo "==> Using provided patch: $PATCH_FILE"
fi

export PATCH_FILE

# Build CLI args
CLI_ARGS=(
  --goal "$GOAL"
  --patch-file "$PATCH_FILE"
)
if [[ -n "$CONSTRAINTS" ]]; then
  CLI_ARGS+=(--constraints "$CONSTRAINTS")
fi

# Run evaluation
echo "==> Starting evaluation run ..."
echo "    REPO_URL=$REPO_URL"
echo "    BASE_REF=$BASE_REF"
echo "    ARTIFACTS_ROOT=$ARTIFACTS_ROOT"
echo ""

if python -m agent_runner.cli "${CLI_ARGS[@]}"; then
  echo ""
  echo "==> Evaluation completed successfully."

  # Find the latest run and show summary
  LATEST_RUN="$(ls -t "$ARTIFACTS_ROOT/runs/" 2>/dev/null | head -1)"
  if [[ -n "$LATEST_RUN" ]]; then
    echo ""
    bash "$SKILL_DIR/scripts/show-results.sh" "$LATEST_RUN"
  fi
else
  RC=$?
  echo "" >&2
  echo "==> Evaluation failed (exit code $RC)." >&2

  LATEST_RUN="$(ls -t "$ARTIFACTS_ROOT/runs/" 2>/dev/null | head -1)"
  if [[ -n "$LATEST_RUN" ]]; then
    echo "    Artifacts: $ARTIFACTS_ROOT/runs/$LATEST_RUN/" >&2
    STDERR_LOG="$ARTIFACTS_ROOT/runs/$LATEST_RUN/stderr.log"
    if [[ -f "$STDERR_LOG" && -s "$STDERR_LOG" ]]; then
      echo "" >&2
      echo "--- stderr.log ---" >&2
      tail -20 "$STDERR_LOG" >&2
    fi
  fi
  exit $RC
fi
