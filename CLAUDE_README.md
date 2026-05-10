# Claude Code エージェント開発フレームワーク

このリポジトリには **Supervisor / Implementer パターン** を使った Claude Code 向け開発フレームワークが含まれています。
新しいプロジェクトへのテンプレートとして再利用することを想定して設計されています。

---

## 目次

1. [フレームワーク概要](#1-フレームワーク概要)
2. [ファイル構成と役割](#2-ファイル構成と役割)
3. [新プロジェクトへの導入手順](#3-新プロジェクトへの導入手順)
4. [Claude への依頼方法](#4-claude-への依頼方法)
5. [開発フロー詳細](#5-開発フロー詳細)
6. [並列実行フロー](#6-並列実行フロー)
7. [スクリプトリファレンス](#7-スクリプトリファレンス)
8. [よくある質問](#8-よくある質問)

---

## 1. フレームワーク概要

### 目的

Claude Code を使って大きな開発タスクを **安全・段階的・並列** に進めるための仕組みです。

- 人間は方向性の確認だけを行い、実装作業は Claude に委任する
- 1 issue = 1 責務の粒度で issue を管理し、ファイル競合を防ぐ
- 依存関係のない issue は git worktree を使って並列実装し、開発速度を上げる

### 登場人物

| 役割 | 誰が担うか | 主な責務 |
|------|-----------|---------|
| **Human** | あなた | Supervisor への指示、PR レビュー・マージ、方向修正 |
| **Supervisor** | Claude（監督役） | issue 分割・依存整理・Implementer への委譲・進捗管理 |
| **Implementer** | Claude（作業役） | issue の実装・PR 作成・完了報告 |

Human は Supervisor にのみ指示を出す。Supervisor が Implementer を管理する。

---

## 2. ファイル構成と役割

```
.
├── CLAUDE.md                    # Claude Code がセッション開始時に読む設定ファイル
├── CLAUDE_README.md             # このファイル（人間向けフレームワーク説明書）
├── SPEC.md                      # 仕様書（プロジェクト固有）
│
├── agents/
│   ├── supervisor.md            # Supervisor エージェントへの指示書
│   └── implementer.md           # Implementer エージェントへの指示書
│
├── issues/
│   ├── issue-template.md        # issue 作成テンプレート
│   ├── issue01.md               # 各 issue の定義（Supervisor が作成）
│   └── ...
│
├── docs/
│   └── workflow.md              # issue 一覧と状態管理表（Supervisor が更新）
│
└── scripts/
    ├── parallel-check.sh        # 並列実行可能 issue グループを判定
    └── workflow-status.sh       # issue 進捗ダッシュボードを表示
```

### 各ファイルの詳細

#### `CLAUDE.md`

Claude Code がプロジェクトのルートに置かれた `CLAUDE.md` を自動的に読み込みます。
ここにエージェントの運用ルール・禁止事項・フローを記述します。

- **プロジェクト固有の箇所（Human が差し替える）**: プロジェクト概要・技術スタック・実装優先順位（`[要差し替え]` でマーク済み）
- **汎用箇所（差し替え不要）**: Supervisor/Implementer の責務・並列実行ルール・ブランチ運用ルール

#### `agents/supervisor.md`

Supervisor 役の Claude に渡す指示書です。
「どの issue を並列化できるか判断し、Implementer を起動する」という判断ロジックが書かれています。

- **プロジェクト固有の箇所（Human が差し替える）**: 設計ルール（`[要差し替え]` でマーク済み）
- **汎用箇所（差し替え不要）**: issue 分割ルール・並列実行フロー・禁止事項

#### `agents/implementer.md`

Implementer 役の Claude に渡す指示書です。
「指定された issue だけを最小変更で実装し PR を作る」という作業ルールが書かれています。
内容はほぼ汎用的で差し替え不要です。

#### `issues/issue-template.md`

issue を作るときのテンプレートです。Supervisor が各 issue 定義ファイルを作る際に参照します。
**重要な項目:**

| セクション | 役割 |
|-----------|------|
| `Editable Files` | このファイルを変更して良いファイルの一覧。並列化の可否判定に使われる |
| `Do Not Edit` | 触ってはいけないファイルの一覧 |
| `Dependencies` | 先に完了している必要がある issue の一覧 |
| `Acceptance Criteria` | PR 作成前に全項目 `[x]` にする必要がある完了条件 |
| `Definition of Done` | 実装完了の基準 |

#### `docs/workflow.md`

issue の状態一覧表です。Supervisor が更新します。
`scripts/workflow-status.sh` で git ログベースの最新状態も確認できます。

#### `scripts/parallel-check.sh`

`issues/` ディレクトリを解析し、並列実行可能な issue グループを自動判定します。

判定基準:
1. `pending` 状態（main にマージ未済み・ローカルブランチなし）
2. 依存 issue がすべて `done`（main にマージ済み）
3. 他の pending issue と `Editable Files` が重複しない

#### `scripts/workflow-status.sh`

git ログを元に全 issue の進捗を一覧表示します。
`docs/workflow.md` の手動更新を補完するダッシュボードです。

---

## 3. 新プロジェクトへの導入手順

### Step 1: ファイルをコピーする

以下のファイル・ディレクトリをコピーします（`issues/` の個別 issue は不要）:

```
CLAUDE.md
CLAUDE_README.md
agents/supervisor.md
agents/implementer.md
issues/issue-template.md
docs/workflow.md        ← issue 一覧表は空にする
scripts/parallel-check.sh
scripts/workflow-status.sh
.claude/settings.json
.claude/hooks/pre-pr-check.sh
```

### Step 2: プロジェクト固有箇所を差し替える（Human が実施）

**担当: Human**（Supervisor や Implementer は実施しない）

`CLAUDE.md` の `[要差し替え]` でマークされた箇所を編集します:

1. **`## プロジェクト概要`** — プロジェクト名・概要・仕様書ファイル名を書く
2. **`## 開発方針`** — 使用する言語・フレームワーク・DB・ツールを書く
3. **`## 実装優先順位`** — このプロジェクト固有の実装順序を書く

`agents/supervisor.md` の `## 設計ルール` — プロジェクト固有のアーキテクチャ制約を書く。

> **なぜ Human が行うか**: ここに書く内容はプロジェクトの技術的方向性そのものであり、
> 人間が意思決定して確定させるべき情報です。Supervisor はこの設定を前提として動きます。

### Step 3: 仕様書を用意する（Human が実施）

`SPEC.md`（または任意のファイル名）に仕様を記述します。
Supervisor はこれを読んで issue を作成します。

### Step 4: `.claude/settings.json` を確認する（Human が実施）

`permissions.allow` に、このプロジェクトで使うコマンドが含まれているか確認します:

```json
{
  "permissions": {
    "allow": [
      "Bash(git *)",
      "Bash(gh *)",
      "Bash(<プロジェクトのビルドコマンド> *)"
    ]
  }
}
```

---

## 4. Claude への依頼方法

### Supervisor を起動する

Claude Code のチャットで以下のように依頼します:

```
agents/supervisor.md を読み、SPEC.md に基づいて issue を分割してください。
```

または新機能追加・仕様変更時:

```
agents/supervisor.md を読み、<やりたいこと> を実現するための issue を作成してください。
既存の実装（issues/, docs/workflow.md）も確認したうえで、
依存関係と並列化可能グループも整理してください。
```

### Implementer を単体起動する（手動）

特定の issue だけを実装させたい場合（**worktree 不要**）:

```
agents/implementer.md を読み、issues/issue03.md を実装してください。
ブランチ feature/issue03-xxx を main から作成して作業してください。
```

> **worktree について**: `isolation: "worktree"` は Supervisor が**複数の Implementer を並列起動するとき**に限り必要です。
> 手動で1つだけ起動する場合は通常のセッションで完結するため、worktree の設定は不要です。
>
> | 起動方法 | worktree | 理由 |
> |---------|---------|------|
> | Supervisor が並列起動 | **必要** | 複数エージェントが同時に同リポジトリを触るため競合が起きる |
> | Human が手動で単体起動 | **不要** | 1セッション・1ブランチで完結するため競合しない |

### 進捗を確認する

```
bash scripts/workflow-status.sh
```

### 並列化可能グループを確認する

```
bash scripts/parallel-check.sh
```

### PR 前チェックを手動実行する

```
echo '{"command":"gh pr create"}' | bash .claude/hooks/pre-pr-check.sh
```

---

## 5. 開発フロー詳細

```
Human                  Supervisor              Implementer
  │                        │                       │
  │── 「SPEC.md を読んで   │                       │
  │    issue を作って」 ──>│                       │
  │                        │ issues/issueXX.md 作成│
  │                        │ 依存関係・グループ整理 │
  │<── 「issueXX 作りました│                       │
  │    グループA: 01,03    │                       │
  │    グループB: 02」 ────│                       │
  │                        │                       │
  │── 「進めてください」 ──>│                       │
  │                        │── worktree で同時起動 ─>│ (issue01)
  │                        │── worktree で同時起動 ─>│ (issue03)
  │                        │                       │ 実装・PR作成
  │                        │<── 「PR #X 作成」 ─────│
  │<── 「グループA 完了。  │                       │
  │    PR #X, #Y を確認」 ─│                       │
  │                        │                       │
  │── PR レビュー・マージ  │                       │
  │── 「マージしました」 ──>│                       │
  │                        │── 次グループへ ───────>│ (issue02)
  │                        │                        │
```

### ルール

- **Human は Supervisor にのみ話しかける**
- **Supervisor は人間確認なしで次のグループに進まない**
- **PR は Human がレビュー・マージする**
- **pre-pr-check フックが Acceptance Criteria を自動検証する**

---

## 6. 並列実行フロー

### なぜ worktree を使うか

通常の git では 1 つのブランチしか checkout できませんが、
`git worktree` を使うと **同じリポジトリを複数ディレクトリに同時展開** できます。

Claude Code の `Agent(isolation: "worktree")` は、この仕組みを使って
各 Implementer に独立した作業空間を与えます。

```
repo/
├── main worktree    (main ブランチ)
├── worktree-A/      (feature/issue01 ブランチ) ← Implementer A
└── worktree-B/      (feature/issue03 ブランチ) ← Implementer B
```

### 並列化の条件

| 条件 | 理由 |
|------|------|
| 依存 issue がすべて main にマージ済み | 未マージの変更を前提に実装するとコンフリクトが発生する |
| Editable Files が他 issue と重複しない | 同じファイルを同時編集するとマージ競合が起きる |

### SQLite の注意

SQLite はファイルベースの DB のため、複数 worktree から同一ファイルに同時書き込みすると壊れる可能性があります。
テスト実行時は各 worktree で独立した DB ファイルを使ってください:

```bash
# 例: issue 番号を DB パスに含める
export DATABASE_URL="sqlite:///./test-issue01.db"
```

---

## 7. スクリプトリファレンス

### `scripts/workflow-status.sh`

```bash
bash scripts/workflow-status.sh
```

全 issue の進捗を表示します。git ログから状態を自動判定します。

**出力例:**
```
==================================
  MVP 進捗ダッシュボード
==================================

  ✓ issue01     done      環境構築
  ✓ issue02     done      DBモデル定義
  ⏳ issue03     in progress  ClamAV実装
  ○ issue04     pending   scan コマンド

----------------------------------
  完了: 2 / 4
==================================
```

### `scripts/parallel-check.sh`

```bash
bash scripts/parallel-check.sh          # 人間向け表示
bash scripts/parallel-check.sh --json   # JSON 出力（Supervisor が読み込む用）
```

並列実行可能な issue グループを表示します。

**出力例:**
```
============================================
  並列実行可能グループ
============================================

  【グループ 1】同時実行可
    issue02     DBモデル定義
                branch: feature/issue02-db-model
                files:  src/models.py src/repository.py

    issue03     ClamAV実装
                branch: feature/issue03-clamav
                files:  src/scanner.py src/parser.py

--------------------------------------------
  実行可能: 2 issue  /  1 グループ
============================================
```

### `.claude/hooks/pre-pr-check.sh`

`gh pr create` 実行前に自動で呼び出されます（`PreToolUse` フック）。

- ブランチ名から issue ID を抽出（`feature/issue04-xxx` → `issue04`）
- `issues/issue04.md` の `- [ ]` 項目を検出
- 未完了項目がある場合は `exit 2` でブロックし、未完了リストを表示

---

## 8. よくある質問

### Q. SPEC.md は必須ですか？

Supervisor が仕様を理解するための入力として必要です。
ファイル名は何でも構いません。`CLAUDE.md` の `## プロジェクト概要` で参照ファイルを指定してください。
SPEC.md がない場合は、Supervisor への依頼時に仕様を直接テキストで伝えることもできます。

### Q. issue の粒度はどのくらいが適切ですか？

**1 issue = 1〜2 ファイルの変更** が目安です。
それより大きい場合は分割してください。分割の基準:
- 「このファイルだけ変えれば動く」単位
- テストできる最小単位
- 独立してレビューできる単位

### Q. 人間が直接 Implementer に話しかけても良いですか？

問題ありませんが、Supervisor を経由することで依存チェック・並列化判定が行われます。
緊急の修正など小さな変更は直接 Implementer に指示しても構いません。

### Q. pre-pr-check フックが邪魔なときは？

`issues/issueXX.md` の Acceptance Criteria / Definition of Done を `[x]` にチェックすれば通過します。
フック自体を無効化する場合は `.claude/settings.json` の `hooks` セクションを削除してください。

### Q. issue-template.md の Test Plan セクションがないのはなぜですか？

このフレームワークでは `Acceptance Criteria` と `Definition of Done` がテスト計画を兼ねています。
プロジェクトの要件に応じて `## Test Plan` セクションを template に追加しても構いません。
その場合、`pre-pr-check.sh` は `- [ ]` 形式の行を全て検出するため、自動的にチェック対象に含まれます。
