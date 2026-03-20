from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scanlog.config import DB_PATH, ensure_dirs
from scanlog.models import Base


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
