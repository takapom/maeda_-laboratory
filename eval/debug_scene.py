"""Debug CoppeliaSim scene bridge interactions step-by-step.

Usage:
    python -m eval.debug_scene --source-dir <path> --scene-id <id> [--seed 42]

This command is intentionally verbose. It prints each major Remote API step
with flush=True so the last emitted line identifies the crash point if
CoppeliaSim exits unexpectedly.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import cast

from eval.scene_adapter import SceneAdapter
from eval.scene_catalog import load_scene_definition
from sim_eval.sim_client import SimClient


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument(
        "--skip-load-scene",
        action="store_true",
        help="Assume the target scene is already open in CoppeliaSim and do not call loadScene().",
    )
    parser.add_argument(
        "--command",
        type=float,
        nargs=3,
        metavar=("VX", "VY", "VZ"),
        default=(0.0, 0.0, 0.0),
        help="Command applied after the initial read_state call.",
    )
    return parser.parse_args(argv)


def _print_stage(message: str) -> None:
    print(message, flush=True)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    scene = load_scene_definition(args.source_dir, args.scene_id)
    client = SimClient(
        host=os.environ.get("COPPELIASIM_HOST", "127.0.0.1"),
        port=int(os.environ.get("COPPELIASIM_PORT", "23000")),
        connect_timeout_sec=int(os.environ.get("CONNECT_TIMEOUT_SEC", "30")),
    )
    adapter = SceneAdapter(scene, client)
    simulation_started = False

    _print_stage(f"[1/9] connect {client.host}:{client.port}")
    client.connect()
    _print_stage(f"connected: CoppeliaSim v{client.get_version()}")

    try:
        if args.skip_load_scene:
            _print_stage("[2/9] skip load_scene (using currently open scene)")
        else:
            _print_stage(f"[2/9] load_scene {scene.scene_path}")
            adapter.load_scene()

        _print_stage(f"[3/9] bind_bridge {scene.bridge_script_path}")
        adapter.bind_bridge()

        _print_stage("[4/9] start_simulation")
        client.start_simulation()
        simulation_started = True

        _print_stage(f"[5/9] reset_episode seed={args.seed}")
        adapter.reset_episode(args.seed)

        _print_stage("[6/9] read_state initial")
        state = adapter.read_state()
        print(json.dumps(asdict(state), ensure_ascii=False, indent=2), flush=True)

        command = cast(
            tuple[float, float, float],
            tuple(float(value) for value in args.command),
        )
        _print_stage(f"[7/9] apply_control {command}")
        adapter.apply_control(command)

        for step_index in range(args.steps):
            _print_stage(f"[8/9] step {step_index + 1}/{args.steps}")
            client.step()
            state = adapter.read_state()
            print(json.dumps(asdict(state), ensure_ascii=False, indent=2), flush=True)

        _print_stage("[9/9] completed")
    finally:
        if simulation_started:
            _print_stage("stopping simulation")
            client.stop_simulation()


if __name__ == "__main__":
    main()
