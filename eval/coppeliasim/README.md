# EvalBridge スキャフォールド

このディレクトリには、`eval/run.py` が想定している `/EvalBridge` スクリプト
オブジェクト向けの CoppeliaSim 側スキャフォールドが含まれています。

## ファイル

- `EvalBridge.lua`
  - CoppeliaSim のスクリプトオブジェクトに取り付けるための Lua シミュレーションスクリプトのひな形
  - `reset_episode`、`read_state`、`apply_control` を公開します

## 取り付け方

1. CoppeliaSim でシーンを開きます。
2. 新しいスクリプトオブジェクトを追加し、エイリアスを `EvalBridge` に設定します。
3. **simulation script** として設定します。
4. `EvalBridge.lua` の内容をそのスクリプトオブジェクトに貼り付けます。
5. `CONFIG` ブロック内のオブジェクトパスを、自分のシーンに合うよう更新します。

Python 側の evaluator は絶対シーンパス `/EvalBridge` でブリッジを解決するため、
スクリプトオブジェクトのエイリアスは `EvalBridge` のままにしてください。

## 想定されるシーン契約

このスキャフォールドは `eval/scene_adapter.py` に合わせて作られています。

- `reset_episode(seed)`
- `read_state()`
  - 次のキーを持つマップを返します:
    - `position`
    - `velocity`
    - `goal_position`
    - `collision_count`
    - `success`
    - `error_code`
- `apply_control(vx, vy, vz)`

## コマンドモード

`EvalBridge.lua` は 2 つのコマンドモードをサポートしています。

- `scene_specific`
  - 最も安全なデフォルト設定です
  - `applyCommandSceneSpecific(...)` をドローンモデルのアクチュエータ、ターゲットダミー、
    または低レベルコントローラに接続するまでは移動しません
- `kinematic_position`
  - 各ステップで `sim.setObjectPosition` を使い、`control_object_path` を直接移動します
  - ダミーや非動的なプロキシオブジェクトを使ったスモークテストにのみ有用です
  - 実際の動的ドローンモデルには適していません

## 速度倍率と waypoint

スモークテストでは、Lua 側で速度倍率と waypoint 経由の移動を設定できます。

- `speed_scale`
  - Python controller が出した速度指令に掛ける倍率
  - `0.10` なら実移動量は 1/10、`0.5` なら半分になります
- `route_mode`
  - `none`: final Goal のみに向かいます
  - `axis_steps`: まず浮上し、x 方向、y 方向の順に段階的な target を作り、最後に浮上高度の final Goal へ向かいます
  - `zigzag_steps`: まず浮上し、Goal 方向の左右に中間 target を作って曲がりながら進みます
  - `custom_waypoints`: `custom_route_waypoints` に指定した world 座標を順番に通ります
- `route_lift_height_m`
  - start 位置から何 m 上に浮上するか
  - `0.5` なら最初に z 方向へ 0.5m 移動します
- `route_turn_count`
  - `zigzag_steps` で追加する曲がり waypoint の数です
- `route_turn_offset_m`
  - `zigzag_steps` で直線ルートから左右にずらす距離です
- `move_goal_object_to_active_route_target`
  - `true` の場合、CoppeliaSim 上の `/Goal` 表示も現在の target に移動します

例:

```lua
speed_scale = 0.10,
route_mode = 'zigzag_steps',
route_lift_height_m = 0.5,
route_turn_count = 6,
route_turn_offset_m = 0.35,
route_waypoint_tolerance_m = 0.10,
move_goal_object_to_active_route_target = true,
```

## 必須設定

`EvalBridge.lua` の `CONFIG` ブロックを編集してください。

- `drone_root_path`
  - ドローンの衝突コレクションを構築するためのルートオブジェクト
- `state_object_path`
  - 位置と速度を Python 側へ返すオブジェクト
- `control_object_path`
  - `kinematic_position` モードでコマンドを受け取るオブジェクト
- `goal_object_path`
  - 目標位置を表すオブジェクト
- `collision_entity_path`
  - 衝突判定の対象にする任意のコライダブルなシーンオブジェクト
  - 衝突回数カウントを無効にする場合は `nil` のままにします

## Python 側のシーンパス

Python evaluator はシーンパスを `eval/scenes.yaml` から読み込みます。現在の
デフォルト設定では、次の環境変数から絶対パスを取得する前提です。

- `COPPELIASIM_DEFAULT_SCENE_PATH`

この環境変数には、CoppeliaSim を実行しているマシン上に存在するパスを設定してください。
