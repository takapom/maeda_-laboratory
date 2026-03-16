"""Comparison logic: baseline vs candidate metrics."""

from __future__ import annotations

from typing import Any

from agent_runner.models import EvaluationProfile, Metrics


def compute_delta(baseline: Metrics, candidate: Metrics) -> dict[str, float | None]:
    """Compute metric deltas (candidate - baseline). Positive = improvement for most metrics."""
    delta: dict[str, float | None] = {}

    if baseline.success_rate is not None and candidate.success_rate is not None:
        delta["success_rate"] = candidate.success_rate - baseline.success_rate
    else:
        delta["success_rate"] = None

    if baseline.collision_count_mean is not None and candidate.collision_count_mean is not None:
        # Lower is better, so negative delta = improvement
        delta["collision_count_mean"] = (
            candidate.collision_count_mean - baseline.collision_count_mean
        )
    else:
        delta["collision_count_mean"] = None

    if baseline.time_to_goal_mean_sec is not None and candidate.time_to_goal_mean_sec is not None:
        # Lower is better
        delta["time_to_goal_mean_sec"] = (
            candidate.time_to_goal_mean_sec - baseline.time_to_goal_mean_sec
        )
    else:
        delta["time_to_goal_mean_sec"] = None

    if baseline.reward_mean is not None and candidate.reward_mean is not None:
        delta["reward_mean"] = candidate.reward_mean - baseline.reward_mean
    else:
        delta["reward_mean"] = None

    return delta


def evaluate_pass(
    candidate: Metrics,
    profile: EvaluationProfile,
) -> tuple[bool, str]:
    """Evaluate whether candidate passes the evaluation profile criteria.

    Returns (passed, reason).
    """
    criteria = profile.pass_criteria
    reasons: list[str] = []

    min_sr = criteria.get("success_rate_min")
    if min_sr is not None and candidate.success_rate is not None:
        if candidate.success_rate < min_sr:
            reasons.append(
                f"success_rate {candidate.success_rate:.3f} < min {min_sr}"
            )

    max_cc = criteria.get("collision_count_mean_max")
    if max_cc is not None and candidate.collision_count_mean is not None:
        if candidate.collision_count_mean > max_cc:
            reasons.append(
                f"collision_count_mean {candidate.collision_count_mean:.3f} > max {max_cc}"
            )

    max_ttg = criteria.get("time_to_goal_mean_sec_max")
    if max_ttg is not None and candidate.time_to_goal_mean_sec is not None:
        if candidate.time_to_goal_mean_sec > max_ttg:
            reasons.append(
                f"time_to_goal_mean_sec {candidate.time_to_goal_mean_sec:.3f} > max {max_ttg}"
            )

    if reasons:
        return False, "; ".join(reasons)
    return True, "All criteria passed"


def build_summary(
    baseline: Metrics,
    candidate: Metrics,
    delta: dict[str, float | None],
    profile: EvaluationProfile,
    status: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build summary.json content."""
    passed, reason = evaluate_pass(candidate, profile)

    return {
        "status": status,
        "passed": passed,
        "reason": reason,
        "comparison": {
            "baseline": baseline.to_dict(),
            "candidate": candidate.to_dict(),
            "delta": delta,
        },
        "evaluation_profile": profile.to_dict(),
        "errors": errors,
    }
