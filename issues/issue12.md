# issue12

## Issue ID
issue12

## Title
差分判定ロジック実装（watcher.py）

## Purpose
file_inventory を基準に、対象ファイルの変化を検知する差分判定ロジックを実装する。
size + mtime の比較を優先し、変化があった場合のみ sha256 を計算することで監視コストを抑える。

## Background
watch run（issue13）の核心ロジック。
watcher.py として独立したモジュールに実装し、CLI（cli.py）や scanner.py への影響を最小限にする。
差分判定の結果は「スキャン対象ファイルのリスト」として返し、issue13 でスキャン実行に渡す。

## Scope

### watcher.py（新規作成）

#### `scan_directory(base_path: str, exclude_dirs: set[str]) -> List[Path]`
- base_path 配下のファイルを再帰的に走査する
- exclude_dirs に含まれるディレクトリ名はスキップする
- シンボリックリンクは追わない
- 戻り値: ファイルの Path オブジェクトのリスト

#### `detect_changes(session, watch_path: WatchPath, files: List[Path]) -> List[Path]`
- file_inventory と比較し、スキャン対象ファイルのリストを返す
- 判定ロジック（優先順）:
  1. file_inventory に未登録 → スキャン対象（新規ファイル）
  2. is_deleted = true だったが再出現 → スキャン対象
  3. last_scan_result = 'error' → スキャン対象（前回スキャン失敗の保守的再試行）
  4. file_size または mtime が変化 → sha256 を計算
     - sha256 が変化 → スキャン対象
     - sha256 が同一 → スキャン不要（mtime/size のみの変化と判定）
  5. file_size も mtime も変化なし → スキャン不要

#### `compute_sha256(file_path: Path) -> str`
- ファイルの SHA256 ハッシュを計算して返す
- 読み取りエラーの場合は None を返す（スキャン対象として扱う）

#### `update_inventory(session, watch_path: WatchPath, scanned_files: List[Path], scan_results: dict, all_files: List[Path])`
- watch run 完了後に file_inventory を更新する
- 全走査ファイルの last_seen_at を更新する
- スキャン済みファイルの sha256 / last_scanned_at / last_scan_result を更新する
- 走査で見つからなかったファイルは is_deleted = true に更新する
- 新規ファイルは INSERT する（first_seen_at = 現在時刻）

### repository.py への追記
- `get_inventory_by_path(session, file_path: str) -> FileInventory | None`
- `upsert_inventory(session, data: dict) -> FileInventory`
  - file_path をキーに INSERT or UPDATE する
- `mark_deleted_inventory(session, watch_path_id: int, existing_paths: set[str])`
  - existing_paths に含まれないファイルを is_deleted = true に更新する

## Out of Scope
- watch run の CLI 実装（issue13）
- 除外ポリシーの設定（issue13 で DEFAULT_EXCLUDE_DIRS として定義）
- watch_paths CRUD（issue11 完了済み）

## Editable Files
- src/scanlog/watcher.py（新規作成）
- src/scanlog/repository.py

## Do Not Edit
- src/scanlog/cli.py
- src/scanlog/models.py
- src/scanlog/scanner.py
- src/scanlog/parser.py
- src/scanlog/collector.py

## Dependencies
- issue10
- issue11

## Branch
feature/issue12-diff-detection

## Implementation Notes
- `os.stat()` で file_size（st_size）と mtime（st_mtime）を取得する
- mtime の比較は float で行う（datetime 変換は DB 保存時のみ）
- sha256 計算は `hashlib.sha256()` を 8KB チャンクで読み込んで計算する
- `detect_changes()` は副作用なし（DB 更新は `update_inventory()` に分離する）
- `compute_sha256()` は読み取りエラー時に None を返し、呼び出し側でスキャン対象扱いにする

## Acceptance Criteria
- [ ] `scan_directory()` がファイルリストを返す
- [ ] exclude_dirs に指定したディレクトリ配下のファイルが結果から除外される
- [ ] 新規ファイルがスキャン対象として返される
- [ ] size/mtime 変化なしのファイルはスキャン対象から外れる
- [ ] size/mtime 変化あり + sha256 同一のファイルはスキャン対象から外れる
- [ ] size/mtime 変化あり + sha256 変化のファイルはスキャン対象として返される
- [ ] last_scan_result = 'error' のファイルはスキャン対象として返される
- [ ] `update_inventory()` 後に is_deleted が正しく更新される

## Definition of Done
- [ ] コードが追加されている
- [ ] SPEC.md と矛盾しない
- [ ] 実装内容を説明できる
