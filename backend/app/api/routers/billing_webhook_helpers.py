from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from typing import Optional

from fastapi import HTTPException, status


def parse_stripe_signature_header(signature_header: str) -> tuple[int, list[str]]:
    timestamp: Optional[int] = None
    signatures: list[str] = []

    for part in signature_header.split(","):
        key, _, value = part.strip().partition("=")
        if not key or not value:
            continue
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Stripe-Signature timestamp.",
                ) from exc
        elif key == "v1":
            signatures.append(value)

    if timestamp is None or not signatures:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe-Signature header.",
        )
    return timestamp, signatures


def verify_stripe_signature_or_raise(
    *,
    payload: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int,
) -> None:
    timestamp, signatures = parse_stripe_signature_header(signature_header)

    tolerance = max(1, int(tolerance_seconds))
    now_epoch = int(time.time())
    if abs(now_epoch - timestamp) > tolerance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook signature timestamp is outside tolerance window.",
        )

    try:
        payload_text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload must be valid UTF-8 JSON.",
        ) from exc

    signed_payload = f"{timestamp}.{payload_text}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not any(hmac.compare_digest(expected, value) for value in signatures):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature.",
        )


def extract_user_id_from_webhook_payload(payload: dict) -> Optional[uuid.UUID]:
    candidate_paths = [
        payload.get("user_id"),
        payload.get("metadata", {}).get("user_id"),
        payload.get("data", {}).get("object", {}).get("metadata", {}).get("user_id"),
    ]
    for value in candidate_paths:
        if value is None:
            continue
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError):
            continue
    return None


def extract_customer_identifier_from_webhook_payload(payload: dict) -> Optional[str]:
    object_payload = payload.get("data", {}).get("object", {})
    candidates = [
        object_payload.get("customer"),
        payload.get("customer"),
        object_payload.get("customer_id"),
        object_payload.get("metadata", {}).get("customer"),
    ]
    for value in candidates:
        normalized = (str(value).strip() if value is not None else "")
        if normalized:
            return normalized
    return None


def extract_subscription_identifier_from_webhook_payload(
    payload: dict,
    *,
    event_type: Optional[str],
) -> Optional[str]:
    object_payload = payload.get("data", {}).get("object", {})
    candidates = [
        object_payload.get("subscription"),
        payload.get("subscription"),
    ]
    if (event_type or "").startswith("customer.subscription."):
        candidates.append(object_payload.get("id"))

    for value in candidates:
        normalized = (str(value).strip() if value is not None else "")
        if normalized:
            return normalized
    return None


def webhook_retry_backoff_seconds(*, base_seconds: int, attempt_count: int) -> int:
    safe_base = max(1, int(base_seconds))
    safe_attempt = max(0, int(attempt_count) - 1)
    seconds = safe_base * (2**safe_attempt)
    return max(1, min(int(seconds), 3600))
