# issue18: cli.py - 不要コマンド・関数の削除

## 概要

`collect → preview → approve → execute` フローを廃止し、
それに関連するコマンドと内部関数を cli.py から削除する。

## ブランチ名

`refactor/remove-plan-commands`

## 依存 issue

- issue16（models.py 変更が main にマージ済みであること）
- issue17（repository.py 変更が main にマージ済みであること）

## Editable Files

- `src/scanlog/cli.py`

## 変更内容

### 削除するコマンド

- `collect` コマンド
- `preview` コマンド
- `approve` コマンド
- `execute` コマンド

### 削除する関数

- `_run_execute()` 内部関数

### 削除する import

```python
# 削除対象
from scanlog.collector import collect as do_collect
from scanlog.models import PlanItem, ScanBatch, ScanPlan, ScanRun, ...
from scanlog.repository import (
    get_latest_plan,
    get_pending_plan_items,
    get_plan_by_id,
    get_plan_items,
    ...
)
from scanlog.scanner import _BATCH_CHUNK_SIZE, iter_batch_scan, run_batch_scan, run_scan
```

### 維持するもの

- `_calc_result_status()` ヘルパー関数
- `_print_scan_result()` ヘルパー関数
- `app` / `watch_app` Typer アプリ
- `scan` コマンド（この時点では動作しなくてよい。次の issue で修正）
- `watch add / list / remove / run` コマンド（この時点では動作しなくてよい。次の issue で修正）
- `main` callback

**注意**: この issue では「削除のみ」を行う。scan コマンドや watch_run の書き直しは issue19/20 で実施する。
削除後は cli.py が import エラーを起こさない状態を目指す（未使用変数・importは許容）。

## Acceptance Criteria

- [ ] `collect` / `preview` / `approve` / `execute` コマンドが cli.py に存在しない
- [ ] `_run_execute` 関数が cli.py に存在しない
- [ ] `from scanlog.collector import` の import が存在しない
- [ ] `ScanPlan` / `PlanItem` / `ScanRun` / `ScanBatch` の import が存在しない
- [ ] `uv run scanlog --help` に collect/preview/approve/execute が表示されない
- [ ] `uv run scanlog watch --help` が正常に表示される

## Definition of Done

- [ ] Acceptance Criteria 全項目を確認済み
- [ ] PR を作成済み
