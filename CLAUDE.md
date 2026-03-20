# CLAUDE.md

## このプロジェクトについて
このプロジェクトは ClamAV を利用した Python CLI スキャンツールである。
仕様の正本は SPEC.md とする。

## 最重要ルール
- 実装・設計判断は必ず SPEC.md を参照する
- 仕様変更が必要な場合は、実装前に変更案を明示する
- MVPを優先し、過剰な抽象化や将来機能の先回り実装を避ける
- 既存コードの変更は最小限にする
- 1つのissueでは、原則として指定された編集対象ファイルのみ変更する

## 開発方針
- Python は uv で管理する
- DB は SQLite を使用する
- ORM は SQLAlchemy を使用する
- CLI は Typer を使用する
- ClamAV は subprocess 経由で呼び出す

## エージェント運用方針
- 監督エージェントは issue 分割、依存関係整理、完了判定を担当する
- 作業エージェントは単一 issue を実装する
- 作業エージェントは、issue に記載された編集許可ファイル以外を原則変更しない
- issue 間で変更ファイルが衝突しないようにする

## issue のルール
各 issue には以下を含めること
- 目的
- 対象範囲
- 編集可能ファイル
- 変更禁止ファイル
- 依存issue
- 完了条件
- 実装メモ

## 実装時の注意
- raw_output は必ず保存する
- collect と execute の責務を混ぜない
- scan 処理は collector に依存させない
- manual scan を先に完成させる
- まず動くMVPを作る

## 優先実装順
1. scan コマンド
2. scanner + parser
3. repository + models
4. directory 対応
5. plan 構造
6. collect
7. preview / approve / execute