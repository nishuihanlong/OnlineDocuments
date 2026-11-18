"""安全工具：口令哈希与 JWT 令牌签发/解析。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from pydantic import BaseModel, Field

from src.core.config import Settings
from src.core.exceptions import UnauthorizedError


class TokenPayload(BaseModel):
    """JWT 载荷结构。"""

    sub: str = Field(description="用户 ID")
    username: str = Field(description="用户名")
    exp: int = Field(description="过期时间（Unix 秒）")
    iat: int = Field(description="签发时间（Unix 秒）")


def hash_password(raw_password: str) -> str:
    """使用 bcrypt 生成口令哈希。"""
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password: str, password_hash: str) -> bool:
    """校验明文口令与 bcrypt 哈希是否匹配。"""
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, username: str, settings: Settings) -> str:
    """签发访问令牌，有效期由配置控制。"""
    now = datetime.now(UTC)
    payload = TokenPayload(
        sub=str(user_id),
        username=username,
        iat=int(now.timestamp()),
        exp=int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    )
    return jwt.encode(payload.model_dump(), settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> TokenPayload:
    """解析并校验访问令牌，失败时抛出 401 业务异常。"""
    try:
        raw = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload.model_validate(raw)
    except (jwt.PyJWTError, ValueError) as exc:
        raise UnauthorizedError("令牌无效或已过期") from exc
