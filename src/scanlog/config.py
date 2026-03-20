from pathlib import Path

_BASE_DIR = Path.home() / ".scanlog"
DB_PATH = _BASE_DIR / "scanlog.db"


def ensure_dirs() -> None:
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
