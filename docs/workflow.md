# docs/workflow.md

## Issue 一覧と状態

| Issue   | タイトル                          | 依存        | 状態    |
| ------- | --------------------------------- | ----------- | ------- |
| issue01 | 環境構築（uv / Typer / SQLAlchemy）| なし        | done（PR未） |
| issue02 | DBモデル定義とリポジトリ基盤       | issue01     | done（PR未） |
| issue03 | ClamAV実行とパース                 | issue01     | done（PR未） |
| issue04 | scan コマンド（手動スキャン）      | issue02,03  | done（PR#1） |
| issue05 | collector 実装（対象抽出ロジック） | issue04     | pending      |
| issue06 | collect/preview/approve/execute   | issue04,05  | pending      |

---

## 基本フロー

1. 人間が Supervisor に指示する
2. Supervisor が issue を作成する
3. issue ごとに branch を定義する
4. Implementer が実装する（ブランチは必ず最新 main から作成）
5. 実装完了後に Pull Request を作成する
6. 人間が PR をレビュー・マージする
7. main を最新に更新してから次の issue に進む
8. 完了後、人間確認で停止

---

## ブランチ命名

feature/issueXX-<short-name>

---

## PR 作成ルール

- issue 実装完了後に必ず `gh pr create` で PR を作成する
- base ブランチは常に `main`
- PR タイトルは `feat(issueXX): <タイトル>` 形式
- **PR 作成前に Test Plan の全項目を実行し、全て通過していることを確認する**
- Test Plan に未実施・失敗項目がある場合は PR を作成しない
- 次の issue に着手する前に依存 issue の PR が main にマージ済みであること

---

## issue 分割ルール

- 1 issue = 1責務
- 原則 1〜2ファイルのみ変更
- 横断変更は禁止

---

## 競合回避ルール

- 同一ファイルを複数 issue で編集しない
- 共通変更は最後にまとめる

---

## MVP優先

- scan（manual）を最優先
- collect / execute は後回し
- 除外・最適化は後回し

---

## 人間の役割

- issue 完了時の確認のみ行う
- 設計の方向修正を行う
- バグ・仕様ズレの最終判断を行う