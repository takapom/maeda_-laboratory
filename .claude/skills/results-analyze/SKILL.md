---
name: results-analyze
description: >-
  実行間でドローン評価結果を分析・比較する。メトリクスの推移を表示し、
  特定の実行を並べて比較し、異なるプロファイルで再評価し、
  分析サマリーをエクスポートする。評価履歴の確認や次のステップの判断に使用する。
compatibility: Python 3.11+ が必要。
allowed-tools: Bash(python:*) Read
metadata:
  author: maeda-laboratory
  version: "0.1"
---

## 概要

このスキルは、`$ARTIFACTS_ROOT/runs/` に保存された評価結果を分析するツールを提供します。

メトリクスの定義と解釈については [references/metrics-guide.md](references/metrics-guide.md) を参照してください。

## 利用可能なスクリプト

- **`scripts/compare-runs.py`** — 2つの実行を並べて比較する。
- **`scripts/trend.py`** — 直近の実行のメトリクス推移を表示する。
- **`scripts/re-evaluate.py`** — 異なる評価プロファイルでエピソードを再評価する。
- **`scripts/export-csv.py`** — 実行履歴を外部分析用に CSV でエクスポートする。

## 使用例

### 2つの実行を比較

```bash
python3 scripts/compare-runs.py RUN_ID_A RUN_ID_B
```

### 直近の推移を表示

```bash
python3 scripts/trend.py --limit 10
```

### 異なるプロファイルで再評価

```bash
python3 scripts/re-evaluate.py RUN_ID --success-rate-min 0.8 --collision-max 2.0
```

### CSV にエクスポート

```bash
python3 scripts/export-csv.py --output /tmp/runs.csv
```
