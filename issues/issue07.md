# issue07

## Issue ID
issue07

## Title
DBモデル拡張 - scan_batches テーブル追加・plan_items / scan_results カラム追加

## Purpose
SPEC.md 更新に伴い、バッチ実行・途中再開に必要な DB スキーマを追加する

## Background
既存の scan_batches テーブルは存在しない。
plan_items に execution_status / batch_id / last_run_id が存在しない。
scan_results に batch_id が存在しない。
これらは issue08・issue09 の実装前提となる。

## Scope

### models.py
- `ScanBatch` ORM クラスを新規追加
  - id, run_id (FK→scan_runs), batch_type, command_line, status, started_at, finished_at
- `PlanItem` に以下カラムを追加
  - `batch_id`: INTEGER, FK → scan_batches.id, nullable
  - `execution_status`: TEXT, nullable, デフォルト `"pending"`
  - `last_run_id`: INTEGER, FK → scan_runs.id, nullable
- `ScanResult` に以下カラムを追加
  - `batch_id`: INTEGER, FK → scan_batches.id, nullable

### repository.py
- `migrate_db()` 関数を追加
  - 既存 SQLite に不足カラム・テーブルを追加する（ALTER TABLE）
  - `init_db()` の後に呼び出し可能にする
- `init_db()` は `migrate_db()` を内部で呼ぶように更新

### cli.py
- `main()` コールバックの `init_db()` 呼び出しを `init_db()` のみ維持（migrate_db は init_db 内で呼ぶ）

## Out of Scope
- バッチ実行ロジック（issue08）
- execute コマンドの更新（issue09）

## Editable Files
- src/scanlog/models.py
- src/scanlog/repository.py

## Do Not Edit
- src/scanlog/cli.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
- issue02（完了済み）

## Branch
feature/issue07-db-batch-schema

## Implementation Notes
- `migrate_db()` は `ALTER TABLE IF NOT EXISTS` 相当の処理を行う
  - SQLite は `ALTER TABLE ADD COLUMN` をサポートするが `IF NOT EXISTS` は非対応
  - 既存カラム確認は `PRAGMA table_info(<table>)` で行う
  - カラムが既に存在する場合はスキップ（冪等性を保つ）
- `ScanBatch.status` の値: pending / running / completed / failed
- `PlanItem.execution_status` の値: pending / completed / failed / skipped
- collect コマンドで plan_item を作成する際は `execution_status = "pending"` をデフォルトとする
  （既存の collect コマンドは issue09 で更新するため、ここでは DB 側のデフォルト値のみ設定）

## Acceptance Criteria
- [ ] `ScanBatch` ORM クラスが定義されている（7カラム）
- [ ] `PlanItem` に `batch_id` / `execution_status` / `last_run_id` が追加されている
- [ ] `ScanResult` に `batch_id` が追加されている
- [ ] 既存 DB に対して `init_db()` を呼ぶと不足カラム・テーブルが追加される（既存データは保持）
- [ ] `init_db()` を2回呼んでもエラーにならない（冪等性）

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
