"""Metrics calculation from raw observations."""

from __future__ import annotations

from agent_runner.models import EpisodeObservation, Metrics, MetricsMeta


def compute_metrics(observations: list[EpisodeObservation]) -> tuple[Metrics, MetricsMeta]:
    """Compute aggregate metrics from episode observations."""
    total = len(observations)
    if total == 0:
        return Metrics(), MetricsMeta()

    successes = [o for o in observations if o.success]
    success_count = len(successes)
    failed_count = total - success_count

    success_rate = success_count / total

    collision_total = sum(o.collision_count for o in observations)
    collision_count_mean = collision_total / total

    if success_count > 0:
        time_to_goal_mean = sum(
            o.time_to_goal_sec for o in successes if o.time_to_goal_sec is not None
        ) / success_count
    else:
        time_to_goal_mean = None

    reward_mean = sum(o.reward for o in observations) / total

    metrics = Metrics(
        success_rate=success_rate,
        collision_count_mean=collision_count_mean,
        time_to_goal_mean_sec=time_to_goal_mean,
        reward_mean=reward_mean,
    )

    meta = MetricsMeta(
        total_episodes=total,
        success_episodes=success_count,
        failed_episodes=failed_count,
    )

    return metrics, meta
