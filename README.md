# scanlog

ClamAV を利用したファイル/ディレクトリのウィルススキャン CLI ツール。
スキャン結果を SQLite に保存し、定期スキャンフローにも対応する。

---

## セットアップ

### 必要条件

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- ClamAV（`clamscan` コマンドが使えること）

### インストール

```bash
git clone https://github.com/ytahara-0119/scanlog.git
cd scanlog
uv sync
```

---

## コマンドリファレンス

### `scan` — 手動スキャン

指定したファイルまたはディレクトリを即時スキャンする。

```bash
uv run scanlog scan <path>
```

| 引数 | 説明 |
|---|---|
| `<path>` | スキャン対象のファイルまたはディレクトリ |

**例**

```bash
# ファイルをスキャン
uv run scanlog scan ~/Downloads/archive.zip

# ディレクトリを再帰スキャン
uv run scanlog scan ~/projects/myapp
```

---

### `collect` — 対象収集

カレントディレクトリ配下の当日作成/更新ファイルを収集し、スキャンプランを作成する。

```bash
uv run scanlog collect [dir]
```

| 引数 | 説明 | デフォルト |
|---|---|---|
| `[dir]` | 収集対象ディレクトリ | `.`（カレントディレクトリ） |

**例**

```bash
# カレントディレクトリを対象に収集
uv run scanlog collect

# 指定ディレクトリを対象に収集
uv run scanlog collect ~/Downloads
```

実行すると `plan_id` が表示される。

---

### `preview` — プラン確認

作成済みスキャンプランの内容を表示する。

```bash
uv run scanlog preview --latest
uv run scanlog preview --plan-id <id>
```

| オプション | 説明 |
|---|---|
| `--latest` | 最新のプランを表示 |
| `--plan-id <id>` | 指定した ID のプランを表示 |

**例**

```bash
uv run scanlog preview --latest
uv run scanlog preview --plan-id 3
```

---

### `approve` — プラン承認

スキャンプランを承認する（`execute` を実行するために必要）。

```bash
uv run scanlog approve --plan-id <id>
```

**例**

```bash
uv run scanlog approve --plan-id 3
```

---

### `execute` — スキャン実行

承認済みプランのスキャンを実行し、結果を DB に保存する。

```bash
uv run scanlog execute --plan-id <id>
```

> `approve` 済みのプランのみ実行可能。

**例**

```bash
uv run scanlog execute --plan-id 3
```

---

## 定期スキャンフロー

```bash
# 1. 当日更新ファイルを収集してプランを作成
uv run scanlog collect

# 2. プランの内容を確認
uv run scanlog preview --latest

# 3. 問題なければ承認
uv run scanlog approve --plan-id <id>

# 4. スキャン実行
uv run scanlog execute --plan-id <id>
```

---

## SQLite DB の確認

DB ファイルの場所: `~/.scanlog/scanlog.db`

### sqlite3 コマンドで接続

```bash
sqlite3 ~/.scanlog/scanlog.db
```

### よく使うクエリ

```sql
-- スキャンプラン一覧
SELECT id, mode, status, base_path, created_at FROM scan_plans;

-- プランの対象ファイル一覧
SELECT id, target_path, target_type, scan_mode, target_reason
FROM plan_items WHERE plan_id = 1;

-- スキャン実行履歴
SELECT id, plan_id, status, started_at, finished_at FROM scan_runs;

-- スキャン結果サマリ
SELECT id, target_path, target_type, result_status, exit_code
FROM scan_results;

-- 感染ファイルの一覧
SELECT sr.target_path, e.scanned_path, e.virus_name
FROM scan_result_entries e
JOIN scan_results sr ON e.scan_result_id = sr.id
WHERE e.entry_status = 'infected';
```

### テーブル構造の確認

```bash
sqlite3 ~/.scanlog/scanlog.db ".schema"
```

---

## DB テーブル構造

| テーブル | 説明 |
|---|---|
| `scan_plans` | スキャンプラン（manual_scan / scheduled_scan） |
| `plan_items` | プランの対象ファイル/ディレクトリ |
| `scan_runs` | スキャン実行履歴 |
| `scan_results` | スキャン結果（対象ごと） |
| `scan_result_entries` | スキャン結果の行ごとの詳細 |

### `scan_plans.status` の遷移

```
draft → approved → executing → completed / failed
```
