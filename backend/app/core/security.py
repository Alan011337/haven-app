# backend/app/core/security.py
from datetime import timedelta
import hashlib
from typing import Optional
from passlib.context import CryptContext

# 👇 [修改] 引入 settings
from app.core.config import settings
from app.core.datetime_utils import utcnow

# 設定密碼加密的方式 (使用 bcrypt，這邊維持 argon2 也可以，看你環境有無安裝)
# 如果報錯說找不到 argon2，可以改回 "bcrypt"
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Lazy dummy hash for constant-time login rejection (timing attack mitigation).
# Argon2 hashing at import time can block startup on some systems.
_dummy_hash: str | None = None
_jwt_backend = None


def _get_jwt_backend():
    global _jwt_backend
    if _jwt_backend is None:
        from jose import jwt as jose_jwt
        _jwt_backend = jose_jwt
    return _jwt_backend


def get_dummy_argon2_hash() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = pwd_context.hash("__timing_safe_dummy__")
    return _dummy_hash



# 👇 [修改] 這些值現在從 settings 讀取，保持單一來源
ALGORITHM = settings.ALGORITHM

# 1. 驗證密碼
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 2. 加密密碼
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# 3. 產生 JWT Token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = utcnow() + expires_delta
    else:
        # 使用 settings 裡的設定
        expire = utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.setdefault("typ", "access")
    to_encode.update({"exp": expire})

    # 👇 [關鍵] 使用 settings.SECRET_KEY 簽名
    encoded_jwt = _get_jwt_backend().encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = utcnow() + expires_delta
    else:
        expire = utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"typ": "refresh", "exp": expire})
    return _get_jwt_backend().encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def hash_refresh_token_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
