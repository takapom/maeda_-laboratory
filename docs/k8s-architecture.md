# 要件定義書（完全版）

LLM による controller 改変 → CoppeliaSim 評価 → 結果観測・比較 基盤

MVP v0.2 / 研究プロトタイプ向け

## 1. 背景

本研究では、LLM（Codex / Claude Code 等）によりドローン制御コードを生成・改変し、その結果を CoppeliaSim 上で評価して、改善ループを回したい。
ただし、初期段階では汎用性や完全自動化よりも、まず確実に1回動作し、評価対象と結果が再現できることを最優先とする。

そのため本MVPでは、以下を重視する。

- 動くこと
- 再現できること
- baseline と candidate を同条件で比較できること
- 失敗時でも原因が追えること
- 実装をシンプルに保つこと

## 2. 目的

本システムの目的は、以下を実現することである。

- LLM が controller/ 配下のコード変更案を生成する
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
- 拡張性
- 汎用性
- 並列性

## 4. スコープ

### 4.1 MVPで実装すること

- Agent Runner による run 実行開始
- repo の fresh clone
- LLM による patch 生成
- patch 保存
- lint / typecheck / unit 実行
- sim-eval Job 起動
- baseline / candidate の同一条件評価
- metrics / summary / logs / metadata 保存
- active run の排他制御
- 外部 CoppeliaSim への名前解決
- 失敗 run でも metrics.json / summary.json を残す

### 4.2 MVPで実装しないこと

- 自動 PR 作成
- 自動 merge
- 並列 run
- 複数 simulator の同時スケジューリング
- 汎用 runner contract
- multi-repo 対応
- object storage 本格対応
- Web UI
- Grafana / Prometheus による高度可視化
- k8s 上での simulator 実行

## 5. 前提条件

- CoppeliaSim は Mac / x86_64 マシン側 で動作する
- k3s は Raspberry Pi クラスタ 上で動作する
- k3s から CoppeliaSim ホストへ TCP 到達可能である
- Remote API は ZeroMQ を使用する
- repo は monorepo 前提とする
- repo は本要件の固定コマンド契約を満たす
- k3s のストレージは local-path を前提とする
- PVC 共有のため agent-runner と sim-eval は 同一 Node に pin する
- Secret の etcd 暗号化は MVP では必須化しない
- CoppeliaSim は単一インスタンス前提とし、同時実行は行わない

## 6. 全体アーキテクチャ

### 6.1 構成方針

- 外部 x86_64 ホスト
- CoppeliaSim を実行
- k3s クラスタ
- Agent Runner
- sim-eval Job
- artifacts 保存
- lock 管理

### 6.2 アーキテクチャ図

```text
+---------------------------+        +---------------------------------------------+
| External Inputs           |        | External x86_64 Host                        |
|                           |        |                                             |
|  repo_url + base_ref      |        |  +---------------------------------------+  |
|  LLM API                  |        |  | CoppeliaSim                           |  |
+-------------+-------------+        |  | Remote API: ZeroMQ                    |  |
              |                      |  | Mode: stepping                        |  |
              |                      |  +-------------------+-------------------+  |
              |                      +----------------------+----------------------+
              |                                             ^
              v                                             |
+----------------------------------------------------------------------------------+
| k3s Cluster / Namespace: sim                                                     |
|                                                                                  |
|  +---------------------------+          +---------------------------+             |
|  | Agent Runner              |          | sim-eval Job              |             |
|  | Deployment / replicas: 1  |          | baseline / candidate eval|             |
|  |                           |          | scene load/reset          |             |
|  | - fresh clone             |          | comparison                |             |
|  | - patch generate          |          | metrics/summary output    |             |
|  | - static check            |          +-------------+-------------+             |
|  | - job submit              |                        |                           |
|  | - artifact collect        |                        |                           |
|  +------+------+-------------+                        |                           |
|         |      |                                      |                           |
|         |      +------------------+                   |                           |
|         |                         |                   |                           |
|         v                         v                   v                           |
|  +-------------+        +-------------------+   +---------------------------+     |
|  | Secret      |        | Service /         |   | PVC                       |     |
|  | llm-api-    |        | EndpointSlice     |   | sim-artifacts-pvc         |     |
|  | secret      |        | coppeliasim.sim   |   |                           |     |
|  |             |        | .svc.cluster.local|   | - /artifacts/runs/<id>/   |     |
|  | Agent Runner|        +---------+---------+   | - /artifacts/locks/       |     |
|  | only        |                  |             |   active_run.lock          |     |
|  +-------------+                  |             +---------------------------+     |
|                                   |                                               |
+-----------------------------------+-----------------------------------------------+
                                    |
                                    +-------- TCP / ZeroMQ --------> CoppeliaSim
```

### 6.3 コンポーネント

#### Agent Runner

責務:

- run 開始
- repo clone
- LLM 呼び出し
- patch 生成
- static check
- sim-eval Job 起動
- artifacts 収集
- run 終了処理

#### sim-eval Job

責務:

- baseline source 構成
- candidate source 構成
- scene load/reset
- evaluator 実行
- comparison 算出
- metrics / logs 保存

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

## 7. Kubernetes リソース要件

### 7.1 Namespace

固定値: sim

### 7.2 Service / EndpointSlice

CoppeliaSim はクラスタ外の外部ホスト上にあるため、selector なし Service と手動 EndpointSlice を用いて Pod から名前解決できるようにする。

必要リソース:

- Service/coppeliasim
- EndpointSlice/coppeliasim-1

要件:

- Service は selector を持たない
- EndpointSlice は kubernetes.io/service-name: coppeliasim を持つ
- ports.name は Service と EndpointSlice で一致させる
- Pod からは coppeliasim.sim.svc.cluster.local:<PORT> で接続する

### 7.3 PVC

名前: sim-artifacts-pvc

AccessMode: ReadWriteOnce

要件:

- local-path 前提のため、同一 Node に pin する
- artifacts と lock をこの PVC 上で管理する

### 7.4 Deployment

agent-runner

replica 数は 1 固定

### 7.5 Job

sim-eval

run ごとに 1 Job 作成

### 7.6 ServiceAccount

- agent-runner-sa
- sim-eval-sa

### 7.7 Secret

llm-api-secret

- agent-runner のみが参照可
- sim-eval には渡さない

## 8. スケジューリング要件

### 8.1 同一 Node 配置

agent-runner と sim-eval は同一 Node に配置すること。

実装要件:

- nodeSelector: { sim-node: "true" }
- 対象 Node に sim-node=true ラベルを付与する

### 8.2 同時実行禁止

MVPでは同時 run を禁止する。

実装要件:

- /artifacts/locks/active_run.lock を使用
- lock が存在する場合、新規 run を拒否
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

### 9.4 branch / base_ref

MVPでは branch 指定は使わない

repo_url + base_ref を取得元とする

評価対象の基準コードは常に base_ref

## 10. candidate の正本定義

### 10.1 方針

candidate source の正本は base_ref + patch.diff とする。

### 10.2 理由

- local-only commit SHA では Job 側が再現できない
- bundle 方式より実装が軽い
- artifacts のみで candidate を再構成できる

### 10.3 必須要件

- agent-runner は patch.diff を保存する
- patch_sha256 を計算して保存する
- sim-eval は base_ref を clone し、patch を適用して candidate を再構成する
- artifacts のみから評価対象が再構成できること

## 11. scene / simulator 契約

### 11.1 Remote API

固定: ZeroMQ

### 11.2 simulator mode

固定: stepping

### 11.3 scene 管理

各 run 開始時に、sim-eval は必ず以下を行う。

- scene を明示的に load
- 初期状態へ reset
- simulation start / stop を evaluator が制御

### 11.4 scene_id

scene_id は論理名

eval/scenes.yaml で実体にマップする

scenes.yaml に必要な項目:

- scene_id
- scene_path
- scene_hash または scene_version

## 12. 実行フロー

### 12.1 1 run の流れ

- Agent Runner が lock 取得
- run_id 採番
- fresh clone
- request / params 生成
- LLM で patch 生成
- patch 保存
- patch 適用
- lint / typecheck / unit 実行
- sim-eval Job 起動
- Job 完了待ち
- artifacts 収集
- summary 作成
- cleanup
- lock 解放

### 12.2 1 run の評価内容

1 run は以下を含む。

- baseline 評価
- candidate 評価
- comparison 算出
- artifacts 永続化

### 12.3 baseline / candidate 順序

同一 run 内で以下順で評価する。

- baseline
- candidate
- comparison

### 12.4 同一条件の定義

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

- 毎回 fresh clone
- 作業ディレクトリは /workspace/<run_id>/
- 前回 run の残骸を使わない
- untracked file / build cache を持ち越さない
- run 終了後に cleanup する

## 14. LLM 要件

### 14.1 対象範囲

生成・変更対象は原則 controller/

eval/ は原則固定

### 14.2 eval 変更

MVPでは eval/ のバグ修正は許可してよい

ただし eval_sha を全 run に記録する

eval_changed=true の run は、同じ eval_sha で baseline を再実行しない限り過去 run と単純比較しない

### 14.3 保存する LLM metadata

- llm_provider
- llm_model
- temperature
- prompt_template_version

## 15. sim-eval Job 要件

### 15.1 Job 動作

sim-eval Job は以下を行う。

- repo clone
- baseline source 構成
- candidate source 構成
- baseline 評価
- candidate 評価
- comparison 算出
- metrics.json / summary.json / logs 出力

### 15.2 Job 失敗ポリシー

Job manifest は以下を必須とする。

- restartPolicy: Never
- backoffLimit: 0
- activeDeadlineSeconds
- ttlSecondsAfterFinished

### 15.3 deadline

job_deadline_sec は概ね以下で算出する。

```text
connect_timeout_sec + episodes * sim_time_limit_sec + buffer_sec
```

## 16. time limit 定義

以下を分離して扱うこと。

### 16.1 connect_timeout_sec

simulator 接続待ち上限

### 16.2 sim_time_limit_sec

1 episode の simulation time 上限

### 16.3 wall_time_sec

実際の実行経過時間

### 16.4 job_deadline_sec

Kubernetes Job 全体の wall clock 上限

## 17. status / stage / errors

### 17.1 status

いずれか 1 つ。

- succeeded
- failed
- timed_out
- cancelled

### 17.2 stage

いずれか 1 つ。

- llm_generate
- patch_apply
- static_check
- job_submit
- sim_connect
- eval_run
- artifact_collect

### 17.3 errors[]

各要素は以下を持つ。

- code
- message
- retryable

### 17.4 代表的 error code

- llm_generate_failed
- patch_apply_failed
- static_check_failed
- job_submit_failed
- sim_connect_failed
- eval_timeout
- eval_failed
- artifact_collect_failed

### 17.5 失敗時の原則

- 失敗 run でも metrics.json は必ず生成する
- 成功時は metrics を埋める
- 失敗時は metrics = null とし errors[] を埋める

## 18. 比較方式

### 18.1 比較方式

MVPでは 1 run = baseline と candidate の同一条件比較 とする。

### 18.2 comparison 出力

- baseline metrics
- candidate metrics
- delta
- summary

### 18.3 比較不能条件

以下の場合は単純比較不可扱いとする。

- eval_sha が異なる
- scene_hash が異なる
- remote_api_mode が異なる
- sim_time_limit_sec が異なる
- baseline が同一 run で再評価されていない

## 19. メトリクス定義

### 19.1 主指標

- success_rate
- collision_count_mean
- time_to_goal_mean_sec

### 19.2 診断用指標

- reward_mean

### 19.3 定義

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

reward は controller 側変更対象になりうるため、主指標ではなく診断用に留める

### 19.4 metrics_meta

最低限以下を含める。

- 分母定義
- episode 母数
- success episode 数
- 失敗 episode の扱い
- reward 定義バージョン

## 20. 再現性 metadata

各 run で以下を保存する。

- controller_base_sha
- candidate_source_mode
- patch_sha256
- eval_sha
- image_ref
- image_digest
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
- job_deadline_sec
- llm_provider
- llm_model
- temperature
- prompt_template_version

## 21. artifacts 保存規約

### 21.1 保存先

/artifacts/runs/<run_id>/

### 21.2 必須ファイル

- request.json
- patch.diff
- git.json
- params.json
- llm.json
- job.json
- env.json
- metrics.json
- summary.json
- stdout.log
- stderr.log

### 21.3 推奨ファイル

- episodes_baseline.jsonl
- episodes_candidate.jsonl

### 21.4 lock 保存先

/artifacts/locks/active_run.lock

## 22. ファイル定義

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
- eval_sha

params.json

- seed list
- episodes
- scene_id
- connect_timeout_sec
- sim_time_limit_sec
- job_deadline_sec

llm.json

- provider
- model
- temperature
- prompt_template_version

job.json

- Job spec の要約
- node
- restart policy
- deadline

env.json

- image_ref
- image_digest
- python_version
- dependency hash

metrics.json

- canonical な評価結果
- 失敗時も生成必須

summary.json

- 判定要約
- baseline / candidate の比較サマリ

## 23. metrics.json スキーマ

```json
{
  "schema_version": "v1",
  "run_id": "20260316-221500-ab12cd-9f3a",
  "status": "succeeded",
  "stage": "artifact_collect",
  "candidate_source_mode": "patch",
  "comparison_mode": "baseline_vs_candidate",
  "controller_base_sha": "abc123",
  "patch_sha256": "....",
  "eval_sha": "def456",
  "llm": {
    "provider": "openai",
    "model": "codex",
    "temperature": 0.2,
    "prompt_template_version": "v1"
  },
  "sim": {
    "remote_api": "zeromq",
    "remote_api_mode": "stepping",
    "coppeliasim_version": "x.y.z",
    "scene_id": "sceneA",
    "scene_path": "/scenes/sceneA.ttt",
    "scene_hash": "....",
    "connect_timeout_sec": 10,
    "sim_time_limit_sec": 30,
    "job_deadline_sec": 420,
    "wall_time_sec": 188.4
  },
  "env": {
    "image_ref": "repo/image@sha256:...",
    "image_digest": "sha256:...",
    "python_version": "3.11.8",
    "requirements_lock_hash": "...."
  },
  "baseline": {
    "status": "succeeded",
    "metrics": {
      "success_rate": 0.4,
      "collision_count_mean": 2.1,
      "time_to_goal_mean_sec": 14.2,
      "reward_mean": 31.0
    }
  },
  "candidate": {
    "status": "succeeded",
    "metrics": {
      "success_rate": 0.7,
      "collision_count_mean": 1.0,
      "time_to_goal_mean_sec": 11.8,
      "reward_mean": 36.4
    }
  },
  "comparison": {
    "success_rate_delta": 0.3,
    "collision_count_mean_delta": -1.1,
    "time_to_goal_mean_sec_delta": -2.4,
    "reward_mean_delta": 5.4
  },
  "metrics_meta": {
    "success_rate_denominator": "requested_episodes",
    "time_to_goal_mean_sec_denominator": "successful_episodes_only",
    "reward_mean_role": "diagnostic"
  },
  "errors": []
}
```

## 24. セキュリティ要件

- agent-runner と sim-eval は別 ServiceAccount を使う
- sim-eval に LLM API key を渡さない
- Secret を artifacts に出力しない
- request.json, stdout.log, stderr.log には secret redaction を行う
- Agent Runner の RBAC は Job 作成・取得・ログ取得に必要な最小権限のみ
- MVPでは etcd at-rest encryption 未対応リスクを受容する

## 25. ログ / デバッグ要件

- selector なし Service に対して kubectl port-forward service/... は前提にしない

デバッグ手段は以下とする

- agent-runner Pod からの疎通確認
- sim-eval Job のログ確認
- PVC 上 artifacts の確認
- metrics.json, summary.json, stdout.log, stderr.log の確認

## 26. 保持方針

- artifacts は 最新100 run を保持
- 古いものから削除する
- Job / Pod API オブジェクトは ttlSecondsAfterFinished により自動削除してよい
- PVC 上 artifacts は別 cleanup 処理で削除する

## 27. 受け入れ条件（Definition of Done）

MVP 完了条件は以下。

- Service + EndpointSlice で simulator に接続できる
- Agent Runner から 1 run を開始できる
- baseline と candidate を同一 run 内で評価できる
- patch.diff から candidate を再構成できる
- metrics.json と summary.json が必ず残る
- 失敗 run でも metrics.json が残る
- timeout 時に Job が hanging しない
- active run 中は新規 run が拒否される
- agent-runner と sim-eval が同一 Node に配置される
- run に必要な再現情報が artifacts に残る

## 28. 今回の実装方針の要点

今回のMVPでは、以下を固定して実装する。

- candidate 正本は base_ref + patch.diff
- baseline / candidate は同一 run 比較
- monorepo 固定
- 固定コマンド契約
- ZeroMQ + stepping mode 固定
- scene は毎回 reload/reset
- local-path + 同一 Node pin
- 同時実行禁止
- 失敗時も metrics.json 生成
- 最新100 run 保持

必要なら次に、これをそのまま実装に落とすための
Codex向け TODO 分解版 か k8s マニフェストひな形一式 を出します。
