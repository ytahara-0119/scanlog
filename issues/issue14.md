# issue14

## Title
仕上げと整合性確認（watch 機能 end-to-end 動作確認 + SPEC 整合）

## Purpose
監視機能（issue10〜13）の実装が完了した時点で、
全コマンドの end-to-end 動作確認を行い、SPEC.md との整合性を確認する。
不足・矛盾があれば修正する。

## Background
issue09（手動スキャン完成）と issue10〜13（監視機能）が積み上がった段階での最終確認 issue。
個別 issue の Acceptance Criteria は各 issue でチェック済みだが、
コマンド間の連携や DB 状態の整合を通しで確認する必要がある。

## Scope

### 動作確認（手動テスト）

#### 手動スキャン系（既存機能のリグレッション確認）
- `scanlog scan <file>` が正常動作すること
- `scanlog scan <directory>` が正常動作すること
- `scanlog collect` → `preview` → `approve` → `execute` の一連フローが動作すること
- `execute` の途中再開（resume）が動作すること

#### 監視機能系（新機能の確認）
- `scanlog watch add <path>` で登録できること
- `scanlog watch list` で一覧が表示されること
- `scanlog watch remove <path>` で削除できること
- `scanlog watch run` が初回実行で全ファイルをスキャンすること（全ファイルが新規扱い）
- `scanlog watch run` が2回目実行で差分なしの場合「変更ファイルなし」と表示すること
- ファイルを変更後 `scanlog watch run` を実行すると、変更ファイルのみスキャンされること
- node_modules / .venv 配下のファイルが watch run でスキャンされないこと
- node_modules / .venv 配下のファイルが `scan <directory>` ではスキャンされること

### コード整合確認

- `preview` コマンドが `mode = watch_scan` の scan_plan を表示できること
- `plan_items.target_reason = 'watch_diff'` が正しく保存・表示されること
- `scan_plans.mode` に `watch_scan` が入っている場合に既存コマンドがエラーにならないこと

### 修正対応
- 動作確認で発見した軽微なバグや表示崩れを修正する
- SPEC.md との記述差異があれば修正する

## Out of Scope
- 新機能の追加
- per-path 除外設定（将来対応）
- 設定ファイルによる除外リストカスタマイズ（将来対応）
- 並列処理・通知・quarantine（将来対応）

## Editable Files
- src/scanlog/cli.py（軽微な修正のみ）
- src/scanlog/watcher.py（軽微な修正のみ）
- src/scanlog/repository.py（軽微な修正のみ）
- SPEC.md（記述差異の修正のみ）

## Do Not Edit
- src/scanlog/models.py（スキーマ変更が生じる場合は別 issue）
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
- issue13

## Branch
feature/issue14-watch-integration

## Implementation Notes
- この issue では大きな機能追加は行わない
- 動作確認は実際に ClamAV がインストールされた環境で行う
- バグ修正は1ファイルに閉じた軽微なものに限る
- 大きな問題が発見された場合は別 issue として切り出す

## Acceptance Criteria
- [ ] 手動スキャン（scan / collect / execute）が引き続き正常動作する
- [ ] watch add / list / remove が正常動作する
- [ ] watch run が初回・2回目・変更ありの各ケースで期待通りに動作する
- [ ] node_modules 等の除外ディレクトリが watch run でスキップされる
- [ ] 手動 scan では除外が適用されない
- [ ] preview コマンドが watch_scan mode の plan を正常表示できる
- [ ] `scanlog --help` ですべてのコマンドが表示される

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
