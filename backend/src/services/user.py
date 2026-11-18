"""用户管理业务逻辑。"""

from __future__ import annotations

from src.core.cache_keys import invalidate_user_context
from src.core.deps import CurrentUser
from src.core.exceptions import ConflictError, NotFoundError
from src.core.security import hash_password
from src.db.session import DatabaseSession
from src.models.user import USER_STATUS_ACTIVE, User
from src.repositories.user import LogRepository, RoleRepository, UserRepository
from src.schemas.auth import RequestMeta
from src.schemas.common import PageResult
from src.schemas.user import RoleOut, UserCreateIn, UserOut, UserQuery, UserUpdateIn


def to_user_out(user: User) -> UserOut:
    """把 User ORM 对象转换为不含敏感字段的输出 DTO。"""
    return UserOut(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        email=user.email,
        phone=user.phone,
        dept_id=user.dept_id,
        data_scope=user.data_scope,
        post_id=user.post_id,
        status=user.status,
        is_superuser=user.is_superuser,
        roles=[
            RoleOut(id=role.id, code=role.code, name=role.name, description=role.description)
            for role in user.roles
        ],
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


class UserService:
    """用户 CRUD 与审计日志编排。"""

    def __init__(self, session: DatabaseSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.logs = LogRepository(session)

    async def list_users(
        self, query: UserQuery, principal: CurrentUser
    ) -> PageResult[UserOut]:
        """按数据范围分页查询用户列表。"""
        rows, total = await self.users.paginate(
            self.users.build_query(query, principal), query.page, query.page_size
        )
        return PageResult(
            items=[to_user_out(user) for user in rows],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_user(self, user_id: int, principal: CurrentUser) -> UserOut:
        """按数据范围查询用户详情。"""
        user = await self.users.get_by_id(user_id)
        if user is None or (
            not principal.is_superuser
            and principal.data_scope != "all"
            and user.id != principal.id
        ):
            raise NotFoundError("用户不存在")
        return to_user_out(user)

    async def create_user(
        self, payload: UserCreateIn, principal: CurrentUser, meta: RequestMeta
    ) -> UserOut:
        """新增用户，校验用户名唯一性并绑定角色。"""
        if await self.users.get_by_username(payload.username):
            raise ConflictError("用户名已存在")
        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            real_name=payload.real_name,
            email=payload.email,
            phone=payload.phone,
            dept_id=payload.dept_id,
            data_scope=payload.data_scope,
            post_id=payload.post_id,
            status=1,
            roles=await self.roles.get_by_ids(payload.role_ids),
        )
        await self.users.add(user)
        await self.logs.add_operation_log(
            principal.id, principal.username, "用户管理", f"新增用户 {user.username}", meta
        )
        await self.session.commit()
        return to_user_out(user)

    async def update_user(
        self, user_id: int, payload: UserUpdateIn, principal: CurrentUser, meta: RequestMeta
    ) -> UserOut:
        """更新用户资料、状态与角色。"""
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        updates = payload.model_dump(exclude_unset=True, exclude={"role_ids"})
        for field, value in updates.items():
            setattr(user, field, value)
        if payload.role_ids is not None:
            user.roles = await self.roles.get_by_ids(payload.role_ids)
        await self.session.flush()
        await self.logs.add_operation_log(
            principal.id, principal.username, "用户管理", f"更新用户 {user.username}", meta
        )
        await self.session.commit()
        await invalidate_user_context(user_id)
        return to_user_out(user)

    async def disable_user(
        self, user_id: int, principal: CurrentUser, meta: RequestMeta
    ) -> None:
        """停用用户（逻辑删除，不物理删除）。"""
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        user.status = 0
        await self.logs.add_operation_log(
            principal.id, principal.username, "用户管理", f"停用用户 {user.username}", meta
        )
        await self.session.commit()
        await invalidate_user_context(user_id)

    async def activate_user(
        self, user_id: int, principal: CurrentUser, meta: RequestMeta
    ) -> UserOut:
        """激活待激活或停用用户，恢复为启用状态。"""
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        user.status = USER_STATUS_ACTIVE
        await self.logs.add_operation_log(
            principal.id, principal.username, "用户管理", f"激活用户 {user.username}", meta
        )
        await self.session.commit()
        await invalidate_user_context(user_id)
        return to_user_out(user)
