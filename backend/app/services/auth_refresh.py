from __future__ import annotations

import hmac
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session

from app.api.error_handling import commit_with_error_handling
from app.core.datetime_utils import utcnow
from app.core.security import hash_refresh_token_value
from app.models.auth_refresh_session import AuthRefreshSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RefreshSessionRotationResult:
    ok: bool
    reason: str
    session: AuthRefreshSession | None = None
    new_jti: str | None = None


def create_refresh_session(
    *,
    session: Session,
    user_id: uuid.UUID,
    raw_jti: str,
    expires_at: datetime,
    device_id: str | None,
    client_ip: str | None,
    user_agent: str | None,
) -> AuthRefreshSession:
    token_hash = hash_refresh_token_value(raw_jti)
    if not token_hash:
        raise ValueError("raw_jti must be non-empty")

    row = AuthRefreshSession(
        user_id=user_id,
        current_token_hash=token_hash,
        device_id=device_id,
        client_ip_hash=hash_refresh_token_value(client_ip),
        user_agent_hash=hash_refresh_token_value(user_agent),
        expires_at=expires_at,
    )
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="auth_refresh_create",
        conflict_detail="Refresh session create conflict. Please retry.",
        failure_detail="Refresh session create failed.",
    )
    session.refresh(row)
    return row


def rotate_refresh_session(
    *,
    session: Session,
    refresh_session: AuthRefreshSession,
    presented_jti: str,
    request_device_id: str | None,
    token_device_id: str | None,
    request_client_ip: str | None,
    request_user_agent: str | None,
    refresh_expires_at: datetime,
) -> RefreshSessionRotationResult:
    now = utcnow()

    if refresh_session.revoked_at is not None:
        return RefreshSessionRotationResult(ok=False, reason="session_revoked")
    if refresh_session.expires_at <= now:
        return RefreshSessionRotationResult(ok=False, reason="session_expired")

    expected_device = refresh_session.device_id
    if expected_device:
        if request_device_id and request_device_id != expected_device:
            refresh_session.revoked_at = now
            refresh_session.replayed_at = now
            session.add(refresh_session)
            commit_with_error_handling(
                session,
                logger=logger,
                action="auth_refresh_revoke_device_mismatch",
                conflict_detail="Refresh session update conflict.",
                failure_detail="Refresh session update failed.",
            )
            return RefreshSessionRotationResult(ok=False, reason="device_mismatch")
        if token_device_id and token_device_id != expected_device:
            refresh_session.revoked_at = now
            refresh_session.replayed_at = now
            session.add(refresh_session)
            commit_with_error_handling(
                session,
                logger=logger,
                action="auth_refresh_revoke_token_device_mismatch",
                conflict_detail="Refresh session update conflict.",
                failure_detail="Refresh session update failed.",
            )
            return RefreshSessionRotationResult(ok=False, reason="token_device_mismatch")

    presented_hash = hash_refresh_token_value(presented_jti)
    if not presented_hash:
        return RefreshSessionRotationResult(ok=False, reason="invalid_jti")

    if not hmac.compare_digest(presented_hash, refresh_session.current_token_hash):
        refresh_session.revoked_at = now
        refresh_session.replayed_at = now
        session.add(refresh_session)
        commit_with_error_handling(
            session,
            logger=logger,
            action="auth_refresh_revoke_replay_detected",
            conflict_detail="Refresh session update conflict.",
            failure_detail="Refresh session update failed.",
        )
        return RefreshSessionRotationResult(ok=False, reason="token_replay_detected")

    new_jti = uuid.uuid4().hex
    new_hash = hash_refresh_token_value(new_jti)
    if not new_hash:
        return RefreshSessionRotationResult(ok=False, reason="rotation_hash_failed")

    refresh_session.current_token_hash = new_hash
    refresh_session.last_rotated_at = now
    refresh_session.expires_at = refresh_expires_at
    refresh_session.rotation_counter += 1
    refresh_session.client_ip_hash = hash_refresh_token_value(request_client_ip)
    refresh_session.user_agent_hash = hash_refresh_token_value(request_user_agent)

    session.add(refresh_session)
    commit_with_error_handling(
        session,
        logger=logger,
        action="auth_refresh_rotate",
        conflict_detail="Refresh token rotation conflict. Please retry.",
        failure_detail="Refresh token rotation failed.",
    )
    session.refresh(refresh_session)
    return RefreshSessionRotationResult(
        ok=True,
        reason="rotated",
        session=refresh_session,
        new_jti=new_jti,
    )
