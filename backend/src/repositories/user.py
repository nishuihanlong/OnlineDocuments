"""用户、角色、菜单与日志仓储。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from src.core.deps import DATA_SCOPE_ALL, DATA_SCOPE_DEPT, CurrentUser
from src.db.session import DatabaseSession
from src.models.log import LoginLog, OperationLog
from src.models.user import Menu, Role, User
from src.repositories.base import BaseRepository
from src.schemas.auth import RequestMeta
from src.schemas.user import UserQuery


class UserRepository(BaseRepository[User]):
    """用户表 CRUD。"""

    model = User

    async def get_by_username(self, username: str) -> User | None:
        """按用户名查询用户，同时预加载角色。"""
        statement = (
            select(User).options(selectinload(User.roles)).where(User.username == username)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    def build_query(
        self, query: UserQuery, principal: CurrentUser | None = None
    ) -> Select[Any]:
        """构造用户查询，按数据范围限制可见用户。"""
        statement = select(User).options(selectinload(User.roles))
        if query.keyword:
            keyword = f"%{query.keyword}%"
            statement = statement.where(
                User.username.like(keyword) | User.real_name.like(keyword)
            )
        if query.status is not None:
            statement = statement.where(User.status == query.status)
        if principal is not None and not principal.is_superuser:
            if principal.data_scope == DATA_SCOPE_DEPT and principal.dept_id is not None:
                statement = statement.where(User.dept_id == principal.dept_id)
            elif principal.data_scope != DATA_SCOPE_ALL:
                statement = statement.where(User.id == principal.id)
        return statement.order_by(User.id.desc())


class RoleRepository(BaseRepository[Role]):
    """角色表 CRUD。"""

    model = Role

    async def get_by_ids(self, role_ids: Sequence[int]) -> list[Role]:
        """按 ID 列表批量查询角色。"""
        if not role_ids:
            return []
        statement = select(Role).where(Role.id.in_(role_ids))
        return list((await self.session.execute(statement)).scalars().all())

    async def get_by_code(self, code: str) -> Role | None:
        """按角色编码查询。"""
        statement = select(Role).where(Role.code == code)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_all(self) -> list[Role]:
        """查询全部角色。"""
        statement = select(Role).order_by(Role.id)
        return list((await self.session.execute(statement)).scalars().all())


class MenuRepository(BaseRepository[Menu]):
    """菜单表 CRUD。"""

    model = Menu

    async def list_enabled(self) -> list[Menu]:
        """查询全部启用菜单，按排序值返回。"""
        # 用 == True 而非 is_(True)：后者被达梦方言编译为 "IS 1"（达梦不支持），
        # 前者编译为 "= 1"，在达梦与 SQLite 下行为一致。
        statement = select(Menu).where(Menu.enabled == True).order_by(Menu.sort, Menu.id)  # noqa: E712
        return list((await self.session.execute(statement)).scalars().all())

    async def list_all(self) -> list[Menu]:
        """查询全部菜单（含隐藏与停用），按排序返回。"""
        statement = select(Menu).order_by(Menu.sort, Menu.id)
        return list((await self.session.execute(statement)).scalars().all())

    async def get_by_name(self, name: str) -> Menu | None:
        """按菜单名称查询，用于唯一性校验。"""
        statement = select(Menu).where(Menu.name == name)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_by_ids(self, menu_ids: Sequence[int]) -> list[Menu]:
        """按 ID 列表批量查询菜单。"""
        if not menu_ids:
            return []
        statement = select(Menu).where(Menu.id.in_(menu_ids))
        return list((await self.session.execute(statement)).scalars().all())


class LogRepository:
    """审计日志仓储。"""

    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    async def add_login_log(
        self, username: str, meta: RequestMeta, success: bool, message: str
    ) -> None:
        """写入登录日志（含失败尝试）。"""
        self.session.add(
            LoginLog(
                username=username,
                ip=meta.ip,
                user_agent=meta.user_agent[:256],
                success=success,
                message=message[:256],
            )
        )
        await self.session.flush()

    async def add_operation_log(
        self,
        user_id: int | None,
        username: str,
        module: str,
        action: str,
        meta: RequestMeta,
        status_code: int = 200,
        detail: str | None = None,
    ) -> None:
        """写入操作日志。"""
        self.session.add(
            OperationLog(
                user_id=user_id,
                username=username,
                module=module,
                action=action,
                method=meta.method,
                path=meta.path,
                ip=meta.ip,
                status_code=status_code,
                detail=detail,
            )
        )
        await self.session.flush()

    async def count_operation_logs(self) -> int:
        """统计操作日志条数，用于系统监控概览。"""
        statement = select(func.count()).select_from(OperationLog)
        return int((await self.session.execute(statement)).scalar_one())
