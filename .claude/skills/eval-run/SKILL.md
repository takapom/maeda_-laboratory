---
name: eval-run
description: >-
  ドローンコントローラーの評価を実行する。controller/ の変更から patch.diff を生成し、
  Agent Runner を使って CoppeliaSim 上でベースラインと候補を評価する。
  コントローラーコードの変更を評価したい場合やシミュレーション比較を実行したい場合に使用する。
compatibility: Python 3.11+、git、プロジェクトの仮想環境（.venv）が有効化されていること。
allowed-tools: Bash(git:*) Bash(python:*) Read Write
metadata:
  author: maeda-laboratory
  version: "0.1"
---

## 概要

このスキルは、コントローラーコードの変更をベースラインに対してエンドツーエンドで評価します。

ワークフロー：

1. 現在の `controller/` の変更から `patch.diff` を生成
2. パッチを使って Agent Runner を実行
3. 評価結果を報告（メトリクス、比較、合否判定）

詳細な手順は [references/workflow.md](references/workflow.md) を参照してください。

## クイックスタート

パッチを生成して評価を実行：

```bash
bash scripts/run-eval.sh --goal "最適化の目標を記述"
```

## 利用可能なスクリプト

- **`scripts/run-eval.sh`** — メインのエントリーポイント。ワーキングツリーからパッチを生成し、評価を実行し、サマリーを表示する。
- **`scripts/gen-patch.sh`** — コミットされていない `controller/` の変更から `patch.diff` を生成する。
- **`scripts/show-results.sh`** — 完了した実行のメトリクスとサマリーを表示する。

## 一般的な使い方

### 1. コントローラーコードを修正

`controller/` 配下のファイルを編集してドローンの動作を改善する（例：ゲインの調整、ロジックの変更）。

### 2. 評価を実行

```bash
bash scripts/run-eval.sh --goal "成功率を維持しつつ衝突回数を減らす"
```

スクリプトは以下を行います：
- プロジェクトルートと仮想環境を検出
- コミットされていない `controller/` の変更からパッチを生成
- パッチを使って Agent Runner を実行
- 評価サマリーを表示

### 3. 結果を確認

```bash
bash scripts/show-results.sh <run_id>
```

またはアーティファクトを直接確認：

```bash
cat $ARTIFACTS_ROOT/runs/<run_id>/summary.json | python3 -m json.tool
cat $ARTIFACTS_ROOT/runs/<run_id>/metrics.json | python3 -m json.tool
```

## 環境変数

スクリプトは以下の環境変数を参照します（デフォルト値あり）：

| 変数 | デフォルト値 | 説明 |
|---|---|---|
| `ARTIFACTS_ROOT` | `/tmp/drone-poc/artifacts` | 実行アーティファクトの保存先 |
| `WORKSPACE_ROOT` | `/tmp/drone-poc/workspace` | クリーンクローンの作成先 |
| `COPPELIASIM_HOST` | `127.0.0.1` | CoppeliaSim ホスト |
| `COPPELIASIM_PORT` | `23000` | CoppeliaSim ポート |

## エラーハンドリング

- `controller/` の変更がない場合、パッチ生成ステップが明確なメッセージで失敗する。
- Agent Runner が非ゼロで終了した場合、スクリプトは stderr と `stdout.log` のパスを表示する。
- 古いロックファイルが検出された場合、削除方法が案内される。
