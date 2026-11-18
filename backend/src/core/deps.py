"""FastAPI 依赖注入：数据库会话、当前用户与权限校验。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.cache import cached_json
from src.core.config import Settings, get_settings
from src.core.exceptions import ForbiddenError, UnauthorizedError
from src.core.permissions import expand_permissions
from src.core.security import decode_access_token
from src.db.session import DatabaseSession, get_db
from src.models.user import Role, User

DbSession = Annotated[DatabaseSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

DATA_SCOPE_ALL = "all"
DATA_SCOPE_SELF = "self"
DATA_SCOPE_DEPT = "dept"


class CurrentUser(BaseModel):
    """认证后的用户上下文，供服务层使用。"""

    id: int
    username: str
    real_name: str = ""
    is_superuser: bool = False
    dept_id: int | None = None
    data_scope: str = Field(default=DATA_SCOPE_SELF, description="数据范围 all/self/dept")
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    menu_ids: list[int] = Field(default_factory=list, description="角色可访问的菜单 ID")


def extract_token(authorization: str | None) -> str:
    """解析 Authorization 头，兼容 'Bearer <token>' 与裸 token 两种形式。"""
    if not authorization:
        raise UnauthorizedError()
    value = authorization.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    if not value:
        raise UnauthorizedError()
    return value


async def get_current_user(
    session: DbSession,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> CurrentUser:
    """校验 JWT 并加载用户、角色与菜单权限（带缓存）。

    权限上下文读多写少且解析涉及多表查询，是高频请求热点；按用户 ID 缓存
    300 秒。用户状态、角色授权或菜单权限变更时由写路径主动失效缓存。
    """
    payload = decode_access_token(extract_token(authorization), settings)
    user_id = int(payload.sub)

    async def load() -> CurrentUser:
        statement = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.menus))
            .where(User.id == user_id)
        )
        user = (await session.execute(statement)).scalar_one_or_none()
        if user is None:
            raise UnauthorizedError("用户不存在")
        if user.status == 2:
            raise ForbiddenError("账号待管理员激活")
        if user.status != 1:
            raise ForbiddenError("账号已停用")

        permissions: set[str] = set()
        menu_ids: set[int] = set()
        for role in user.roles:
            for menu in role.menus:
                if menu.enabled:
                    menu_ids.add(menu.id)
                    if menu.permission_code:
                        permissions.add(menu.permission_code)
        if user.is_superuser:
            permissions.add("*")
        else:
            # 粗粒度权限码蕴含其模块下全部细粒度按钮权限，兼容旧角色授权。
            permissions = expand_permissions(permissions)
        return CurrentUser(
            id=user.id,
            username=user.username,
            real_name=user.real_name,
            is_superuser=user.is_superuser,
            dept_id=user.dept_id,
            data_scope=user.data_scope,
            roles=[role.code for role in user.roles],
            permissions=sorted(permissions),
            menu_ids=sorted(menu_ids),
        )

    return await cached_json(f"auth:ctx:{user_id}", CurrentUser, load, settings=settings)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_permissions(*required: str):
    """返回一个依赖，用于校验当前用户是否拥有全部指定权限码。"""

    async def dependency(user: CurrentUserDep) -> CurrentUser:
        if user.is_superuser or "*" in user.permissions:
            return user
        missing = [code for code in required if code not in user.permissions]
        if missing:
            raise ForbiddenError(f"缺少权限: {', '.join(missing)}")
        return user

    return dependency
