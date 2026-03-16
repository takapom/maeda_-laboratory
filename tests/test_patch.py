"""Tests for patch module."""

from __future__ import annotations

from agent_runner.patch import compute_sha256


def test_sha256():
    h = compute_sha256("hello\n")
    assert len(h) == 64
    assert h == compute_sha256("hello\n")
    assert h != compute_sha256("world\n")
