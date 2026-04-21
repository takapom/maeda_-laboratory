# drone-eval-poc

Claude Code / Skill によるドローン制御コード改変と CoppeliaSim 評価の PoC 基盤。

operator が Claude Code 等で `controller/` 配下のコードを改変し、patch.diff として保存。Agent Runner がその patch を受け取り、baseline（変更前）と candidate（変更後）を CoppeliaSim 上で同一条件で評価・比較する。

## 構成

```
agent_runner/       Agent Runner - run オーケストレーション
  cli.py              CLI エントリポイント
  runner.py           end-to-end 実行フロー
  config.py           環境変数からの設定読み込み
  lock.py             active_run.lock 排他制御
  artifacts.py        artifact 保存・cleanup
  workspace.py        fresh clone・workspace 管理
  patch_provider.py   patch 取得の抽象化（手動ファイル / API）
  patch.py            patch 検証・適用
  static_check.py     make lint / typecheck / unit 実行
  models.py           共通データモデル
sim_eval/           sim-eval - baseline/candidate 評価
  cli.py              CLI エントリポイント
  sim_client.py       CoppeliaSim ZeroMQ 接続ラッパー
  evaluator.py        episode 実行・raw observation 収集
  metrics.py          raw observation → metrics 算出
  comparison.py       baseline vs candidate 比較・pass 判定
controller/         LLM が改変する対象コード
eval/               評価ロジック（repo 契約）
  run.py              python -m eval.run の実体
  scenes.yaml         scene_id → scene_path マッピング
tests/              ユニットテスト
```

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 使い方

### 1. patch.diff を用意する

Claude Code 等で `controller/` のコードを改変し、diff を保存する。

```bash
# 例: 手動で diff を作成
git diff controller/ > /tmp/my-patch.diff
```

### 2. run を実行する

```bash
REPO_URL=/path/to/this/repo \
BASE_REF=$(git rev-parse HEAD) \
ARTIFACTS_ROOT=/tmp/drone-poc/artifacts \
WORKSPACE_ROOT=/tmp/drone-poc/workspace \
python -m agent_runner.cli \
  --goal "Reduce collision count" \
  --patch-file /tmp/my-patch.diff
```

### 3. 結果を確認する

```bash
# artifacts 一覧
ls $ARTIFACTS_ROOT/runs/<run_id>/

# 評価結果
cat $ARTIFACTS_ROOT/runs/<run_id>/metrics.json
cat $ARTIFACTS_ROOT/runs/<run_id>/summary.json

# episode 単位の raw observation
cat $ARTIFACTS_ROOT/runs/<run_id>/episodes_baseline.jsonl
cat $ARTIFACTS_ROOT/runs/<run_id>/episodes_candidate.jsonl
```

## 環境変数

| 変数 | 必須 | 説明 |
|---|---|---|
| `REPO_URL` | yes | 対象 repo のパスまたは URL |
| `BASE_REF` | yes | 評価基準の commit SHA |
| `PATCH_FILE` | \*  | 手動生成した patch.diff のパス |
| `OPENAI_API_KEY` | \* | OpenAI API key（API fallback 用） |
| `PATCH_TOOL_NAME` | no | patch 生成に使ったツール名（metadata 用、default: `claude_code`） |
| `PATCH_SKILL_NAME` | no | patch 生成に使った skill 名（metadata 用） |
| `OPERATOR_NAME` | no | operator 名（default: OS ユーザー名） |
| `COPPELIASIM_HOST` | no | CoppeliaSim ホスト（default: `127.0.0.1`） |
| `COPPELIASIM_PORT` | no | CoppeliaSim ポート（default: `23000`） |
| `ARTIFACTS_ROOT` | no | artifacts 保存先（default: `/artifacts`） |
| `WORKSPACE_ROOT` | no | workspace 保存先（default: `/workspace`） |
| `SCENE_ID` | no | 評価 scene（default: `default`） |
| `SEED_LIST` | no | カンマ区切りの seed 一覧（default: `42`） |
| `SIM_TIME_LIMIT_SEC` | no | 1 episode の simulation time 上限（default: `60`） |
| `CONNECT_TIMEOUT_SEC` | no | simulator 接続待ち上限（default: `30`） |

\* `PATCH_FILE` または `OPENAI_API_KEY` のどちらか一方が必要。

## CLI オプション

```
python -m agent_runner.cli \
  --goal <string>           # 必須: 最適化の目標
  --constraints <string>    # 任意: 制約条件
  --repo-url <path|url>     # 任意: REPO_URL の上書き
  --base-ref <sha>          # 任意: BASE_REF の上書き
  --patch-file <path>       # 任意: PATCH_FILE の上書き
```

## CoppeliaSim 接続テスト

```bash
COPPELIASIM_HOST=<host> COPPELIASIM_PORT=<port> make smoke-test
```

## 手動で開いた scene を使う実行

`sim.loadScene(...)` が不安定な環境では、CoppeliaSim で scene を手動で開いたまま
`eval.run` / `eval.debug_scene` を `skip-load` モードで実行できる。

```bash
python -m eval.debug_scene \
  --source-dir /path/to/repo \
  --scene-id default \
  --seed 42 \
  --steps 2 \
  --command 0.2 0 0 \
  --skip-load-scene
```

```bash
python -m eval.run \
  --source-dir /path/to/repo \
  --scene-id default \
  --seed-list 42 \
  --output-dir /tmp/eval-run \
  --skip-load-scene
```

## EvalBridge 雛形

CoppeliaSim 側の `/EvalBridge` script object の Lua 雛形は
[`eval/coppeliasim/EvalBridge.lua`](eval/coppeliasim/EvalBridge.lua) に置いてある。

scene への組み込み手順と契約は
[`eval/coppeliasim/README.md`](eval/coppeliasim/README.md) を参照。

## テスト

```bash
make lint        # ruff
make typecheck   # mypy
make unit        # pytest
```

## artifacts 構成

各 run は `$ARTIFACTS_ROOT/runs/<run_id>/` に以下を保存する。

| ファイル | 内容 |
|---|---|
| `request.json` | goal, constraints, prompt input |
| `patch.diff` | candidate 再構成の正本 |
| `git.json` | repo_url, base_ref, controller_base_sha |
| `params.json` | seed list, episodes, scene_id, timeout 設定 |
| `patch_provider.json` | provider_type, tool_name, operator 等 |
| `runtime.json` | host, python_version, dependency hash |
| `evaluation_profile.json` | profile_name, weights, pass_criteria |
| `metrics.json` | baseline/candidate metrics, delta |
| `summary.json` | 判定要約, 比較サマリ |
| `episodes_baseline.jsonl` | baseline の episode 単位 raw observation |
| `episodes_candidate.jsonl` | candidate の episode 単位 raw observation |
| `stdout.log` | sim-eval の標準出力 |
| `stderr.log` | sim-eval の標準エラー |

失敗 run でも `metrics.json` と `summary.json` は必ず生成される。

## 評価結果の見方

結果ファイルは次の順で読むと分かりやすい。

1. `episodes_baseline.jsonl` / `episodes_candidate.jsonl`
2. `metrics.json`
3. `summary.json`

`episodes_*.jsonl` が episode 単位の元データ、`metrics.json` がその集計結果、`summary.json` が最終判定である。

### `summary.json`

- `status`
  - run 全体が正常終了したかどうかを表す
  - `succeeded` は patch 適用、静的チェック、評価、artifact 出力まで完了したことを意味する
- `passed`
  - evaluation profile 上で不合格ではなかったことを表す
  - 改善したことを直接保証する値ではない
- `comparison.baseline`
  - 変更前コードの集計結果
- `comparison.candidate`
  - 変更後コードの集計結果
- `comparison.delta`
  - `candidate - baseline` の差分
  - `0.0` は差分なし、正負は metric ごとの定義に従う

### `metrics.json`

- `success_rate`
  - 成功した episode 数 / 総 episode 数
  - `1.0` は全 episode 成功、`0.0` は全 episode 失敗を意味する
- `collision_count_mean`
  - 全 episode の衝突回数合計 / 総 episode 数
  - 小さいほど良い
- `time_to_goal_mean_sec`
  - 成功した episode のゴール到達時間の平均値
  - 単位は秒で、小さいほど良い
- `reward_mean`
  - episode ごとの reward の平均値
  - 具体的な意味は evaluator 実装に依存する
- `baseline_meta` / `candidate_meta`
  - 分母定義、成功 episode 数、失敗 episode 数などの集計条件

### `episodes_baseline.jsonl` / `episodes_candidate.jsonl`

各行が 1 episode の raw observation を表す。

- `seed`
  - その episode で使った乱数 seed
  - 再現確認に使う
- `status`
  - episode の終了状態
  - 例: `completed`, `error`
- `success`
  - その episode が成功扱いかどうか
- `collision_count`
  - その episode で発生した衝突回数
- `time_to_goal_sec`
  - ゴール到達までにかかった時間
  - 未到達時は `null` になり得る
- `reward`
  - その episode の報酬値またはスコア
- `timed_out`
  - 時間上限で終了したかどうか
- `error_code`
  - 失敗時の理由コード

### 読み方の補足

- `episodes=1` の場合、`metrics.json` の値はほぼその 1 episode の値そのものになる
- baseline と candidate が同じ値なら、今回の run では変更差分が結果に現れていない
- 現在の PoC では `eval/run.py` が乱数 stub のため、値は実 simulator の挙動ではなく integration 用のダミー結果である

## 設計ドキュメント

詳細な要件定義は [docs/not-k8s-architecture.md](docs/not-k8s-architecture.md) を参照。
