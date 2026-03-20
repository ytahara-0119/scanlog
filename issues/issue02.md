# issue02

## Issue ID
issue02

## Title
DBモデル定義とリポジトリ基盤（models.py / repository.py）

## Purpose
SPEC.md のDB設計に基づき SQLAlchemy ORM モデルと DB 初期化処理を実装する

## Background
scan・collect・execute 全コマンドが DB に依存する。モデルが先に必要。

## Scope
- src/scanlog/models.py に全テーブルの ORM モデルを定義
  - ScanPlan, PlanItem, ScanRun, ScanResult, ScanResultEntry
- src/scanlog/repository.py に DB セッション管理と init_db() を実装
- init_db() は CLI 起動時に呼び出せるようにする（cli.py からは issue04 で追加）

## Out of Scope
- CLI コマンドへの組み込み（issue04以降）
- クエリメソッドの実装（必要なものは各 issue で追加）

## Editable Files
- src/scanlog/models.py（新規作成）
- src/scanlog/repository.py（新規作成）

## Do Not Edit
- src/scanlog/cli.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
- issue01

## Branch
feature/issue02-db-models

## Implementation Notes
- SQLAlchemy の declarative_base() を使用
- Relationship は外部キーのみ定義し、lazy loading は使わない
- plan_items.excluded_by_user と exclude_reason は将来用として定義するが NULL 可
- scan_plans.status: draft / approved / executing / completed / failed
- repository.py の get_session() はコンテキストマネージャで実装

## Acceptance Criteria
- [ ] 5テーブル全ての ORM クラスが定義されている
- [ ] init_db() を呼ぶと SQLite にテーブルが生成される
- [ ] SPEC.md のカラム定義と一致している

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
