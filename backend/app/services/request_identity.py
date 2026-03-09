from __future__ import annotations

import re

from fastapi import Request

# Allowed characters for device IDs: alphanumeric, dots, hyphens, underscores.
# Rejects special chars that could enable log injection or rate-limit bucket pollution.
_DEVICE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._\-]{1,128}$")


def resolve_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def resolve_device_id(
    request: Request,
    *,
    header_name: str = "x-device-id",
) -> str | None:
    header_candidates = [header_name, "x-client-id"]
    for candidate in header_candidates:
        raw_value = request.headers.get(candidate)
        if raw_value is None:
            continue
        normalized = raw_value.strip()[:128]
        if normalized and _DEVICE_ID_PATTERN.match(normalized):
            return normalized
    return None
