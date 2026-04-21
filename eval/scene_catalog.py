"""Scene catalog loading for simulator-backed evaluation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

_UNRESOLVED_ENV_PATTERN = re.compile(r"\$(\w+|\{[^}]+\})")


class SceneCatalogError(Exception):
    """Raised when scenes.yaml is missing or invalid."""


@dataclass(frozen=True)
class SceneDefinition:
    scene_id: str
    scene_path: str
    scene_version: str | None = None
    bridge_script_path: str = "/EvalBridge"
    bridge_reset_function: str = "reset_episode"
    bridge_read_state_function: str = "read_state"
    bridge_apply_control_function: str = "apply_control"


def load_scene_definition(source_dir: Path, scene_id: str) -> SceneDefinition:
    """Load a scene definition from source_dir/eval/scenes.yaml."""
    return load_scene_definition_from_path(source_dir / "eval" / "scenes.yaml", scene_id)


def load_scene_definition_from_path(catalog_path: Path, scene_id: str) -> SceneDefinition:
    """Load a scene definition from an explicit catalog path."""
    if not catalog_path.exists():
        raise SceneCatalogError(f"Scene catalog not found: {catalog_path}")

    data = yaml.safe_load(catalog_path.read_text())
    if not isinstance(data, dict):
        raise SceneCatalogError(f"Scene catalog must be a mapping: {catalog_path}")

    raw_scenes = data.get("scenes")
    if not isinstance(raw_scenes, list):
        raise SceneCatalogError(f"Scene catalog must contain a 'scenes' list: {catalog_path}")

    for raw_scene in raw_scenes:
        if not isinstance(raw_scene, dict):
            continue
        if raw_scene.get("scene_id") != scene_id:
            continue
        return _parse_scene_definition(raw_scene)

    raise SceneCatalogError(f"Scene ID '{scene_id}' not found in {catalog_path}")


def _parse_scene_definition(data: dict[str, Any]) -> SceneDefinition:
    scene_path = _expand_scene_path(_require_str(data, "scene_path"))
    if not Path(scene_path).is_absolute():
        raise SceneCatalogError(
            f"scene_path must be absolute after env expansion: {scene_path}"
        )

    return SceneDefinition(
        scene_id=_require_str(data, "scene_id"),
        scene_path=scene_path,
        scene_version=_optional_str(data.get("scene_version")),
        bridge_script_path=_optional_str(data.get("bridge_script_path")) or "/EvalBridge",
        bridge_reset_function=_optional_str(data.get("bridge_reset_function")) or "reset_episode",
        bridge_read_state_function=_optional_str(data.get("bridge_read_state_function"))
        or "read_state",
        bridge_apply_control_function=_optional_str(data.get("bridge_apply_control_function"))
        or "apply_control",
    )


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SceneCatalogError(f"Scene catalog key '{key}' must be a non-empty string")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SceneCatalogError("Optional scene catalog values must be strings")
    stripped = value.strip()
    return stripped or None


def _expand_scene_path(value: str) -> str:
    expanded = os.path.expandvars(value)
    unresolved = _UNRESOLVED_ENV_PATTERN.search(expanded)
    if unresolved:
        raise SceneCatalogError(
            f"scene_path contains unresolved environment variables: {value}"
        )
    return expanded
