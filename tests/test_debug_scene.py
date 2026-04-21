"""Tests for eval.debug_scene."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eval import debug_scene
from eval.scene_adapter import SceneState


@dataclass
class FakeSceneDefinition:
    scene_id: str = "default"
    scene_path: str = "/tmp/default_drone.ttt"
    scene_version: str = "1.0.0"
    bridge_script_path: str = "/EvalBridge"
    bridge_reset_function: str = "reset_episode"
    bridge_read_state_function: str = "read_state"
    bridge_apply_control_function: str = "apply_control"


class FakeSimClient:
    def __init__(self, host: str, port: int, connect_timeout_sec: int = 30):
        self.host = host
        self.port = port
        self.connect_timeout_sec = connect_timeout_sec
        self.started = False
        self.steps = 0

    def connect(self) -> None:
        return None

    def get_version(self) -> str:
        return "4.10.0"

    def start_simulation(self) -> None:
        self.started = True

    def step(self) -> None:
        self.steps += 1

    def stop_simulation(self) -> None:
        self.started = False


class FakeSceneAdapter:
    def __init__(self, scene: FakeSceneDefinition, client: FakeSimClient):
        self.scene = scene
        self.client = client
        self.reset_seed: int | None = None
        self.command: tuple[float, float, float] | None = None
        self.loaded = False
        self.bound = False

    def load_scene(self) -> None:
        self.loaded = True

    def bind_bridge(self) -> None:
        self.bound = True

    def reset_episode(self, seed: int) -> None:
        self.reset_seed = seed

    def read_state(self) -> SceneState:
        return SceneState(
            position=(1.0, 2.0, 3.0),
            velocity=(0.0, 0.0, 0.0),
            goal_position=(4.0, 5.0, 6.0),
            collision_count=0,
            success=False,
            error_code=None,
        )

    def apply_control(self, command: tuple[float, float, float]) -> None:
        self.command = command


def test_debug_scene_prints_stage_progress(monkeypatch, capsys, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    monkeypatch.setattr(debug_scene, "load_scene_definition", lambda *_: FakeSceneDefinition())
    monkeypatch.setattr(debug_scene, "SimClient", FakeSimClient)
    monkeypatch.setattr(debug_scene, "SceneAdapter", FakeSceneAdapter)

    debug_scene.main(
        [
            "--source-dir",
            str(source_dir),
            "--scene-id",
            "default",
            "--seed",
            "7",
            "--steps",
            "2",
            "--command",
            "0.1",
            "0.0",
            "-0.1",
        ]
    )

    out = capsys.readouterr().out
    assert "[1/8] connect" not in out
    assert "[1/9] connect" in out
    assert "[3/9] bind_bridge /EvalBridge" in out
    assert "[5/9] reset_episode seed=7" in out
    assert "[8/9] step 2/2" in out
    assert "[9/9] completed" in out
    assert "stopping simulation" in out


def test_debug_scene_can_skip_scene_load(monkeypatch, capsys, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    monkeypatch.setattr(debug_scene, "load_scene_definition", lambda *_: FakeSceneDefinition())
    monkeypatch.setattr(debug_scene, "SimClient", FakeSimClient)
    monkeypatch.setattr(debug_scene, "SceneAdapter", FakeSceneAdapter)

    debug_scene.main(
        [
            "--source-dir",
            str(source_dir),
            "--scene-id",
            "default",
            "--skip-load-scene",
        ]
    )

    out = capsys.readouterr().out
    assert "[2/9] skip load_scene" in out
