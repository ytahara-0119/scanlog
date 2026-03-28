# issue13

## Issue ID
issue13

## Title
watch run コマンド実装（差分スキャン + 除外ポリシー + file_inventory 更新）

## Purpose
`scanlog watch run` コマンドを実装する。
enabled な watch_paths を巡回し、差分ありファイルのみをスキャンして結果を DB に保存する。
定期監視向けの重い依存ディレクトリ除外ポリシーをここで適用する。

## Background
issue12 で差分判定ロジックが実装された。
このコマンドは watcher.py の関数を呼び出し、差分ありファイルに対して
既存の execute バッチ処理（issue09）を再利用してスキャンを実行する。
手動スキャン（scan コマンド）と同じエンジンを使うことで実装の重複を避ける。

## Scope

### watcher.py への追記
- `DEFAULT_EXCLUDE_DIRS: set[str]` を定数として定義する
  ```python
  DEFAULT_EXCLUDE_DIRS = {
      "node_modules", ".venv", "vendor", "target",
      "build", "dist", ".git"
  }
  ```
  - この除外は「安全だから」ではなく「監視コスト削減のためのポリシー」であることをコメントで明記する

### cli.py - `watch run` コマンドを追加

処理フロー:

1. watch_paths から enabled = true の全 path を取得する
   - 0件の場合は「監視対象が登録されていません」を表示して終了
2. 各 watch_path に対して以下を実行する:
   a. `scan_directory(path, DEFAULT_EXCLUDE_DIRS)` でファイルリストを取得
   b. `detect_changes(session, watch_path, files)` でスキャン対象を特定
3. 全 watch_paths の対象ファイルをまとめる
   - スキャン対象が0件の場合は「変更ファイルなし」を表示して終了（スキャン不要）
4. scan_plan を作成する（mode = 'watch_scan', status = 'approved'）
5. plan_items を作成する（target_reason = 'watch_diff'）
6. execute と同じバッチ処理を呼び出してスキャンを実行する
   - 既存の `_run_execute(session, plan)` 相当の処理を共有する
7. 完了後、`update_inventory()` を呼び出して file_inventory を更新する
8. 結果サマリを表示する（スキャン件数、clean/infected/error の内訳）

### cli.py - execute 処理の共通化（必要な場合）
- `scan` コマンドと `execute` コマンドで共有している実行ロジックが関数化されていない場合、
  `_run_execute(session, plan_id)` のような内部関数に切り出して watch run から呼べるようにする

## Out of Scope
- per-path の除外設定（watch_paths テーブルへの追加は将来対応）
- 除外リストのカスタマイズ（設定ファイル対応は将来対応）
- watch_paths の enabled/disabled 切り替えコマンド（将来対応）

## Editable Files
- src/scanlog/cli.py
- src/scanlog/watcher.py

## Do Not Edit
- src/scanlog/models.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py
- src/scanlog/repository.py（追記が必要な場合のみ例外）

## Dependencies
- issue11
- issue12

## Branch
feature/issue13-watch-run

## Implementation Notes
- `DEFAULT_EXCLUDE_DIRS` の除外はディレクトリ名の一致で判定する（絶対パスでなくディレクトリ名）
- 複数 watch_paths の対象ファイルをまとめて1つの scan_plan に入れる（watch_path ごとに plan を作らない）
- watch run のスキャン対象はすべて file target（individual file）として扱う
  - directory target は watch run では生成しない（ファイル単位で差分管理するため）
- `update_inventory()` の呼び出しはスキャン完了後に1回まとめて行う
- cron などから呼ばれることを想定し、エラー時は exit code 1 で終了する

## Acceptance Criteria
- [ ] `scanlog watch run` が enabled な全 watch_path を対象に実行される
- [ ] 差分なしファイルはスキャンされない（「変更ファイルなし」で正常終了）
- [ ] DEFAULT_EXCLUDE_DIRS に含まれるディレクトリ（例: node_modules）は走査されない
- [ ] スキャン結果が scan_plans / scan_results に記録される（mode = 'watch_scan'）
- [ ] スキャン完了後に file_inventory が更新される（last_seen_at, last_scan_result）
- [ ] 走査で見つからなかったファイルは file_inventory で is_deleted = true になる
- [ ] 手動スキャン（scan コマンド）では DEFAULT_EXCLUDE_DIRS は適用されない
- [ ] watch_paths が0件の場合は適切なメッセージを表示して終了する
- [ ] スキャン対象が0件（差分なし）の場合は scan_plan が作成されない

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
