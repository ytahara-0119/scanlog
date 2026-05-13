# issue19: cli.py - scan コマンド簡素化

## 概要

`scan` コマンドを、ScanPlan / PlanItem / ScanRun / ScanBatch を使わない
シンプルな直接保存方式に書き直す。

## ブランチ名

`refactor/simplify-scan-command`

## 依存 issue

- issue18（不要コマンド削除が main にマージ済みであること）

## Editable Files

- `src/scanlog/cli.py`

## 変更内容

### scan コマンドの新しい実装

```
scan <path>
  1. Path を解決し存在チェック
  2. ファイル / ディレクトリを判定
  3. ClamAV を実行
     - file:      iter_batch_scan([str(target)]) でスキャン
     - directory: run_scan(str(target), "recursive") でスキャン
  4. 出力をパース
  5. ScanResult(mode="manual", scanned_at=now, ...) を保存
  6. 各エントリを ScanResultEntry として保存
  7. _print_scan_result() でサマリ表示
```

### 追加 / 変更する import

```python
from datetime import datetime
from scanlog.models import ScanResult, ScanResultEntry, WatchPath  # PlanItem等は不要
from scanlog.scanner import iter_batch_scan, run_scan  # run_batch_scan は不要
from scanlog.repository import get_session, init_db  # plan系は不要
```

### DB 保存仕様

```python
ScanResult(
    mode="manual",
    scanned_at=datetime.now(),
    target_path=str(target),
    target_type=target_type,     # "file" or "directory"
    result_status=result_status, # "clean" / "infected" / "error"
    raw_output=raw_output,
    exit_code=exit_code,
)
```

### 進捗表示（fileスキャン時）

file スキャンでチャンクが複数になる場合、既存の進捗表示（`[done/total] %...`）を維持する。

## Acceptance Criteria

- [ ] `uv run scanlog scan <存在するファイルパス>` が正常終了する
- [ ] `uv run scanlog scan <存在するディレクトリパス>` が正常終了する
- [ ] `uv run scanlog scan /nonexistent` が `Error: ... が存在しません` を表示して終了する
- [ ] スキャン後に SQLite の scan_results テーブルに mode="manual" のレコードが存在する
- [ ] スキャン後に SQLite の scan_result_entries テーブルにエントリが存在する
- [ ] scan_plans / plan_items / scan_runs / scan_batches テーブルへの書き込みが発生しない

### テスト手順

```bash
# DB を削除してクリーンな状態で確認
rm -f ~/.scanlog/scanlog.db

# ファイルスキャン
uv run scanlog scan /tmp/test_scanlog.txt  # 適当なファイルで確認

# ディレクトリスキャン
uv run scanlog scan /tmp/

# SQLite で確認
sqlite3 ~/.scanlog/scanlog.db "SELECT mode, scanned_at, target_path, result_status FROM scan_results;"
sqlite3 ~/.scanlog/scanlog.db ".tables"  # scan_plans 等が存在しないことを確認
```

## Definition of Done

- [ ] Acceptance Criteria 全項目を確認済み
- [ ] PR を作成済み
