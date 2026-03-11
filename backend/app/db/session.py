import logging
import time
from threading import Lock
from typing import Any

from sqlalchemy import event, text
from sqlmodel import create_engine, SQLModel, Session
from app.core.config import settings
from app.db.slow_query_labels import classify_slow_query_kind, query_fingerprint
from app.middleware.request_context import mode_var, request_id_var, route_var

logger = logging.getLogger(__name__)

_DB_RUNTIME_LOCK = Lock()
_DB_RUNTIME_COUNTERS: dict[str, int] = {
    "connect_total": 0,
    "checkout_total": 0,
    "checkin_total": 0,
    "statement_timeout_applied_total": 0,
    "query_total": 0,
    "slow_query_total": 0,
}
_DB_RUNTIME_STATE: dict[str, Any] = {
    "last_slow_query_fingerprint": "-",
    "last_slow_query_kind": "-",
    "last_slow_query_route": "-",
    "last_slow_query_request_id": "-",
    "last_slow_query_duration_ms": 0,
}


def _increment_runtime_counter(key: str, *, amount: int = 1) -> None:
    if amount <= 0:
        return
    with _DB_RUNTIME_LOCK:
        _DB_RUNTIME_COUNTERS[key] = int(_DB_RUNTIME_COUNTERS.get(key, 0)) + int(amount)


def _database_statement_timeout_ms() -> int:
    return max(1000, int(getattr(settings, "DATABASE_STATEMENT_TIMEOUT_MS", 8000)))


def _database_pool_timeout_seconds() -> int:
    return max(1, int(getattr(settings, "DATABASE_POOL_TIMEOUT_SECONDS", 30)))


def _database_slow_query_ms() -> int:
    return max(10, int(getattr(settings, "DATABASE_SLOW_QUERY_MS", 250)))


def _is_postgres_url(url: str | None) -> bool:
    raw = (url or "").strip().lower()
    return raw.startswith("postgresql://") or raw.startswith("postgres://")


def _attach_engine_runtime_hooks(db_engine, *, apply_statement_timeout: bool) -> None:
    @event.listens_for(db_engine, "connect")
    def _on_connect(dbapi_connection, _connection_record) -> None:  # pragma: no cover
        _increment_runtime_counter("connect_total")
        if not apply_statement_timeout:
            return
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute(f"SET statement_timeout = {_database_statement_timeout_ms()}")
            cursor.close()
            _increment_runtime_counter("statement_timeout_applied_total")
        except Exception:
            logger.warning("DB statement timeout setup failed on connect", exc_info=True)

    @event.listens_for(db_engine, "checkout")
    def _on_checkout(*_args) -> None:  # pragma: no cover
        _increment_runtime_counter("checkout_total")

    @event.listens_for(db_engine, "checkin")
    def _on_checkin(*_args) -> None:  # pragma: no cover
        _increment_runtime_counter("checkin_total")

    @event.listens_for(db_engine, "before_cursor_execute")
    def _before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany):  # pragma: no cover
        try:
            _conn.info["_haven_query_started_monotonic"] = time.monotonic()
            _conn.info["_haven_query_statement"] = str(statement or "")
        except Exception:
            return

    @event.listens_for(db_engine, "after_cursor_execute")
    def _after_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany):  # pragma: no cover
        _increment_runtime_counter("query_total")
        started = _conn.info.pop("_haven_query_started_monotonic", None)
        recorded_statement = _conn.info.pop("_haven_query_statement", None) or statement
        if not isinstance(started, (float, int)):
            return
        duration_ms = int(max(0.0, (time.monotonic() - float(started)) * 1000.0))
        if duration_ms < _database_slow_query_ms():
            return
        _increment_runtime_counter("slow_query_total")
        fingerprint = _query_fingerprint(str(recorded_statement or ""))
        query_kind = classify_slow_query_kind(str(recorded_statement or ""))
        route = str(route_var.get() or "-")[:160]
        request_id = str(request_id_var.get() or "-")[:128]
        mode = str(mode_var.get() or "-")[:32]
        with _DB_RUNTIME_LOCK:
            _DB_RUNTIME_STATE["last_slow_query_fingerprint"] = fingerprint
            _DB_RUNTIME_STATE["last_slow_query_kind"] = query_kind
            _DB_RUNTIME_STATE["last_slow_query_route"] = route
            _DB_RUNTIME_STATE["last_slow_query_request_id"] = request_id
            _DB_RUNTIME_STATE["last_slow_query_duration_ms"] = duration_ms
        logger.warning(
            "DB slow query detected: fingerprint=%s kind=%s route=%s mode=%s request_id=%s duration_ms=%d threshold_ms=%d",
            fingerprint,
            query_kind,
            route,
            mode,
            request_id,
            duration_ms,
            _database_slow_query_ms(),
        )


def _query_fingerprint(statement: str) -> str:
    return query_fingerprint(statement)


def get_db_pool_runtime_snapshot() -> dict[str, Any]:
    pool = getattr(engine, "pool", None)
    checked_out = int(getattr(pool, "checkedout", lambda: 0)() if pool else 0)
    overflow = int(getattr(pool, "overflow", lambda: 0)() if pool else 0)
    size = int(getattr(pool, "size", lambda: 0)() if pool else 0)
    with _DB_RUNTIME_LOCK:
        counters = dict(_DB_RUNTIME_COUNTERS)
        state = dict(_DB_RUNTIME_STATE)
    return {
        "captured_at_unix": int(time.time()),
        "statement_timeout_ms": _database_statement_timeout_ms(),
        "pool_timeout_seconds": _database_pool_timeout_seconds(),
        "checked_out": checked_out,
        "overflow": overflow,
        "size": size,
        "slow_query_threshold_ms": _database_slow_query_ms(),
        "counters": counters,
        "state": state,
    }


def get_db_query_runtime_snapshot() -> dict[str, Any]:
    with _DB_RUNTIME_LOCK:
        counters = dict(_DB_RUNTIME_COUNTERS)
        state = dict(_DB_RUNTIME_STATE)
    return {
        "captured_at_unix": int(time.time()),
        "slow_query_threshold_ms": _database_slow_query_ms(),
        "query_total": int(counters.get("query_total", 0)),
        "slow_query_total": int(counters.get("slow_query_total", 0)),
        "last_slow_query_fingerprint": str(state.get("last_slow_query_fingerprint", "-")),
        "last_slow_query_kind": str(state.get("last_slow_query_kind", "-")),
        "last_slow_query_route": str(state.get("last_slow_query_route", "-")),
        "last_slow_query_request_id": str(state.get("last_slow_query_request_id", "-")),
        "last_slow_query_duration_ms": int(state.get("last_slow_query_duration_ms", 0)),
    }


# 🚀 Added max_overflow for connection pool headroom under burst traffic.
# pool_pre_ping ensures stale connections are recycled before use.
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=max(2, settings.DATABASE_POOL_SIZE),
    pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
    pool_timeout=_database_pool_timeout_seconds(),
)
_attach_engine_runtime_hooks(
    engine,
    apply_statement_timeout=_is_postgres_url(settings.DATABASE_URL),
)

# P2-B: Read replica engine (optional). When set, use for read-only queries.
_read_replica_url = (settings.DATABASE_READ_REPLICA_URL or "").strip()
engine_read = (
    create_engine(
        _read_replica_url,
        echo=settings.SQL_ECHO,
        pool_pre_ping=True,
        pool_size=max(2, settings.DATABASE_POOL_SIZE - 1),
        max_overflow=max(2, settings.DATABASE_POOL_SIZE - 1),
        pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
        pool_timeout=_database_pool_timeout_seconds(),
    )
    if _read_replica_url
    else engine
)
if engine_read is not engine:
    _attach_engine_runtime_hooks(
        engine_read,
        apply_statement_timeout=_is_postgres_url(_read_replica_url),
    )

# 3. 初始化資料庫
def init_db():
    from app import models  # noqa: F401 — side-effect import registers SQLModel tables

    logger.info("Initializing database tables")
    SQLModel.metadata.create_all(engine)
    logger.info("Database table initialization complete")

# 4. Dependency (給 FastAPI 用)
def get_session():
    with Session(engine) as session:
        yield session


def get_read_session():
    """Use for read-only queries (e.g. journal list, history). Uses replica when DATABASE_READ_REPLICA_URL is set."""
    with Session(engine_read) as session:
        yield session


def run_db_runtime_smoke_query() -> int:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    return int(result or 0)
