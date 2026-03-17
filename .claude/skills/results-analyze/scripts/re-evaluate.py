# /// script
# dependencies = []
# ///
"""異なる評価基準で実行のエピソードを再評価する。

シミュレーションは再実行しない。既存のエピソード JSONL を読み込み、
新しい閾値でメトリクス/合否判定を再計算する。

使い方:
    python3 scripts/re-evaluate.py RUN_ID [オプション]

オプション:
    --success-rate-min FLOAT    最小成功率（デフォルト: 0.0）
    --collision-max FLOAT       最大平均衝突回数（デフォルト: なし）
    --time-max FLOAT            最大ゴール到達平均時間（デフォルト: なし）
    --json                      JSON で出力
    --help                      このヘルプを表示

終了コード:
    0  再評価に合格
    1  再評価に不合格またはエラー
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    args = sys.argv[1:]
    if "--help" in args or len(args) < 1:
        print(__doc__.strip())
        sys.exit(0 if "--help" in args else 1)

    run_id = args[0]
    sr_min: float | None = None
    cc_max: float | None = None
    ttg_max: float | None = None
    json_mode = False

    i = 1
    while i < len(args):
        if args[i] == "--success-rate-min":
            sr_min = float(args[i + 1])
            i += 2
        elif args[i] == "--collision-max":
            cc_max = float(args[i + 1])
            i += 2
        elif args[i] == "--time-max":
            ttg_max = float(args[i + 1])
            i += 2
        elif args[i] == "--json":
            json_mode = True
            i += 1
        else:
            print(f"エラー: 不明な引数: {args[i]}", file=sys.stderr)
            sys.exit(1)

    artifacts_root = Path(os.environ.get("ARTIFACTS_ROOT", "/tmp/drone-poc/artifacts"))
    run_dir = artifacts_root / "runs" / run_id

    if not run_dir.exists():
        print(f"エラー: 実行が見つかりません: {run_id}", file=sys.stderr)
        sys.exit(1)

    # エピソード JSONL からメトリクスを再計算
    baseline_metrics = _compute_from_jsonl(run_dir / "episodes_baseline.jsonl")
    candidate_metrics = _compute_from_jsonl(run_dir / "episodes_candidate.jsonl")

    # 新しい基準を適用
    reasons: list[str] = []
    if sr_min is not None and candidate_metrics["success_rate"] is not None:
        if candidate_metrics["success_rate"] < sr_min:
            reasons.append(
                f"success_rate {candidate_metrics['success_rate']:.4f} < {sr_min}"
            )
    if cc_max is not None and candidate_metrics["collision_count_mean"] is not None:
        if candidate_metrics["collision_count_mean"] > cc_max:
            reasons.append(
                f"collision_count_mean {candidate_metrics['collision_count_mean']:.4f} > {cc_max}"
            )
    if ttg_max is not None and candidate_metrics["time_to_goal_mean_sec"] is not None:
        if candidate_metrics["time_to_goal_mean_sec"] > ttg_max:
            reasons.append(
                f"time_to_goal_mean_sec {candidate_metrics['time_to_goal_mean_sec']:.4f} > {ttg_max}"
            )

    passed = len(reasons) == 0
    result = {
        "run_id": run_id,
        "passed": passed,
        "reason": "; ".join(reasons) if reasons else "全基準に合格",
        "criteria": {
            "success_rate_min": sr_min,
            "collision_count_mean_max": cc_max,
            "time_to_goal_mean_sec_max": ttg_max,
        },
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
    }

    if json_mode:
        print(json.dumps(result, indent=2))
    else:
        print(f"実行:    {run_id}")
        print(f"合否:    {passed}")
        print(f"理由:    {result['reason']}")
        print()
        print("候補メトリクス:")
        for k, v in candidate_metrics.items():
            print(f"  {k}: {v}")

    sys.exit(0 if passed else 1)


def _compute_from_jsonl(path: Path) -> dict:
    if not path.exists():
        return {
            "success_rate": None,
            "collision_count_mean": None,
            "time_to_goal_mean_sec": None,
            "reward_mean": None,
        }

    episodes = []
    for line in path.read_text().strip().splitlines():
        episodes.append(json.loads(line))

    total = len(episodes)
    if total == 0:
        return {
            "success_rate": None,
            "collision_count_mean": None,
            "time_to_goal_mean_sec": None,
            "reward_mean": None,
        }

    successes = [e for e in episodes if e.get("success")]
    success_count = len(successes)

    success_rate = success_count / total
    collision_mean = sum(e.get("collision_count", 0) for e in episodes) / total

    if success_count > 0:
        ttg_mean = sum(
            e.get("time_to_goal_sec", 0) for e in successes
            if e.get("time_to_goal_sec") is not None
        ) / success_count
    else:
        ttg_mean = None

    reward_mean = sum(e.get("reward", 0) for e in episodes) / total

    return {
        "success_rate": success_rate,
        "collision_count_mean": collision_mean,
        "time_to_goal_mean_sec": ttg_mean,
        "reward_mean": reward_mean,
    }


if __name__ == "__main__":
    main()
