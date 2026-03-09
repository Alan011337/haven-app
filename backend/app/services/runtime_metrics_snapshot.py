from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from app.core.config import settings
from app.core.datetime_utils import utcnow

logger = logging.getLogger(__name__)

_SNAPSHOT_LOCK = Lock()
_SNAPSHOT_SCHEMA_VERSION = "v1"


def _snapshot_path() -> Optional[Path]:
    raw = (getattr(settings, "RUNTIME_METRICS_SNAPSHOT_PATH", None) or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def persist_runtime_metrics_snapshot(payload: dict[str, Any]) -> bool:
    path = _snapshot_path()
    if path is None:
        return False
    if not isinstance(payload, dict):
        return False

    envelope = {
        "schema_version": _SNAPSHOT_SCHEMA_VERSION,
        "recorded_at": utcnow().isoformat(),
        "payload": payload,
    }
    try:
        with _SNAPSHOT_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=str(path.parent),
                suffix=".tmp",
            ) as tmp:
                json.dump(envelope, tmp, ensure_ascii=True, separators=(",", ":"))
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = Path(tmp.name)
            os.replace(tmp_path, path)
        return True
    except Exception:
        logger.debug("runtime_metrics_snapshot_persist_failed", exc_info=True)
        return False


def load_runtime_metrics_snapshot(max_age_seconds: int = 900) -> Optional[dict[str, Any]]:
    path = _snapshot_path()
    if path is None or not path.exists():
        return None
    try:
        with _SNAPSHOT_LOCK:
            raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("runtime_metrics_snapshot_read_failed", exc_info=True)
        return None

    if not isinstance(raw, dict):
        return None
    if raw.get("schema_version") != _SNAPSHOT_SCHEMA_VERSION:
        return None
    recorded_at = raw.get("recorded_at")
    payload = raw.get("payload")
    if not isinstance(recorded_at, str) or not isinstance(payload, dict):
        return None
    try:
        from datetime import datetime

        recorded_dt = datetime.fromisoformat(recorded_at)
        age_seconds = (utcnow() - recorded_dt).total_seconds()
    except Exception:
        return None
    if age_seconds > max(1, int(max_age_seconds)):
        return None
    return payload
