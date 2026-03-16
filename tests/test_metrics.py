"""Tests for metrics calculation."""

from __future__ import annotations

from agent_runner.models import EpisodeObservation
from sim_eval.metrics import compute_metrics


def _obs(
    success: bool, collision: int = 0, ttg: float | None = None, reward: float = 0.0,
) -> EpisodeObservation:
    return EpisodeObservation(
        episode_index=0, seed=42, status="completed",
        success=success, collision_count=collision,
        time_to_goal_sec=ttg, reward=reward, timed_out=False,
    )


def test_all_success():
    obs = [_obs(True, 0, 5.0, 100.0), _obs(True, 1, 10.0, 80.0)]
    m, meta = compute_metrics(obs)
    assert m.success_rate == 1.0
    assert m.collision_count_mean == 0.5
    assert m.time_to_goal_mean_sec == 7.5
    assert m.reward_mean == 90.0
    assert meta.total_episodes == 2
    assert meta.success_episodes == 2


def test_mixed():
    obs = [_obs(True, 0, 5.0, 100.0), _obs(False, 3, None, 10.0)]
    m, meta = compute_metrics(obs)
    assert m.success_rate == 0.5
    assert m.collision_count_mean == 1.5
    assert m.time_to_goal_mean_sec == 5.0  # only success episodes
    assert meta.failed_episodes == 1


def test_all_fail():
    obs = [_obs(False, 2, None, 0.0)]
    m, _ = compute_metrics(obs)
    assert m.success_rate == 0.0
    assert m.time_to_goal_mean_sec is None


def test_empty():
    m, meta = compute_metrics([])
    assert meta.total_episodes == 0
