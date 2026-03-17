---
name: patch-generate
description: >-
  ドローン評価用のコントローラーパッチを生成する。現在の controller/ コードを読み取り、
  最適化目標を分析し、controller/ ファイルを修正して patch.diff を出力する。
  ドローンコントローラーの動作を改善したい場合や評価用の候補を作成したい場合に使用する。
compatibility: Python 3.11+、git が必要。
allowed-tools: Bash(git:*) Read Write Edit
metadata:
  author: maeda-laboratory
  version: "0.1"
---

## 概要

このスキルは、最適化目標を達成するために `controller/` コードを修正し、
`eval-run` で評価可能な `patch.diff` を生成するプロセスをガイドします。

コントローラーアーキテクチャと修正パターンの詳細は [references/controller-guide.md](references/controller-guide.md) を参照してください。

## ワークフロー

### 1. 現在のコントローラーを理解する

コントローラーコードを読んで現在の実装を把握する：

```bash
bash scripts/read-controller.sh
```

### 2. 過去の評価結果を確認（任意）

以前の実行がある場合、過去に試した内容を確認する：

```bash
bash scripts/list-past-goals.sh
```

### 3. コントローラーコードを修正

最適化目標に基づいて `controller/` 配下のファイルを編集する。

**ルール：**
- `controller/` 配下のファイルのみを修正すること
- `eval/` は修正しないこと（PoC では固定）
- 記載された目標に集中した変更にすること
- コードが有効な Python であることを確認すること

### 4. 変更を検証

```bash
bash scripts/validate-patch.sh
```

以下のチェックが実行される：
- 修正ファイルのシンタックスチェック
- 差分のプレビュー生成
- 変更が `controller/` 内のみであることの確認

### 5. patch.diff を生成

```bash
bash scripts/gen-patch.sh --output /tmp/drone-poc/patch.diff
```

### 6. 評価に引き渡す

生成されたパッチは `eval-run` で使用できる：

```bash
bash .claude/skills/eval-run/scripts/run-eval.sh \
  --goal "最適化の目標" \
  --patch-file /tmp/drone-poc/patch.diff
```

## 利用可能なスクリプト

- **`scripts/read-controller.sh`** — controller/ の全ソースファイルをコンテキスト付きで表示。
- **`scripts/list-past-goals.sh`** — 過去の評価実行の目標を一覧表示。
- **`scripts/validate-patch.sh`** — パッチ生成前に controller/ の変更を検証。
- **`scripts/gen-patch.sh`** — controller/ の変更から patch.diff を生成。

## よくある修正パターン

| 目標 | 一般的な変更 |
|---|---|
| より速い応答 | `kp`（比例ゲイン）を増加 |
| オーバーシュートの低減 | 微分項またはダンピングを追加 |
| 衝突回避 | 障害物回避ロジックを追加 |
| より滑らかな軌道 | 軌道平滑化 / フィルタリングを追加 |
