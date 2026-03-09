from __future__ import annotations

from typing import Any

from app.schemas import ApiEnvelope, ApiError, ApiMeta


def build_success_envelope(*, request_id: str, data: Any) -> dict[str, Any]:
    """Build API v2 success envelope."""
    payload = ApiEnvelope[Any](data=data, meta=ApiMeta(request_id=request_id), error=None)
    encoded = payload.model_dump(mode="json")
    # Legacy compatibility during cutover: preserve dict payload at top-level
    if isinstance(data, dict):
        for key, value in data.items():
            encoded.setdefault(key, value)
    return encoded


def build_error_envelope(
    *,
    request_id: str,
    status_code: int,
    message: str,
    details: Any = None,
    code: str | None = None,
) -> dict[str, Any]:
    """Build API v2 error envelope."""
    error_code = code or f"http_{status_code}"
    payload = ApiEnvelope[None](
        data=None,
        meta=ApiMeta(request_id=request_id),
        error=ApiError(code=error_code, message=message, details=details),
    )
    encoded = payload.model_dump(mode="json")
    # Legacy compatibility: keep top-level detail in error responses.
    encoded["detail"] = details if details is not None else message
    return encoded

