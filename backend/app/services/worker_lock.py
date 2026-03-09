from __future__ import annotations

import fcntl
import json
import logging
import os
import threading
from pathlib import Path

from app.core.config import settings
from app.core.datetime_utils import utcnow

logger = logging.getLogger(__name__)


class WorkerSingletonLock:
    def __init__(self, *, lock_name: str, heartbeat_seconds: float | None = None) -> None:
        normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in lock_name)
        self._normalized_lock_name = normalized
        self._lock_file_path = Path(f"/tmp/haven-worker-{normalized}.lock")
        self._heartbeat_seconds = max(
            1.0,
            float(
                heartbeat_seconds
                if heartbeat_seconds is not None
                else getattr(settings, "WORKER_SINGLETON_HEARTBEAT_SECONDS", 5.0)
            ),
        )
        self._lock_fd: int | None = None
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    @property
    def lock_file_path(self) -> Path:
        return self._lock_file_path

    @property
    def heartbeat_seconds(self) -> float:
        return self._heartbeat_seconds

    @property
    def lock_name(self) -> str:
        return self._normalized_lock_name

    def acquire(self) -> bool:
        if not bool(getattr(settings, "WORKER_SINGLETON_LOCK_ENABLED", True)):
            return True
        self._lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self._lock_file_path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._lock_fd = fd
        self._write_state(status="acquired")
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"worker-lock-heartbeat-{self._lock_file_path.name}",
            daemon=True,
        )
        self._heartbeat_thread.start()
        return True

    def release(self) -> None:
        self._heartbeat_stop.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)
        if self._lock_fd is None:
            return
        try:
            self._write_state(status="released")
            fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
        except OSError:
            logger.debug("worker_lock_release_failed", exc_info=True)
        finally:
            try:
                os.close(self._lock_fd)
            except OSError:
                pass
            self._lock_fd = None

    def _heartbeat_loop(self) -> None:
        while not self._heartbeat_stop.wait(self._heartbeat_seconds):
            self._write_state(status="heartbeat")

    def _write_state(self, *, status: str) -> None:
        if self._lock_fd is None:
            return
        payload = {
            "pid": os.getpid(),
            "status": status,
            "updated_at": utcnow().isoformat(),
        }
        try:
            os.lseek(self._lock_fd, 0, os.SEEK_SET)
            os.ftruncate(self._lock_fd, 0)
            os.write(self._lock_fd, json.dumps(payload, ensure_ascii=True).encode("utf-8"))
            os.fsync(self._lock_fd)
        except OSError:
            logger.debug("worker_lock_write_failed", exc_info=True)

    @staticmethod
    def read_lock_state(lock_name: str) -> dict[str, object] | None:
        normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in lock_name)
        lock_path = Path(f"/tmp/haven-worker-{normalized}.lock")
        if not lock_path.exists():
            return None
        try:
            raw = lock_path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        return payload
