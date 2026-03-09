"""Identity and fingerprint helpers shared by AI router runtime."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any


def normalize_idempotency_key(*, idempotency_key: str | None, request_id: str | None) -> str:
    raw = (idempotency_key or request_id or "").strip()
    if 8 <= len(raw) <= 200:
        return raw
    return str(uuid.uuid4())


def build_normalized_content_hash(content: str) -> str:
    normalized = (content or "").strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest


def canonical_json_dumps(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def build_input_fingerprint(*, payload: dict[str, Any]) -> str:
    canonical = canonical_json_dumps(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_router_key(*, subject_key: str, request_class: str, idempotency_key: str) -> str:
    safe_subject = (subject_key or "anonymous").strip() or "anonymous"
    raw = f"v1:{safe_subject}:{request_class}:{idempotency_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

