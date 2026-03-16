"""Workspace management: fresh clone and cleanup."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_workspace_root: Path = Path("/workspace")


def configure(workspace_root: str) -> None:
    """Set workspace root path."""
    global _workspace_root
    _workspace_root = Path(workspace_root)


def fresh_clone(repo_url: str, base_ref: str, run_id: str) -> Path:
    """Clone repo at base_ref into <workspace_root>/<run_id>/."""
    work_dir = _workspace_root / run_id
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "clone", "--quiet", repo_url, str(work_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", base_ref],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(work_dir),
    )
    return work_dir


def cleanup(run_id: str) -> None:
    """Remove workspace for a run."""
    work_dir = _workspace_root / run_id
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
