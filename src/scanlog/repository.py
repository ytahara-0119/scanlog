from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from scanlog.config import DB_PATH, ensure_dirs
from scanlog.models import Base, FileInventory, PlanItem, ScanBatch, ScanPlan, WatchPath


def _get_engine():
    ensure_dirs()
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def _existing_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def migrate_db() -> None:
    """既存 DB に不足カラム・テーブルを追加する（冪等）。"""
    engine = _get_engine()
    with engine.connect() as conn:
        # plan_items カラム追加
        existing_cols = _existing_columns(conn, "plan_items")
        additions = {
            "batch_id":         "ALTER TABLE plan_items ADD COLUMN batch_id INTEGER",
            "execution_status": "ALTER TABLE plan_items ADD COLUMN execution_status TEXT DEFAULT 'pending'",
            "last_run_id":      "ALTER TABLE plan_items ADD COLUMN last_run_id INTEGER",
        }
        for col, stmt in additions.items():
            if col not in existing_cols:
                conn.execute(text(stmt))

        # scan_results カラム追加
        existing_cols = _existing_columns(conn, "scan_results")
        if "batch_id" not in existing_cols:
            conn.execute(text("ALTER TABLE scan_results ADD COLUMN batch_id INTEGER"))

        # watch_paths テーブル追加（監視機能）
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS watch_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))

        # file_inventory テーブル追加（監視差分判定の基準データ）
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS file_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watch_path_id INTEGER REFERENCES watch_paths(id),
                file_path TEXT NOT NULL UNIQUE,
                file_size INTEGER,
                mtime REAL,
                sha256 TEXT,
                first_seen_at DATETIME,
                last_seen_at DATETIME,
                last_scanned_at DATETIME,
                last_scan_result TEXT,
                is_deleted BOOLEAN NOT NULL DEFAULT 0
            )
        """))

        conn.commit()


def init_db() -> None:
    engine = _get_engine()
    Base.metadata.create_all(engine)
    migrate_db()


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


def get_plan_by_id(session: Session, plan_id: int) -> ScanPlan | None:
    return session.get(ScanPlan, plan_id)


def get_latest_plan(session: Session) -> ScanPlan | None:
    return session.query(ScanPlan).order_by(ScanPlan.id.desc()).first()


def get_plan_items(session: Session, plan_id: int) -> list[PlanItem]:
    return session.query(PlanItem).filter(PlanItem.plan_id == plan_id).all()


def get_pending_plan_items(session: Session, plan_id: int) -> list[PlanItem]:
    """execution_status が pending または failed の plan_items を返す。"""
    return (
        session.query(PlanItem)
        .filter(
            PlanItem.plan_id == plan_id,
            PlanItem.execution_status.in_(["pending", "failed"]),
        )
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
