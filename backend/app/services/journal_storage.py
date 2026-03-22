from __future__ import annotations

import mimetypes
import re
import uuid
from urllib.parse import quote

import httpx

from app.core.config import settings


ALLOWED_JOURNAL_IMAGE_TYPES = frozenset(
    {
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)
MAX_JOURNAL_IMAGE_BYTES = 5 * 1024 * 1024


class JournalStorageConfigError(RuntimeError):
    """Raised when journal media storage is not configured."""


def _storage_origin() -> str:
    raw = (
        getattr(settings, "SUPABASE_URL", None)
        or getattr(settings, "NEXT_PUBLIC_SUPABASE_URL", None)
        or ""
    )
    origin = str(raw).strip().rstrip("/")
    if not origin:
        raise JournalStorageConfigError("SUPABASE_URL is not configured")
    return origin


def _service_role_key() -> str:
    raw = str(getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "") or "").strip()
    if not raw:
        raise JournalStorageConfigError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    return raw


def _bucket() -> str:
    return str(getattr(settings, "SUPABASE_STORAGE_JOURNAL_BUCKET", "journal-media") or "journal-media").strip()


def journal_storage_enabled() -> bool:
    try:
        _storage_origin()
        _service_role_key()
    except JournalStorageConfigError:
        return False
    return True


def sanitize_file_name(file_name: str | None, *, fallback_extension: str = ".png") -> str:
    raw = str(file_name or "").strip()
    if not raw:
        return f"image{fallback_extension}"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-")
    if not cleaned:
        return f"image{fallback_extension}"
    if "." not in cleaned:
        return f"{cleaned}{fallback_extension}"
    return cleaned[:120]


def _build_headers(*, content_type: str | None = None) -> dict[str, str]:
    service_role_key = _service_role_key()
    headers = {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key,
        "x-upsert": "false",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def infer_extension(content_type: str, file_name: str | None) -> str:
    guessed = mimetypes.guess_extension(content_type) or ""
    if guessed:
        return guessed
    raw_name = str(file_name or "").strip()
    if "." in raw_name:
        return f".{raw_name.rsplit('.', 1)[-1].lower()}"
    return ".png"


def build_storage_path(
    *,
    attachment_id: uuid.UUID,
    journal_id: uuid.UUID,
    user_id: uuid.UUID,
    file_name: str | None,
    content_type: str,
) -> str:
    extension = infer_extension(content_type, file_name)
    safe_name = sanitize_file_name(file_name, fallback_extension=extension)
    return f"journals/{user_id}/{journal_id}/{attachment_id}-{safe_name}"


async def upload_journal_attachment_bytes(
    *,
    attachment_id: uuid.UUID,
    journal_id: uuid.UUID,
    user_id: uuid.UUID,
    file_name: str | None,
    content_type: str,
    payload: bytes,
) -> str:
    storage_path = build_storage_path(
        attachment_id=attachment_id,
        journal_id=journal_id,
        user_id=user_id,
        file_name=file_name,
        content_type=content_type,
    )
    origin = _storage_origin()
    bucket = _bucket()
    url = f"{origin}/storage/v1/object/{bucket}/{quote(storage_path, safe='/')}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
        response = await client.post(
            url,
            content=payload,
            headers=_build_headers(content_type=content_type),
        )
    response.raise_for_status()
    return storage_path


async def create_signed_journal_attachment_url(
    storage_path: str,
    *,
    expires_in: int,
) -> str:
    origin = _storage_origin()
    bucket = _bucket()
    url = f"{origin}/storage/v1/object/sign/{bucket}/{quote(storage_path, safe='/')}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        response = await client.post(
            url,
            json={"expiresIn": int(max(60, expires_in))},
            headers=_build_headers(),
        )
    response.raise_for_status()
    payload = response.json()
    signed_url = str(payload.get("signedURL") or payload.get("signedUrl") or "").strip()
    if not signed_url:
        raise RuntimeError("Supabase signed URL response missing signedURL")
    if signed_url.startswith("http://") or signed_url.startswith("https://"):
        return signed_url
    return f"{origin}/storage/v1{signed_url}"


async def delete_journal_attachment_object(storage_path: str) -> None:
    origin = _storage_origin()
    bucket = _bucket()
    url = f"{origin}/storage/v1/object/{bucket}/{quote(storage_path, safe='/')}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        response = await client.delete(url, headers=_build_headers())
    response.raise_for_status()
