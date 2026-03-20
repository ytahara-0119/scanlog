from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scanlog.config import DB_PATH, ensure_dirs
from scanlog.models import Base, PlanItem, ScanPlan


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


def get_plan_by_id(session: Session, plan_id: int) -> ScanPlan | None:
    return session.get(ScanPlan, plan_id)


def get_latest_plan(session: Session) -> ScanPlan | None:
    return session.query(ScanPlan).order_by(ScanPlan.id.desc()).first()


def get_plan_items(session: Session, plan_id: int) -> list[PlanItem]:
    return session.query(PlanItem).filter(PlanItem.plan_id == plan_id).all()
