# issue05

## Issue ID
issue05

## Title
collector 実装（対象抽出ロジック）

## Purpose
カレントディレクトリ配下の当日作成/更新ファイルを収集し、target 種別を判定して plan_items を生成する

## Background
定期スキャンフロー（collect → preview → approve → execute）の起点。
scanner とは独立した処理として実装する。

## Scope
- src/scanlog/collector.py に collect(base_path: str) を実装
  - 当日作成/更新ファイルを探索
  - ファイル → file target（単体ファイルかアーカイブ系）
  - ディレクトリ → directory target（プロジェクトルート判定含む）
  - 戻り値: List[dict] （target_path, target_type, scan_mode, target_reason）
- プロジェクトルート判定（.git, pyproject.toml 等のマーカーファイルを確認）

## Out of Scope
- DB 保存（issue06 で cli.py から呼び出す）
- collect コマンドの CLI 定義（issue06）

## Editable Files
- src/scanlog/collector.py（新規作成）

## Do Not Edit
- src/scanlog/cli.py
- src/scanlog/models.py
- src/scanlog/repository.py
- src/scanlog/scanner.py
- src/scanlog/parser.py

## Dependencies
- issue01

## Branch
feature/issue05-collector

## Implementation Notes
- os.walk() または pathlib.Path.rglob() で探索
- 当日判定: file mtime または ctime が今日の日付
- アーカイブ系拡張子: .zip, .tar.gz, .dmg, .pkg, .exe, .jar
- プロジェクトルートマーカー: .git, package.json, pyproject.toml, requirements.txt, Pipfile, poetry.lock, Cargo.toml, go.mod, Gemfile, pom.xml, build.gradle, Makefile
- マーカーを含むディレクトリは directory target (scan_mode=recursive)
- シンボリックリンクは追わない

## Acceptance Criteria
- [ ] collect() がターゲットリストを返す
- [ ] プロジェクトルートが directory target になる
- [ ] アーカイブ系ファイルが file target になる
- [ ] target_reason が設定されている

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
