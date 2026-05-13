# SPEC.md

## プロジェクト概要

ローカル環境にインストールされた ClamAV を利用し、
ファイルおよびディレクトリに対してウィルススキャンを実行し、
結果を SQLite に保存する Python CLI アプリケーション。

本システムは以下の2つの利用形態を持つ：

1. 手動スキャン（`scan <path>`）
2. 監視スキャン（`watch run`）

---

## 設計思想

* スキャン処理はシンプルに保つ：対象指定 → ClamAV実行 → 結果保存
* 監視スキャンは「差分のみをスキャン」する。常駐監視ではなく1日1回の巡回実行として扱う
* 差分判定は size + mtime を優先し、変化があった場合のみ sha256 を計算する（監視コスト削減）
* 計画・承認フロー（collect / preview / approve / execute）は廃止し、即実行に統一する

---

## 技術スタック

* 言語: Python 3.x
* CLI: Typer
* DB: SQLite
* ORM: SQLAlchemy
* ClamAV呼び出し: subprocess
* ハッシュ計算: hashlib（sha256、差分判定用）

---

## アーキテクチャ

### モジュール構成

* cli.py        : CLIエントリ
* scanner.py    : ClamAV実行
* parser.py     : 出力パース
* repository.py : DB操作
* models.py     : ORM定義
* config.py     : 設定管理
* watcher.py    : 監視差分判定・対象抽出（監視モード専用）

---

## コマンド一覧

### 1. scan

```bash
scanlog scan <path>
```

指定されたファイルまたはディレクトリを即時スキャンする。

#### 挙動

* path がファイル → `clamscan --no-summary <file>` で実行
* path がディレクトリ → `clamscan -r --no-summary <directory>` で実行
* 結果を scan_results / scan_result_entries に保存
* 実行後にサマリを表示する

---

### 2. watch add

```bash
scanlog watch add <path>
```

監視対象 path を登録する。既に登録済みの場合は enabled = true に更新する。

---

### 3. watch list

```bash
scanlog watch list
```

登録済みの監視対象 path 一覧を表示する。
表示項目: id, enabled, created_at, path

---

### 4. watch remove

```bash
scanlog watch remove <path>
```

監視対象 path を登録から削除する。
file_inventory のレコードは保持する（履歴として残す）。

---

### 5. watch run

```bash
scanlog watch run
```

enabled = true の全 watch_path を対象に差分チェックを実行し、
変化のあったファイルのみ ClamAV でスキャンする。

#### 挙動

1. watch_paths から enabled = true の path を取得
   - 0件の場合: 「監視対象が登録されていません」を表示して終了
2. 各 watch_path 配下のファイルを走査（除外ポリシー適用）
3. file_inventory と比較し、差分ありファイルを特定
4. 差分が0件の場合: 「変更ファイルなし」を表示してスキャンをスキップ
   - ただし file_inventory の last_seen_at / is_deleted は更新する
5. 差分が1件以上の場合: バッチスキャンを実行し結果を保存
6. file_inventory を更新（スキャン有無に関わらず実行）

---

### 6. recent

```bash
scanlog recent [--limit 10]
```

直近のスキャン結果を新しい順に表示する（デフォルト: 10件）。

#### 表示内容

* scanned_at（スキャン日時）
* mode（manual / watch）
* result_status（clean / infected / error）
* target_path

infected があれば詳細（virus_name）も表示する。

---

## ClamAV 実行仕様

### ファイルスキャン（バッチ実行）

複数ファイルをまとめて1回の clamscan に渡す。ARG_MAX 超過を防ぐためチャンク分割する。

```bash
clamscan --no-summary <file1> <file2> <file3> ...
```

### ディレクトリスキャン（再帰実行）

```bash
clamscan -r --no-summary <directory>
```

---

## 出力パース仕様

| ClamAV 出力        | entry_status  | 説明                       |
| ------------------ | ------------- | -------------------------- |
| `OK`               | clean         | 正常                       |
| `<name> FOUND`     | infected      | ウィルス検出               |
| `Empty file`       | clamav_error  | 0バイトファイル（スキャン不可） |
| `Symbolic link`    | clamav_error  | シンボリックリンク（スキャン不可） |
| `<message> ERROR`  | clamav_error  | 権限不足・アクセス不可     |
| その他             | error         | 予期しない出力             |

* `clamav_error` は result_status に影響しない（infected > error > clean の優先順位）

---

## DB設計

### scan_results

スキャン実行ごとの結果テーブル。

| カラム         | 型       | 説明                           |
| -------------- | -------- | ------------------------------ |
| id             | INTEGER  | PK                             |
| mode           | TEXT     | manual / watch                 |
| scanned_at     | DATETIME | スキャン実行日時               |
| target_path    | TEXT     | スキャン対象パス               |
| target_type    | TEXT     | file / directory               |
| result_status  | TEXT     | clean / infected / error       |
| raw_output     | TEXT     | clamscan の stdout 全体        |
| exit_code      | INTEGER  |                                |

---

### scan_result_entries

scan_results の詳細エントリ（ファイル単位）。

| カラム          | 型      | 説明                                      |
| --------------- | ------- | ----------------------------------------- |
| id              | INTEGER | PK                                        |
| scan_result_id  | INTEGER | FK → scan_results.id                     |
| scanned_path    | TEXT    | スキャンされたファイルパス                |
| entry_status    | TEXT    | clean / infected / clamav_error / error   |
| virus_name      | TEXT    | 検出されたウィルス名（infected のみ）     |
| raw_line        | TEXT    | ClamAV 出力の生ライン                     |

---

### watch_paths

監視対象 path の登録テーブル。

| カラム     | 型       | 説明                              |
| ---------- | -------- | --------------------------------- |
| id         | INTEGER  | PK                                |
| path       | TEXT     | 監視対象の絶対パス（UNIQUE）      |
| enabled    | BOOLEAN  | 有効フラグ（デフォルト true）     |
| created_at | DATETIME |                                   |
| updated_at | DATETIME |                                   |

---

### file_inventory

監視対象ファイルの最新状態を保持するテーブル。
`watch run` 実行時に更新される。差分判定の基準データとして使用する。

| カラム           | 型       | 説明                                           |
| ---------------- | -------- | ---------------------------------------------- |
| id               | INTEGER  | PK                                             |
| watch_path_id    | INTEGER  | FK → watch_paths.id                            |
| file_path        | TEXT     | ファイルの絶対パス（UNIQUE）                   |
| file_size        | INTEGER  | バイト数                                       |
| mtime            | FLOAT    | ファイルの最終更新時刻（Unix timestamp）       |
| sha256           | TEXT     | SHA256ハッシュ（差分ありと判定されたときのみ更新） |
| first_seen_at    | DATETIME | 初回検出日時                                   |
| last_seen_at     | DATETIME | 最後に存在確認した日時                         |
| last_scanned_at  | DATETIME | 最後にスキャンした日時                         |
| last_scan_result | TEXT     | clean / infected / error / null（未スキャン） |
| is_deleted       | BOOLEAN  | ファイルが見つからない場合 true（論理削除）    |

---

## 差分判定ロジック（watch run）

```
対象ファイルを走査（除外ポリシー適用後）
  └─ file_inventory に未登録 → 新規ファイル → スキャン対象
  └─ is_deleted = true だったが再出現 → スキャン対象
  └─ file_size または mtime が変化
       └─ sha256 を計算
            └─ sha256 が変化 → スキャン対象
            └─ sha256 が同一 → スキャン不要（mtime/size のみの変化と判定）
  └─ file_size も mtime も変化なし → スキャン不要

前回 error のファイル（last_scan_result = error）
  → 再スキャン対象とする（保守的判定）
```

---

## 監視除外ポリシー（watch run）

以下のディレクトリ名に一致する場合、配下のファイルを走査対象から外す。
これは「安全だから除外する」のではなく、監視コスト削減のためのポリシーである。

```
node_modules
.venv
vendor
target
build
dist
.git
```

手動スキャン（`scan <path>`）では除外ポリシーを適用しない。

---

## 処理フロー

### 手動スキャン（scan <path>）

```
scan <path>
  └─ ClamAV 実行（ファイル: バッチ、ディレクトリ: 再帰）
  └─ 出力パース
  └─ scan_results / scan_result_entries に保存
  └─ 結果サマリを表示
```

### 監視スキャン（watch run）

```
watch run
  1. enabled な watch_paths を取得
  2. 各 watch_path を走査（除外ポリシー適用）
  3. file_inventory と比較し差分ファイルを特定
  4. 差分ファイルをバッチスキャン
  5. 結果を scan_results / scan_result_entries に保存
  6. file_inventory を更新（last_seen_at / is_deleted / last_scan_result 等）
  7. 結果サマリを表示
```

---

## スコープ

### 実装対象

* `scanlog scan <path>`（ファイル / ディレクトリ）
* `scanlog watch add / list / remove / run`
* `scanlog recent [--limit N]`
* ClamAV実行（バッチ実行・チャンク分割）
* 出力パース（clamav_error 対応含む）
* SQLite保存
* 差分判定（watch run）

### 対象外（将来拡張）

* per-path の除外設定
* 並列処理
* 通知
* quarantine
* GUI
