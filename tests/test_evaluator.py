"""Tests for sim_eval.evaluator."""

from __future__ import annotations

import json
from pathlib import Path

from sim_eval.evaluator import run_episodes


def test_run_episodes_saves_eval_stdout_and_stderr(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    eval_dir = source_dir / "eval"
    eval_dir.mkdir(parents=True)
    (eval_dir / "__init__.py").write_text("")
    (eval_dir / "run.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import json",
                "import sys",
                "from pathlib import Path",
                "",
                "def main() -> None:",
                "    output_dir = Path(sys.argv[sys.argv.index('--output-dir') + 1])",
                "    output_dir.mkdir(parents=True, exist_ok=True)",
                "    (output_dir / 'episodes.jsonl').write_text(",
                "        json.dumps({",
                "            'episode_index': 0,",
                "            'seed': 7,",
                "            'status': 'completed',",
                "            'success': True,",
                "            'collision_count': 1,",
                "            'time_to_goal_sec': 2.5,",
                "            'reward': 3.0,",
                "            'timed_out': False,",
                "            'error_code': None,",
                "        }) + '\\n'",
                "    )",
                "    print('stdout from eval.run')",
                "    print('stderr from eval.run', file=sys.stderr)",
                "",
                "if __name__ == '__main__':",
                "    main()",
            ]
        )
        + "\n"
    )

    output_dir = tmp_path / "output"
    observations = run_episodes(
        source_dir=source_dir,
        scene_id="default",
        seed_list=[7],
        output_dir=output_dir,
        sim_time_limit_sec=10,
        connect_timeout_sec=5,
        coppeliasim_host="127.0.0.1",
        coppeliasim_port=23000,
    )

    assert len(observations) == 1
    assert observations[0].success is True
    assert observations[0].collision_count == 1
    assert (output_dir / "eval_stdout.log").read_text().strip() == "stdout from eval.run"
    assert (output_dir / "eval_stderr.log").read_text().strip() == "stderr from eval.run"

    written = json.loads((output_dir / "episodes.jsonl").read_text().strip())
    assert written["seed"] == 7
