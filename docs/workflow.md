# docs/workflow.md

## 基本フロー

1. 人間が Supervisor に指示する
2. Supervisor が issue を作成する
3. issue ごとに branch を定義する
4. Implementer が実装する
5. 完了後、人間確認で停止
6. 承認後、次の issue に進む

---

## ブランチ命名

feature/issueXX-<short-name>

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