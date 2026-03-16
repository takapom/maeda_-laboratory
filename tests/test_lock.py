"""Tests for lock module."""

from __future__ import annotations

import json

import pytest

from agent_runner import lock


@pytest.fixture(autouse=True)
def tmp_lock(tmp_path):
    """Redirect lock to a temp directory."""
    lock.configure(str(tmp_path))
    yield tmp_path / "locks" / "active_run.lock"


def test_acquire_release(tmp_lock):
    lock.acquire("run-001")
    assert tmp_lock.exists()
    data = json.loads(tmp_lock.read_text())
    assert data["run_id"] == "run-001"

    lock.release()
    assert not tmp_lock.exists()


def test_acquire_fails_when_locked(tmp_lock):
    lock.acquire("run-001")
    with pytest.raises(lock.LockError, match="Active run lock exists"):
        lock.acquire("run-002")
    lock.release()


def test_release_noop_when_unlocked(tmp_lock):
    lock.release()  # Should not raise


def test_is_locked(tmp_lock):
    assert not lock.is_locked()
    lock.acquire("run-001")
    assert lock.is_locked()
    lock.release()
    assert not lock.is_locked()
