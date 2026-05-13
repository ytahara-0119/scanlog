from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scanlog.config import DB_PATH, ensure_dirs
from scanlog.models import Base, FileInventory, ScanResult, WatchPath


def _get_engine():
    ensure_dirs()
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> None:
    engine = _get_engine()
    Base.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    engine = _get_engine()
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_recent_scan_results(session: Session, limit: int = 10) -> list[ScanResult]:
    """ScanResult を scanned_at 降順で最大 limit 件返す。"""
    return (
        session.query(ScanResult)
        .order_by(ScanResult.scanned_at.desc())
        .limit(limit)
        .all()
    )


# --- watch_paths CRUD ---

def get_watch_path_by_path(session: Session, path: str) -> WatchPath | None:
    return session.query(WatchPath).filter(WatchPath.path == path).first()


def add_watch_path(session: Session, path: str) -> WatchPath:
    """path を監視対象として登録する。既存レコードがある場合は enabled = True に更新する。"""
    from datetime import datetime
    existing = get_watch_path_by_path(session, path)
    if existing:
        existing.enabled = True
        existing.updated_at = datetime.now()
        return existing
    wp = WatchPath(path=path, enabled=True, created_at=datetime.now(), updated_at=datetime.now())
    session.add(wp)
    return wp


def list_watch_paths(session: Session) -> list[WatchPath]:
    return session.query(WatchPath).order_by(WatchPath.id).all()


def remove_watch_path(session: Session, path: str) -> bool:
    """path を watch_paths から削除する。削除成功で True、未登録で False を返す。
    file_inventory のレコードは保持する（履歴として残す）。
    """
    wp = get_watch_path_by_path(session, path)
    if wp is None:
        return False
    session.delete(wp)
    return True


# --- file_inventory CRUD ---

def get_inventory_by_path(session: Session, file_path: str) -> FileInventory | None:
    return session.query(FileInventory).filter(FileInventory.file_path == file_path).first()


def upsert_inventory(session: Session, data: dict) -> FileInventory:
    """file_path をキーに INSERT or UPDATE する。"""
    inv = get_inventory_by_path(session, data["file_path"])
    if inv is None:
        inv = FileInventory(**data)
        session.add(inv)
    else:
        for key, value in data.items():
            setattr(inv, key, value)
    return inv


def mark_deleted_inventory(session: Session, watch_path_id: int, existing_paths: set[str]) -> None:
    """existing_paths に含まれないファイルを is_deleted = True に更新する。"""
    records = (
        session.query(FileInventory)
        .filter(FileInventory.watch_path_id == watch_path_id, FileInventory.is_deleted == False)  # noqa: E712
        .all()
    )
    for inv in records:
        if inv.file_path not in existing_paths:
            inv.is_deleted = True
