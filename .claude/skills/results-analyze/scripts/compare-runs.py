# /// script
# dependencies = []
# ///
"""Compare two evaluation runs side-by-side.

Usage:
    python3 scripts/compare-runs.py RUN_A RUN_B
    python3 scripts/compare-runs.py RUN_A RUN_B --json

Options:
    --json    Output as JSON instead of formatted table
    --help    Show this help

Exit codes:
    0  Success
    1  Run not found or parse error
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    args = sys.argv[1:]

    if "--help" in args or len(args) < 2:
        print(__doc__.strip())
        sys.exit(0 if "--help" in args else 1)

    json_mode = "--json" in args
    args = [a for a in args if a != "--json"]
    run_a, run_b = args[0], args[1]

    artifacts_root = Path(os.environ.get("ARTIFACTS_ROOT", "/tmp/drone-poc/artifacts"))

    data_a = _load_run(artifacts_root, run_a)
    data_b = _load_run(artifacts_root, run_b)

    if data_a is None:
        print(f"Error: Run not found: {run_a}", file=sys.stderr)
        sys.exit(1)
    if data_b is None:
        print(f"Error: Run not found: {run_b}", file=sys.stderr)
        sys.exit(1)

    if json_mode:
        print(json.dumps({"run_a": data_a, "run_b": data_b}, indent=2))
        return

    _print_comparison(run_a, data_a, run_b, data_b)


def _load_run(artifacts_root: Path, run_id: str) -> dict | None:
    run_dir = artifacts_root / "runs" / run_id
    if not run_dir.exists():
        return None

    result: dict = {"run_id": run_id}

    for name in ("metrics.json", "summary.json", "request.json"):
        path = run_dir / name
        if path.exists():
            result[name.replace(".json", "")] = json.loads(path.read_text())

    return result


def _print_comparison(id_a: str, a: dict, id_b: str, b: dict) -> None:
    goal_a = a.get("request", {}).get("goal", "N/A")
    goal_b = b.get("request", {}).get("goal", "N/A")

    print(f"{'':30s} {'Run A':>20s}  {'Run B':>20s}")
    print(f"{'ID':30s} {id_a:>20s}  {id_b:>20s}")
    print(f"{'Goal':30s} {goal_a[:20]:>20s}  {goal_b[:20]:>20s}")

    status_a = a.get("summary", {}).get("status", "?")
    status_b = b.get("summary", {}).get("status", "?")
    print(f"{'Status':30s} {status_a:>20s}  {status_b:>20s}")

    passed_a = str(a.get("summary", {}).get("passed", "?"))
    passed_b = str(b.get("summary", {}).get("passed", "?"))
    print(f"{'Passed':30s} {passed_a:>20s}  {passed_b:>20s}")
    print()

    metrics_a = a.get("metrics", {}).get("candidate", {}) or {}
    metrics_b = b.get("metrics", {}).get("candidate", {}) or {}

    print("--- Candidate Metrics ---")
    all_keys = sorted(set(list(metrics_a.keys()) + list(metrics_b.keys())))
    for k in all_keys:
        va = metrics_a.get(k)
        vb = metrics_b.get(k)
        sa = f"{va:.4f}" if isinstance(va, (int, float)) else str(va)
        sb = f"{vb:.4f}" if isinstance(vb, (int, float)) else str(vb)
        print(f"  {k:28s} {sa:>20s}  {sb:>20s}")


if __name__ == "__main__":
    main()
