# docs/workflow.md

## ブランチ命名
- feature/issueXX-<short-name>

## 基本フロー
1. 監督が issue を作成する
2. issue ごとに branch を切る
3. 作業エージェントが issue を実装する
4. 完了したら内容を報告する
5. 監督が完了判定する

## issue 分割ルール
- 1 issue = 1つの小さな責務
- 原則として主要変更ファイルは 1〜2個まで
- 変更範囲が広い場合は再分割する

## 競合回避ルール
- 同じ主要ファイルを複数 issue で編集しない
- 横断的変更は最後の統合 issue に寄せる

## MVP優先ルール
- まず scan コマンドを完成させる
- collect / execute は後続
- 除外や quarantine は後回し