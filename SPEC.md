# SPEC.md

## プロジェクト概要

ローカル環境にインストールされた ClamAV を利用し、
ファイルおよびディレクトリに対してウィルススキャンを実行し、
結果を SQLite に保存する Python CLI アプリケーションを実装する。

本システムは以下の2つの利用形態を持つ：

1. 手動スキャン（path指定）
2. 定期スキャン（collect → execute）

---

## 設計思想（重要）

* スキャン処理は「対象抽出」と「スキャン実行」を分離する
* スキャン対象は「ファイル」ではなく「スキャン単位（target）」として扱う
* target は以下の2種類を持つ：

  * file target
  * directory target
* directory target は再帰スキャン（ClamAV）で処理する
* **file target は複数ファイルをまとめて1回の clamscan に渡す（バッチ実行）**
* **execute は常に未完了 item のみを対象とする（自然な途中再開）**
* 初期段階では除外は適用しない（全スキャン）
* ただし将来的な除外機能のためにDB設計には余白を持たせる

---

## 技術スタック

* 言語: Python 3.x
* CLI: Typer（推奨）
* DB: SQLite
* ORM: SQLAlchemy（推奨）
* 設定: TOML または YAML
* ClamAV呼び出し: subprocess

---

## アーキテクチャ

### モジュール構成

* cli.py          : CLIエントリ
* collector.py    : 対象抽出
* scanner.py      : ClamAV実行
* parser.py       : 出力パース
* repository.py   : DB操作
* models.py       : ORM定義
* config.py       : 設定管理

---

## 機能一覧

### 1. 手動スキャン

```bash
scanlog scan <path>
```

#### 概要

指定されたファイルまたはディレクトリを即時スキャンする

#### 挙動

* path がファイル → file target
* path がディレクトリ → directory target

内部処理：

1. scan_plan 作成（mode = manual_scan）
2. plan_items 作成
3. 自動で approved
4. scan_run を作成しバッチ実行

---

### 2. collect（対象抽出）

```bash
scanlog collect
```

#### 概要

スキャン対象を収集し scan_plan を作成する

#### 条件

* カレントディレクトリ配下を探索
* 当日作成 / 当日更新ファイルを対象

#### 重要仕様

collect は「ファイル一覧」ではなく
「スキャン対象単位」を生成する

---

### target の種類

#### file target

以下に該当する場合：

* 単体ファイル
* アーカイブ・インストーラ系

例:

* .zip
* .tar.gz
* .dmg
* .pkg
* .exe
* .jar

scan_mode: `single`

---

#### directory target

以下に該当する場合：

* ディレクトリ
* プロジェクトルート
* 大量ファイルを含む構造

例:

* node_modules を含む
* .venv を含む
* .git を含む
* 依存パッケージ群

scan_mode: `recursive`

---

### プロジェクトルート判定

以下を含む場合 directory target とする：

* .git
* package.json
* pyproject.toml
* requirements.txt
* Pipfile
* poetry.lock
* Cargo.toml
* go.mod
* Gemfile
* pom.xml
* build.gradle
* Makefile

---

### 3. preview

```bash
scanlog preview --latest
```

#### 内容

* target_path
* target_type
* scan_mode
* target_reason
* execution_status

---

### 4. approve

```bash
scanlog approve --plan-id <id>
```

---

### 5. execute

```bash
scanlog execute --plan-id <id>
```

#### 処理

* approved plan のみ実行
* plan_items をそのまま使用（再collect はしない）
* **execution_status = pending / failed の item のみ対象**
* **completed の item はスキップ（途中再開に対応）**
* バッチ単位で処理し、バッチごとに DB を更新する

#### 途中再開（resume）

同一 plan_id に対して `execute` を再実行すると、
`execution_status = completed` の item は自動的にスキップされ、
未完了分（pending / failed）のみが実行される。

```bash
# 失敗・中断後の再実行（resume として機能する）
scanlog execute --plan-id <id>
```

---

## ClamAV 実行仕様

### file target（バッチ実行）

同一 scan_run 内の全 file target をまとめて1コマンドに渡す。

```bash
clamscan --no-summary <file1> <file2> <file3> ...
```

* MVP では file target 全体を1バッチとして扱う
* 将来的にはバッチサイズの上限設定を追加可能

---

### directory target（個別実行）

directory target は1ディレクトリ = 1バッチとして個別に実行する。

```bash
clamscan -r --no-summary <directory>
```

---

## 出力例

```text
/path/file1: OK
/path/file2: Eicar-Test-Signature FOUND
/path/file3: Empty file
/path/file4: Symbolic link
/path/file5: Can't access file ERROR
```

---

## パース仕様

| ClamAV 出力           | entry_status  | 説明                         |
| ------------------- | ------------- | -------------------------- |
| `OK`                | clean         | 正常                         |
| `<name> FOUND`      | infected      | ウィルス検出                     |
| `Empty file`        | clamav_error  | 0バイトファイル（スキャン不可）           |
| `Symbolic link`     | clamav_error  | シンボリックリンク（スキャン不可）          |
| `<message> ERROR`   | clamav_error  | 権限不足・アクセス不可                |
| その他                 | error         | 予期しない出力                    |

* `clamav_error` は result_status に影響しない（infected > error > clean の優先順位）
* `clamav_error` はスキャン結果に件数のみサマリ表示する

---

## DB設計

### scan_plans

| カラム        | 型        | 説明                                           |
| ---------- | -------- | -------------------------------------------- |
| id         | INTEGER  | PK                                           |
| mode       | TEXT     | manual_scan / scheduled_scan                 |
| status     | TEXT     | draft / approved / executing / completed / failed |
| base_path  | TEXT     | 収集対象ディレクトリ                                   |
| created_at | DATETIME |                                              |

---

### plan_items

| カラム              | 型       | 説明                                      |
| ---------------- | ------- | --------------------------------------- |
| id               | INTEGER | PK                                      |
| plan_id          | INTEGER | FK → scan_plans.id                      |
| target_path      | TEXT    |                                         |
| target_type      | TEXT    | file / directory                        |
| scan_mode        | TEXT    | single / recursive                      |
| target_reason    | TEXT    | manual / archive / modified_today / project_root |
| selected         | BOOLEAN |                                         |
| excluded_by_user | BOOLEAN | 将来用                                     |
| exclude_reason   | TEXT    | 将来用                                     |
| batch_id         | INTEGER | FK → scan_batches.id（実行後に設定）            |
| execution_status | TEXT    | pending / completed / failed / skipped  |
| last_run_id      | INTEGER | FK → scan_runs.id（最後に実行した run）          |

---

### scan_runs

| カラム         | 型        | 説明                             |
| ----------- | -------- | ------------------------------ |
| id          | INTEGER  | PK                             |
| plan_id     | INTEGER  | FK → scan_plans.id             |
| started_at  | DATETIME |                                |
| finished_at | DATETIME |                                |
| status      | TEXT     | running / completed / failed   |

---

### scan_batches

バッチ実行単位を管理するテーブル。
1レコード = 1回の clamscan 実行に対応する。

| カラム         | 型        | 説明                                        |
| ----------- | -------- | ----------------------------------------- |
| id          | INTEGER  | PK                                        |
| run_id      | INTEGER  | FK → scan_runs.id                         |
| batch_type  | TEXT     | file / directory                          |
| command_line| TEXT     | 実際に実行した clamscan コマンド全体                   |
| status      | TEXT     | pending / running / completed / failed    |
| started_at  | DATETIME |                                           |
| finished_at | DATETIME |                                           |

---

### scan_results（親）

| カラム           | 型       | 説明                              |
| ------------- | ------- | ------------------------------- |
| id            | INTEGER | PK                              |
| run_id        | INTEGER | FK → scan_runs.id               |
| batch_id      | INTEGER | FK → scan_batches.id            |
| plan_item_id  | INTEGER | FK → plan_items.id              |
| target_path   | TEXT    |                                 |
| target_type   | TEXT    | file / directory                |
| result_status | TEXT    | clean / infected / error        |
| raw_output    | TEXT    | clamscan の stdout 全体            |
| exit_code     | INTEGER |                                 |

---

### scan_result_entries（子）

| カラム            | 型       | 説明                                       |
| -------------- | ------- | ---------------------------------------- |
| id             | INTEGER | PK                                       |
| scan_result_id | INTEGER | FK → scan_results.id                     |
| scanned_path   | TEXT    |                                          |
| entry_status   | TEXT    | clean / infected / clamav_error / error  |
| virus_name     | TEXT    |                                          |
| raw_line       | TEXT    |                                          |

---

## 状態管理

### scan_plan.status

```
draft → approved → executing → completed
                              → failed
```

---

### plan_item.execution_status

```
pending → completed
        → failed
        → skipped   （clamav_error のみの場合）
```

* `pending`   : 未実行（初期値）
* `completed` : スキャン正常完了
* `failed`    : スキャン実行エラー（clamscan 自体の異常終了）
* `skipped`   : clamav_error のみで実スキャン結果なし

---

### scan_batch.status

```
pending → running → completed
                  → failed
```

---

## 処理フロー

### 手動スキャン

```
scan <path>
  └─ scan_plan 作成（manual_scan / approved）
  └─ plan_item 作成（execution_status = pending）
  └─ scan_run 作成
  └─ execute と同じバッチ処理を実行
```

---

### 定期スキャン

```
collect → preview → approve → execute
```

---

### execute の詳細フロー

```
execute --plan-id <id>
  1. plan.status を executing に更新
  2. execution_status = pending / failed の plan_items を取得
  3. file targets をまとめて1つの scan_batch を生成
  4. directory targets を1件ずつ scan_batch として生成
  5. 各 scan_batch を順に実行:
     a. batch.status = running, started_at を記録
     b. clamscan を subprocess 実行（command_line を保存）
     c. 出力をパース
     d. scan_results / scan_result_entries を保存
     e. 対応する plan_items.execution_status を更新
        - 正常: completed
        - 実行失敗: failed
        - clamav_error のみ: skipped
     f. plan_items.batch_id, last_run_id を更新
     g. batch.status = completed / failed, finished_at を記録
  6. 全バッチ完了後:
     - scan_run.status, finished_at を更新
     - scan_plan.status を completed / failed に更新
```

---

## MVPスコープ

### 必須

* scan（file / directory）
* ClamAV実行（バッチ実行）
* 出力パース（clamav_error 対応含む）
* SQLite保存
* collect
* execute（途中再開対応）

---

### 非対象

* 除外ルール適用
* ハッシュ管理
* 並列処理
* バッチサイズの設定
* GUI
* 通知
* quarantine

---

## 実装順序（重要）

1. scanコマンド（手動）
2. ClamAV実行 + パース（clamav_error 対応）
3. DB保存（scan_batches テーブル含む）
4. directory対応
5. plan構造導入（execution_status / batch_id / last_run_id）
6. collect実装
7. preview / approve / execute（バッチ実行・途中再開対応）

---

## 重要な設計ルール

* scan処理は独立させる
* collectはscanに依存しない
* executeはplan_itemsのみを使用（再collect禁止）
* raw_outputは必ず保存
* **バッチ処理はバッチごとにDBをコミットする（途中再開を可能にするため）**
* **execution_status は plan_item 単位で管理する**

---

## 除外仕様（将来）

MVPでは除外は適用しない

ただし以下を保持：

* excluded_by_user
* exclude_reason

将来：

* パス除外
* 拡張子除外
* ディレクトリ除外

---
