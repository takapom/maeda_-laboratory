#!/usr/bin/env bash
set -euo pipefail

# gen-patch.sh — Generate patch.diff from uncommitted controller/ changes.
#
# Usage:
#   bash scripts/gen-patch.sh [--output FILE]
#
# Options:
#   --output FILE   Write patch to FILE (default: /tmp/drone-poc/patch.diff)
#   --help          Show this help
#
# Exit codes:
#   0  Patch generated successfully
#   1  No controller/ changes found
#   2  Invalid arguments

OUTPUT="/tmp/drone-poc/patch.diff"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    --help)
      head -14 "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      echo "Usage: bash scripts/gen-patch.sh [--output FILE]" >&2
      exit 2
      ;;
  esac
done

# Find project root (where .git is)
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: Not inside a git repository." >&2
  exit 1
}

# Check for controller/ changes (staged + unstaged)
DIFF="$(git -C "$PROJECT_ROOT" diff HEAD -- controller/)"

if [[ -z "$DIFF" ]]; then
  # Also check for untracked files in controller/
  UNTRACKED="$(git -C "$PROJECT_ROOT" ls-files --others --exclude-standard -- controller/)"
  if [[ -z "$UNTRACKED" ]]; then
    echo "Error: No changes detected in controller/." >&2
    echo "Modify files under controller/ before generating a patch." >&2
    exit 1
  fi
  # For untracked files, use diff against /dev/null
  DIFF="$(git -C "$PROJECT_ROOT" diff --no-index /dev/null -- $UNTRACKED 2>/dev/null || true)"
  if [[ -z "$DIFF" ]]; then
    echo "Error: Could not generate diff for untracked controller/ files." >&2
    exit 1
  fi
fi

# Write patch
mkdir -p "$(dirname "$OUTPUT")"
echo "$DIFF" > "$OUTPUT"

LINES="$(wc -l < "$OUTPUT" | tr -d ' ')"
echo "Patch generated: $OUTPUT ($LINES lines)"
