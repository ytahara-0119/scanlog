# issue11

## Issue ID
issue11

## Title
watch_paths 管理コマンド実装（watch add / list / remove）

## Purpose
監視対象 path を登録・一覧・削除できる CLI コマンドを実装する。
`watch run` の前提として、監視対象 path を DB で管理できる状態にする。

## Background
issue10 で watch_paths テーブルが追加された。
このテーブルを操作する CLI コマンドと repository 関数を実装する。
watch run（issue13）はここで登録された path を使って動作する。

## Scope

### cli.py
- `watch` サブコマンドグループを追加（`typer.Typer()` の sub-app として定義）
- `scanlog watch add <path>` コマンドを実装
  - 絶対パスに正規化して登録する
  - 既に登録済みの場合は enabled = true に更新する（上書き）
  - 登録した path を表示して終了
- `scanlog watch list` コマンドを実装
  - 登録済みの watch_paths を一覧表示する
  - 表示項目: id, path, enabled, created_at
  - 登録なしの場合は「登録された監視対象はありません」を表示
- `scanlog watch remove <path>` コマンドを実装
  - 指定された path を watch_paths から削除する
  - file_inventory のレコードは保持する（履歴として残す）
  - 存在しない path の場合はエラーメッセージを表示して終了

### repository.py
- `add_watch_path(session, path: str) -> WatchPath` を追加
  - 既存レコードがある場合は enabled = True に更新
- `list_watch_paths(session) -> List[WatchPath]` を追加
- `remove_watch_path(session, path: str) -> bool` を追加
  - 削除成功で True、未登録で False を返す
- `get_watch_path_by_path(session, path: str) -> WatchPath | None` を追加

## Out of Scope
- watch run（issue13）
- file_inventory の操作
- 差分判定（issue12）

## Editable Files
- src/scanlog/cli.py
- src/scanlog/repository.py

## Do Not Edit
- src/scanlog/models.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py
- src/scanlog/watcher.py

## Dependencies
- issue10

## Branch
feature/issue11-watch-paths-commands

## Implementation Notes
- path の正規化: `str(Path(path).resolve())` を使う
- `watch` サブコマンドグループは `cli.py` 内で `watch_app = typer.Typer()` として定義し、`app.add_typer(watch_app, name="watch")` で登録する
- `watch list` の出力は tabular 形式でなくても可（シンプルな行形式で十分）
- `watch remove` は file_inventory を削除しない（SPEC の設計方針）
- enabled フラグは MVP では常に true として扱う（無効化コマンドは将来対応）

## Acceptance Criteria
- [ ] `scanlog watch add <path>` で watch_paths に登録される
- [ ] 同じ path を再登録すると enabled = true に更新される（エラーにならない）
- [ ] `scanlog watch list` で登録済み path 一覧が表示される
- [ ] `scanlog watch remove <path>` で watch_paths から削除される
- [ ] remove 後も file_inventory のレコードは残る
- [ ] 存在しない path を remove しようとするとエラーメッセージが表示される
- [ ] `scanlog watch --help` でサブコマンド一覧が表示される

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
