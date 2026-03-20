# CLAUDE.md

## プロジェクト概要
本プロジェクトは ClamAV を利用した Python CLI スキャンツールである。
仕様の正本は SPEC.md とする。

---

## 最重要ルール

- 仕様の正本は SPEC.md とする
- 実装・設計判断は必ず SPEC.md を参照する
- 仕様変更が必要な場合は、実装前に変更案を提示する
- MVPを最優先とし、過剰な抽象化を避ける
- 既存コードの変更は最小限にする
- issueごとの変更範囲を厳守する

---

## 開発方針

- Python は uv で管理する
- DB は SQLite を使用する
- ORM は SQLAlchemy を使用する
- CLI は Typer を使用する
- ClamAV は subprocess 経由で呼び出す

---

## エージェント運用方針

このプロジェクトは以下の構成で進める：

- Supervisor（監督）
- Implementer（作業エージェント 1〜2）

人間は Supervisor にのみ指示を出す。

---

## Supervisor の責務

- SPEC.md を読み、MVPを達成するための issue を分割する
- issueごとの依存関係を整理する
- 各 issue に対して branch 名、編集対象、完了条件を定義する
- 実装順を決定する
- Implementer に issue を委譲する
- issue 完了後に必ず人間確認で停止する
- 人間の承認後に次の issue に進む
- 最終的に進捗レポートを作成する

---

## Implementer の責務

- 指定された issue のみを実装する
- issue に記載された Editable Files を中心に変更する
- MVPに必要な最小実装を行う
- 完了条件を満たす
- 実装内容を簡潔に報告する

---

## 実行ルール（重要）

Supervisor は以下の流れで進行すること：

1. SPEC.md を読む
2. issue を 5〜7 個に分割する
3. issues/issueXX.md を作成する
4. docs/workflow.md を必要に応じて更新する
5. 依存関係に従って最初の issue を選択する
6. Implementer に実装を委譲する
7. 完了後、必ず停止して人間確認を求める
8. 承認後、次の issue に進む

---

## 禁止事項

- 複数 issue で同一ファイルを同時に編集させること
- MVP外の機能を先に実装すること
- issue を曖昧なまま作成すること
- 人間確認なしで連続実行すること

---

## 実装優先順位

1. 環境構築（uv / SQLite / Typer / SQLAlchemy）
2. scan（manual）
3. scanner + parser
4. DB保存
5. directory対応
6. plan構造
7. collect
8. preview / approve / execute

---

## 成功条件

- issue単位で安全に実装が進む
- ファイル競合が発生しない
- 人間は最終確認のみ行う
- MVPが段階的に完成する