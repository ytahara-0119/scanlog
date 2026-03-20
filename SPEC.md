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
4. scan_run 実行

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
* plan_items をそのまま使用
* 再collectはしない

---

## ClamAV 実行仕様

### file target

```bash
clamscan --no-summary <file>
```

---

### directory target

```bash
clamscan -r --no-summary <directory>
```

---

## 出力例

```text
/path/file1: OK
/path/file2: Eicar-Test-Signature FOUND
```

---

## パース仕様

* OK → clean
* FOUND → infected
* その他 → error

---

## DB設計

### scan_plans

| カラム        | 型        |
| ---------- | -------- |
| id         | INTEGER  |
| mode       | TEXT     |
| status     | TEXT     |
| base_path  | TEXT     |
| created_at | DATETIME |

---

### plan_items

| カラム              | 型       |
| ---------------- | ------- |
| id               | INTEGER |
| plan_id          | INTEGER |
| target_path      | TEXT    |
| target_type      | TEXT    |
| scan_mode        | TEXT    |
| target_reason    | TEXT    |
| selected         | BOOLEAN |
| excluded_by_user | BOOLEAN |
| exclude_reason   | TEXT    |

---

### scan_runs

| カラム         | 型        |
| ----------- | -------- |
| id          | INTEGER  |
| plan_id     | INTEGER  |
| started_at  | DATETIME |
| finished_at | DATETIME |
| status      | TEXT     |

---

### scan_results（親）

| カラム           | 型       |
| ------------- | ------- |
| id            | INTEGER |
| run_id        | INTEGER |
| plan_item_id  | INTEGER |
| target_path   | TEXT    |
| target_type   | TEXT    |
| result_status | TEXT    |
| raw_output    | TEXT    |
| exit_code     | INTEGER |

---

### scan_result_entries（子）

| カラム            | 型       |
| -------------- | ------- |
| id             | INTEGER |
| scan_result_id | INTEGER |
| scanned_path   | TEXT    |
| entry_status   | TEXT    |
| virus_name     | TEXT    |
| raw_line       | TEXT    |

---

## 状態管理

### scan_plan.status

* draft
* approved
* executing
* completed
* failed

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

## 処理フロー

### 手動

scan → execute

---

### 定期

collect → preview → approve → execute

---

## MVPスコープ

### 必須

* scan（file / directory）
* ClamAV実行
* 出力パース
* SQLite保存
* collect
* execute

---

### 非対象

* 除外ルール適用
* ハッシュ管理
* 並列処理
* GUI
* 通知
* quarantine

---

## 実装順序（重要）

1. scanコマンド（手動）
2. ClamAV実行 + パース
3. DB保存
4. directory対応
5. plan構造導入
6. collect実装
7. preview / approve / execute

---

## 重要な設計ルール

* scan処理は独立させる
* collectはscanに依存しない
* executeはplan_itemsのみを使用
* raw_outputは必ず保存

---
