# 評価実行ワークフロー

## 前提条件

- プロジェクトの仮想環境（`.venv`）がセットアップ済み：`pip install -e ".[dev]"`
- リポジトリに最低1つのコミットがあること（Agent Runner がクローンするため）
- `controller/` の変更がワーキングツリーに存在すること（ステージ済みまたは未ステージ）

## 手順

### 1. コントローラーの変更を準備

`controller/` 配下のファイルを編集してドローンの動作を改善する。変更は `controller/` のみに限定すること — `eval/` は PoC では固定。

### 2. patch.diff を生成

```bash
bash scripts/gen-patch.sh
```

現在の `controller/` の差分から `/tmp/drone-poc/` に `patch.diff` を作成する。

変更が検出されない場合、スクリプトは終了コード 1 でエラーメッセージを表示する。

### 3. 評価を実行

```bash
bash scripts/run-eval.sh --goal "<最適化の目標>"
```

または明示的なオプション付きで：

```bash
bash scripts/run-eval.sh \
  --goal "より速い応答のために比例ゲインを増加" \
  --constraints "衝突回数を増やさないこと"
```

内部で行われる処理：

1. `gen-patch.sh` が `/tmp/drone-poc/patch.diff` を生成
2. Agent Runner が呼び出される：
   - ロックを取得
   - HEAD でリポジトリをクリーンクローン
   - クローンにパッチを適用
   - `make lint`、`make typecheck`、`make unit` を実行
   - サブプロセスとして sim-eval を起動
   - sim-eval が同じシード/シーンでベースラインと候補を評価
   - metrics.json、summary.json、エピソード JSONL を出力
   - ロックを解放

### 4. 結果を確認

```bash
bash scripts/show-results.sh <run_id>
```

スクリプトは以下を表示：
- 実行ステータス（成功 / 失敗 / タイムアウト）
- ベースライン vs 候補のメトリクス
- デルタ（改善/悪化）
- 評価プロファイルに基づく合否判定

### 5. 反復

結果に基づいて `controller/` を修正し、ステップ 2 から再実行する。

## アーティファクトの構成

実行後、`$ARTIFACTS_ROOT/runs/<run_id>/` には以下が含まれる：

```
request.json              目標と制約条件
patch.diff                適用された差分
git.json                  リポジトリURL、base_ref、SHA
params.json               シード、エピソード数、タイムアウト
patch_provider.json       パッチの生成方法
runtime.json              Pythonバージョン、依存関係ハッシュ
evaluation_profile.json   重み、合格基準
metrics.json              ベースライン/候補のメトリクス + デルタ
summary.json              合否判定 + 理由
episodes_baseline.jsonl   エピソードごとの生観測データ（ベースライン）
episodes_candidate.jsonl  エピソードごとの生観測データ（候補）
stdout.log                sim-eval の標準出力
stderr.log                sim-eval の標準エラー出力
```

## トラブルシューティング

### クラッシュ後にロックファイルが残る

```bash
rm $ARTIFACTS_ROOT/locks/active_run.lock
```

### コントローラーの変更が検出されない

`controller/` にコミットされていない変更があることを確認してください。ステージ済みでも未ステージでも問題ありません。

### sim-eval がタイムアウトする

環境変数 `SIM_TIME_LIMIT_SEC` または `CONNECT_TIMEOUT_SEC` を増やしてください。
