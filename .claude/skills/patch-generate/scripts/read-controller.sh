#!/usr/bin/env bash
set -euo pipefail

# read-controller.sh — Print all controller/ source files with context.
#
# Usage:
#   bash scripts/read-controller.sh
#
# Exit codes:
#   0  Success
#   1  No controller/ directory found

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: Not inside a git repository." >&2
  exit 1
}

CONTROLLER_DIR="$PROJECT_ROOT/controller"

if [[ ! -d "$CONTROLLER_DIR" ]]; then
  echo "Error: controller/ directory not found at $CONTROLLER_DIR" >&2
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
  echo "No Python files found in controller/."
else
  echo "--- $FILE_COUNT file(s) ---"
fi
