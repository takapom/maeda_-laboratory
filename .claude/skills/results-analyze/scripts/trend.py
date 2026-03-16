# /// script
# dependencies = []
# ///
"""Show metrics trend across recent evaluation runs.

Usage:
    python3 scripts/trend.py [--limit N] [--metric NAME] [--json]

Options:
    --limit N       Number of recent runs to show (default: 10)
    --metric NAME   Focus on a specific metric (default: all primary metrics)
    --json          Output as JSON
    --help          Show this help

Exit codes:
    0  Success
    1  No runs found
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    args = sys.argv[1:]
    if "--help" in args:
        print(__doc__.strip())
        sys.exit(0)

    limit = 10
    metric_filter = None
    json_mode = False

    i = 0
    while i < len(args):
        if args[i] == "--limit":
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--metric":
            metric_filter = args[i + 1]
            i += 2
        elif args[i] == "--json":
            json_mode = True
            i += 1
        else:
            print(f"Error: Unknown argument: {args[i]}", file=sys.stderr)
            sys.exit(1)

    artifacts_root = Path(os.environ.get("ARTIFACTS_ROOT", "/tmp/drone-poc/artifacts"))
    runs_dir = artifacts_root / "runs"

    if not runs_dir.exists():
        print("No runs found.", file=sys.stderr)
        sys.exit(1)

    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    run_dirs = run_dirs[:limit]
    run_dirs.reverse()  # oldest first for trend

    rows = []
    for rd in run_dirs:
        run_id = rd.name
        metrics_path = rd / "metrics.json"
        summary_path = rd / "summary.json"
        request_path = rd / "request.json"

        row: dict = {"run_id": run_id}

        if request_path.exists():
            req = json.loads(request_path.read_text())
            row["goal"] = req.get("goal", "")

        if summary_path.exists():
            summary = json.loads(summary_path.read_text())
            row["status"] = summary.get("status", "?")
            row["passed"] = summary.get("passed")

        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text())
            candidate = metrics.get("candidate") or {}
            delta = metrics.get("delta") or {}
            row["candidate"] = candidate
            row["delta"] = delta

        rows.append(row)

    if not rows:
        print("No runs found.", file=sys.stderr)
        sys.exit(1)

    if json_mode:
        print(json.dumps(rows, indent=2))
        return

    metrics_keys = ["success_rate", "collision_count_mean", "time_to_goal_mean_sec"]
    if metric_filter:
        metrics_keys = [metric_filter]

    # Header
    header = f"{'RUN_ID':>28s}  {'STATUS':>10s}"
    for k in metrics_keys:
        short = k.replace("_mean", "").replace("_sec", "")[:16]
        header += f"  {short:>16s}"
    print(header)
    print("-" * len(header))

    for row in rows:
        line = f"{row['run_id']:>28s}  {row.get('status', '?'):>10s}"
        candidate = row.get("candidate", {})
        for k in metrics_keys:
            v = candidate.get(k)
            if isinstance(v, (int, float)):
                line += f"  {v:>16.4f}"
            else:
                line += f"  {'N/A':>16s}"
        print(line)


if __name__ == "__main__":
    main()
