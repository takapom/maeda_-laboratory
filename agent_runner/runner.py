"""Core runner: orchestrates a single evaluation run end-to-end."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from agent_runner import artifacts, lock, run_id, workspace
from agent_runner.config import Config
from agent_runner.models import EvaluationProfile, RunError, RunStage, RunStatus
from agent_runner.patch import PatchError, apply_patch, compute_sha256
from agent_runner.patch_provider import PatchProviderError, resolve_patch
from agent_runner.static_check import run_all as run_static_checks


def execute_run(
    config: Config,
    goal: str,
    constraints: str = "",
    evaluation_profile: EvaluationProfile | None = None,
) -> str:
    """Execute a full evaluation run. Returns run_id."""
    rid = run_id.generate()
    profile = evaluation_profile or EvaluationProfile()
    errors: list[dict[str, Any]] = []
    stage = RunStage.PATCH_GENERATE
    status = RunStatus.FAILED
    work_dir: Path | None = None

    try:
        # --- Configure paths from config ---
        artifacts.configure(config.artifacts_root)
        lock.configure(config.artifacts_root)
        workspace.configure(config.workspace_root)

        # --- Lock ---
        lock.acquire(rid)

        # --- Create artifact dir ---
        artifacts.ensure_run_dir(rid)

        # --- Fresh clone ---
        print(f"[{rid}] Cloning {config.repo_url} @ {config.base_ref} ...")
        work_dir = workspace.fresh_clone(config.repo_url, config.base_ref, rid)
        controller_base_sha = _git_rev(work_dir)

        # --- Save request.json ---
        artifacts.write_json(rid, "request.json", {
            "goal": goal,
            "constraints": constraints,
            "prompt_input": f"goal={goal}",
        })

        # --- Save git.json ---
        artifacts.write_json(rid, "git.json", {
            "repo_url": config.repo_url,
            "base_ref": config.base_ref,
            "controller_base_sha": controller_base_sha,
        })

        # --- Save params.json ---
        artifacts.write_json(rid, "params.json", {
            "seed_list": config.seed_list,
            "episodes": config.episodes,
            "scene_id": config.scene_id,
            "connect_timeout_sec": config.connect_timeout_sec,
            "sim_time_limit_sec": config.sim_time_limit_sec,
            "run_timeout_sec": config.run_timeout_sec,
            "evaluation_profile": profile.profile_name,
        })

        # --- Save runtime.json ---
        artifacts.write_json(rid, "runtime.json", {
            "host": platform.node(),
            "python_version": platform.python_version(),
            "dependency_hash": _pip_freeze_hash(),
            "coppeliasim_endpoint": f"{config.coppeliasim_host}:{config.coppeliasim_port}",
        })

        # --- Save evaluation_profile.json ---
        artifacts.write_json(rid, "evaluation_profile.json", profile.to_dict())

        # --- Patch generation ---
        stage = RunStage.PATCH_GENERATE
        print(f"[{rid}] Resolving patch ...")
        controller_code = _read_controller(work_dir)
        patch_result = resolve_patch(config, goal, constraints, controller_code)
        patch_content = patch_result.patch_content
        patch_sha = compute_sha256(patch_content)

        artifacts.write_json(rid, "patch_provider.json", patch_result.metadata)

        # --- Save patch.diff ---
        artifacts.write_text(rid, "patch.diff", patch_content)

        # --- Apply patch ---
        stage = RunStage.PATCH_APPLY
        print(f"[{rid}] Applying patch (sha256={patch_sha[:12]}...) ...")
        try:
            apply_patch(patch_content, work_dir)
        except PatchError as e:
            errors.append(RunError("patch_apply_failed", str(e)).to_dict())
            raise

        # --- Static checks ---
        stage = RunStage.STATIC_CHECK
        print(f"[{rid}] Running static checks ...")
        check_results = run_static_checks(work_dir)
        for cr in check_results:
            if not cr.passed:
                errors.append(RunError(
                    "static_check_failed",
                    f"{cr.name} failed (rc={cr.returncode}): {cr.stderr[:500]}",
                ).to_dict())
                raise RuntimeError(f"Static check '{cr.name}' failed")

        # --- sim-eval ---
        stage = RunStage.EVAL_START
        print(f"[{rid}] Starting sim-eval ...")
        eval_output = Path(config.artifacts_root) / "runs" / rid
        seed_csv = ",".join(str(s) for s in config.seed_list)

        sim_eval_cmd = [
            sys.executable, "-m", "sim_eval.cli",
            "--baseline-dir", str(work_dir),
            "--candidate-dir", str(work_dir),
            "--scene-id", config.scene_id,
            "--seed-list", seed_csv,
            "--output-dir", str(eval_output),
            "--sim-time-limit-sec", str(config.sim_time_limit_sec),
            "--connect-timeout-sec", str(config.connect_timeout_sec),
            "--coppeliasim-host", config.coppeliasim_host,
            "--coppeliasim-port", str(config.coppeliasim_port),
        ]

        stage = RunStage.EVAL_RUN
        result = subprocess.run(
            sim_eval_cmd,
            capture_output=True,
            text=True,
            timeout=config.run_timeout_sec,
        )

        # Save stdout/stderr
        artifacts.write_text(rid, "stdout.log", result.stdout)
        artifacts.write_text(rid, "stderr.log", result.stderr)

        if result.returncode != 0:
            errors.append(RunError(
                "eval_failed",
                f"sim-eval exited with rc={result.returncode}",
                retryable=True,
            ).to_dict())
        else:
            status = RunStatus.SUCCEEDED

    except subprocess.TimeoutExpired:
        status = RunStatus.TIMED_OUT
        errors.append(RunError("eval_timeout", "Run timed out").to_dict())
    except PatchProviderError as e:
        errors.append(RunError("patch_generate_failed", str(e)).to_dict())
    except lock.LockError:
        raise
    except Exception as e:
        errors.append(RunError(
            f"{stage.value}_failed",
            str(e),
        ).to_dict())
    finally:
        # --- Fallback artifacts ---
        stage = RunStage.ARTIFACT_COLLECT
        run_dir = artifacts.run_dir(rid)
        if not (run_dir / "metrics.json").exists():
            artifacts.write_fallback_metrics(rid, errors)
        if not (run_dir / "stdout.log").exists():
            artifacts.write_text(rid, "stdout.log", "")
        if not (run_dir / "stderr.log").exists():
            artifacts.write_text(rid, "stderr.log", "")

        # --- Cleanup ---
        if work_dir:
            workspace.cleanup(rid)
        artifacts.cleanup_old_runs()
        lock.release()

    print(f"[{rid}] Run complete. Status: {status.value}")
    return rid


def _git_rev(work_dir: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=str(work_dir),
    )
    return result.stdout.strip()


def _read_controller(work_dir: Path) -> str:
    """Read all Python files under controller/."""
    controller_dir = work_dir / "controller"
    if not controller_dir.exists():
        return "# No controller code found"

    parts: list[str] = []
    for py_file in sorted(controller_dir.rglob("*.py")):
        rel = py_file.relative_to(work_dir)
        parts.append(f"# --- {rel} ---\n{py_file.read_text()}")
    return "\n\n".join(parts) if parts else "# No controller code found"


def _pip_freeze_hash() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True, text=True,
    )
    return hashlib.sha256(result.stdout.encode()).hexdigest()
