"""Patch generation, validation, and application."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


class PatchError(Exception):
    pass


def compute_sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def check_patch(patch_content: str, work_dir: Path) -> bool:
    """Dry-run apply to check if patch is valid."""
    result = subprocess.run(
        ["git", "apply", "--check", "-"],
        input=patch_content,
        capture_output=True,
        text=True,
        cwd=str(work_dir),
    )
    return result.returncode == 0


def apply_patch(patch_content: str, work_dir: Path) -> None:
    """Apply patch to the workspace. Raises PatchError on failure."""
    if not check_patch(patch_content, work_dir):
        result = subprocess.run(
            ["git", "apply", "--check", "-"],
            input=patch_content,
            capture_output=True,
            text=True,
            cwd=str(work_dir),
        )
        raise PatchError(f"Patch check failed: {result.stderr}")

    result = subprocess.run(
        ["git", "apply", "-"],
        input=patch_content,
        capture_output=True,
        text=True,
        cwd=str(work_dir),
    )
    if result.returncode != 0:
        raise PatchError(f"Patch apply failed: {result.stderr}")
