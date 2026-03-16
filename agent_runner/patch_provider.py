"""Patch provider resolution for manual and API-backed workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_runner.config import Config
from agent_runner.llm import generate_patch


class PatchProviderError(Exception):
    pass


@dataclass
class PatchProviderResult:
    patch_content: str
    metadata: dict[str, Any]


def resolve_patch(
    config: Config,
    goal: str,
    constraints: str,
    controller_code: str,
) -> PatchProviderResult:
    """Resolve a patch from either a manual patch file or the optional OpenAI API."""
    if config.patch_file:
        patch_path = Path(config.patch_file)
        if not patch_path.exists():
            raise PatchProviderError(f"Patch file not found: {patch_path}")
        return PatchProviderResult(
            patch_content=patch_path.read_text(),
            metadata={
                "provider_type": "manual_patch_file",
                "patch_generation_mode": "manual",
                "tool_name": config.patch_tool_name,
                "skill_name": config.patch_skill_name,
                "operator": config.operator_name,
                "prompt_template_version": config.prompt_template_version,
            },
        )

    if config.openai_api_key:
        return PatchProviderResult(
            patch_content=generate_patch(config, goal, constraints, controller_code),
            metadata={
                "provider_type": config.llm_provider,
                "patch_generation_mode": "api",
                "tool_name": config.llm_model,
                "skill_name": "",
                "operator": config.operator_name,
                "prompt_template_version": config.prompt_template_version,
            },
        )

    raise PatchProviderError(
        "Either PATCH_FILE/--patch-file or OPENAI_API_KEY must be provided.",
    )
