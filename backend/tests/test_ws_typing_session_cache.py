from __future__ import annotations

import time

from app.services.ws_typing_session_cache import WsTypingSessionCache


def test_ws_typing_session_cache_hit_and_expire() -> None:
    cache = WsTypingSessionCache(ttl_seconds=0.05, max_entries=32)
    key = cache.build_key(
        sender_user_id="user-a",
        partner_user_id="user-b",
        raw_session_id="abc",
    )
    assert cache.get(key) is None

    cache.set(key, "session-1")
    assert cache.get(key) == "session-1"

    time.sleep(0.06)
    assert cache.get(key) is None


def test_ws_typing_session_cache_prunes_overflow() -> None:
    cache = WsTypingSessionCache(ttl_seconds=5.0, max_entries=3)
    for idx in range(10):
        cache.set(f"k-{idx}", f"v-{idx}")
    assert len(cache._rows) <= 3
