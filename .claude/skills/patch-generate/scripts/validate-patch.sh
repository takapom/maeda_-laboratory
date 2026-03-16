#!/usr/bin/env bash
set -euo pipefail

# validate-patch.sh — Validate controller/ changes before generating a patch.
#
# Usage:
#   bash scripts/validate-patch.sh
#
# Checks:
#   1. controller/ has uncommitted changes
#   2. Changes are limited to controller/ only
#   3. Modified Python files have valid syntax
#   4. Preview of the diff
#
# Exit codes:
#   0  All checks passed
#   1  Validation failed

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: Not inside a git repository." >&2
  exit 1
}

ERRORS=0

echo "==> Checking for controller/ changes ..."
DIFF="$(git -C "$PROJECT_ROOT" diff HEAD -- controller/)"
if [[ -z "$DIFF" ]]; then
  echo "  FAIL: No changes detected in controller/" >&2
  ERRORS=$((ERRORS + 1))
else
  LINES="$(echo "$DIFF" | wc -l | tr -d ' ')"
  echo "  OK: $LINES lines of diff in controller/"
fi

echo ""
echo "==> Checking for changes outside controller/ ..."
OTHER_DIFF="$(git -C "$PROJECT_ROOT" diff HEAD -- ':!controller/' ':!.claude/')"
if [[ -n "$OTHER_DIFF" ]]; then
  CHANGED_FILES="$(git -C "$PROJECT_ROOT" diff HEAD --name-only -- ':!controller/' ':!.claude/')"
  echo "  WARN: Changes detected outside controller/:" >&2
  echo "$CHANGED_FILES" | sed 's/^/    /' >&2
  echo "  These will NOT be included in the patch." >&2
else
  echo "  OK: No changes outside controller/"
fi

echo ""
echo "==> Syntax checking modified Python files ..."
MODIFIED="$(git -C "$PROJECT_ROOT" diff HEAD --name-only -- 'controller/*.py' 2>/dev/null || true)"
if [[ -n "$MODIFIED" ]]; then
  for f in $MODIFIED; do
    FULL="$PROJECT_ROOT/$f"
    if [[ -f "$FULL" ]]; then
      if python3 -c "import py_compile; py_compile.compile('$FULL', doraise=True)" 2>/dev/null; then
        echo "  OK: $f"
      else
        echo "  FAIL: $f has syntax errors" >&2
        ERRORS=$((ERRORS + 1))
      fi
    fi
  done
else
  echo "  (no modified .py files)"
fi

echo ""
echo "==> Diff preview ..."
if [[ -n "$DIFF" ]]; then
  echo "$DIFF" | head -40
  TOTAL="$(echo "$DIFF" | wc -l | tr -d ' ')"
  if [[ $TOTAL -gt 40 ]]; then
    echo "  ... ($((TOTAL - 40)) more lines)"
  fi
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "RESULT: Validation FAILED ($ERRORS error(s))"
  exit 1
else
  echo "RESULT: Validation PASSED"
  exit 0
fi
