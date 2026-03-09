"""
auth_cookies.py — 管理 httpOnly Cookie 的認證策略

此模組負責：
1. 在登入/刷新後設置 httpOnly Cookie
2. 從請求 Cookie 中提取令牌（用於 WebSocket）
3. 在登出時清除 Cookie
4. 確保 CSRF 保護
"""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import Response, Request
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cookie 名稱常數
ACCESS_TOKEN_COOKIE_NAME = "access_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
CSRF_TOKEN_COOKIE_NAME = "csrf_token"


def _get_cookie_domain() -> Optional[str]:
    """獲取 Cookie domain，用於跨子域共享。"""
    if not settings.COOKIE_DOMAIN:
        return None
    return settings.COOKIE_DOMAIN


def _get_cookie_secure() -> bool:
    """確定 Cookie 是否應為 secure（HTTPS only）。"""
    return settings.ENVIRONMENT == "production" or settings.COOKIE_SECURE


def set_auth_cookies(
    response: Response,
    access_token: str,
    access_token_expires_delta: timedelta,
    refresh_token: Optional[str] = None,
    refresh_token_expires_delta: Optional[timedelta] = None,
) -> None:
    """
    在響應中設置 httpOnly Cookie。
    
    Args:
        response: FastAPI 響應對象
        access_token: 訪問令牌
        access_token_expires_delta: 訪問令牌過期時間
        refresh_token: 刷新令牌（可選）
        refresh_token_expires_delta: 刷新令牌過期時間（可選）
    """
    secure = _get_cookie_secure()
    domain = _get_cookie_domain()
    
    # 設置訪問令牌 Cookie
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        max_age=int(access_token_expires_delta.total_seconds()),
        expires=int(access_token_expires_delta.total_seconds()),
        httponly=True,  # 防止 JavaScript 訪問
        secure=secure,  # HTTPS only（生產環境）
        samesite="lax",  # CSRF 防護
        domain=domain,
    )
    
    # 設置刷新令牌 Cookie（如果提供）
    if refresh_token and refresh_token_expires_delta:
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            max_age=int(refresh_token_expires_delta.total_seconds()),
            expires=int(refresh_token_expires_delta.total_seconds()),
            httponly=True,
            secure=secure,
            samesite="lax",
            domain=domain,
        )
    
    logger.info("Auth cookies set for user (access_token + refresh_token if applicable)")


def clear_auth_cookies(response: Response) -> None:
    """清除認證 Cookie。"""
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        secure=_get_cookie_secure(),
        samesite="lax",
        domain=_get_cookie_domain(),
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        secure=_get_cookie_secure(),
        samesite="lax",
        domain=_get_cookie_domain(),
    )
    logger.info("Auth cookies cleared")


def get_access_token_from_cookies(request: Request) -> Optional[str]:
    """從 Cookie 中提取訪問令牌。"""
    return request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)


def get_refresh_token_from_cookies(request: Request) -> Optional[str]:
    """從 Cookie 中提取刷新令牌。"""
    return request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)


def get_token_from_request(request: Request) -> Optional[str]:
    """
    從請求中獲取令牌（優先級：Authorization header > Cookie）。
    
    用於 WebSocket 和其他需要靈活認證方式的端點。
    """
    # 首先嘗試 Authorization header（例如：Bearer <token>）
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # 移除 "Bearer " 前綴
    
    # 否則，嘗試從 Cookie 中獲取
    return get_access_token_from_cookies(request)
