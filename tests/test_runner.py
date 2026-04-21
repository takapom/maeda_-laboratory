"""Tests for runner workspace separation."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

from agent_runner.config import Config
from agent_runner.patch_provider import PatchProviderResult
from agent_runner.runner import execute_run
from agent_runner.static_check import CheckResult


def test_execute_run_uses_separate_baseline_and_candidate_dirs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run_workspace = tmp_path / "workspace"
    baseline_dir = run_workspace / "run-123" / "baseline"
    candidate_dir = run_workspace / "run-123" / "candidate"
    baseline_dir.mkdir(parents=True)
    candidate_dir.mkdir(parents=True)
    (baseline_dir / "controller").mkdir()
    (candidate_dir / "controller").mkdir()

    sim_eval_calls: list[list[str]] = []
    applied_dirs: list[Path] = []
    static_check_dirs: list[Path] = []
    clone_slots: list[str] = []

    def fake_fresh_clone(repo_url: str, base_ref: str, run_id: str, slot: str) -> Path:
        clone_slots.append(slot)
        return baseline_dir if slot == "baseline" else candidate_dir

    def fake_apply_patch(patch_content: str, work_dir: Path) -> None:
        applied_dirs.append(work_dir)

    def fake_run_static_checks(work_dir: Path) -> list[CheckResult]:
        static_check_dirs.append(work_dir)
        return [CheckResult(name="lint", passed=True, stdout="", stderr="", returncode=0)]

    def fake_subprocess_run(
        cmd: list[str],
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> CompletedProcess[str]:
        sim_eval_calls.append(cmd)
        run_dir = tmp_path / "artifacts" / "runs" / "run-123"
        (run_dir / "metrics.json").write_text("{}\n")
        (run_dir / "summary.json").write_text("{}\n")
        return CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr("agent_runner.runner.run_id.generate", lambda: "run-123")
    monkeypatch.setattr("agent_runner.runner._git_rev", lambda work_dir: "base-sha")
    monkeypatch.setattr("agent_runner.runner._pip_freeze_hash", lambda: "dep-hash")
    monkeypatch.setattr("agent_runner.runner._read_controller", lambda work_dir: "# controller")
    monkeypatch.setattr("agent_runner.runner.workspace.fresh_clone", fake_fresh_clone)
    monkeypatch.setattr("agent_runner.runner.apply_patch", fake_apply_patch)
    monkeypatch.setattr("agent_runner.runner.run_static_checks", fake_run_static_checks)
    monkeypatch.setattr(
        "agent_runner.runner.resolve_patch",
        lambda config, goal, constraints, controller_code: PatchProviderResult(
            patch_content="diff --git a/controller/a.py b/controller/a.py\n",
            metadata={"provider_type": "manual_patch_file"},
        ),
    )
    monkeypatch.setattr("agent_runner.runner.subprocess.run", fake_subprocess_run)

    config = Config(
        repo_url="dummy-repo",
        base_ref="dummy-base",
        artifacts_root=str(tmp_path / "artifacts"),
        workspace_root=str(run_workspace),
        seed_list=[1, 2],
    )

    run_id = execute_run(config, goal="improve")

    assert run_id == "run-123"
    assert clone_slots == ["baseline", "candidate"]
    assert applied_dirs == [candidate_dir]
    assert static_check_dirs == [candidate_dir]
    assert sim_eval_calls
    cmd = sim_eval_calls[0]
    assert "--baseline-dir" in cmd
    assert "--candidate-dir" in cmd
    assert "--evaluation-profile" in cmd
    assert cmd[cmd.index("--baseline-dir") + 1] == str(baseline_dir)
    assert cmd[cmd.index("--candidate-dir") + 1] == str(candidate_dir)
    assert cmd[cmd.index("--evaluation-profile") + 1].endswith("evaluation_profile.json")

    git_json = json.loads((tmp_path / "artifacts" / "runs" / "run-123" / "git.json").read_text())
    assert git_json["controller_base_sha"] == "base-sha"
