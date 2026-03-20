# issue06

## Issue ID
issue06

## Title
collect / preview / approve / execute コマンド実装

## Purpose
定期スキャンフロー（collect → preview → approve → execute）を CLI から操作できるようにする

## Background
MVPの定期スキャン側のフローを完成させる。issue04 で scan コマンドは完成済み。

## Scope
- src/scanlog/cli.py に以下4コマンドを追加
  - `collect`: collector.collect() を呼び出し scan_plan(mode=scheduled_scan, status=draft) と plan_items を DB 保存。plan_id を表示。
  - `preview --latest` または `preview --plan-id <id>`: plan_items 一覧を表示（target_path, target_type, scan_mode, target_reason）
  - `approve --plan-id <id>`: scan_plan.status を approved に更新
  - `execute --plan-id <id>`: approved な plan の plan_items を使って scan を実行し結果を DB 保存

## Out of Scope
- 除外ルール適用
- 並列処理

## Editable Files
- src/scanlog/cli.py（4コマンドを追加）

## Do Not Edit
- src/scanlog/models.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
- issue04
- issue05

## Branch
feature/issue06-collect-execute

## Implementation Notes
- execute は再 collect をしない（plan_items をそのまま使用、SPEC.md 重要設計ルール）
- execute は scan_plan.status が approved でなければエラー終了
- execute 中は scan_plan.status を executing に更新、完了後 completed に更新
- repository.py に必要なクエリ関数があれば追記可（repository.py は Editable 扱い）
- preview はテーブル形式で表示（typer.echo でも可）

## Acceptance Criteria
- [ ] `uv run scanlog collect` で scan_plan と plan_items が DB 保存される
- [ ] `uv run scanlog preview --latest` で plan 内容が表示される
- [ ] `uv run scanlog approve --plan-id <id>` で status が approved になる
- [ ] `uv run scanlog execute --plan-id <id>` でスキャンが実行され結果が DB 保存される
- [ ] approved 以外の plan を execute しようとするとエラーになる

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
