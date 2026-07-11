"""SQLAlchemy engine/session setup (plan.md §8.1)."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def _default_db_path() -> str:
    return os.environ.get("SANJEEVANI_DB_PATH", "data/sanjeevani.db")


def make_engine(db_path: str | None = None):
    path = db_path or _default_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


engine = make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
