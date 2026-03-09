from typing import Annotated, Optional
import uuid
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.config import settings
from app.db.session import get_session, get_read_session
from app.models import User
from app.middleware.request_context import partner_id_var, user_id_var
from app.services.auth_cookies import get_token_from_request
from app.services.posthog_events import capture_posthog_event

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# ==========================================
# 1. 定義 SessionDep (資料庫連線捷徑)
# ==========================================
SessionDep = Annotated[Session, Depends(get_session)]

# P2-B: Use for read-only endpoints (e.g. journal list); uses replica when DATABASE_READ_REPLICA_URL is set.
ReadSessionDep = Annotated[Session, Depends(get_read_session)]

# ==========================================
# 2. 取得當前使用者 (解析 Token)
# ==========================================
async def get_current_user(
    request: Request,
    session: SessionDep,
) -> User:
    """
    從請求中提取並驗證令牌。
    支持多種令牌來源：
    1. Authorization header: Bearer <token>
    2. httpOnly Cookie: access_token（推薦，安全）
    3. Legacy 支持：以防萬一需要回相容
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    def _capture_unauthorized(reason: str) -> None:
        capture_posthog_event(
            event_name="unauthorized_request",
            distinct_id="system",
            properties={"reason": reason},
        )
    
    # 嘗試從請求中提取令牌（優先級：Authorization header > Cookie）
    token = get_token_from_request(request)
    
    if not token:
        _capture_unauthorized("missing_token")
        raise credentials_exception
    
    # Lazily import jose to avoid blocking app load on some macOS envs
    from jose import jwt, JWTError
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("typ")
        if token_type == "refresh":
            # 不允許使用刷新令牌進行標準 API 請求
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_uuid = uuid.UUID(user_id)
    except JWTError:
        _capture_unauthorized("token_decode_error")
        raise credentials_exception
    except ValueError:
        _capture_unauthorized("token_subject_invalid")
        raise credentials_exception
    
    user = session.get(User, user_uuid)
    if user is None:
        _capture_unauthorized("user_not_found")
        raise credentials_exception
    if not user.is_active:
        _capture_unauthorized("user_inactive")
        raise credentials_exception
    if user.deleted_at is not None:
        _capture_unauthorized("user_soft_deleted")
        raise credentials_exception

    # Make user_id available for structured logs/traces during this request.
    user_id_var.set(str(user.id))
    partner_id_var.set(str(user.partner_id) if user.partner_id else "")
    return user

# ==========================================
# 3. 定義 CurrentUser (使用者捷徑)
# ==========================================
CurrentUser = Annotated[User, Depends(get_current_user)]


def _resolve_admin_allowlist() -> frozenset[str]:
    raw = settings.CS_ADMIN_ALLOWED_EMAILS or ""
    return frozenset(item.strip().lower() for item in raw.split(",") if item.strip())


async def require_admin_user(current_user: CurrentUser) -> User:
    if not settings.CS_ADMIN_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin panel is disabled.",
        )
    allowlist = _resolve_admin_allowlist()
    if not allowlist or current_user.email.lower() not in allowlist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user


CurrentAdminUser = Annotated[User, Depends(require_admin_user)]


def _resolve_admin_write_allowlist() -> frozenset[str]:
    raw = settings.CS_ADMIN_WRITE_EMAILS or ""
    return frozenset(item.strip().lower() for item in raw.split(",") if item.strip())


async def require_admin_write(current_user: CurrentAdminUser) -> User:
    """Require write-level admin privilege (least-privilege enforcement for CP-02)."""
    write_list = _resolve_admin_write_allowlist()
    if not write_list or current_user.email.lower() not in write_list:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin write privileges required.",
        )
    return current_user


CurrentAdminWriteUser = Annotated[User, Depends(require_admin_write)]


# ==========================================
# 4. 雙向 Partner 驗證 (BOLA 防禦)
# ==========================================
def verify_active_partner_id(
    *,
    session: Session,
    current_user: User,
) -> Optional[uuid.UUID]:
    """
    驗證 partner 配對關係是否為雙向有效。

    僅當 current_user.partner_id 存在，且對方的 partner_id 也指向自己時，
    才回傳 partner_id。否則回傳 None。

    這是防止 OWASP API1:2023 BOLA 的關鍵：
    若一方已解除配對，另一方不應繼續存取前伴侶的資料。
    """
    if not current_user.partner_id:
        return None

    partner = session.get(User, current_user.partner_id)
    if not partner:
        return None

    # 雙向驗證：對方的 partner_id 必須指向自己
    if partner.partner_id != current_user.id:
        return None

    return current_user.partner_id
