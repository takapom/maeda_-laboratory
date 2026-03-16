"""Tests for patch provider resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_runner.config import Config
from agent_runner.patch_provider import PatchProviderError, resolve_patch


def test_resolve_patch_from_manual_file(tmp_path: Path) -> None:
    patch_file = tmp_path / "candidate.diff"
    patch_file.write_text("diff --git a/controller/a.py b/controller/a.py\n")

    config = Config(
        patch_file=str(patch_file),
        patch_tool_name="claude_code",
        patch_skill_name="patch-generate",
        operator_name="tester",
    )

    result = resolve_patch(config, "goal", "constraints", "controller code")

    assert result.patch_content == "diff --git a/controller/a.py b/controller/a.py\n"
    assert result.metadata == {
        "provider_type": "manual_patch_file",
        "patch_generation_mode": "manual",
        "tool_name": "claude_code",
        "skill_name": "patch-generate",
        "operator": "tester",
        "prompt_template_version": "v1",
    }


def test_resolve_patch_raises_without_provider() -> None:
    config = Config(openai_api_key="", patch_file="")

    with pytest.raises(PatchProviderError, match="PATCH_FILE/--patch-file"):
        resolve_patch(config, "goal", "constraints", "controller code")
