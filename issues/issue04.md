# issue04

## Issue ID
issue04

## Title
scan コマンド（手動スキャン エンドツーエンド）

## Purpose
`scanlog scan <path>` で手動スキャンが一通り動作するようにする

## Background
MVPの最重要コマンド。DB保存まで含めたエンドツーエンドを実装する。

## Scope
- src/scanlog/cli.py に `scan` コマンドを実装
  - path がファイル → target_type=file, scan_mode=single
  - path がディレクトリ → target_type=directory, scan_mode=recursive
  - 内部処理: scan_plan作成(mode=manual_scan) → plan_item作成 → approved → scan_run作成 → scanner実行 → parser → scan_result/scan_result_entries保存
- CLI 起動時に init_db() を呼び出す
- 結果をターミナルに表示（clean/infected/error）

## Out of Scope
- collect / preview / approve / execute コマンド（issue05以降）
- 除外処理

## Editable Files
- src/scanlog/cli.py（scan コマンドと init_db 呼び出しを追加）

## Do Not Edit
- src/scanlog/models.py
- src/scanlog/repository.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
- issue02
- issue03

## Branch
feature/issue04-scan-command

## Implementation Notes
- plan_item.selected = True, excluded_by_user = False で作成
- scan_run.status は "completed" または "failed" で更新
- scan_result.result_status は entries の中に infected があれば "infected", 全 clean なら "clean", エラーあれば "error"
- typer.echo() で結果サマリを表示
- repository.py に必要なクエリ関数があれば追記可

## Acceptance Criteria
- [ ] `uv run scanlog scan <file>` が動作し結果が表示される
- [ ] `uv run scanlog scan <dir>` が動作し結果が表示される
- [ ] scan_plans / plan_items / scan_runs / scan_results / scan_result_entries が DB に保存される
- [ ] infected ファイルがあれば画面に表示される

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
