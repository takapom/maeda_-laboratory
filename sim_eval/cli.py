"""sim-eval CLI: evaluate baseline and candidate, output metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_runner.models import EvaluationProfile, Metrics, MetricsMeta
from sim_eval.comparison import build_summary, compute_delta
from sim_eval.evaluator import run_episodes
from sim_eval.metrics import compute_metrics


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="sim-eval: evaluate baseline and candidate")
    parser.add_argument("--baseline-dir", required=True, type=Path)
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--seed-list", required=True, help="Comma-separated seed list")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--sim-time-limit-sec", type=int, default=60)
    parser.add_argument("--connect-timeout-sec", type=int, default=30)
    parser.add_argument("--coppeliasim-host", default="127.0.0.1")
    parser.add_argument("--coppeliasim-port", type=int, default=23000)
    parser.add_argument("--evaluation-profile", type=Path, default=None)
    return parser.parse_args(argv)


def load_profile(path: Path | None) -> EvaluationProfile:
    if path and path.exists():
        data = json.loads(path.read_text())
        return EvaluationProfile(
            profile_name=data.get("profile_name", "balanced"),
            primary_metrics=data.get("primary_metrics", []),
            weights=data.get("weights", {}),
            pass_criteria=data.get("pass_criteria", {}),
        )
    return EvaluationProfile()


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    seeds = [int(s.strip()) for s in args.seed_list.split(",")]
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    profile = load_profile(args.evaluation_profile)
    errors: list[dict[str, object]] = []

    # --- Evaluate baseline ---
    print("Evaluating baseline ...")
    baseline_output = output_dir / "baseline"
    try:
        baseline_obs = run_episodes(
            source_dir=args.baseline_dir,
            scene_id=args.scene_id,
            seed_list=seeds,
            output_dir=baseline_output,
            sim_time_limit_sec=args.sim_time_limit_sec,
            connect_timeout_sec=args.connect_timeout_sec,
            coppeliasim_host=args.coppeliasim_host,
            coppeliasim_port=args.coppeliasim_port,
        )
        baseline_metrics, baseline_meta = compute_metrics(baseline_obs)
    except Exception as e:
        print(f"Baseline evaluation failed: {e}", file=sys.stderr)
        errors.append({"code": "eval_failed", "message": f"baseline: {e}", "retryable": False})
        baseline_obs = []
        baseline_metrics = Metrics()
        baseline_meta = MetricsMeta()

    # --- Evaluate candidate ---
    print("Evaluating candidate ...")
    candidate_output = output_dir / "candidate"
    try:
        candidate_obs = run_episodes(
            source_dir=args.candidate_dir,
            scene_id=args.scene_id,
            seed_list=seeds,
            output_dir=candidate_output,
            sim_time_limit_sec=args.sim_time_limit_sec,
            connect_timeout_sec=args.connect_timeout_sec,
            coppeliasim_host=args.coppeliasim_host,
            coppeliasim_port=args.coppeliasim_port,
        )
        candidate_metrics, candidate_meta = compute_metrics(candidate_obs)
    except Exception as e:
        print(f"Candidate evaluation failed: {e}", file=sys.stderr)
        errors.append({"code": "eval_failed", "message": f"candidate: {e}", "retryable": False})
        candidate_obs = []
        candidate_metrics = Metrics()
        candidate_meta = MetricsMeta()

    # --- Comparison ---
    delta = compute_delta(baseline_metrics, candidate_metrics)
    status = "succeeded" if not errors else "failed"

    # --- Write outputs ---
    # episodes_baseline.jsonl
    _write_jsonl(output_dir / "episodes_baseline.jsonl", [o.to_dict() for o in baseline_obs])
    # episodes_candidate.jsonl
    _write_jsonl(output_dir / "episodes_candidate.jsonl", [o.to_dict() for o in candidate_obs])

    # metrics.json
    metrics_data = {
        "baseline": baseline_metrics.to_dict(),
        "candidate": candidate_metrics.to_dict(),
        "delta": delta,
        "baseline_meta": baseline_meta.to_dict(),
        "candidate_meta": candidate_meta.to_dict(),
        "errors": errors,
    }
    _write_json(output_dir / "metrics.json", metrics_data)

    # summary.json
    summary = build_summary(
        baseline=baseline_metrics,
        candidate=candidate_metrics,
        delta=delta,
        profile=profile,
        status=status,
        errors=errors,
    )
    _write_json(output_dir / "summary.json", summary)

    # evaluation_profile.json
    _write_json(output_dir / "evaluation_profile.json", profile.to_dict())

    print(f"sim-eval complete. Status: {status}")
    if errors:
        sys.exit(1)


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n")


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


if __name__ == "__main__":
    main()
