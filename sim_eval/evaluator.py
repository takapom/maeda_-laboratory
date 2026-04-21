"""Evaluator: run episodes in CoppeliaSim and collect raw observations."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agent_runner.models import EpisodeObservation


def run_episodes(
    source_dir: Path,
    scene_id: str,
    seed_list: list[int],
    output_dir: Path,
    sim_time_limit_sec: int,
    connect_timeout_sec: int,
    coppeliasim_host: str,
    coppeliasim_port: int,
) -> list[EpisodeObservation]:
    """Run evaluation episodes using the repo's eval.run contract.

    Calls: python -m eval.run --source-dir <path> --scene-id <scene_id>
           --seed-list <csv> --output-dir <dir>

    Returns parsed episode observations.
    """
    seed_csv = ",".join(str(s) for s in seed_list)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update({
        "COPPELIASIM_HOST": coppeliasim_host,
        "COPPELIASIM_PORT": str(coppeliasim_port),
        "CONNECT_TIMEOUT_SEC": str(connect_timeout_sec),
        "SIM_TIME_LIMIT_SEC": str(sim_time_limit_sec),
    })

    result = subprocess.run(
        [
            sys.executable, "-m", "eval.run",
            "--source-dir", str(source_dir),
            "--scene-id", scene_id,
            "--seed-list", seed_csv,
            "--output-dir", str(output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(source_dir),
        env=env,
        timeout=connect_timeout_sec + len(seed_list) * sim_time_limit_sec + 60,
    )

    (output_dir / "eval_stdout.log").write_text(result.stdout)
    (output_dir / "eval_stderr.log").write_text(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"eval.run failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    return _parse_observations(output_dir, seed_list)


def _parse_observations(
    output_dir: Path, seed_list: list[int]
) -> list[EpisodeObservation]:
    """Parse episode results from output_dir.

    Expects output_dir/episodes.jsonl written by eval.run.
    Falls back to generating stub observations if the file is missing.
    """
    import json

    jsonl_path = output_dir / "episodes.jsonl"
    observations: list[EpisodeObservation] = []

    if jsonl_path.exists():
        for line in jsonl_path.read_text().strip().splitlines():
            data = json.loads(line)
            observations.append(EpisodeObservation(
                episode_index=data["episode_index"],
                seed=data["seed"],
                status=data.get("status", "completed"),
                success=data.get("success", False),
                collision_count=data.get("collision_count", 0),
                time_to_goal_sec=data.get("time_to_goal_sec"),
                reward=data.get("reward", 0.0),
                timed_out=data.get("timed_out", False),
                error_code=data.get("error_code"),
            ))
    else:
        # Fallback: mark all episodes as failed
        for i, seed in enumerate(seed_list):
            observations.append(EpisodeObservation(
                episode_index=i,
                seed=seed,
                status="error",
                success=False,
                collision_count=0,
                time_to_goal_sec=None,
                reward=0.0,
                timed_out=False,
                error_code="episodes_jsonl_missing",
            ))

    return observations
