# CoppeliaSim 実行手順

この手順は、CoppeliaSim で既に開いている scene を使い、`controller/drone_controller.py` を実行して step log を取得するためのものです。

現状では Python から `loadScene()` を呼ぶと CoppeliaSim が落ちる場合があるため、scene は手動で開き、`--skip-load-scene` 付きで実行します。

## できること

- CoppeliaSim の simulation をコマンドから開始・step 実行・停止する
- `controller/drone_controller.py` の `compute_control()` を使って Drone を動かす
- Drone が Goal に向かう各 step の log を JSONL で保存する
- episode 全体の成功可否、到達時間、衝突回数、reward を保存する

## 前提

- CoppeliaSim が起動している
- CoppeliaSim の ZeroMQ Remote API server が待ち受けている
- scene 内に次の object がある
  - `/Drone`
  - `/Goal`
  - `/EvalBridge`
- `/EvalBridge` には `eval/coppeliasim/EvalBridge.lua` が貼り付けられている
- smoke test 用には `EvalBridge.lua` の `CONFIG.command_mode` が `kinematic_position` になっている

## 1. CoppeliaSim 側の準備

1. CoppeliaSim を起動する。
2. 対象 scene を開く。
3. scene hierarchy に `/Drone`, `/Goal`, `/EvalBridge` があることを確認する。
4. `/EvalBridge` の script editor を開き、`CONFIG` が以下のようになっていることを確認する。

```lua
local CONFIG = {
    drone_root_path = '/Drone',
    state_object_path = '/Drone',
    control_object_path = '/Drone',
    goal_object_path = '/Goal',
    collision_entity_path = nil,
    command_mode = 'kinematic_position',
    reset_dynamic_root = false,
    speed_scale = 0.10,
    route_mode = 'zigzag_steps',
    route_lift_height_m = 0.5,
    route_turn_count = 6,
    route_turn_offset_m = 0.35,
    route_waypoint_tolerance_m = 0.10,
    move_goal_object_to_active_route_target = true,
    goal_tolerance_m = 0.15,
    max_linear_speed_mps = 2.0,
    start_position_jitter_m = {0.0, 0.0, 0.0},
    goal_position_jitter_m = {0.0, 0.0, 0.0},
}
```

この設定では、Python controller が出した速度指令を Lua 側で `0.10` 倍して反映します。

また `route_mode = 'zigzag_steps'` により、Drone は最終 Goal に直行せず、以下のように段階的な target を通ります。

```text
start
  -> 現在位置から z 方向へ 0.5m 浮上する waypoint
  -> 直線ルートから左右にずらした turn_01 waypoint
  -> 反対側にずらした turn_02 waypoint
  -> ...
  -> turn_06 waypoint
  -> 浮上高度を保った final Goal
```

`move_goal_object_to_active_route_target = true` の場合、CoppeliaSim 上の `/Goal` 表示も現在向かう waypoint に移動します。

5. scene を保存する。

保存先の例:

```bash
/Users/takagiyuuki/maeda_-laboratory/scenes/default_drone.ttt
```

## 2. Python 環境を有効化する

```bash
cd /Users/takagiyuuki/maeda_-laboratory
source .venv/bin/activate
```

## 3. 環境変数を設定する

`COPPELIASIM_DEFAULT_SCENE_PATH` は必ず 1 行で設定してください。途中で改行すると、`scene_path` が壊れます。

```bash
export COPPELIASIM_HOST=127.0.0.1
export COPPELIASIM_PORT=23000
export CONNECT_TIMEOUT_SEC=30
export SIM_TIME_LIMIT_SEC=180
export COPPELIASIM_DEFAULT_SCENE_PATH=/Users/takagiyuuki/maeda_-laboratory/scenes/default_drone.ttt
```

設定確認:

```bash
echo "$COPPELIASIM_DEFAULT_SCENE_PATH"
```

期待される出力:

```bash
/Users/takagiyuuki/maeda_-laboratory/scenes/default_drone.ttt
```

## 4. 接続確認

```bash
make smoke-test
```

成功例:

```text
Connecting to CoppeliaSim at 127.0.0.1:23000 (timeout=30s) ...
OK: Connected to CoppeliaSim v4.10.0
```

## 5. debug_scene で切り分け確認する

まず `eval.run` の前に `debug_scene` を実行すると、どの段階まで進んでいるか確認できます。

```bash
python -m eval.debug_scene \
  --source-dir /Users/takagiyuuki/maeda_-laboratory \
  --scene-id default \
  --seed 42 \
  --steps 2 \
  --command 0.2 0 0 \
  --skip-load-scene
```

成功例:

```text
[1/9] connect 127.0.0.1:23000
connected: CoppeliaSim v4.10.0
[2/9] skip load_scene (using currently open scene)
[3/9] bind_bridge /EvalBridge
[4/9] start_simulation
[5/9] reset_episode seed=42
[6/9] read_state initial
[7/9] apply_control (0.2, 0.0, 0.0)
[8/9] step 1/2
[8/9] step 2/2
[9/9] completed
stopping simulation
```

ここまで通れば、CoppeliaSim との接続、`/EvalBridge`、simulation start、step 実行は動いています。

## 6. eval.run で log を取得する

```bash
python -m eval.run \
  --source-dir /Users/takagiyuuki/maeda_-laboratory \
  --scene-id default \
  --seed-list 42 \
  --output-dir /tmp/eval-run \
  --skip-load-scene
```

1 行で実行したい場合:

```bash
python -m eval.run --source-dir /Users/takagiyuuki/maeda_-laboratory --scene-id default --seed-list 42 --output-dir /tmp/eval-run --skip-load-scene
```

成功例:

```text
Episode 0 (seed=42): success=True timed_out=False error=None
Wrote 1 episodes to /tmp/eval-run/episodes.jsonl
```

## 7. log を確認する

出力先:

```text
/tmp/eval-run/
  episodes.jsonl
  scene_info.json
  steps/
    episode_0000.jsonl
```

episode 全体の結果:

```bash
cat /tmp/eval-run/episodes.jsonl
```

step 単位の log:

```bash
sed -n '1,10p' /tmp/eval-run/steps/episode_0000.jsonl
```

scene metadata:

```bash
cat /tmp/eval-run/scene_info.json
```

## 8. log の見方

`episodes.jsonl` は episode 全体の要約です。

主な項目:

- `success`: Goal に到達したか
- `collision_count`: 衝突回数
- `time_to_goal_sec`: Goal 到達までの simulation time
- `reward`: 評価用の累積 reward
- `timed_out`: 時間切れで終了したか
- `error_code`: エラー種別

`steps/episode_0000.jsonl` は step ごとの詳細 log です。

主な項目:

- `step_index`: step 番号
- `sim_time`: simulation time
- `position`: Drone の位置
- `velocity`: Drone の速度
- `goal_position`: Goal の位置
- `goal_distance`: Goal までの距離
- `command`: controller が出した制御入力
- `collision_count`: その時点の衝突回数
- `success`: その step 時点で成功しているか

例:

```json
{
  "step_index": 0,
  "sim_time": 0.05,
  "position": [-1.0325, 0.63125, 0.0],
  "velocity": [0.0, 0.0, 0.0],
  "goal_position": [0.25, 0.275, 0.0],
  "goal_distance": 1.331,
  "command": [1.35, -0.375, 0.0],
  "collision_count": 0,
  "success": false
}
```

## 9. よくあるエラー

### `scene_path` が `/Users/.../maeda_-laboratory/` になる

原因:

- `export COPPELIASIM_DEFAULT_SCENE_PATH=...` の途中で改行している

対処:

```bash
export COPPELIASIM_DEFAULT_SCENE_PATH=/Users/takagiyuuki/maeda_-laboratory/scenes/default_drone.ttt
echo "$COPPELIASIM_DEFAULT_SCENE_PATH"
```

### `eval.run` で CoppeliaSim が落ちる

原因:

- Python から `loadScene()` を呼ぶと落ちる環境がある

対処:

- CoppeliaSim で scene を手動で開く
- `--skip-load-scene` を付けて実行する

### Drone が動かない

原因:

- `EvalBridge.lua` の `command_mode` が `scene_specific` のまま
- `scene_specific` は actuator 接続を書くまで no-op

対処:

```lua
command_mode = 'kinematic_position'
```

### Drone を遅くしたい

`EvalBridge.lua` の `CONFIG.speed_scale` を変更します。

```lua
speed_scale = 0.10
```

`0.10` なら移動量は 1/10、`0.5` なら半分、`1.0` なら元の速度です。

### Goal に直行せず waypoint を踏ませたい

`EvalBridge.lua` の `CONFIG.route_mode` を使います。

```lua
route_mode = 'zigzag_steps'
route_lift_height_m = 0.5
route_turn_count = 6
route_turn_offset_m = 0.35
```

`zigzag_steps` は、start から final Goal へ直行せず、まず z 方向へ浮上し、その後 Goal 方向の左右に中間 target を作ります。

`route_turn_count` を増やすと曲がる回数が増え、`route_turn_offset_m` を大きくすると横移動が大きくなります。

既存の x/y 分割ルートに戻す場合は次のようにします。

```lua
route_mode = 'axis_steps'
```

`axis_steps` は、まず z 方向へ浮上し、その後 x 方向、y 方向の順に段階的な target を作ります。

独自 waypoint を使う場合は次のようにします。

```lua
route_mode = 'custom_waypoints'
custom_route_waypoints = {
    {-0.5, 0.6, 0.0},
    {0.0, 0.6, 0.0},
}
```

この場合も final Goal は最後に自動で追加されます。

### `/EvalBridge` が見つからない

原因:

- script object の alias が `EvalBridge` になっていない
- scene を保存していない

対処:

- scene hierarchy で script object の名前を `EvalBridge` にする
- scene を保存する

## 10. 現在の制約

できること:

- CoppeliaSim の simulation 開始、step 実行、停止をコマンドから行う
- Drone が Goal に向かう各 step の log を取得する
- episode 単位の成功結果を保存する

まだできないこと:

- Python から scene を安全に自動 load する
- CoppeliaSim アプリ自体を完全自動起動する
- 実 drone model の actuator に command を流す
- baseline / candidate 比較を実 simulator flow に完全接続する
- 衝突判定を本格運用する
