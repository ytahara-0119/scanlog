# issue03

## Issue ID
issue03

## Title
ClamAV実行とパース（scanner.py / parser.py）

## Purpose
subprocess 経由で ClamAV を呼び出し、出力を構造化データにパースする

## Background
scan コマンドと execute コマンドの核心処理。CLI から独立させて単体テスト可能にする。

## Scope
- src/scanlog/scanner.py に run_scan(target_path, scan_mode) を実装
  - scan_mode = "single" → `clamscan --no-summary <file>`
  - scan_mode = "recursive" → `clamscan -r --no-summary <directory>`
  - 戻り値: (stdout: str, exit_code: int)
- src/scanlog/parser.py に parse_output(raw_output: str) を実装
  - 各行を解析して {scanned_path, entry_status, virus_name, raw_line} のリストを返す
  - OK → clean, FOUND → infected, その他 → error

## Out of Scope
- DB保存（issue04で統合）
- CLI コマンドへの組み込み（issue04）

## Editable Files
- src/scanlog/scanner.py（新規作成）
- src/scanlog/parser.py（新規作成）

## Do Not Edit
- src/scanlog/cli.py
- src/scanlog/models.py
- src/scanlog/repository.py
- src/scanlog/collector.py

## Dependencies
- issue01

## Branch
feature/issue03-scanner-parser

## Implementation Notes
- scanner.py は subprocess.run() を使用、timeout=300 秒
- ClamAV が存在しない場合は RuntimeError を送出
- parser.py は行単位でパース。形式: `<path>: <status>` または `<path>: <VirusName> FOUND`
- 空行・summary 行（`----------`以降）は無視する

## Acceptance Criteria
- [ ] run_scan("some/file.txt", "single") を呼ぶと (stdout, exit_code) が返る
- [ ] parse_output() が OK/FOUND/ERROR 行を正しく分類する
- [ ] raw_output（stdout全体）が保持される

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
