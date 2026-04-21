"""Adapter between eval.run and a CoppeliaSim scene bridge script."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from eval.scene_catalog import SceneDefinition
from sim_eval.sim_client import SimClient

Vector3 = tuple[float, float, float]


class SceneAdapterError(Exception):
    """Raised when the scene bridge contract is violated."""


@dataclass(frozen=True)
class SceneState:
    position: Vector3
    velocity: Vector3
    goal_position: Vector3 | None = None
    collision_count: int = 0
    success: bool = False
    error_code: str | None = None


class SceneAdapter:
    """Thin adapter around a scene-local bridge script object."""

    def __init__(self, scene: SceneDefinition, client: SimClient):
        self.scene = scene
        self.client = client
        self._bridge_functions: Any | None = None

    def load_scene(self) -> None:
        """Reload the configured scene file."""
        self.client.load_scene(self.scene.scene_path)

    def bind_bridge(self) -> None:
        """Resolve a callable proxy for the scene bridge script."""
        self._bridge_functions = self.client.get_script_functions(self.scene.bridge_script_path)

    def prepare_episode(self, *, skip_scene_load: bool = False) -> None:
        """Reload the scene if needed and prepare the bridge for a new episode."""
        if not skip_scene_load:
            self.load_scene()
        self.bind_bridge()

    def reset_episode(self, seed: int) -> None:
        """Reset the prepared scene using the bridge script."""
        bridge = self._require_bridge()
        reset_function = getattr(
            bridge,
            self.scene.bridge_reset_function,
            None,
        )
        if not callable(reset_function):
            raise SceneAdapterError(
                f"Bridge reset function '{self.scene.bridge_reset_function}' is missing"
            )
        reset_function(seed)

    def read_state(self) -> SceneState:
        """Read the current bridge state from CoppeliaSim."""
        bridge = self._require_bridge()
        read_function = getattr(bridge, self.scene.bridge_read_state_function, None)
        if not callable(read_function):
            raise SceneAdapterError(
                f"Bridge read function '{self.scene.bridge_read_state_function}' is missing"
            )
        raw_state = read_function()
        if not isinstance(raw_state, Mapping):
            raise SceneAdapterError("Bridge read_state must return a mapping")

        position = _parse_vector(raw_state.get("position"), "position")
        velocity = _parse_vector(raw_state.get("velocity"), "velocity")
        goal_raw = raw_state.get("goal_position")
        goal_position = None if goal_raw is None else _parse_vector(goal_raw, "goal_position")
        collision_count = int(raw_state.get("collision_count", 0))
        success = bool(raw_state.get("success", False))
        error_code_raw = raw_state.get("error_code")
        if error_code_raw is not None and not isinstance(error_code_raw, str):
            raise SceneAdapterError("error_code must be a string when present")

        return SceneState(
            position=position,
            velocity=velocity,
            goal_position=goal_position,
            collision_count=collision_count,
            success=success,
            error_code=error_code_raw,
        )

    def apply_control(self, command: Vector3) -> None:
        """Apply a controller command to the bridge script."""
        bridge = self._require_bridge()
        apply_function = getattr(bridge, self.scene.bridge_apply_control_function, None)
        if not callable(apply_function):
            raise SceneAdapterError(
                f"Bridge control function '{self.scene.bridge_apply_control_function}' is missing"
            )
        apply_function(*command)

    def _require_bridge(self) -> Any:
        if self._bridge_functions is None:
            raise SceneAdapterError("Scene bridge is not initialized. Call prepare_episode first.")
        return self._bridge_functions


def _parse_vector(value: object, label: str) -> Vector3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise SceneAdapterError(f"{label} must be a length-3 vector")
    try:
        x, y, z = value
        return (float(x), float(y), float(z))
    except (TypeError, ValueError) as exc:
        raise SceneAdapterError(f"{label} must contain numeric values") from exc
