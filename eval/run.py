"""Evaluation runner contract.

Usage:
    python -m eval.run --source-dir <path> --scene-id <id>
        --seed-list <csv> --output-dir <dir>

Outputs episodes.jsonl to output-dir.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--seed-list", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    seeds = [int(s.strip()) for s in args.seed_list.split(",")]
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    episodes: list[dict[str, object]] = []

    for i, seed in enumerate(seeds):
        random.seed(seed)
        # TODO: Replace with actual CoppeliaSim evaluation
        # For now, generate stub observations for integration testing
        episode = {
            "episode_index": i,
            "seed": seed,
            "status": "completed",
            "success": True,
            "collision_count": 0,
            "time_to_goal_sec": 5.0 + random.random() * 10,
            "reward": 100.0 - random.random() * 20,
            "timed_out": False,
            "error_code": None,
        }
        episodes.append(episode)
        print(f"Episode {i} (seed={seed}): success={episode['success']}")

    # Write episodes.jsonl
    jsonl_path = output_dir / "episodes.jsonl"
    with jsonl_path.open("w") as f:
        for ep in episodes:
            f.write(json.dumps(ep) + "\n")

    print(f"Wrote {len(episodes)} episodes to {jsonl_path}")


if __name__ == "__main__":
    main()
