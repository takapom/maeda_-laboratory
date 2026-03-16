# /// script
# dependencies = []
# ///
"""Re-evaluate a run's episodes with different evaluation criteria.

Does NOT re-run the simulation. Reads existing episodes JSONL and
recomputes metrics/pass-fail with new thresholds.

Usage:
    python3 scripts/re-evaluate.py RUN_ID [OPTIONS]

Options:
    --success-rate-min FLOAT    Minimum success rate (default: 0.0)
    --collision-max FLOAT       Maximum collision count mean (default: none)
    --time-max FLOAT            Maximum time to goal mean sec (default: none)
    --json                      Output as JSON
    --help                      Show this help

Exit codes:
    0  Re-evaluation passed
    1  Re-evaluation failed or error
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    args = sys.argv[1:]
    if "--help" in args or len(args) < 1:
        print(__doc__.strip())
        sys.exit(0 if "--help" in args else 1)

    run_id = args[0]
    sr_min: float | None = None
    cc_max: float | None = None
    ttg_max: float | None = None
    json_mode = False

    i = 1
    while i < len(args):
        if args[i] == "--success-rate-min":
            sr_min = float(args[i + 1])
            i += 2
        elif args[i] == "--collision-max":
            cc_max = float(args[i + 1])
            i += 2
        elif args[i] == "--time-max":
            ttg_max = float(args[i + 1])
            i += 2
        elif args[i] == "--json":
            json_mode = True
            i += 1
        else:
            print(f"Error: Unknown argument: {args[i]}", file=sys.stderr)
            sys.exit(1)

    artifacts_root = Path(os.environ.get("ARTIFACTS_ROOT", "/tmp/drone-poc/artifacts"))
    run_dir = artifacts_root / "runs" / run_id

    if not run_dir.exists():
        print(f"Error: Run not found: {run_id}", file=sys.stderr)
        sys.exit(1)

    # Re-compute metrics from episodes JSONL
    baseline_metrics = _compute_from_jsonl(run_dir / "episodes_baseline.jsonl")
    candidate_metrics = _compute_from_jsonl(run_dir / "episodes_candidate.jsonl")

    # Apply new criteria
    reasons: list[str] = []
    if sr_min is not None and candidate_metrics["success_rate"] is not None:
        if candidate_metrics["success_rate"] < sr_min:
            reasons.append(
                f"success_rate {candidate_metrics['success_rate']:.4f} < {sr_min}"
            )
    if cc_max is not None and candidate_metrics["collision_count_mean"] is not None:
        if candidate_metrics["collision_count_mean"] > cc_max:
            reasons.append(
                f"collision_count_mean {candidate_metrics['collision_count_mean']:.4f} > {cc_max}"
            )
    if ttg_max is not None and candidate_metrics["time_to_goal_mean_sec"] is not None:
        if candidate_metrics["time_to_goal_mean_sec"] > ttg_max:
            reasons.append(
                f"time_to_goal_mean_sec {candidate_metrics['time_to_goal_mean_sec']:.4f} > {ttg_max}"
            )

    passed = len(reasons) == 0
    result = {
        "run_id": run_id,
        "passed": passed,
        "reason": "; ".join(reasons) if reasons else "All criteria passed",
        "criteria": {
            "success_rate_min": sr_min,
            "collision_count_mean_max": cc_max,
            "time_to_goal_mean_sec_max": ttg_max,
        },
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
    }

    if json_mode:
        print(json.dumps(result, indent=2))
    else:
        print(f"Run:    {run_id}")
        print(f"Passed: {passed}")
        print(f"Reason: {result['reason']}")
        print()
        print("Candidate metrics:")
        for k, v in candidate_metrics.items():
            print(f"  {k}: {v}")

    sys.exit(0 if passed else 1)


def _compute_from_jsonl(path: Path) -> dict:
    if not path.exists():
        return {
            "success_rate": None,
            "collision_count_mean": None,
            "time_to_goal_mean_sec": None,
            "reward_mean": None,
        }

    episodes = []
    for line in path.read_text().strip().splitlines():
        episodes.append(json.loads(line))

    total = len(episodes)
    if total == 0:
        return {
            "success_rate": None,
            "collision_count_mean": None,
            "time_to_goal_mean_sec": None,
            "reward_mean": None,
        }

    successes = [e for e in episodes if e.get("success")]
    success_count = len(successes)

    success_rate = success_count / total
    collision_mean = sum(e.get("collision_count", 0) for e in episodes) / total

    if success_count > 0:
        ttg_mean = sum(
            e.get("time_to_goal_sec", 0) for e in successes
            if e.get("time_to_goal_sec") is not None
        ) / success_count
    else:
        ttg_mean = None

    reward_mean = sum(e.get("reward", 0) for e in episodes) / total

    return {
        "success_rate": success_rate,
        "collision_count_mean": collision_mean,
        "time_to_goal_mean_sec": ttg_mean,
        "reward_mean": reward_mean,
    }


if __name__ == "__main__":
    main()
