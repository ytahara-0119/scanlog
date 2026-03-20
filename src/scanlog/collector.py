from datetime import date
from pathlib import Path

_ARCHIVE_SUFFIXES = {".zip", ".dmg", ".pkg", ".exe", ".jar"}
_ARCHIVE_COMPOUND = {".tar.gz", ".tar.bz2", ".tar.xz"}

_PROJECT_MARKERS = {
    ".git", "package.json", "pyproject.toml", "requirements.txt",
    "Pipfile", "poetry.lock", "Cargo.toml", "go.mod", "Gemfile",
    "pom.xml", "build.gradle", "Makefile",
}


def _is_today(path: Path) -> bool:
    mtime = date.fromtimestamp(path.stat().st_mtime)
    ctime = date.fromtimestamp(path.stat().st_ctime)
    today = date.today()
    return mtime == today or ctime == today


def _is_archive(path: Path) -> bool:
    name = path.name
    for ext in _ARCHIVE_COMPOUND:
        if name.endswith(ext):
            return True
    return path.suffix in _ARCHIVE_SUFFIXES


def _is_project_root(path: Path) -> bool:
    for marker in _PROJECT_MARKERS:
        if (path / marker).exists():
            return True
    return False


def collect(base_path: str) -> list[dict]:
    base = Path(base_path).resolve()
    today = date.today()
    targets: list[dict] = []
    visited_dirs: set[Path] = set()

    for current_dir, dirs, files in base.walk(follow_symlinks=False):
        current = Path(current_dir)

        # すでに directory target として登録済みの親ディレクトリ配下はスキップ
        if any(current == d or d in current.parents for d in visited_dirs):
            dirs.clear()
            continue

        # カレントディレクトリ自体が当日更新 かつ プロジェクトルートなら directory target
        if _is_project_root(current) and current != base:
            if _is_today(current):
                targets.append({
                    "target_path": str(current),
                    "target_type": "directory",
                    "scan_mode": "recursive",
                    "target_reason": "project_root",
                })
                visited_dirs.add(current)
                dirs.clear()
                continue

        # ファイルを個別チェック
        for fname in files:
            fpath = current / fname
            if fpath.is_symlink():
                continue
            try:
                if not _is_today(fpath):
                    continue
            except OSError:
                continue

            if _is_archive(fpath):
                targets.append({
                    "target_path": str(fpath),
                    "target_type": "file",
                    "scan_mode": "single",
                    "target_reason": "archive",
                })
            else:
                targets.append({
                    "target_path": str(fpath),
                    "target_type": "file",
                    "scan_mode": "single",
                    "target_reason": "modified_today",
                })

    return targets
