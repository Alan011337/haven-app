from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app import models, schemas
from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.core.security import (
    get_dummy_argon2_hash,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.db.session import get_session
from app.services.auth_refresh import create_refresh_session, rotate_refresh_session
from app.services.auth_cookies import set_auth_cookies
from app.services.alpha_allowlist import enforce_alpha_allowlist_or_raise
from app.services.posthog_events import capture_posthog_event
from app.services.rate_limit import enforce_login_rate_limit
from app.services.request_identity import resolve_client_ip, resolve_device_id
from app.services.trace_span import trace_span

router = APIRouter()
logger = logging.getLogger(__name__)
_jwt_backend = None
_jwt_error_type = None


def _get_jwt_backend():
    global _jwt_backend
    global _jwt_error_type
    if _jwt_backend is None or _jwt_error_type is None:
        from jose import JWTError as jose_jwt_error, jwt as jose_jwt

        _jwt_backend = jose_jwt
        _jwt_error_type = jose_jwt_error
    return _jwt_backend


def _jwt_error_types() -> tuple[type[BaseException], ...]:
    global _jwt_error_type
    if _jwt_error_type is None:
        _get_jwt_backend()
    if _jwt_error_type is None:
        return ()
    return (_jwt_error_type,)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _issue_access_refresh_tokens(*, session: Session, request: Request, user: models.User) -> dict[str, str | int]:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    if not settings.REFRESH_TOKEN_ROTATION_ENABLED:
        return {"access_token": access_token, "token_type": "bearer"}

    refresh_expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_expires_at = utcnow() + refresh_expires_delta
    refresh_jti = uuid.uuid4().hex
    device_id = resolve_device_id(request, header_name=settings.RATE_LIMIT_DEVICE_HEADER)
    client_ip = resolve_client_ip(request)
    user_agent = request.headers.get("user-agent")

    refresh_session = create_refresh_session(
        session=session,
        user_id=user.id,
        raw_jti=refresh_jti,
        expires_at=refresh_expires_at,
        device_id=device_id,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    refresh_payload: dict[str, str] = {
        "sub": str(user.id),
        "sid": str(refresh_session.id),
        "jti": refresh_jti,
    }
    if device_id:
        refresh_payload["did"] = device_id

    refresh_token = create_refresh_token(
        data=refresh_payload,
        expires_delta=refresh_expires_delta,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "refresh_expires_in": int(refresh_expires_delta.total_seconds()),
    }


# AUTHZ_MATRIX: POST /api/auth/token
@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session),
):
    with trace_span("api.auth.login"):
        return _login_for_access_token_inner(request, response, form_data, session)


def _login_for_access_token_inner(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm,
    session: Session,
):
    # 0. IP-based rate limiting (brute-force protection)
    client_ip = resolve_client_ip(request)
    enforce_login_rate_limit(
        client_ip=client_ip,
        ip_limit_count=settings.LOGIN_RATE_LIMIT_IP_COUNT,
        ip_window_seconds=settings.LOGIN_RATE_LIMIT_IP_WINDOW_SECONDS,
    )

    # 1. 去資料庫找這個 Email 的使用者
    # (注意：OAuth2PasswordRequestForm 預設欄位叫 username，我們把它當 email 用)
    enforce_alpha_allowlist_or_raise(email=form_data.username, auth_stage="login")
    statement = select(models.User).where(models.User.email == form_data.username)
    user = session.exec(statement).first()

    # 2. 驗證使用者是否存在，以及密碼是否正確
    #    Always run verify_password to prevent timing-based user enumeration.
    if not user:
        verify_password(form_data.password, get_dummy_argon2_hash())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_response = _issue_access_refresh_tokens(
        session=session,
        request=request,
        user=user,
    )
    capture_posthog_event(
        event_name="login_succeeded",
        distinct_id=str(user.id),
        properties={"auth_stage": "login"},
    )
    
    # 🔒 設置 httpOnly Cookie（安全認證）
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    set_auth_cookies(
        response=response,
        access_token=token_response["access_token"],
        access_token_expires_delta=access_token_expires,
        refresh_token=token_response.get("refresh_token"),
        refresh_token_expires_delta=(
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS) 
            if token_response.get("refresh_token") else None
        ),
    )
    
    return token_response


# AUTHZ_MATRIX: POST /api/auth/refresh
@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(
    request: Request,
    response: Response,
    payload: schemas.RefreshTokenRequest,
    session: Session = Depends(get_session),
):
    with trace_span("api.auth.refresh"):
        return _refresh_access_token_inner(request, response, payload, session)


def _refresh_access_token_inner(
    request: Request,
    response: Response,
    payload: schemas.RefreshTokenRequest,
    session: Session,
):
    if not settings.REFRESH_TOKEN_ROTATION_ENABLED:
        capture_posthog_event(
            event_name="token_refresh_failed",
            distinct_id="system",
            properties={"reason": "refresh_rotation_disabled"},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Refresh token rotation disabled",
        )

    credentials_exception = _credentials_exception()
    raw_refresh_token = payload.refresh_token.strip() if payload.refresh_token else ""
    if not raw_refresh_token:
        capture_posthog_event(
            event_name="token_refresh_failed",
            distinct_id="system",
            properties={"reason": "missing_refresh_token"},
        )
        raise credentials_exception

    jwt_backend = _get_jwt_backend()
    jwt_error_types = _jwt_error_types()
    try:
        decoded = jwt_backend.decode(raw_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if decoded.get("typ") != "refresh":
            raise credentials_exception
        sub_value = decoded.get("sub")
        sid_value = decoded.get("sid")
        jti_value = decoded.get("jti")
        if not isinstance(sub_value, str) or not sub_value:
            raise credentials_exception
        if not isinstance(sid_value, str) or not sid_value:
            raise credentials_exception
        if not isinstance(jti_value, str) or not jti_value:
            raise credentials_exception
        token_user_id = uuid.UUID(sub_value)
        token_session_id = uuid.UUID(sid_value)
        token_device_id = decoded.get("did")
        if token_device_id is not None and not isinstance(token_device_id, str):
            raise credentials_exception
    except jwt_error_types + (ValueError,):
        capture_posthog_event(
            event_name="token_refresh_failed",
            distinct_id="system",
            properties={"reason": "token_decode_failed"},
        )
        raise credentials_exception

    user = session.get(models.User, token_user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        capture_posthog_event(
            event_name="token_refresh_failed",
            distinct_id="system",
            properties={"reason": "user_inactive_or_missing"},
        )
        raise credentials_exception

    refresh_session = session.get(models.AuthRefreshSession, token_session_id)
    if not refresh_session:
        capture_posthog_event(
            event_name="token_refresh_failed",
            distinct_id=str(user.id),
            properties={"reason": "refresh_session_missing"},
        )
        raise credentials_exception
    if refresh_session.user_id != user.id:
        capture_posthog_event(
            event_name="token_refresh_failed",
            distinct_id=str(user.id),
            properties={"reason": "refresh_session_subject_mismatch"},
        )
        raise credentials_exception

    request_device_id = resolve_device_id(request, header_name=settings.RATE_LIMIT_DEVICE_HEADER)
    refresh_expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rotate_result = rotate_refresh_session(
        session=session,
        refresh_session=refresh_session,
        presented_jti=jti_value,
        request_device_id=request_device_id,
        token_device_id=token_device_id,
        request_client_ip=resolve_client_ip(request),
        request_user_agent=request.headers.get("user-agent"),
        refresh_expires_at=utcnow() + refresh_expires_delta,
    )
    if not rotate_result.ok or not rotate_result.new_jti or not rotate_result.session:
        logger.warning("Refresh token rotation rejected: reason=%s", rotate_result.reason)
        capture_posthog_event(
            event_name="token_refresh_failed",
            distinct_id=str(user.id),
            properties={"reason": f"rotation_rejected:{rotate_result.reason or 'unknown'}"},
        )
        raise credentials_exception

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    refresh_payload: dict[str, str] = {
        "sub": str(user.id),
        "sid": str(rotate_result.session.id),
        "jti": rotate_result.new_jti,
    }
    if rotate_result.session.device_id:
        refresh_payload["did"] = rotate_result.session.device_id
    refresh_token = create_refresh_token(
        data=refresh_payload,
        expires_delta=refresh_expires_delta,
    )

    token_response = {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "refresh_expires_in": int(refresh_expires_delta.total_seconds()),
    }
    
    # 🔒 設置 httpOnly Cookie（安全認證更新）
    set_auth_cookies(
        response=response,
        access_token=access_token,
        access_token_expires_delta=access_token_expires,
        refresh_token=refresh_token,
        refresh_token_expires_delta=refresh_expires_delta,
    )
    capture_posthog_event(
        event_name="token_refresh_succeeded",
        distinct_id=str(user.id),
        properties={"auth_stage": "refresh"},
    )
    
    return token_response

# AUTHZ_MATRIX: POST /api/auth/logout
@router.post("/logout")
def logout(response: Response):
    """
    登出端點 - 清除認證 Cookie。
    無需身份驗證，因為浏览器會自動發送 Cookie。
    """
    from app.services.auth_cookies import clear_auth_cookies
    clear_auth_cookies(response)
    capture_posthog_event(
        event_name="logout_clicked",
        distinct_id="system",
        properties={"auth_stage": "logout"},
    )
    logger.info("auth.logout_successful")
    return {"message": "Successfully logged out"}
