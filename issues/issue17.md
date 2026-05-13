# issue17: repository.py - CRUD整理とDB初期化更新

## 概要

issue16 のモデル変更に合わせ、不要な CRUD 関数を削除し、
`init_db` を新スキーマに対応させる。また `recent` コマンド用の
`get_recent_scan_results()` を追加する。

## ブランチ名

`refactor/simplify-repository`

## 依存 issue

- issue16（models.py 変更が main にマージ済みであること）

## Editable Files

- `src/scanlog/repository.py`

## 変更内容

### 削除する関数

- `migrate_db()` — 旧テーブル用マイグレーション。新スキーマでは不要
- `get_plan_by_id()`
- `get_latest_plan()`
- `get_plan_items()`
- `get_pending_plan_items()`

### 変更する関数

**`init_db()`**
- `Base.metadata.create_all(engine)` のみを呼ぶ（migrate_db 呼び出しを削除）
- これにより新スキーマのテーブルが自動生成される

### 追加する関数

```python
def get_recent_scan_results(session: Session, limit: int = 10) -> list[ScanResult]:
    """ScanResult を scanned_at 降順で最大 limit 件返す。"""
```

### 維持する関数（変更なし）

- `get_session()`
- `add_watch_path()`
- `list_watch_paths()`
- `remove_watch_path()`
- `get_watch_path_by_path()`
- `get_inventory_by_path()`
- `upsert_inventory()`
- `mark_deleted_inventory()`

## Acceptance Criteria

- [ ] `migrate_db` / `get_plan_by_id` / `get_latest_plan` / `get_plan_items` / `get_pending_plan_items` が存在しない
- [ ] `init_db()` が `Base.metadata.create_all()` のみ呼ぶ
- [ ] `get_recent_scan_results(session, limit=10)` が実装されている
- [ ] `uv run python -c "from scanlog.repository import get_session, init_db, get_recent_scan_results; print('OK')"` が通る

## Definition of Done

- [ ] Acceptance Criteria 全項目を確認済み
- [ ] PR を作成済み
