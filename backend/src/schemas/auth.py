"""认证相关请求/响应 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.common import Iso8601DateTime


class LoginIn(BaseModel):
    """登录请求。"""

    username: str = Field(min_length=1, max_length=64, description="用户名")
    password: str = Field(min_length=1, max_length=128, description="明文口令")


class RegisterIn(BaseModel):
    """用户自助注册请求，注册后需管理员激活。"""

    username: str = Field(min_length=1, max_length=64, description="用户名")
    password: str = Field(min_length=6, max_length=128, description="明文口令，至少 6 位")
    real_name: str = Field(default="", max_length=64, description="姓名")
    email: str | None = Field(default=None, max_length=128, description="邮箱")


class RegisterOut(BaseModel):
    """注册结果，只回显用户名与激活提示，不签发令牌。"""

    username: str
    message: str = "注册成功，请等待管理员激活后登录"


class UserBriefOut(BaseModel):
    """前端会话中保存的用户信息。"""

    id: int
    username: str
    real_name: str = ""
    is_superuser: bool = False
    dept_id: int | None = None
    data_scope: str = "self"
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class LoginOut(BaseModel):
    """登录结果，字段名与前端 LoginResult 保持一致。"""

    accessToken: str = Field(description="JWT 访问令牌")
    tokenType: str = Field(default="Bearer", description="令牌类型")
    expiresIn: int = Field(description="有效期（秒）")
    user: UserBriefOut


class CurrentUserOut(BaseModel):
    """当前登录用户详情。"""

    id: int
    username: str
    real_name: str
    email: str | None = None
    is_superuser: bool = False
    dept_id: int | None = None
    data_scope: str = "self"
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    last_login_at: Iso8601DateTime | None = None


class RequestMeta(BaseModel):
    """从 HTTP 请求中提取的审计信息，由路由层传给服务层。"""

    ip: str = ""
    user_agent: str = ""
    method: str = ""
    path: str = ""
