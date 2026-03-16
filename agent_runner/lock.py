"""Active run lock using local filesystem."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

_lock_dir: Path = Path("/artifacts/locks")
_lock_file: Path = _lock_dir / "active_run.lock"


class LockError(Exception):
    pass


def configure(artifacts_root: str) -> None:
    """Set lock paths based on artifacts root."""
    global _lock_dir, _lock_file
    _lock_dir = Path(artifacts_root) / "locks"
    _lock_file = _lock_dir / "active_run.lock"


def acquire(run_id: str) -> None:
    """Acquire the active run lock. Raises LockError if already locked."""
    _lock_dir.mkdir(parents=True, exist_ok=True)

    if _lock_file.exists():
        try:
            info = json.loads(_lock_file.read_text())
            existing_run = info.get("run_id", "unknown")
        except (json.JSONDecodeError, OSError):
            existing_run = "unknown"
        raise LockError(
            f"Active run lock exists (run_id={existing_run}). "
            "Another run is in progress or a stale lock remains. "
            f"Remove {_lock_file} manually if the previous run crashed."
        )

    lock_data = {
        "run_id": run_id,
        "pid": os.getpid(),
        "acquired_at": time.time(),
    }

    # Write atomically via temp file
    tmp = _lock_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(lock_data, indent=2))
    tmp.rename(_lock_file)


def release() -> None:
    """Release the active run lock. No-op if lock does not exist."""
    try:
        _lock_file.unlink(missing_ok=True)
    except OSError:
        pass


def is_locked() -> bool:
    return _lock_file.exists()
