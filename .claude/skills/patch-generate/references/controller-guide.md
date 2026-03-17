# コントローラーアーキテクチャガイド

## ディレクトリ構成

```
controller/
  __init__.py
  drone_controller.py    # メインのコントローラークラス
```

## DroneController クラス

`drone_controller.py` の中核クラス：

```python
class DroneController:
    def __init__(self, goal_position):
        self.goal_position = goal_position
        self.kp = 1.0  # 比例ゲイン

    def compute_control(self, current_position, current_velocity):
        # (vx, vy, vz) の速度指令を返す
        ...
```

### 主要インターフェース

- **入力**: `current_position (x, y, z)` と `current_velocity (vx, vy, vz)`
- **出力**: `(vx, vy, vz)` 速度指令タプル
- **目標**: 衝突と所要時間を最小化しつつ `self.goal_position` へ移動する

### 評価メトリクス

コントローラーは以下で評価される：

1. **success_rate** — ゴールに到達したエピソードの割合
2. **collision_count_mean** — エピソードあたりの平均衝突回数（低いほど良い）
3. **time_to_goal_mean_sec** — 成功エピソードでのゴール到達平均時間（低いほど良い）
4. **reward_mean** — 平均累積報酬（診断用）

## 修正ガイドライン

### 安全な変更

- ゲインパラメータの調整（`kp`、`kd`、`ki`）
- 新しい制御項の追加（微分、積分）
- 障害物検出・回避ロジックの追加
- 軌道平滑化の追加
- 状態推定の改善

### 避けるべきこと

- `compute_control` メソッドのシグネチャ変更
- 評価環境で利用できないモジュールのインポート
- ファイル I/O やネットワーク呼び出しの追加
- `controller/` 外のファイルの修正

## 新しいファイルの追加

`controller/` 配下に新しいファイルを追加できます。パッチに含まれます。
必要に応じて `drone_controller.py` からインポートしてください：

```python
# controller/utils.py
def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

# controller/drone_controller.py
from controller.utils import clamp
```
