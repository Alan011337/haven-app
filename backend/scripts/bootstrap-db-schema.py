#!/usr/bin/env python3
"""
Bootstrap a brand-new database with current SQLModel metadata and stamp
Alembic revision to head.

Supported targets:
- PostgreSQL / Postgres
- SQLite file URLs

Safety guards:
- Refuses to run if the database already contains tables.
- Refuses sqlite in-memory URLs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Set

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine.url import make_url
from sqlmodel import SQLModel

BACKEND_DIR = Path(__file__).resolve().parents[1]
SUPPORTED_BACKENDS = {"postgresql", "postgres", "sqlite"}


def _resolve_database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        raise RuntimeError("DATABASE_URL is required.")
    return raw


def _validate_supported_backend(database_url: str) -> str:
    parsed = make_url(database_url)
    backend_name = parsed.get_backend_name()
    if backend_name not in SUPPORTED_BACKENDS:
        raise RuntimeError(
            "Only postgres/postgresql and sqlite DATABASE_URL values are supported "
            "by this bootstrap script."
        )
    if backend_name == "sqlite":
        raw_db_path = parsed.database or ""
        if not raw_db_path or raw_db_path == ":memory:":
            raise RuntimeError("DATABASE_URL must point to a sqlite file path, not in-memory.")
    return backend_name


def _prepare_sqlite_parent_dir(database_url: str) -> None:
    parsed = make_url(database_url)
    if parsed.get_backend_name() != "sqlite":
        return

    raw_db_path = parsed.database or ""
    db_path = Path(raw_db_path)
    if not db_path.is_absolute():
        db_path = (BACKEND_DIR / db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _read_existing_tables(database_url: str) -> Set[str]:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        return set(inspector.get_table_names())
    finally:
        engine.dispose()


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
        backend_name = _validate_supported_backend(database_url)
        existing_tables = _read_existing_tables(database_url)
        if existing_tables:
            preview = ", ".join(sorted(existing_tables)[:10])
            raise RuntimeError(
                "Refusing to bootstrap non-empty database. "
                f"Found tables: {preview}"
            )

        _prepare_sqlite_parent_dir(database_url)

        # Ensure all SQLModel metadata is registered before create_all.
        from app import models  # noqa: F401

        engine = create_engine(database_url, pool_pre_ping=True)
        try:
            SQLModel.metadata.create_all(engine)
        finally:
            engine.dispose()

        _stamp_head(database_url)

        print(f"[bootstrap-db-schema] ok: initialized {backend_name} database and stamped head")
        return 0
    except Exception as exc:
        print(f"[bootstrap-db-schema] fail: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
