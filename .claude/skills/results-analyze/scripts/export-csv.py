# /// script
# dependencies = []
# ///
"""Export evaluation run history to CSV.

Usage:
    python3 scripts/export-csv.py [--output FILE] [--limit N]

Options:
    --output FILE   Write CSV to FILE (default: stdout)
    --limit N       Export last N runs (default: all)
    --help          Show this help

Exit codes:
    0  Success
    1  No runs found
"""

from __future__ import annotations

import csv
import json
import os
import sys
from io import StringIO
from pathlib import Path


COLUMNS = [
    "run_id",
    "status",
    "passed",
    "goal",
    "baseline_success_rate",
    "baseline_collision_count_mean",
    "baseline_time_to_goal_mean_sec",
    "candidate_success_rate",
    "candidate_collision_count_mean",
    "candidate_time_to_goal_mean_sec",
    "delta_success_rate",
    "delta_collision_count_mean",
    "delta_time_to_goal_mean_sec",
]


def main() -> None:
    args = sys.argv[1:]
    if "--help" in args:
        print(__doc__.strip())
        sys.exit(0)

    output_file = None
    limit = None

    i = 0
    while i < len(args):
        if args[i] == "--output":
            output_file = args[i + 1]
            i += 2
        elif args[i] == "--limit":
            limit = int(args[i + 1])
            i += 2
        else:
            print(f"Error: Unknown argument: {args[i]}", file=sys.stderr)
            sys.exit(1)

    artifacts_root = Path(os.environ.get("ARTIFACTS_ROOT", "/tmp/drone-poc/artifacts"))
    runs_dir = artifacts_root / "runs"

    if not runs_dir.exists():
        print("No runs found.", file=sys.stderr)
        sys.exit(1)

    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if limit:
        run_dirs = run_dirs[:limit]
    run_dirs.reverse()

    if not run_dirs:
        print("No runs found.", file=sys.stderr)
        sys.exit(1)

    buf = StringIO() if output_file is None else None
    out = open(output_file, "w", newline="") if output_file else buf
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()

    for rd in run_dirs:
        row = _extract_row(rd)
        writer.writerow(row)

    if output_file:
        out.close()
        print(f"Exported {len(run_dirs)} runs to {output_file}")
    else:
        sys.stdout.write(buf.getvalue())


def _extract_row(run_dir: Path) -> dict:
    run_id = run_dir.name
    row: dict = {c: "" for c in COLUMNS}
    row["run_id"] = run_id

    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        s = json.loads(summary_path.read_text())
        row["status"] = s.get("status", "")
        row["passed"] = s.get("passed", "")

    request_path = run_dir / "request.json"
    if request_path.exists():
        r = json.loads(request_path.read_text())
        row["goal"] = r.get("goal", "")

    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text())
        for side in ("baseline", "candidate"):
            data = m.get(side) or {}
            for k in ("success_rate", "collision_count_mean", "time_to_goal_mean_sec"):
                row[f"{side}_{k}"] = data.get(k, "")
        delta = m.get("delta") or {}
        for k in ("success_rate", "collision_count_mean", "time_to_goal_mean_sec"):
            row[f"delta_{k}"] = delta.get(k, "")

    return row


if __name__ == "__main__":
    main()
