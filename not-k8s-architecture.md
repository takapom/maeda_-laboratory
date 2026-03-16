# 要件定義書（Kubernetes なし PoC 版）

Claude Code / Skill による controller 改変 → CoppeliaSim 評価 → 結果観測・比較 基盤

MVP v0.1 / PoC 向け

## 1. 背景

本研究では、Claude Code 等のコーディングエージェントを用いてドローン制御コードを生成・改変し、その結果を CoppeliaSim 上で評価して、改善ループを回したい。

ただし PoC 段階では、分散実行や高度な運用性よりも、まず確実に 1 run が完走し、baseline と candidate を同条件で比較でき、結果を再現できることを優先する。

そのため本 PoC では、Kubernetes を使わず、単一実行ホスト上のプロセスとローカルファイル保存で構成する。

また、patch 生成は LLM API の自動呼び出しではなく、operator が Claude Code / Skill を使って行う human-in-the-loop 方式とする。

## 2. 目的

本システムの目的は、以下を実現することである。

- operator が Claude Code / Skill を用いて controller/ 配下のコード変更案を生成する
- 変更案を candidate として評価可能な形で保存する
- CoppeliaSim に接続し、baseline と candidate を同一条件で評価する
- 評価結果・差分・実行条件・再現情報を run 単位で保存する
- 次の生成や分析に使える観測基盤を作る

## 3. 非機能上の優先順位

優先順位は以下の通り。

- 動作すること
- 再現可能であること
- 比較可能であること
- 失敗時の原因追跡が可能であること
- 実装をシンプルに保つこと
- 拡張性

## 4. スコープ

### 4.1 PoC で実装すること

- Agent Runner による run 実行開始
- repo の fresh clone
- Patch Provider による patch 生成
- patch 保存
- lint / typecheck / unit 実行
- sim-eval プロセス起動
- baseline / candidate の同一条件評価
- metrics / summary / logs / metadata 保存
- evaluation_profile による評価判定切り替え
- active run の排他制御
- 外部 CoppeliaSim への直接接続
- 失敗 run でも metrics.json / summary.json を残す

### 4.2 PoC で実装しないこと

- Kubernetes
- 並列 run
- 複数 simulator の同時スケジューリング
- 自動 PR 作成
- 自動 merge
- 汎用 runner contract
- multi-repo 対応
- object storage 本格対応
- Web UI
- Grafana / Prometheus による可視化
- LLM API 連携による完全自動 patch 生成

## 5. 前提条件

- CoppeliaSim は Mac / x86_64 ホスト上で動作する
- 実行ホストから CoppeliaSim ホストへ TCP 到達可能である
- Remote API は ZeroMQ を使用する
- simulator mode は stepping とする
- repo は monorepo 前提とする
- repo は本要件の固定コマンド契約を満たす
- 同時実行は行わない
- CoppeliaSim は単一インスタンス前提とする
- base_ref は再現性のため commit SHA を使う
- patch 生成は operator が Claude Code / Skill を用いて行う
- 本システムは LLM API を必須としない

## 6. 全体アーキテクチャ

### 6.1 構成方針

- 単一実行ホスト
- Agent Runner は常駐プロセスまたは CLI
- Patch Provider は operator + Claude Code / Skill とする
- sim-eval は子プロセスまたは別 CLI
- artifacts と lock はローカルファイルシステムで管理する
- CoppeliaSim は外部ホスト上で動作する

### 6.2 アーキテクチャ図

```text
+---------------------------+   +---------------------------------+   +--------------------------------------+
| External Inputs           |   | Operator / Patch Provider       |   | External x86_64 Host                 |
|                           |   |                                 |   |                                      |
|  repo_url + base_ref      |   |  Claude Code + Skill            |   |  +--------------------------------+  |
|  request / params         |   |  patch.diff を生成              |   |  | CoppeliaSim                    |  |
+-------------+-------------+   +----------------+----------------+   |  | Remote API: ZeroMQ             |  |
              |                                  |                    |  | Mode: stepping                 |  |
              |                                  |                    |  +---------------+----------------+  |
              v                                  v                    +------------------+-------------------+
+------------------------------------------------------------------------------------------------------------+
| Execution Host                                                                                             |
|                                                                                                            |
|  +---------------------------+        +----------------------------------+                                 |
|  | Agent Runner              |        | sim-eval                         |                                 |
|  |                           |        |                                  |                                 |
|  | - lock acquire/release    |        | - baseline source setup          |                                 |
|  | - fresh clone             |        | - candidate source setup         |                                 |
|  | - request/params generate |        | - scene load/reset               |                                 |
|  | - patch receive/apply     |        | - baseline/candidate evaluation  |                                 |
|  | - static check            |        | - comparison / metrics output    |                                 |
|  | - artifact collect        |        |                                  |                                 |
|  +------+--------------------+        +----------------+-----------------+                                 |
|         |                                              |                                                   |
|         +---------------------+------------------------+                                                   |
|                               |                                                                            |
|                     +---------v------------------------------------------+                                 |
|                     | Local Filesystem                                  |                                 |
|                     | - /artifacts/runs/<run_id>/                       |                                 |
|                     | - /artifacts/locks/active_run.lock                |                                 |
|                     | - /workspace/<run_id>/                            |                                 |
|                     +---------------------------------------------------+                                 |
+------------------------------------------------------------------------------------------------------------+
                                                  |
                                                  +----------- TCP / ZeroMQ -------------> CoppeliaSim
```

### 6.3 コンポーネント

#### Agent Runner

責務:

- run 開始
- active run lock の取得と解放
- repo clone
- request / params 生成
- patch 生成待ち
- patch 受領
- patch 妥当性検証
- patch 保存
- patch 適用
- lint / typecheck / unit 実行
- sim-eval 起動
- artifacts 収集
- run 終了処理
- sim-eval が成果物を残せなかった場合の fallback artifact 生成

#### Patch Provider

責務:

- request / params を読む
- Claude Code / Skill を用いて patch.diff を生成する
- Agent Runner に patch を渡す
- patch 生成に関する metadata を残す

#### sim-eval

責務:

- baseline source 構成
- candidate source 構成
- scene load/reset
- evaluator 実行
- raw observation 保存
- raw observation から metrics 算出
- evaluation_profile 適用
- comparison 算出
- metrics / summary / logs 保存

#### CoppeliaSim

責務:

- シミュレーション実行
- scene 読み込み
- stepping mode 実行
- simulation start / stop

#### Artifact Storage

責務:

- run 単位の成果物保存
- patch / metadata / metrics / logs 保持

#### Lock

責務:

- active run の排他制御

## 7. ローカルリソース要件

### 7.1 artifacts ルート

固定値: /artifacts

### 7.2 workspace ルート

固定値: /workspace

### 7.3 lock ファイル

固定値: /artifacts/locks/active_run.lock

### 7.4 認証情報

PoC では本システムが LLM API key を直接管理することは必須としない。

要件:

- Claude Code / Skill 利用に必要な認証は operator 側環境で管理する
- sim-eval には渡さない
- artifacts に出力しない

## 8. 実行・排他制御要件

### 8.1 単一実行

PoC では同時 run を禁止する。

### 8.2 排他制御

実装要件:

- /artifacts/locks/active_run.lock を使用する
- lock が存在する場合、新規 run を拒否する
- 正常終了 / 異常終了時に lock 解放を試みる
- lock が残留した場合は手動解除を許容する

## 9. repo 前提と固定契約

### 9.1 repo 形態

monorepo 固定

### 9.2 ディレクトリ構成

最低限以下を含む。

```text
repo/
  controller/
  eval/
  Makefile
  eval/scenes.yaml
```

### 9.3 固定コマンド契約

repo は以下を提供すること。

```text
make lint
make typecheck
make unit
python -m eval.run --source-dir <path> --scene-id <scene_id> --seed-list <csv> --output-dir <dir>
```

### 9.4 base_ref

取得元は repo_url + base_ref とする。

base_ref は commit SHA とする。

評価対象の基準コードは常に base_ref とする。

## 10. candidate の正本定義

### 10.1 方針

candidate source の正本は base_ref + patch.diff とする。

### 10.2 patch 契約

- patch.diff は git diff 形式で保存する
- patch_sha256 を計算して保存する
- patch は適用前に check を行う
- patch 適用失敗時は run を failed とする

### 10.3 変更対象

- 変更対象は原則 controller/ のみとする
- eval/ は PoC では固定とする

## 11. scene / simulator 契約

### 11.1 Remote API

固定: ZeroMQ

### 11.2 simulator mode

固定: stepping

### 11.3 scene 管理

各 run 開始時に、sim-eval は必ず以下を行う。

- scene を明示的に load する
- 初期状態へ reset する
- simulation start / stop は evaluator が制御する

### 11.4 scene_id

scene_id は論理名とする。

eval/scenes.yaml で実体にマップする。

scenes.yaml に必要な項目:

- scene_id
- scene_path
- scene_hash または scene_version

## 12. 実行フロー

### 12.1 1 run の流れ

- Agent Runner が lock を取得する
- run_id を採番する
- fresh clone を行う
- request / params を生成する
- operator が Claude Code / Skill を用いて patch を生成する
- Agent Runner が patch を受領する
- patch.diff を保存する
- patch を適用する
- lint / typecheck / unit を実行する
- sim-eval を起動する
- baseline を評価する
- candidate を評価する
- comparison を算出する
- artifacts を永続化する
- summary を作成する
- cleanup を行う
- lock を解放する

### 12.2 baseline / candidate の同一条件

baseline と candidate は必ず以下を共通にする。

- 同じ evaluator
- 同じ scene_id
- 同じ scene 実体
- 同じ seed list
- 同じ episode 数
- 同じ connect timeout
- 同じ sim_time_limit
- 同じ remote_api_mode

## 13. workspace 要件

- 毎回 fresh clone とする
- 作業ディレクトリは /workspace/<run_id>/ とする
- 前回 run の残骸を使わない
- untracked file / build cache を持ち越さない
- run 終了後に cleanup する

## 14. sim-eval プロセス要件

### 14.1 動作

sim-eval は以下を行う。

- repo clone または workspace の source を受け取る
- baseline source を構成する
- candidate source を構成する
- baseline を評価する
- candidate を評価する
- raw observation を保存する
- raw observation から metrics を計算する
- evaluation_profile に基づいて comparison / summary を生成する
- comparison を算出する
- metrics.json / summary.json / logs を出力する

### 14.2 起動方法

PoC では Agent Runner から sim-eval を子プロセスとして起動する。

### 14.3 timeout

Agent Runner は sim-eval 全体に wall clock timeout を設定する。

run_timeout_sec は概ね以下で算出する。

```text
connect_timeout_sec + 2 * episodes * sim_time_limit_sec + buffer_sec
```

## 15. time limit 定義

### 15.1 connect_timeout_sec

simulator 接続待ち上限

### 15.2 sim_time_limit_sec

1 episode の simulation time 上限

### 15.3 wall_time_sec

実際の実行経過時間

### 15.4 run_timeout_sec

1 run 全体の wall clock 上限

## 16. status / stage / errors

### 16.1 status

いずれか 1 つ。

- succeeded
- failed
- timed_out
- cancelled

### 16.2 stage

いずれか 1 つ。

- patch_generate
- patch_apply
- static_check
- eval_start
- sim_connect
- eval_run
- artifact_collect

### 16.3 errors[]

各要素は以下を持つ。

- code
- message
- retryable

### 16.4 代表的 error code

- patch_generate_failed
- patch_apply_failed
- static_check_failed
- eval_start_failed
- sim_connect_failed
- eval_timeout
- eval_failed
- artifact_collect_failed

### 16.5 失敗時の原則

- 失敗 run でも metrics.json は必ず生成する
- 成功時は metrics を埋める
- 失敗時は metrics = null とし errors[] を埋める
- sim-eval が metrics.json / summary.json を残せなかった場合は Agent Runner が fallback を生成する

## 17. 比較方式

### 17.1 比較方式

PoC では 1 run = baseline と candidate の同一条件比較 とする。

### 17.2 comparison 出力

- baseline metrics
- candidate metrics
- delta
- summary
- evaluation_profile

### 17.3 比較不能条件

以下の場合は単純比較不可扱いとする。

- scene_hash が異なる
- remote_api_mode が異なる
- sim_time_limit_sec が異なる
- baseline が同一 run で再評価されていない

## 18. メトリクス定義

### 18.1 主指標

- success_rate
- collision_count_mean
- time_to_goal_mean_sec

### 18.2 診断用指標

- reward_mean

### 18.3 定義

success_rate

定義: 成功 episode 数 / 要求 episode 数

接続失敗や途中失敗 episode は失敗として分母に含める

collision_count_mean

定義: 全 episode の collision count 合計 / 要求 episode 数

time_to_goal_mean_sec

定義: 成功 episode のみを母数とした simulation time の平均

成功 episode が 0 の場合は null

reward_mean

定義: 各 episode の cumulative reward の平均

reward は診断用に留める

### 18.4 metrics_meta

最低限以下を含める。

- 分母定義
- episode 母数
- success episode 数
- 失敗 episode の扱い

### 18.5 評価軸チューニング方針

PoC では、評価実行と評価判断を分離する。

- evaluator は simulation を実行し、episode 単位の raw observation を出力する
- metrics 算出は raw observation から行う
- 最終的な評価判定は evaluation_profile に基づいて行う
- 通常の評価軸チューニングは evaluation_profile の変更で行う
- 新しい raw observation が必要な場合のみ evaluator 実装を変更する

### 18.6 raw observation 要件

raw observation は baseline / candidate それぞれについて episode 単位で保存する。

最低限以下を含める。

- episode_index
- seed
- status
- success
- collision_count
- time_to_goal_sec
- reward
- timed_out
- error_code

### 18.7 evaluation_profile 要件

evaluation_profile は run ごとに指定可能とする。

最低限以下を含める。

- profile_name
- primary_metrics
- weights
- pass_criteria

evaluation_profile の変更では、simulation 実行ロジックおよび CoppeliaSim 接続ロジックは変更しないことを原則とする。

### 18.8 評価軸変更時の変更責務

- 重み、閾値、主指標の切り替えは evaluation_profile を変更する
- metric の計算式変更は metrics 算出ロジックを変更する
- 新しい raw observation が必要な場合のみ evaluator を変更する

## 19. 再現性 metadata

各 run で以下を保存する。

- controller_base_sha
- candidate_source_mode
- patch_sha256
- image_ref または runtime_name
- python_version
- requirements_lock_hash または pip_freeze_hash
- coppeliasim_version
- scene_id
- scene_path
- scene_hash または scene_version
- remote_api
- remote_api_mode
- connect_timeout_sec
- sim_time_limit_sec
- run_timeout_sec
- evaluation_profile_name
- evaluation_profile_hash
- patch_provider
- patch_generation_mode
- skill_name または workflow_name
- operator
- prompt_template_version

## 20. artifacts 保存規約

### 20.1 保存先

/artifacts/runs/<run_id>/

### 20.2 必須ファイル

- request.json
- patch.diff
- git.json
- params.json
- patch_provider.json
- runtime.json
- evaluation_profile.json
- metrics.json
- summary.json
- episodes_baseline.jsonl
- episodes_candidate.jsonl
- stdout.log
- stderr.log

### 20.3 推奨ファイル

- なし

### 20.4 lock 保存先

/artifacts/locks/active_run.lock

## 21. ファイル定義

request.json

- goal
- constraints
- prompt input
- allowlist / denylist

patch.diff

- candidate 再構成の正本

git.json

- repo_url
- base_ref
- controller_base_sha

params.json

- seed list
- episodes
- scene_id
- connect_timeout_sec
- sim_time_limit_sec
- run_timeout_sec
- evaluation_profile

patch_provider.json

- provider_type
- patch_generation_mode
- tool_name
- skill_name
- operator
- prompt_template_version

runtime.json

- host
- python_version
- dependency hash
- coppeliasim endpoint

evaluation_profile.json

- profile_name
- primary_metrics
- weights
- pass_criteria

metrics.json

- canonical な評価結果
- 失敗時も生成必須

summary.json

- 判定要約
- baseline / candidate の比較サマリ
- evaluation_profile に基づく判定理由

episodes_baseline.jsonl / episodes_candidate.jsonl

- episode 単位の raw observation
- 後段の再集計と評価軸差し替えの基礎データ

## 22. セキュリティ要件

- Claude Code / Skill 利用に必要な認証情報を artifacts に出力しない
- sim-eval に operator 側認証情報を渡さない
- request.json, stdout.log, stderr.log には secret redaction を行う
- PoC では operator 側環境で認証を管理する

## 23. ログ / デバッグ要件

デバッグ手段は以下とする。

- Agent Runner の標準出力 / 標準エラー確認
- sim-eval の標準出力 / 標準エラー確認
- /artifacts 配下の確認
- metrics.json, summary.json, stdout.log, stderr.log の確認

## 24. 保持方針

- artifacts は最新 100 run を保持する
- 古いものから削除する
- cleanup は別処理または手動実行でよい

## 25. 受け入れ条件（Definition of Done）

PoC 完了条件は以下。

- Agent Runner から 1 run を開始できる
- operator が Claude Code / Skill を用いて patch.diff を生成できる
- CoppeliaSim に直接接続できる
- baseline と candidate を同一 run 内で評価できる
- patch.diff から candidate を再構成できる
- metrics.json と summary.json が必ず残る
- 失敗 run でも metrics.json が残る
- episodes_baseline.jsonl / episodes_candidate.jsonl から再集計できる
- evaluation_profile を変更しても simulation 実行ロジックを変えずに評価判定を切り替えられる
- timeout 時に sim-eval が hanging しない
- active run 中は新規 run が拒否される
- run に必要な再現情報が artifacts に残る
