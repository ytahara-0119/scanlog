# supervisor-runbook.md

## 目的
Supervisor が初回に行う作業を定義する。

## 指示
SPEC.md を仕様の正本として読み込み、MVPを実現するための issue を 5〜7 個に分割すること。

## 運用ルール
- あなたは supervisor として振る舞う
- review 役は置かない
- implementer 1〜2 へ必要に応じて委譲する
- issue はファイル競合が起きにくいように分割する
- issue 完了ごとに必ず人間確認で停止する
- 人間の確認が出るまで次の issue に進まない
- 最初に uv / SQLite / Typer / SQLAlchemy の環境準備を含める
- issue ごとに branch 名、編集可能ファイル、依存関係、完了条件を定義する

## 出力後の動作
- issue 作成後、実装は開始せず停止する
- 人間が確認後、「issue01を開始して」と指示されたら実装を開始する

## 出力先
- issues/issue01.md 以降
- docs/workflow.md
- 必要なら CLAUDE.md の追記案