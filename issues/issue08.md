# issue08

## Issue ID
issue08

## Title
scanner.py バッチ実行対応 - 複数 file target を1コマンドでスキャン

## Purpose
SPEC.md の「file target は複数ファイルをまとめて clamscan に渡す」を実装する

## Background
現在の `run_scan()` は1ターゲット = 1コマンド実行。
file target が大量にある場合、プロセス起動コストが高くなる。
バッチ実行により複数ファイルを1回の clamscan 呼び出しで処理する。

## Scope

### scanner.py
- `run_batch_scan(file_paths: list[str]) -> tuple[str, int, str]` を新規追加
  - 複数ファイルをまとめて `clamscan --no-summary file1 file2 ...` で実行
  - 戻り値: (stdout, exit_code, command_line)
  - `command_line` は実際に実行したコマンド文字列（DB 保存用）
- 既存の `run_scan()` は後方互換のため維持する（directory target で引き続き使用）

## Out of Scope
- execute コマンドへの組み込み（issue09）
- DB 保存（issue09）

## Editable Files
- src/scanlog/scanner.py

## Do Not Edit
- src/scanlog/cli.py
- src/scanlog/models.py
- src/scanlog/repository.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
- issue07

## Branch
feature/issue08-batch-scanner

## Implementation Notes
- `run_batch_scan()` の command_line は `" ".join(cmd)` で生成
- file_paths が空リストの場合は `("", 0, "")` を返す
- clamscan が存在しない場合は RuntimeError を送出（run_scan と同様）
- timeout は 600 秒（ファイルが多い場合を考慮）
- directory target は引き続き `run_scan()` を使用する

## Acceptance Criteria
- [ ] `run_batch_scan(["file1.zip", "file2.dmg"])` を呼ぶと `(stdout, exit_code, command_line)` が返る
- [ ] `command_line` に実際のコマンド文字列が含まれている
- [ ] 空リストを渡しても正常に動作する
- [ ] ClamAV が存在しない場合に RuntimeError が発生する
- [ ] 既存の `run_scan()` の動作が変わらない

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
