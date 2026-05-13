# issue21: collector.py 削除

## 概要

`collect` コマンド廃止に伴い、不要となった `collector.py` を削除する。

## ブランチ名

`refactor/remove-collector`

## 依存 issue

- issue18（cli.py から `from scanlog.collector import` が削除済みであること）

## Editable Files

- `src/scanlog/collector.py`（削除）

## 変更内容

- `src/scanlog/collector.py` を削除する

## Acceptance Criteria

- [ ] `src/scanlog/collector.py` が存在しない
- [ ] `uv run scanlog --help` が正常に表示される（import エラーなし）
- [ ] `uv run python -c "import scanlog.cli"` が正常に完了する

## Definition of Done

- [ ] Acceptance Criteria 全項目を確認済み
- [ ] PR を作成済み
