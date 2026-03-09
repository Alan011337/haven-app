"""
Lightweight in-process metric counter for quick observability without external deps.
Not intended as full monitoring — just a safe, low-risk helper to count events.
"""
from __future__ import annotations

from threading import Lock
from typing import Dict, Optional

_counters: Dict[str, int] = {}
_lock = Lock()


def increment(name: str, tags: Optional[Dict[str, str]] = None) -> None:
    """Increment a named counter. Tags are accepted for API parity but not stored.
    Keep implementation minimal to avoid adding external deps.
    """
    global _counters
    with _lock:
        _counters[name] = _counters.get(name, 0) + 1


def get_counter(name: str) -> int:
    with _lock:
        return _counters.get(name, 0)


def snapshot() -> Dict[str, int]:
    with _lock:
        return dict(_counters)
