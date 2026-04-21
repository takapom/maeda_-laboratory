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
