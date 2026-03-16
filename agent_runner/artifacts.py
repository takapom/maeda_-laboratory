"""Artifact storage for run results."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

_artifacts_root: Path = Path("/artifacts")
_runs_dir: Path = _artifacts_root / "runs"
MAX_RUNS = 100


def configure(artifacts_root: str) -> None:
    """Set artifact paths based on artifacts root."""
    global _artifacts_root, _runs_dir
    _artifacts_root = Path(artifacts_root)
    _runs_dir = _artifacts_root / "runs"


def run_dir(run_id: str) -> Path:
    """Return the artifact directory for a given run."""
    return _runs_dir / run_id


def ensure_run_dir(run_id: str) -> Path:
    """Create and return the artifact directory for a given run."""
    d = run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_json(run_id: str, filename: str, data: Any) -> Path:
    """Write a JSON artifact file."""
    d = ensure_run_dir(run_id)
    p = d / filename
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n")
    return p


def write_text(run_id: str, filename: str, content: str) -> Path:
    """Write a text artifact file."""
    d = ensure_run_dir(run_id)
    p = d / filename
    p.write_text(content)
    return p


def write_jsonl(run_id: str, filename: str, records: list[dict[str, Any]]) -> Path:
    """Write a JSONL artifact file."""
    d = ensure_run_dir(run_id)
    p = d / filename
    with p.open("w") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return p


def write_fallback_metrics(run_id: str, errors: list[dict[str, Any]]) -> None:
    """Write fallback metrics.json and summary.json when sim-eval fails to produce them."""
    write_json(run_id, "metrics.json", {
        "baseline": None,
        "candidate": None,
        "delta": None,
        "metrics_meta": None,
        "errors": errors,
    })
    write_json(run_id, "summary.json", {
        "status": "failed",
        "comparison": None,
        "evaluation_profile": None,
        "errors": errors,
    })


def cleanup_old_runs() -> None:
    """Remove oldest runs beyond MAX_RUNS."""
    if not _runs_dir.exists():
        return
    runs = sorted(_runs_dir.iterdir(), key=lambda p: p.stat().st_mtime)
    while len(runs) > MAX_RUNS:
        oldest = runs.pop(0)
        shutil.rmtree(oldest, ignore_errors=True)
