from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from scanlog.config import DB_PATH, ensure_dirs
from scanlog.models import Base, PlanItem, ScanBatch, ScanPlan


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
        # scan_batches は create_all で作成済みのはずだが念のため確認
        existing_cols = _existing_columns(conn, "plan_items")
        additions = {
            "batch_id":         "ALTER TABLE plan_items ADD COLUMN batch_id INTEGER",
            "execution_status": "ALTER TABLE plan_items ADD COLUMN execution_status TEXT DEFAULT 'pending'",
            "last_run_id":      "ALTER TABLE plan_items ADD COLUMN last_run_id INTEGER",
        }
        for col, stmt in additions.items():
            if col not in existing_cols:
                conn.execute(text(stmt))

        existing_cols = _existing_columns(conn, "scan_results")
        if "batch_id" not in existing_cols:
            conn.execute(text("ALTER TABLE scan_results ADD COLUMN batch_id INTEGER"))

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
