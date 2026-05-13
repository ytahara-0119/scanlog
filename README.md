# scanlog

ClamAV を利用したファイル/ディレクトリのウィルススキャン CLI ツール。
スキャン結果を SQLite に保存し、監視対象の差分スキャンに対応する。

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

**例**

```bash
# ファイルをスキャン
uv run scanlog scan ~/Downloads/archive.zip

# ディレクトリを再帰スキャン
uv run scanlog scan ~/projects/myapp
```

---

### `recent` — 直近のスキャン結果表示

直近のスキャン結果を新しい順に表示する（デフォルト: 10件）。

```bash
uv run scanlog recent [--limit N]
```

| オプション | 説明 | デフォルト |
|---|---|---|
| `--limit N` | 表示件数 | `10` |

**例**

```bash
# 直近10件を表示
uv run scanlog recent

# 直近3件を表示
uv run scanlog recent --limit 3
```

**出力例**

```
#    scanned_at             mode     status     target_path
--------------------------------------------------------------------------------
1    2026-05-13 08:00:01    watch    clean      /Users/foo/bar/baz.txt
2    2026-05-13 07:59:58    watch    clean      /Users/foo/qux.py
3    2026-05-12 14:32:11    manual   infected   /Users/foo/evil.dmg
     -> Eicar-Test-Signature (/Users/foo/evil.dmg)
```

---

### `watch` — 監視対象の管理と巡回スキャン

監視対象ディレクトリを登録し、差分のあるファイルだけをスキャンする。
cron などから定期実行することを想定している。

#### `watch add` — 監視対象を登録

```bash
uv run scanlog watch add <path>
```

#### `watch list` — 監視対象を一覧表示

```bash
uv run scanlog watch list
```

#### `watch remove` — 監視対象を削除

```bash
uv run scanlog watch remove <path>
```

#### `watch run` — 差分スキャンを実行

登録済みの全監視対象を対象に差分チェックを行い、変化のあったファイルのみスキャンする。

```bash
uv run scanlog watch run
```

- 前回から変化のないファイルはスキップする（size + mtime → sha256 で判定）
- `node_modules` / `.venv` / `.git` 等の重い依存ディレクトリはデフォルトで除外する

**例**

```bash
# 監視対象を登録
uv run scanlog watch add ~/Downloads
uv run scanlog watch add ~/ghq

# 一覧確認
uv run scanlog watch list

# 差分スキャン実行（cron に登録するコマンド）
uv run scanlog watch run
```

---

## 典型的な使い方

### 単発スキャン

```bash
uv run scanlog scan ~/Downloads/suspicious_file.dmg
```

### 定期監視（cron）

```bash
# crontab -e で登録する例（毎日 8:00 に実行）
0 8 * * * cd /path/to/scanlog && uv run scanlog watch run >> ~/.scanlog/watch.log 2>&1
```

### 結果確認

```bash
# CLI で確認
uv run scanlog recent

# SQLite で直接確認
sqlite3 ~/.scanlog/scanlog.db "SELECT mode, scanned_at, result_status, target_path FROM scan_results ORDER BY scanned_at DESC LIMIT 10;"
```

---

## SQLite DB の確認

DB ファイルの場所: `~/.scanlog/scanlog.db`

### よく使うクエリ

```sql
-- 直近のスキャン結果
SELECT mode, scanned_at, result_status, target_path
FROM scan_results
ORDER BY scanned_at DESC
LIMIT 10;

-- 感染ファイルの一覧
SELECT sr.scanned_at, sr.target_path, e.scanned_path, e.virus_name
FROM scan_result_entries e
JOIN scan_results sr ON e.scan_result_id = sr.id
WHERE e.entry_status = 'infected'
ORDER BY sr.scanned_at DESC;

-- エラーになったファイル
SELECT sr.scanned_at, e.scanned_path, e.raw_line
FROM scan_result_entries e
JOIN scan_results sr ON e.scan_result_id = sr.id
WHERE e.entry_status IN ('error', 'clamav_error')
ORDER BY sr.scanned_at DESC;

-- 監視対象ファイルの最終スキャン状況
SELECT file_path, last_scan_result, last_scanned_at
FROM file_inventory
WHERE last_scan_result != 'clean'
ORDER BY last_scanned_at DESC;
```

---

## DB テーブル構造

| テーブル | 説明 |
|---|---|
| `scan_results` | スキャン結果（対象ごと） |
| `scan_result_entries` | スキャン結果の行ごとの詳細 |
| `watch_paths` | 監視対象パスの登録 |
| `file_inventory` | 監視ファイルの最終状態（差分判定に使用） |
