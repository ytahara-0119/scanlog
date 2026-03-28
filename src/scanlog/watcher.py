"""watcher.py - 監視差分判定ロジック

差分判定の流れ:
  1. scan_directory() でファイルリストを取得（除外ポリシー適用）
  2. detect_changes() で file_inventory と比較しスキャン対象を特定
  3. （issue13 で）スキャン実行
  4. update_inventory() で file_inventory を更新

注意: detect_changes() は副作用なし。DB 更新は update_inventory() のみで行う。
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from scanlog.models import FileInventory, WatchPath
from scanlog.repository import get_inventory_by_path, mark_deleted_inventory

# 定期監視（watch run）でデフォルトに除外するディレクトリ名。
# これは「安全だから除外する」のではなく「監視コスト削減のためのポリシー」である。
# 手動スキャン（scan コマンド）にはこの除外は適用しない。
DEFAULT_EXCLUDE_DIRS: set[str] = {
    "node_modules",
    ".venv",
    "vendor",
    "target",
    "build",
    "dist",
    ".git",
}


def scan_directory(base_path: str, exclude_dirs: set[str]) -> list[Path]:
    """base_path 配下のファイルを再帰的に走査する。

    - exclude_dirs に含まれるディレクトリ名（basename）はスキップする
    - シンボリックリンクは追わない
    """
    result: list[Path] = []
    base = Path(base_path)
    if not base.exists():
        return result

    for root, dirs, files in os.walk(base, followlinks=False):
        # exclude_dirs に含まれるディレクトリを走査から除外（in-place 変更）
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for fname in files:
            fpath = Path(root) / fname
            if not fpath.is_symlink():
                result.append(fpath)

    return result


def compute_sha256(file_path: Path) -> str | None:
    """ファイルの SHA256 ハッシュを計算して返す。読み取りエラーの場合は None を返す。"""
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def detect_changes(session: Session, watch_path: WatchPath, files: list[Path]) -> list[Path]:
    """file_inventory と比較し、スキャン対象ファイルのリストを返す。

    副作用なし（DB 更新は update_inventory() で行う）。

    判定ロジック（優先順）:
      1. file_inventory に未登録            → スキャン対象（新規ファイル）
      2. is_deleted = True だったが再出現   → スキャン対象
      3. last_scan_result = 'error'         → スキャン対象（保守的再試行）
      4. file_size または mtime が変化
           sha256 が変化                    → スキャン対象
           sha256 が同一                    → スキャン不要（mtime/size のみの変化）
      5. file_size も mtime も変化なし      → スキャン不要
    """
    targets: list[Path] = []

    for file_path in files:
        try:
            stat = file_path.stat()
        except OSError:
            # stat 取得不可 → スキャン対象（ClamAV が error として検出）
            targets.append(file_path)
            continue

        current_size = stat.st_size
        current_mtime = stat.st_mtime

        inv = get_inventory_by_path(session, str(file_path))

        # 1. 未登録 → 新規ファイル
        if inv is None:
            targets.append(file_path)
            continue

        # 2. is_deleted = True だったが再出現
        if inv.is_deleted:
            targets.append(file_path)
            continue

        # 3. 前回 error → 保守的再試行
        if inv.last_scan_result == "error":
            targets.append(file_path)
            continue

        # 4. size または mtime が変化 → sha256 で最終確認
        if inv.file_size != current_size or inv.mtime != current_mtime:
            new_sha256 = compute_sha256(file_path)
            if new_sha256 is None:
                # 読み取り失敗 → スキャン対象
                targets.append(file_path)
                continue
            if new_sha256 != inv.sha256:
                targets.append(file_path)
            # sha256 が同一 → mtime/size のみの変化。スキャン不要

        # 5. 変化なし → スキャン不要

    return targets


def update_inventory(
    session: Session,
    watch_path: WatchPath,
    scanned_files: list[Path],
    scan_results: dict[str, str],
    all_files: list[Path],
) -> None:
    """watch run 完了後に file_inventory を更新する。

    - 全走査ファイルの last_seen_at / file_size / mtime を更新する
    - スキャン済みファイルの sha256 / last_scanned_at / last_scan_result を更新する
    - 新規ファイルは INSERT する（first_seen_at = 現在時刻）
    - 走査で見つからなかったファイルは is_deleted = True に更新する
    """
    now = datetime.now()
    scanned_set = {str(f) for f in scanned_files}
    existing_paths = {str(f) for f in all_files}

    for file_path in all_files:
        str_path = str(file_path)
        try:
            stat = file_path.stat()
            file_size: int | None = stat.st_size
            mtime: float | None = stat.st_mtime
        except OSError:
            file_size = None
            mtime = None

        inv = get_inventory_by_path(session, str_path)
        scanned = str_path in scanned_set
        result = scan_results.get(str_path)

        if inv is None:
            session.add(FileInventory(
                watch_path_id=watch_path.id,
                file_path=str_path,
                file_size=file_size,
                mtime=mtime,
                sha256=compute_sha256(file_path) if scanned else None,
                first_seen_at=now,
                last_seen_at=now,
                last_scanned_at=now if scanned else None,
                last_scan_result=result,
                is_deleted=False,
            ))
        else:
            inv.file_size = file_size
            inv.mtime = mtime
            inv.last_seen_at = now
            inv.is_deleted = False
            if scanned:
                inv.sha256 = compute_sha256(file_path)
                inv.last_scanned_at = now
                inv.last_scan_result = result

    # 今回の走査で見つからなかったファイルを論理削除
    mark_deleted_inventory(session, watch_path.id, existing_paths)
