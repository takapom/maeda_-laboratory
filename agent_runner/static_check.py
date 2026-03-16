"""Static checks: lint, typecheck, unit tests."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    stdout: str
    stderr: str
    returncode: int


def run_make_target(target: str, work_dir: Path) -> CheckResult:
    """Run a make target and return the result."""
    result = subprocess.run(
        ["make", target],
        capture_output=True,
        text=True,
        cwd=str(work_dir),
        timeout=120,
    )
    return CheckResult(
        name=target,
        passed=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )


def run_all(work_dir: Path) -> list[CheckResult]:
    """Run lint, typecheck, and unit tests. Stops on first failure."""
    results: list[CheckResult] = []
    for target in ("lint", "typecheck", "unit"):
        r = run_make_target(target, work_dir)
        results.append(r)
        if not r.passed:
            break
    return results
