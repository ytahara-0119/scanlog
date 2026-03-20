# issue01

## Issue ID
issue01

## Title
環境構築（uv / pyproject.toml / Typer / SQLAlchemy）

## Purpose
プロジェクトの Python 環境を整備し、CLIの骨格と設定管理を実装する

## Background
後続の全 issue が依存する基盤。ここがないと実装できない。

## Scope
- uv で pyproject.toml を初期化
- 依存パッケージを追加（typer, sqlalchemy, click）
- src/scanlog/ パッケージ構成を作成
- src/scanlog/cli.py に Typer アプリ骨格を実装（コマンド定義なし）
- src/scanlog/config.py に DB パス等の設定を実装
- src/scanlog/__init__.py を作成

## Out of Scope
- DB テーブル作成（issue02）
- コマンド実装（issue04以降）

## Editable Files
- pyproject.toml（新規作成）
- src/scanlog/__init__.py（新規作成）
- src/scanlog/cli.py（骨格のみ）
- src/scanlog/config.py（新規作成）

## Do Not Edit
- src/scanlog/models.py
- src/scanlog/repository.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
なし

## Branch
feature/issue01-env-setup

## Implementation Notes
- uv init で pyproject.toml を生成
- `uv add typer sqlalchemy` を実行
- DB パスはデフォルト `~/.scanlog/scanlog.db` とする
- cli.py は `app = typer.Typer()` と `if __name__ == "__main__": app()` のみ
- pyproject.toml の scripts に `scanlog = "scanlog.cli:app"` を定義

## Acceptance Criteria
- [ ] `uv run scanlog --help` が動作する
- [ ] pyproject.toml に typer, sqlalchemy が記載されている
- [ ] config.py に DB_PATH が定義されている
- [ ] src/scanlog/__init__.py が存在する

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
