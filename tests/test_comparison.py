"""Tests for comparison logic."""

from __future__ import annotations

import pytest

from agent_runner.models import EvaluationProfile, Metrics
from sim_eval.comparison import compute_delta, evaluate_pass


def test_delta_basic():
    baseline = Metrics(
        success_rate=0.5, collision_count_mean=2.0,
        time_to_goal_mean_sec=10.0, reward_mean=50.0,
    )
    candidate = Metrics(
        success_rate=0.8, collision_count_mean=1.0,
        time_to_goal_mean_sec=8.0, reward_mean=70.0,
    )
    delta = compute_delta(baseline, candidate)
    assert delta["success_rate"] == pytest.approx(0.3)
    assert delta["collision_count_mean"] == pytest.approx(-1.0)
    assert delta["time_to_goal_mean_sec"] == pytest.approx(-2.0)
    assert delta["reward_mean"] == pytest.approx(20.0)


def test_delta_with_none():
    baseline = Metrics(success_rate=0.5, time_to_goal_mean_sec=None)
    candidate = Metrics(success_rate=0.8, time_to_goal_mean_sec=5.0)
    delta = compute_delta(baseline, candidate)
    assert delta["time_to_goal_mean_sec"] is None


def test_evaluate_pass_ok():
    candidate = Metrics(success_rate=0.8, collision_count_mean=1.0, time_to_goal_mean_sec=8.0)
    profile = EvaluationProfile(pass_criteria={"success_rate_min": 0.5})
    passed, reason = evaluate_pass(candidate, profile)
    assert passed


def test_evaluate_pass_fail():
    candidate = Metrics(success_rate=0.2)
    profile = EvaluationProfile(pass_criteria={"success_rate_min": 0.5})
    passed, reason = evaluate_pass(candidate, profile)
    assert not passed
    assert "success_rate" in reason
