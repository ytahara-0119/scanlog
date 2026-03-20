# issue09

## Issue ID
issue09

## Title
execute コマンド バッチ実行・途中再開対応

## Purpose
execute コマンドを SPEC.md のバッチ実行フローに対応させ、
途中再開（execution_status による未完了 item の再実行）を実現する

## Background
現在の execute は1 plan_item = 1 clamscan 実行であり、
バッチ管理・execution_status 管理・途中再開に未対応。
issue07・08 の成果物を組み合わせて execute を書き換える。

## Scope

### cli.py - execute コマンドの更新
以下のフローに変更する：

1. `execution_status = pending / failed` の plan_items のみ取得
2. file target を1バッチにまとめ `ScanBatch` を作成
3. directory target は1件ずつ `ScanBatch` を作成
4. 各バッチを処理:
   a. `batch.status = running`, `started_at` を記録しコミット
   b. file バッチ → `run_batch_scan()` / directory バッチ → `run_scan()`
   c. 出力パース
   d. `scan_results` / `scan_result_entries` を保存
   e. 対応する `plan_items.execution_status` を更新
      - 正常: `completed`
      - run_scan 例外: `failed`
      - clamav_error のみ: `skipped`
   f. `plan_items.batch_id`, `last_run_id` を更新
   g. `batch.status = completed / failed`, `finished_at` を記録しコミット
5. 全バッチ完了後 `scan_run`, `scan_plan` を更新

### cli.py - collect コマンドの更新
plan_item 作成時に `execution_status = "pending"` を明示的に設定する

### cli.py - scan コマンドの更新
手動スキャンでも execute と同じバッチ処理を使う

### repository.py への追記（Editable）
- `get_pending_plan_items(session, plan_id)` を追加
  - `execution_status IN ('pending', 'failed')` の items を返す

## Out of Scope
- バッチサイズの設定（MVP では全 file target を1バッチ）
- 並列処理

## Editable Files
- src/scanlog/cli.py
- src/scanlog/repository.py

## Do Not Edit
- src/scanlog/models.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
- issue07
- issue08

## Branch
feature/issue09-execute-batch-resume

## Implementation Notes
- バッチごとにセッションをコミットする（途中再開の安全性確保）
- file target が0件の場合は file バッチを作成しない
- execute 実行時に pending / failed が0件の場合は「すべて完了済み」と表示して終了
- scan コマンドは1 plan_item しかないため、file target → `run_batch_scan([path])`、directory target → `run_scan(path, "recursive")` で処理可能
- `result_status` の判定ロジックは `_calc_result_status()` を引き続き使用
- preview コマンドで `execution_status` も表示するよう更新する

## Acceptance Criteria
- [ ] `execute --plan-id <id>` が file target をバッチ実行（1コマンドで複数ファイル）する
- [ ] directory target は個別に実行される
- [ ] `scan_batches` テーブルに実行バッチが記録される（`command_line` 含む）
- [ ] `plan_items.execution_status` が completed / failed / skipped に更新される
- [ ] 途中で中断された plan を再度 `execute` すると completed 済み item がスキップされる
- [ ] pending / failed が0件の状態で execute すると「すべて完了済み」と表示される
- [ ] `preview` で `execution_status` が表示される

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
