from __future__ import annotations

import json
import time
import uuid
from copy import deepcopy
from threading import Lock
from typing import Any, Iterable, Protocol


class AbuseStateStore(Protocol):
    supports_global_cleanup_scan: bool

    def load(self, key: str) -> dict[str, Any] | None:
        ...

    def save(self, key: str, value: dict[str, Any], *, ttl_seconds: int | None = None) -> None:
        ...

    def delete(self, key: str) -> None:
        ...

    def iter_keys(self) -> Iterable[str]:
        ...


class InMemoryAbuseStateStore:
    supports_global_cleanup_scan = True

    def __init__(self) -> None:
        self._lock = Lock()
        self._data: dict[str, dict[str, Any]] = {}

    def load(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            payload = self._data.get(key)
            return deepcopy(payload) if payload is not None else None

    def save(self, key: str, value: dict[str, Any], *, ttl_seconds: int | None = None) -> None:
        with self._lock:
            self._data[key] = deepcopy(value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def iter_keys(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())


class RedisAbuseStateStore:
    supports_global_cleanup_scan = False
    _SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local seq_key = KEYS[2]
local now = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])
local limit_count = tonumber(ARGV[3])
local ttl_seconds = tonumber(ARGV[4])
local cutoff = now - window_seconds

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)

if count >= limit_count then
  local first = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local earliest = tonumber(first[2]) or now
  local retry_after = math.floor((earliest + window_seconds) - now)
  if retry_after < 1 then
    retry_after = 1
  end
  if ttl_seconds > 0 then
    redis.call('EXPIRE', key, ttl_seconds)
    redis.call('EXPIRE', seq_key, ttl_seconds)
  end
  return {0, retry_after}
end

local sequence = redis.call('INCR', seq_key)
local member = tostring(now) .. ':' .. tostring(sequence) .. ':' .. ARGV[5]
redis.call('ZADD', key, now, member)
if ttl_seconds > 0 then
  redis.call('EXPIRE', key, ttl_seconds)
  redis.call('EXPIRE', seq_key, ttl_seconds)
end
return {1, 0}
"""

    def __init__(self, *, redis_url: str, key_prefix: str) -> None:
        try:
            import redis
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Redis state store requires the 'redis' package. "
                "Install it or switch ABUSE_GUARD_STORE_BACKEND=memory."
            ) from exc

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix

    def _full_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    def _sliding_window_seq_key(self, key: str) -> str:
        return f"{self._full_key(key)}:seq"

    def load(self, key: str) -> dict[str, Any] | None:
        raw = self._client.get(self._full_key(key))
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.delete(key)
            return None
        if isinstance(payload, dict):
            return payload
        self.delete(key)
        return None

    def save(self, key: str, value: dict[str, Any], *, ttl_seconds: int | None = None) -> None:
        full_key = self._full_key(key)
        payload = json.dumps(value, separators=(",", ":"))
        if ttl_seconds and ttl_seconds > 0:
            self._client.set(full_key, payload, ex=int(ttl_seconds))
            return
        self._client.set(full_key, payload)

    def delete(self, key: str) -> None:
        self._client.delete(self._full_key(key))

    def iter_keys(self) -> list[str]:
        match_pattern = f"{self._key_prefix}*"
        keys: list[str] = []
        for full_key in self._client.scan_iter(match=match_pattern):
            if full_key.startswith(self._key_prefix):
                keys.append(full_key[len(self._key_prefix) :])
        return keys

    def allow_and_record_sliding_window(
        self,
        *,
        key: str,
        limit_count: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        safe_limit = max(1, int(limit_count))
        safe_window = max(1, int(window_seconds))
        now_ts = float(time.time())
        ttl_seconds = safe_window + 60
        nonce = uuid.uuid4().hex
        result = self._client.eval(
            self._SLIDING_WINDOW_LUA,
            2,
            self._full_key(key),
            self._sliding_window_seq_key(key),
            now_ts,
            safe_window,
            safe_limit,
            ttl_seconds,
            nonce,
        )
        if not isinstance(result, list) or len(result) < 2:
            return True, 0
        allowed = bool(int(result[0]))
        retry_after = max(0, int(result[1] or 0))
        return allowed, retry_after
