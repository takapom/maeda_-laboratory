"""Data models for run metadata, artifacts, and evaluation."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class RunStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class RunStage(str, enum.Enum):
    PATCH_GENERATE = "patch_generate"
    PATCH_APPLY = "patch_apply"
    STATIC_CHECK = "static_check"
    EVAL_START = "eval_start"
    SIM_CONNECT = "sim_connect"
    EVAL_RUN = "eval_run"
    ARTIFACT_COLLECT = "artifact_collect"


@dataclass
class RunError:
    code: str
    message: str
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


@dataclass
class EpisodeObservation:
    episode_index: int
    seed: int
    status: str
    success: bool
    collision_count: int
    time_to_goal_sec: float | None
    reward: float
    timed_out: bool
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_index": self.episode_index,
            "seed": self.seed,
            "status": self.status,
            "success": self.success,
            "collision_count": self.collision_count,
            "time_to_goal_sec": self.time_to_goal_sec,
            "reward": self.reward,
            "timed_out": self.timed_out,
            "error_code": self.error_code,
        }


@dataclass
class Metrics:
    success_rate: float | None = None
    collision_count_mean: float | None = None
    time_to_goal_mean_sec: float | None = None
    reward_mean: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success_rate": self.success_rate,
            "collision_count_mean": self.collision_count_mean,
            "time_to_goal_mean_sec": self.time_to_goal_mean_sec,
            "reward_mean": self.reward_mean,
        }


@dataclass
class MetricsMeta:
    total_episodes: int = 0
    success_episodes: int = 0
    failed_episodes: int = 0
    denominator: str = "total_episodes"
    failure_handling: str = "counted_as_failure"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_episodes": self.total_episodes,
            "success_episodes": self.success_episodes,
            "failed_episodes": self.failed_episodes,
            "denominator": self.denominator,
            "failure_handling": self.failure_handling,
        }


@dataclass
class EvaluationProfile:
    profile_name: str = "balanced"
    primary_metrics: list[str] = field(
        default_factory=lambda: ["success_rate", "collision_count_mean", "time_to_goal_mean_sec"]
    )
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "success_rate": 0.5,
            "collision_count_mean": 0.3,
            "time_to_goal_mean_sec": 0.2,
        }
    )
    pass_criteria: dict[str, Any] = field(
        default_factory=lambda: {
            "success_rate_min": 0.0,
            "collision_count_mean_max": None,
            "time_to_goal_mean_sec_max": None,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "primary_metrics": self.primary_metrics,
            "weights": self.weights,
            "pass_criteria": self.pass_criteria,
        }
