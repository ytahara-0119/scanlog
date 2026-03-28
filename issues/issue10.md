# issue10

## Issue ID
issue10

## Title
DBモデル拡張 - watch_paths / file_inventory テーブル追加

## Purpose
監視機能（watch run）の基盤となる DB スキーマを追加する。
watch_paths は監視対象 path の登録管理に、file_inventory は差分判定の基準データに使用する。

## Background
issue09 完了時点で手動スキャン・定期スキャンのスキーマは完成している。
監視機能を追加するにあたり、2つの新テーブルが必要となる。
これは issue11 以降の watch コマンド実装の前提となる。

## Scope

### models.py
- `WatchPath` ORM クラスを新規追加
  - id, path (UNIQUE), enabled (default True), created_at, updated_at
- `FileInventory` ORM クラスを新規追加
  - id, watch_path_id (FK→watch_paths.id), file_path (UNIQUE)
  - file_size, mtime, sha256 (nullable)
  - first_seen_at, last_seen_at, last_scanned_at, last_scan_result (nullable)
  - is_deleted (default False)

### repository.py
- `migrate_db()` を拡張し、上記2テーブルを `CREATE TABLE IF NOT EXISTS` で追加する
  - 既存の migrate_db() パターン（冪等性）に合わせる
  - `init_db()` 呼び出しで自動的に新テーブルも作成される

### scan_plans.mode への対応
- `ScanPlan.mode` のコメントまたは docstring に `watch_scan` を追記する（値自体はテキスト型なので schema 変更不要）

## Out of Scope
- watch コマンドの CLI 実装（issue11）
- 差分判定ロジック（issue12）
- watch run 実装（issue13）

## Editable Files
- src/scanlog/models.py
- src/scanlog/repository.py

## Do Not Edit
- src/scanlog/cli.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py
- src/scanlog/watcher.py（まだ存在しない）

## Dependencies
- issue09（完了済み）

## Branch
feature/issue10-watch-db-schema

## Implementation Notes
- `WatchPath.updated_at` は SQLAlchemy の `onupdate` で自動更新する
- `FileInventory.mtime` は Python の `os.stat().st_mtime`（float）を DATETIME として保存する
- `FileInventory.sha256` は nullable。差分なし判定の場合は更新しない
- `FileInventory.last_scan_result` の値: clean / infected / error / null
- `FileInventory.is_deleted` は論理削除フラグ。watch_run で走査対象から消えた場合に true にする
- 既存 DB への追加は `CREATE TABLE IF NOT EXISTS` で冪等に行う
- `init_db()` を2回呼んでもエラーにならないことを確認する

## Acceptance Criteria
- [ ] `WatchPath` ORM クラスが定義されている（id, path, enabled, created_at, updated_at）
- [ ] `FileInventory` ORM クラスが定義されている（全カラム）
- [ ] `init_db()` を実行すると watch_paths / file_inventory テーブルが作成される
- [ ] `init_db()` を2回呼んでもエラーにならない（冪等性）
- [ ] 既存の scan_plans / plan_items / scan_results 等のテーブルは影響を受けない

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
