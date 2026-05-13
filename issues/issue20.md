# issue20: cli.py - watch_run 簡素化 + recent コマンド追加

## 概要

`watch run` コマンドを _run_execute を使わない直接保存方式に書き直す。
また `scanlog recent` コマンドを新規追加する。

## ブランチ名

`refactor/simplify-watch-and-add-recent`

## 依存 issue

- issue19（scan コマンド簡素化が main にマージ済みであること）

## Editable Files

- `src/scanlog/cli.py`

## 変更内容

### watch_run コマンドの新しい実装

```
watch run
  1. enabled な watch_paths を取得（0件なら終了）
  2. 各 watch_path を scan_directory() で走査（除外ポリシー適用）
  3. detect_changes() で差分ファイルを特定
  4. 差分が0件 → 「変更ファイルなし」を表示してスキャンをスキップ
  5. 差分が1件以上 → iter_batch_scan() でバッチスキャン
  6. チャンクごとに ScanResult + ScanResultEntry を保存（mode="watch"）
  7. update_inventory() で file_inventory を更新
  8. 結果サマリを表示（infected があれば詳細も表示）
```

### DB 保存仕様（watch_run 内）

差分ファイルをスキャンするたびに以下を保存する：

```python
ScanResult(
    mode="watch",
    scanned_at=datetime.now(),
    target_path=str(file_path),
    target_type="file",
    result_status=result_status,
    raw_output=chunk_stdout,
    exit_code=chunk_exit_code,
)
```

### recent コマンドの実装

```bash
scanlog recent [--limit 10]
```

```
recent
  1. get_recent_scan_results(session, limit) で ScanResult を取得
  2. テーブル形式で表示（scanned_at / mode / result_status / target_path）
  3. infected があれば詳細（virus_name）を表示
```

表示例：
```
# scanned_at             mode    status   target_path
----------------------------------------------------------------------
1  2026-05-13 08:00:01  watch   clean    /Users/foo/bar/baz.txt
2  2026-05-13 07:59:58  watch   clean    /Users/foo/qux.py
3  2026-05-12 14:32:11  manual  infected /Users/foo/evil.dmg
   -> Eicar-Test-Signature
```

## Acceptance Criteria

- [ ] `uv run scanlog watch run` が正常終了する（watch_path 登録済みの状態で）
- [ ] `uv run scanlog watch run` 後に scan_results テーブルに mode="watch" のレコードが存在する
- [ ] 変更ファイルが0件のとき「変更ファイルなし」を表示してスキャンをスキップする
- [ ] `uv run scanlog recent` が直近10件を表示する
- [ ] `uv run scanlog recent --limit 3` が直近3件を表示する
- [ ] `uv run scanlog recent` で scan_results が0件のとき「スキャン結果がありません」を表示する

### テスト手順

```bash
# watch run 確認
uv run scanlog watch add ~/Downloads
uv run scanlog watch run

# recent 確認
uv run scanlog recent
uv run scanlog recent --limit 3

# SQLite 確認
sqlite3 ~/.scanlog/scanlog.db "SELECT mode, scanned_at, result_status, target_path FROM scan_results ORDER BY scanned_at DESC LIMIT 10;"
```

## Definition of Done

- [ ] Acceptance Criteria 全項目を確認済み
- [ ] PR を作成済み
