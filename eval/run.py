"""Evaluation runner contract.

Usage:
    python -m eval.run --source-dir <path> --scene-id <id>
        --seed-list <csv> --output-dir <dir>

Outputs episodes.jsonl and step logs under output-dir.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, cast

from agent_runner.models import EpisodeObservation
from eval.scene_adapter import SceneAdapter, SceneAdapterError
from eval.scene_catalog import SceneCatalogError, load_scene_definition
from sim_eval.sim_client import SimClient

Vector3 = tuple[float, float, float]
COLLISION_PENALTY = 5.0
DEFAULT_MAX_STEPS = 10_000


class ControllerProtocol(Protocol):
    def compute_control(
        self,
        current_position: Vector3,
        current_velocity: Vector3,
    ) -> Vector3:
        ...


class ControllerLoadError(Exception):
    """Raised when the controller source tree cannot be loaded."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--seed-list", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--skip-load-scene",
        action="store_true",
        help="Assume the target scene is already open in CoppeliaSim and do not call loadScene().",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    seeds = [int(s.strip()) for s in args.seed_list.split(",") if s.strip()]
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "steps").mkdir(parents=True, exist_ok=True)

    scene = load_scene_definition(args.source_dir, args.scene_id)
    controller_factory = load_controller_factory(args.source_dir)
    client = SimClient(
        host=os.environ.get("COPPELIASIM_HOST", "127.0.0.1"),
        port=int(os.environ.get("COPPELIASIM_PORT", "23000")),
        connect_timeout_sec=int(os.environ.get("CONNECT_TIMEOUT_SEC", "30")),
    )
    client.connect()
    adapter = SceneAdapter(scene, client)
    sim_time_limit_sec = float(os.environ.get("SIM_TIME_LIMIT_SEC", "60"))
    max_steps = int(os.environ.get("MAX_SIM_STEPS", str(DEFAULT_MAX_STEPS)))
    skip_scene_load = args.skip_load_scene or _env_truthy("COPPELIASIM_SKIP_LOAD_SCENE")

    _write_json(
        output_dir / "scene_info.json",
        {
            "scene_id": scene.scene_id,
            "scene_path": scene.scene_path,
            "scene_version": scene.scene_version,
            "bridge_script_path": scene.bridge_script_path,
            "skip_scene_load": skip_scene_load,
        },
    )

    episodes: list[dict[str, object]] = []
    for episode_index, seed in enumerate(seeds):
        controller = controller_factory()
        episode, step_records = _run_episode(
            episode_index=episode_index,
            seed=seed,
            controller=controller,
            adapter=adapter,
            client=client,
            sim_time_limit_sec=sim_time_limit_sec,
            max_steps=max_steps,
            skip_scene_load=skip_scene_load,
        )
        episodes.append(episode.to_dict())
        _write_jsonl(output_dir / "steps" / f"episode_{episode_index:04d}.jsonl", step_records)
        print(
            f"Episode {episode_index} (seed={seed}): "
            f"success={episode.success} timed_out={episode.timed_out} error={episode.error_code}"
        )

    _write_jsonl(output_dir / "episodes.jsonl", episodes)
    print(f"Wrote {len(episodes)} episodes to {output_dir / 'episodes.jsonl'}")


def load_controller_factory(source_dir: Path) -> Callable[[], ControllerProtocol]:
    """Load the controller module from source_dir and return a zero-arg factory."""
    source_dir_str = str(source_dir)
    if source_dir_str not in sys.path:
        sys.path.insert(0, source_dir_str)
    for module_name in list(sys.modules):
        if module_name == "controller" or module_name.startswith("controller."):
            sys.modules.pop(module_name, None)

    module = importlib.import_module("controller.drone_controller")
    controller_cls = getattr(module, "DroneController", None)
    if controller_cls is None:
        raise ControllerLoadError("controller.drone_controller.DroneController is missing")

    def build_controller() -> ControllerProtocol:
        controller = controller_cls()
        compute_control = getattr(controller, "compute_control", None)
        if not callable(compute_control):
            raise ControllerLoadError("DroneController.compute_control is missing")
        return cast(ControllerProtocol, controller)

    return build_controller


def _run_episode(
    episode_index: int,
    seed: int,
    controller: ControllerProtocol,
    adapter: SceneAdapter,
    client: SimClient,
    sim_time_limit_sec: float,
    max_steps: int,
    skip_scene_load: bool,
) -> tuple[EpisodeObservation, list[dict[str, object]]]:
    step_records: list[dict[str, object]] = []
    simulation_started = False

    try:
        adapter.prepare_episode(skip_scene_load=skip_scene_load)
        client.start_simulation()
        simulation_started = True
        adapter.reset_episode(seed)
        state = adapter.read_state()
        _sync_controller_goal(controller, state.goal_position)
        goal_position = state.goal_position or getattr(controller, "goal_position", None)

        if state.success:
            return (
                EpisodeObservation(
                    episode_index=episode_index,
                    seed=seed,
                    status="completed",
                    success=True,
                    collision_count=state.collision_count,
                    time_to_goal_sec=0.0,
                    reward=0.0,
                    timed_out=False,
                    error_code=state.error_code,
                ),
                step_records,
            )

        total_reward = 0.0
        previous_collision_count = state.collision_count
        time_to_goal_sec: float | None = None
        timed_out = False
        final_error_code: str | None = state.error_code
        success: bool = state.success

        for step_index in range(max_steps):
            if final_error_code is not None:
                break

            _sync_controller_goal(controller, state.goal_position)
            command = _normalize_vector(
                controller.compute_control(
                    current_position=state.position,
                    current_velocity=state.velocity,
                ),
                label="controller command",
            )
            adapter.apply_control(command)
            client.step()
            sim_time = client.get_simulation_time()
            state = adapter.read_state()
            goal_position = state.goal_position or goal_position
            goal_distance = _distance(state.position, goal_position)
            collision_delta = max(state.collision_count - previous_collision_count, 0)
            previous_collision_count = state.collision_count
            reward_delta = _compute_reward(goal_distance, collision_delta)
            total_reward += reward_delta

            step_records.append(
                {
                    "episode_index": episode_index,
                    "seed": seed,
                    "step_index": step_index,
                    "sim_time": sim_time,
                    "position": list(state.position),
                    "velocity": list(state.velocity),
                    "goal_position": list(goal_position) if goal_position is not None else None,
                    "goal_distance": goal_distance,
                    "command": list(command),
                    "collision_count": state.collision_count,
                    "collision_delta": collision_delta,
                    "reward_delta": reward_delta,
                    "reward_total": total_reward,
                    "success": state.success,
                    "error_code": state.error_code,
                }
            )

            success = state.success
            final_error_code = state.error_code
            if success:
                time_to_goal_sec = sim_time
                break
            if sim_time >= sim_time_limit_sec:
                timed_out = True
                break
        else:
            final_error_code = "max_steps_exceeded"

        status = "completed" if final_error_code is None else "error"
        return (
            EpisodeObservation(
                episode_index=episode_index,
                seed=seed,
                status=status,
                success=success,
                collision_count=state.collision_count,
                time_to_goal_sec=time_to_goal_sec,
                reward=total_reward,
                timed_out=timed_out,
                error_code=final_error_code,
            ),
            step_records,
        )
    except (ControllerLoadError, SceneAdapterError, SceneCatalogError, ValueError) as exc:
        print(
            f"Episode {episode_index} (seed={seed}) failed: {exc}",
            file=sys.stderr,
        )
        return (
            EpisodeObservation(
                episode_index=episode_index,
                seed=seed,
                status="error",
                success=False,
                collision_count=0,
                time_to_goal_sec=None,
                reward=0.0,
                timed_out=False,
                error_code=type(exc).__name__,
            ),
            [{
                "episode_index": episode_index,
                "seed": seed,
                "event": "error",
                "error_code": type(exc).__name__,
                "message": str(exc),
            }],
        )
    except Exception as exc:  # pragma: no cover - defensive guard around runtime callbacks
        traceback.print_exc()
        return (
            EpisodeObservation(
                episode_index=episode_index,
                seed=seed,
                status="error",
                success=False,
                collision_count=0,
                time_to_goal_sec=None,
                reward=0.0,
                timed_out=False,
                error_code=type(exc).__name__,
            ),
            [{
                "episode_index": episode_index,
                "seed": seed,
                "event": "error",
                "error_code": type(exc).__name__,
                "message": str(exc),
            }],
        )
    finally:
        if simulation_started:
            try:
                client.stop_simulation()
            except Exception:  # pragma: no cover - stop failures should not hide episode result
                traceback.print_exc()


def _normalize_vector(value: object, label: str) -> Vector3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must be a length-3 vector")
    try:
        x, y, z = value
        return (float(x), float(y), float(z))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain numeric values") from exc


def _distance(a: Vector3, b: Vector3 | None) -> float | None:
    if b is None:
        return None
    return math.dist(a, b)


def _compute_reward(goal_distance: float | None, collision_delta: int) -> float:
    if goal_distance is None:
        return -COLLISION_PENALTY * collision_delta
    return -goal_distance - COLLISION_PENALTY * collision_delta


def _sync_controller_goal(
    controller: ControllerProtocol,
    goal_position: Vector3 | None,
) -> None:
    if goal_position is None or not hasattr(controller, "goal_position"):
        return
    setattr(controller, "goal_position", goal_position)


def _env_truthy(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n")


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


if __name__ == "__main__":
    main()
