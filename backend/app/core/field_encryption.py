"""Field-level encryption helpers for top-sensitive text fields.

Implementation notes:
- Uses a versioned envelope (`enc:v1:`) for forward compatibility.
- Uses encrypt-then-MAC with HMAC-SHA256 derived subkeys.
- Backward compatible with legacy plaintext rows (non-prefixed payloads).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
from dataclasses import dataclass

from sqlalchemy.types import Text, TypeDecorator

from app.core.config import settings

ENCRYPTED_PREFIX = "enc:v1:"
_NONCE_BYTES = 16
_MAC_BYTES = 32


@dataclass(frozen=True)
class FieldEncryptionConfigError(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


def _load_master_key() -> bytes | None:
    if not settings.FIELD_LEVEL_ENCRYPTION_ENABLED:
        return None

    raw_key = (settings.FIELD_LEVEL_ENCRYPTION_KEY or "").strip()
    if not raw_key:
        raise FieldEncryptionConfigError(
            "FIELD_LEVEL_ENCRYPTION_KEY is required when FIELD_LEVEL_ENCRYPTION_ENABLED=true"
        )

    try:
        key = base64.urlsafe_b64decode(raw_key.encode("ascii"))
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise FieldEncryptionConfigError(
            "FIELD_LEVEL_ENCRYPTION_KEY must be urlsafe base64"
        ) from exc

    if len(key) != 32:
        raise FieldEncryptionConfigError(
            "FIELD_LEVEL_ENCRYPTION_KEY must decode to exactly 32 bytes"
        )
    return key


def _derive_subkey(master_key: bytes, purpose: bytes) -> bytes:
    return hmac.new(master_key, b"haven-field-encryption:" + purpose, hashlib.sha256).digest()


def _xor_stream(payload: bytes, key: bytes, nonce: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(payload):
        block = hmac.new(
            key,
            nonce + counter.to_bytes(8, "big"),
            hashlib.sha256,
        ).digest()
        output.extend(block)
        counter += 1
    return bytes(a ^ b for a, b in zip(payload, output[: len(payload)]))


def encrypt_field_value(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    if value.startswith(ENCRYPTED_PREFIX):
        return value

    master_key = _load_master_key()
    if master_key is None:
        return value

    nonce = os.urandom(_NONCE_BYTES)
    plaintext = value.encode("utf-8")
    enc_key = _derive_subkey(master_key, b"enc")
    mac_key = _derive_subkey(master_key, b"mac")

    ciphertext = _xor_stream(plaintext, enc_key, nonce)
    mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    envelope = nonce + mac + ciphertext
    encoded = base64.urlsafe_b64encode(envelope).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{encoded}"


def decrypt_field_value(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    if not value.startswith(ENCRYPTED_PREFIX):
        return value

    master_key = _load_master_key()
    if master_key is None:
        raise FieldEncryptionConfigError(
            "Encrypted data found while FIELD_LEVEL_ENCRYPTION_ENABLED=false"
        )

    encoded = value[len(ENCRYPTED_PREFIX) :]
    try:
        envelope = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise FieldEncryptionConfigError("Encrypted data is not valid base64 payload") from exc

    minimum_size = _NONCE_BYTES + _MAC_BYTES
    if len(envelope) < minimum_size:
        raise FieldEncryptionConfigError("Encrypted payload is truncated")

    nonce = envelope[:_NONCE_BYTES]
    expected_mac = envelope[_NONCE_BYTES : _NONCE_BYTES + _MAC_BYTES]
    ciphertext = envelope[_NONCE_BYTES + _MAC_BYTES :]

    enc_key = _derive_subkey(master_key, b"enc")
    mac_key = _derive_subkey(master_key, b"mac")
    actual_mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_mac, actual_mac):
        raise FieldEncryptionConfigError("Encrypted payload MAC mismatch")

    plaintext = _xor_stream(ciphertext, enc_key, nonce)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FieldEncryptionConfigError("Encrypted payload cannot decode to utf-8") from exc


class EncryptedText(TypeDecorator[str]):
    """Transparent encrypted text type for SQLAlchemy/SQLModel."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect):  # type: ignore[override]
        return encrypt_field_value(value)

    def process_result_value(self, value: str | None, dialect):  # type: ignore[override]
        return decrypt_field_value(value)
