"""Tests for eval.run."""

from __future__ import annotations

import json
from pathlib import Path

from eval import run as eval_run
from eval.scene_adapter import SceneState


class FakeSimClient:
    def __init__(self, host: str, port: int, connect_timeout_sec: int = 30):
        self.host = host
        self.port = port
        self.connect_timeout_sec = connect_timeout_sec
        self.scene_paths: list[str] = []
        self.sim_time = 0.0
        self.started = 0
        self.stopped = 0

    def connect(self) -> None:
        return None

    def load_scene(self, scene_path: str) -> None:
        self.scene_paths.append(scene_path)
        self.sim_time = 0.0

    def start_simulation(self) -> None:
        self.started += 1

    def step(self) -> None:
        self.sim_time += 1.0

    def stop_simulation(self) -> None:
        self.stopped += 1

    def get_simulation_time(self) -> float:
        return self.sim_time


class FakeSceneAdapter:
    def __init__(self, scene, client: FakeSimClient):
        self.scene = scene
        self.client = client
        self.skip_scene_load_flags: list[bool] = []

    def prepare_episode(self, *, skip_scene_load: bool = False) -> None:
        self.skip_scene_load_flags.append(skip_scene_load)
        if not skip_scene_load:
            self.client.load_scene(self.scene.scene_path)

    def reset_episode(self, seed: int) -> None:
        assert self.client.started > 0

    def read_state(self):
        step_index = int(self.client.get_simulation_time())
        success = step_index >= 3
        collision_count = 1 if step_index >= 2 else 0
        return SceneState(
            position=(max(0.0, 3.0 - step_index), 0.0, 1.0),
            velocity=(-1.0, 0.0, 0.0),
            goal_position=(0.0, 0.0, 1.0),
            collision_count=collision_count,
            success=success,
            error_code=None,
            extras={"route_phase": "test", "active_route_index": step_index + 1},
        )

    def apply_control(self, command):
        return None


def test_main_runs_episode_loop_and_writes_logs(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    (source_dir / "controller").mkdir(parents=True)
    (source_dir / "eval").mkdir()
    (source_dir / "controller" / "__init__.py").write_text("")
    (source_dir / "eval" / "__init__.py").write_text("")
    (source_dir / "controller" / "drone_controller.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "class DroneController:",
                "    def __init__(self) -> None:",
                "        self.goal_position = (0.0, 0.0, 1.0)",
                "",
                "    def compute_control(self, current_position, current_velocity):",
                "        return (-0.5, 0.0, 0.0)",
            ]
        )
        + "\n"
    )
    (source_dir / "eval" / "scenes.yaml").write_text(
        "\n".join(
            [
                "scenes:",
                "  - scene_id: default",
                "    scene_path: ${COPPELIASIM_DEFAULT_SCENE_PATH}",
                "    scene_version: '1.0.0'",
                "    bridge_script_path: /EvalBridge",
            ]
        )
        + "\n"
    )

    output_dir = tmp_path / "output"
    monkeypatch.setenv("COPPELIASIM_DEFAULT_SCENE_PATH", "/tmp/default_drone.ttt")
    monkeypatch.setenv("SIM_TIME_LIMIT_SEC", "10")
    monkeypatch.setattr(eval_run, "SimClient", FakeSimClient)
    monkeypatch.setattr(eval_run, "SceneAdapter", FakeSceneAdapter)

    eval_run.main(
        [
            "--source-dir",
            str(source_dir),
            "--scene-id",
            "default",
            "--seed-list",
            "42",
            "--output-dir",
            str(output_dir),
        ]
    )

    episodes = [
        json.loads(line)
        for line in (output_dir / "episodes.jsonl").read_text().strip().splitlines()
    ]
    assert len(episodes) == 1
    assert episodes[0]["success"] is True
    assert episodes[0]["collision_count"] == 1
    assert episodes[0]["time_to_goal_sec"] == 3.0

    step_lines = [
        json.loads(line)
        for line in (output_dir / "steps" / "episode_0000.jsonl").read_text().strip().splitlines()
    ]
    assert len(step_lines) == 3
    assert step_lines[-1]["success"] is True
    assert step_lines[-1]["goal_distance"] == 0.0
    assert step_lines[-1]["scene_state"]["route_phase"] == "test"
    assert step_lines[-1]["scene_state"]["active_route_index"] == 4

    scene_info = json.loads((output_dir / "scene_info.json").read_text())
    assert scene_info["scene_path"] == "/tmp/default_drone.ttt"
    assert scene_info["skip_scene_load"] is False


def test_main_supports_skip_load_scene_flag(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    (source_dir / "controller").mkdir(parents=True)
    (source_dir / "eval").mkdir()
    (source_dir / "controller" / "__init__.py").write_text("")
    (source_dir / "eval" / "__init__.py").write_text("")
    (source_dir / "controller" / "drone_controller.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "class DroneController:",
                "    def compute_control(self, current_position, current_velocity):",
                "        return (0.0, 0.0, 0.0)",
            ]
        )
        + "\n"
    )
    (source_dir / "eval" / "scenes.yaml").write_text(
        "\n".join(
            [
                "scenes:",
                "  - scene_id: default",
                "    scene_path: /tmp/default_drone.ttt",
                "    scene_version: '1.0.0'",
                "    bridge_script_path: /EvalBridge",
            ]
        )
        + "\n"
    )

    output_dir = tmp_path / "output"
    monkeypatch.setenv("SIM_TIME_LIMIT_SEC", "0")
    monkeypatch.setattr(eval_run, "SimClient", FakeSimClient)
    monkeypatch.setattr(eval_run, "SceneAdapter", FakeSceneAdapter)

    eval_run.main(
        [
            "--source-dir",
            str(source_dir),
            "--scene-id",
            "default",
            "--seed-list",
            "42",
            "--output-dir",
            str(output_dir),
            "--skip-load-scene",
        ]
    )

    scene_info = json.loads((output_dir / "scene_info.json").read_text())
    assert scene_info["skip_scene_load"] is True


def test_main_syncs_scene_goal_into_controller(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    (source_dir / "controller").mkdir(parents=True)
    (source_dir / "eval").mkdir()
    (source_dir / "controller" / "__init__.py").write_text("")
    (source_dir / "eval" / "__init__.py").write_text("")
    (source_dir / "controller" / "drone_controller.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "class DroneController:",
                "    def __init__(self) -> None:",
                "        self.goal_position = (100.0, 0.0, 1.0)",
                "",
                "    def compute_control(self, current_position, current_velocity):",
                "        return (",
                "            self.goal_position[0] - current_position[0],",
                "            self.goal_position[1] - current_position[1],",
                "            self.goal_position[2] - current_position[2],",
                "        )",
            ]
        )
        + "\n"
    )
    (source_dir / "eval" / "scenes.yaml").write_text(
        "\n".join(
            [
                "scenes:",
                "  - scene_id: default",
                "    scene_path: /tmp/default_drone.ttt",
                "    scene_version: '1.0.0'",
                "    bridge_script_path: /EvalBridge",
            ]
        )
        + "\n"
    )

    output_dir = tmp_path / "output"
    monkeypatch.setenv("SIM_TIME_LIMIT_SEC", "1")
    monkeypatch.setattr(eval_run, "SimClient", FakeSimClient)
    monkeypatch.setattr(eval_run, "SceneAdapter", FakeSceneAdapter)

    eval_run.main(
        [
            "--source-dir",
            str(source_dir),
            "--scene-id",
            "default",
            "--seed-list",
            "42",
            "--output-dir",
            str(output_dir),
        ]
    )

    step_lines = [
        json.loads(line)
        for line in (output_dir / "steps" / "episode_0000.jsonl").read_text().strip().splitlines()
    ]
    assert step_lines[0]["command"] == [-3.0, 0.0, 0.0]
