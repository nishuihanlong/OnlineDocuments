"""认证业务逻辑：登录、当前用户、登出与登录审计。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.config import Settings
from src.core.exceptions import BadRequestError, UnauthorizedError
from src.core.permissions import expand_permissions
from src.core.security import create_access_token, hash_password, verify_password
from src.db.session import DatabaseSession
from src.models.user import USER_STATUS_ACTIVE, USER_STATUS_PENDING, Role, User
from src.repositories.user import LogRepository, RoleRepository, UserRepository
from src.schemas.auth import (
    CurrentUserOut,
    LoginIn,
    LoginOut,
    RegisterIn,
    RegisterOut,
    RequestMeta,
    UserBriefOut,
)


class AuthService:
    """处理认证相关用例，事务由服务层统一提交。"""

    def __init__(self, session: DatabaseSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.logs = LogRepository(session)

    async def register(self, payload: RegisterIn, meta: RequestMeta) -> RegisterOut:
        """自助注册：绑定内置 user 角色并置为待激活，需管理员激活后方可登录。"""
        existing = await self.users.get_by_username(payload.username)
        if existing is not None:
            raise BadRequestError("用户名已存在")

        user_role = await self.roles.get_by_code("user")
        if user_role is None:
            raise BadRequestError("系统未初始化用户角色，请联系管理员")

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            real_name=payload.real_name or "",
            email=payload.email,
            status=USER_STATUS_PENDING,
            is_superuser=False,
            roles=[user_role],
        )
        self.session.add(user)
        await self.logs.add_operation_log(None, payload.username, "认证", "用户注册", meta)
        await self.session.commit()
        return RegisterOut(username=user.username)

    async def login(self, credentials: LoginIn, meta: RequestMeta) -> LoginOut:
        """校验口令，签发 JWT，并记录登录日志（含失败尝试）。"""
        user = await self.users.get_by_username(credentials.username)
        password_ok = bool(user and verify_password(credentials.password, user.password_hash))

        # 待激活账号给出明确提示，停用账号仍按原来的登录失败处理。
        if user is not None and user.status == USER_STATUS_PENDING and password_ok:
            await self.logs.add_login_log(user.username, meta, False, "账号待激活")
            await self.session.commit()
            raise UnauthorizedError("账号待管理员激活，请联系管理员")

        authenticated = bool(user and user.status == USER_STATUS_ACTIVE and password_ok)
        if not authenticated:
            await self.logs.add_login_log(
                credentials.username, meta, False, "用户名或密码错误"
            )
            await self.session.commit()
            raise UnauthorizedError("用户名或密码错误")

        assert user is not None
        user.last_login_at = datetime.now(UTC)
        await self.logs.add_login_log(user.username, meta, True, "登录成功")
        await self.session.commit()

        # 重新加载带角色与菜单的用户，构造前端可用的角色/权限清单。
        detail = await self.session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.menus))
            .where(User.id == user.id)
        )
        current = detail.scalar_one()
        role_codes = [role.code for role in current.roles]
        permissions = self._permissions_of(current)

        return LoginOut(
            accessToken=create_access_token(user.id, user.username, self.settings),
            tokenType="Bearer",
            expiresIn=self.settings.access_token_expire_minutes * 60,
            user=UserBriefOut(
                id=user.id,
                username=user.username,
                real_name=user.real_name,
                is_superuser=user.is_superuser,
                dept_id=user.dept_id,
                data_scope=user.data_scope,
                roles=role_codes,
                permissions=permissions,
            ),
        )

    @staticmethod
    def _permissions_of(user: User) -> list[str]:
        """汇总用户所有启用菜单的权限码；超管用通配符表示全部权限。"""
        if user.is_superuser:
            return ["*"]
        configured = {
            menu.permission_code
            for role in user.roles
            for menu in role.menus
            if menu.enabled and menu.permission_code
        }
        # 粗码展开为细码集合，前端据此做按钮级显隐。
        return sorted(expand_permissions(configured))

    async def get_profile(self, user_id: int) -> CurrentUserOut:
        """查询当前用户资料及其角色权限。"""
        statement = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.menus))
            .where(User.id == user_id)
        )
        user = (await self.session.execute(statement)).scalar_one_or_none()
        if user is None:
            raise UnauthorizedError("用户不存在")
        permissions = self._permissions_of(user)
        return CurrentUserOut(
            id=user.id,
            username=user.username,
            real_name=user.real_name,
            email=user.email,
            is_superuser=user.is_superuser,
            dept_id=user.dept_id,
            data_scope=user.data_scope,
            roles=[role.code for role in user.roles],
            permissions=permissions,
            last_login_at=user.last_login_at,
        )

    async def logout(self, username: str, meta: RequestMeta) -> None:
        """记录登出操作日志；JWT 为无状态令牌，由客户端清除。"""
        await self.logs.add_operation_log(None, username, "认证", "登出", meta)
        await self.session.commit()
