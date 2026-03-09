from __future__ import annotations

from typing import Optional
from uuid import UUID


def normalize_scope_component(raw_value: str | None, *, fallback: str = "unknown") -> str:
    value = (raw_value or "").strip()
    if not value:
        return fallback
    return value[:128]


def build_partner_pair_scope(*, user_id: UUID, partner_id: UUID | None) -> str:
    if partner_id is None:
        return f"solo:{user_id}"
    first, second = sorted((str(user_id), str(partner_id)))
    return f"pair:{first}:{second}"


def build_rate_limit_scope_key(*, domain: str, scope: str, value: str | None) -> str:
    normalized_domain = normalize_scope_component(domain, fallback="unknown")
    normalized_scope = normalize_scope_component(scope, fallback="unknown")
    normalized_value = normalize_scope_component(value, fallback="unknown")
    return f"{normalized_domain}:{normalized_scope}:{normalized_value}"


def build_ws_message_scope_key(
    *,
    user_id: UUID,
    partner_id: UUID | None,
    client_ip: Optional[str],
    device_id: Optional[str],
    include_ip: bool,
    include_device: bool,
    include_partner_pair: bool,
) -> str:
    parts = [f"user:{normalize_scope_component(str(user_id), fallback='unknown')}"]
    if include_ip and client_ip:
        parts.append(f"ip:{normalize_scope_component(client_ip, fallback='unknown')}")
    if include_device and device_id:
        parts.append(f"device:{normalize_scope_component(device_id, fallback='unknown')}")
    if include_partner_pair and partner_id:
        parts.append(f"{build_partner_pair_scope(user_id=user_id, partner_id=partner_id)}")
    return "|".join(parts)
