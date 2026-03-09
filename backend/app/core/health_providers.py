from __future__ import annotations

import logging
import time

from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import engine as db_engine

logger = logging.getLogger(__name__)


def probe_database(*, engine=db_engine) -> dict:
    started = time.perf_counter()
    try:
        with Session(engine) as session:
            session.exec(select(1)).first()
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.warning("Health check database probe failed: reason=%s", type(exc).__name__)
        return {
            "status": "error",
            "latency_ms": latency_ms,
            "error": type(exc).__name__,
        }

    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"status": "ok", "latency_ms": latency_ms}


def probe_redis_if_configured() -> dict:
    backend = (settings.ABUSE_GUARD_STORE_BACKEND or "memory").strip().lower()
    if backend != "redis":
        return {"status": "skipped", "reason": "backend_not_redis"}

    redis_url = (settings.ABUSE_GUARD_REDIS_URL or "").strip()
    if not redis_url:
        return {"status": "error", "reason": "missing_redis_url"}

    try:
        import redis
    except Exception:
        return {"status": "error", "reason": "redis_package_missing"}

    started = time.perf_counter()
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.warning("Health check redis probe failed: reason=%s", type(exc).__name__)
        return {
            "status": "error",
            "latency_ms": latency_ms,
            "error": type(exc).__name__,
        }

    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"status": "ok", "latency_ms": latency_ms}


def provider_checks() -> dict:
    openai_key_ready = bool((settings.OPENAI_API_KEY or "").strip())
    email_key_ready = bool((settings.RESEND_API_KEY or "").strip())

    return {
        "openai": {
            "status": "ok" if openai_key_ready else "error",
            "configured": openai_key_ready,
        },
        "email": {
            "status": "ok" if email_key_ready else "warning",
            "configured": email_key_ready,
        },
    }
