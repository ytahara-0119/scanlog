# issue16: models.py - DBスキーマ簡素化

## 概要

`collect → plan → execute` フロー廃止に伴い、不要なテーブルを削除し、
`scan_results` を直接スキャン結果を持つシンプルな形に変更する。

## ブランチ名

`refactor/simplify-models`

## Editable Files

- `src/scanlog/models.py`

## 変更内容

### 削除するクラス

- `ScanPlan`（scan_plans テーブル）
- `PlanItem`（plan_items テーブル）
- `ScanRun`（scan_runs テーブル）
- `ScanBatch`（scan_batches テーブル）

### 変更するクラス：ScanResult

削除するカラム：
- `run_id`（FK → scan_runs）
- `batch_id`（FK → scan_batches）
- `plan_item_id`（FK → plan_items）

追加するカラム：
- `mode: TEXT` — `manual` / `watch`
- `scanned_at: DATETIME` — スキャン実行日時

変更後のカラム一覧：
| カラム        | 型       | 説明                     |
| ------------- | -------- | ------------------------ |
| id            | INTEGER  | PK                       |
| mode          | TEXT     | manual / watch           |
| scanned_at    | DATETIME | スキャン実行日時         |
| target_path   | TEXT     | スキャン対象パス         |
| target_type   | TEXT     | file / directory         |
| result_status | TEXT     | clean / infected / error |
| raw_output    | TEXT     | clamscan stdout 全体     |
| exit_code     | INTEGER  |                          |

### 維持するクラス（変更なし）

- `ScanResultEntry`（scan_result_entries テーブル）
  - `scan_result_id` FK は維持
- `WatchPath`（watch_paths テーブル）
- `FileInventory`（file_inventory テーブル）

## Acceptance Criteria

- [ ] models.py に ScanPlan / PlanItem / ScanRun / ScanBatch クラスが存在しない
- [ ] ScanResult クラスが mode / scanned_at カラムを持つ
- [ ] ScanResult クラスに run_id / batch_id / plan_item_id が存在しない
- [ ] ScanResultEntry / WatchPath / FileInventory クラスが維持されている
- [ ] `uv run python -c "from scanlog.models import ScanResult, ScanResultEntry, WatchPath, FileInventory; print('OK')"` が通る

## Definition of Done

- [ ] Acceptance Criteria 全項目を確認済み
- [ ] PR を作成済み
