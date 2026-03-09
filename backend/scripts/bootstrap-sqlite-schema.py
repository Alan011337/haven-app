#!/usr/bin/env python3
"""
Bootstrap a brand-new local SQLite database with current SQLModel metadata
and stamp Alembic revision to head.

Safety guards:
- Only supports sqlite:/// file URLs.
- Refuses to run if the database already contains tables.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import Set

from alembic import command
from alembic.config import Config
from sqlalchemy.engine.url import make_url
from sqlmodel import SQLModel, create_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _resolve_database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        raise RuntimeError("DATABASE_URL is required.")
    return raw


def _resolve_sqlite_file_path(database_url: str) -> Path:
    parsed = make_url(database_url)
    if parsed.get_backend_name() != "sqlite":
        raise RuntimeError("Only sqlite DATABASE_URL is supported by this bootstrap script.")

    raw_db_path = parsed.database or ""
    if not raw_db_path or raw_db_path == ":memory:":
        raise RuntimeError("DATABASE_URL must point to a sqlite file path, not in-memory.")

    db_path = Path(raw_db_path)
    if not db_path.is_absolute():
        db_path = (BACKEND_DIR / db_path).resolve()
    return db_path


def _read_existing_tables(db_path: Path) -> Set[str]:
    if not db_path.exists():
        return set()
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {str(row[0]) for row in rows}
    finally:
        conn.close()


def _stamp_head(database_url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.stamp(config, "head")


def main() -> int:
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))

    try:
        database_url = _resolve_database_url()
        db_path = _resolve_sqlite_file_path(database_url)
        existing_tables = _read_existing_tables(db_path)
        if existing_tables:
            preview = ", ".join(sorted(existing_tables)[:10])
            raise RuntimeError(
                "Refusing to bootstrap non-empty sqlite DB. "
                f"Found tables: {preview}"
            )

        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure all SQLModel metadata is registered before create_all.
        from app import models  # noqa: F401

        engine = create_engine(database_url, pool_pre_ping=True)
        SQLModel.metadata.create_all(engine)
        _stamp_head(database_url)

        print(f"[bootstrap-sqlite-schema] ok: initialized {db_path}")
        return 0
    except Exception as exc:
        print(f"[bootstrap-sqlite-schema] fail: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
