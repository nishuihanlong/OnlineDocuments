"""角色与权限（菜单）管理业务逻辑。"""

from __future__ import annotations

from src.core.cache import cached_json
from src.core.cache_keys import (
    PERMISSION_LIST_KEY,
    ROLE_LIST_KEY,
    invalidate_all_auth_contexts,
    invalidate_catalog,
)
from src.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.db.session import DatabaseSession
from src.models.user import Menu, Role
from src.repositories.user import MenuRepository, RoleRepository
from src.schemas.menu import MenuCreateIn, MenuOut, MenuUpdateIn
from src.schemas.user import RoleCreateIn, RoleDetailOut, RoleUpdateIn


def to_menu_out(menu: Menu) -> MenuOut:
    """菜单 ORM 转 DTO。"""
    return MenuOut(
        id=menu.id, name=menu.name, title=menu.title, path=menu.path,
        component=menu.component, redirect=menu.redirect, icon=menu.icon,
        parent_id=menu.parent_id, sort=menu.sort, permission_code=menu.permission_code,
        hidden=menu.hidden, enabled=menu.enabled, created_at=menu.created_at,
    )


def to_role_out(role: Role) -> RoleDetailOut:
    """角色 ORM 转 DTO，含已授权菜单 ID。"""
    return RoleDetailOut(
        id=role.id, code=role.code, name=role.name, description=role.description,
        menu_ids=[menu.id for menu in role.menus], created_at=role.created_at,
    )


class RoleService:
    """角色增删改查与菜单授权。"""

    def __init__(self, session: DatabaseSession) -> None:
        self.session = session
        self.roles = RoleRepository(session)
        self.menus = MenuRepository(session)

    async def list_roles(self) -> list[RoleDetailOut]:
        """查询全部角色（带缓存，写路径失效）。"""
        return await cached_json(
            ROLE_LIST_KEY,
            list[RoleDetailOut],
            lambda: self._load_roles(),
        )

    async def _load_roles(self) -> list[RoleDetailOut]:
        """回源查询全部角色。"""
        return [to_role_out(role) for role in await self.roles.list_all()]

    async def create_role(self, payload: RoleCreateIn) -> RoleDetailOut:
        """新建角色，编码需唯一并校验菜单 ID。"""
        if await self.roles.get_by_code(payload.code) is not None:
            raise ConflictError("角色编码已存在")
        role = Role(
            code=payload.code, name=payload.name, description=payload.description,
            menus=await resolve_menus(self.menus, payload.menu_ids),
        )
        await self.roles.add(role)
        await self.session.commit()
        await invalidate_catalog(ROLE_LIST_KEY)
        return to_role_out(role)

    async def update_role(self, role_id: int, payload: RoleUpdateIn) -> RoleDetailOut:
        """更新角色资料与菜单授权。"""
        role = await self.roles.get_by_id(role_id)
        if role is None:
            raise NotFoundError("角色不存在")
        for field in ("name", "description"):
            value = getattr(payload, field)
            if value is not None:
                setattr(role, field, value)
        if payload.menu_ids is not None:
            role.menus = await resolve_menus(self.menus, payload.menu_ids)
        await self.session.commit()
        # 角色菜单授权变化会影响持有该角色的所有用户权限上下文。
        await invalidate_catalog(ROLE_LIST_KEY)
        await invalidate_all_auth_contexts()
        return to_role_out(role)

    async def delete_role(self, role_id: int) -> None:
        """删除角色；内置管理员与普通用户角色不可删除。"""
        role = await self.roles.get_by_id(role_id)
        if role is None:
            raise NotFoundError("角色不存在")
        if role.code in {"admin", "user"}:
            raise BadRequestError("内置角色不可删除")
        await self.roles.delete(role)
        await self.session.commit()
        await invalidate_catalog(ROLE_LIST_KEY)
        await invalidate_all_auth_contexts()


class PermissionService:
    """菜单与权限码维护。"""

    def __init__(self, session: DatabaseSession) -> None:
        self.session = session
        self.menus = MenuRepository(session)

    async def list_menus(self) -> list[MenuOut]:
        """查询全部菜单（含隐藏与停用，带缓存）。"""
        return await cached_json(
            PERMISSION_LIST_KEY,
            list[MenuOut],
            lambda: self._load_menus(),
        )

    async def _load_menus(self) -> list[MenuOut]:
        """回源查询全部菜单。"""
        return [to_menu_out(menu) for menu in await self.menus.list_all()]

    async def create_menu(self, payload: MenuCreateIn) -> MenuOut:
        """新建菜单，名称需唯一。"""
        if await self.menus.get_by_name(payload.name) is not None:
            raise ConflictError("菜单名称已存在")
        menu = Menu(**payload.model_dump())
        await self.menus.add(menu)
        await self.session.commit()
        await invalidate_catalog(PERMISSION_LIST_KEY)
        await invalidate_all_auth_contexts()
        return to_menu_out(menu)

    async def update_menu(self, menu_id: int, payload: MenuUpdateIn) -> MenuOut:
        """更新菜单配置。"""
        menu = await self.menus.get_by_id(menu_id)
        if menu is None:
            raise NotFoundError("菜单不存在")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(menu, field, value)
        await self.session.commit()
        await invalidate_catalog(PERMISSION_LIST_KEY)
        await invalidate_all_auth_contexts()
        return to_menu_out(menu)

    async def delete_menu(self, menu_id: int) -> None:
        """删除菜单及其子菜单。"""
        menu = await self.menus.get_by_id(menu_id)
        if menu is None:
            raise NotFoundError("菜单不存在")
        children = [item for item in await self.menus.list_all() if item.parent_id == menu_id]
        for child in children:
            await self.menus.delete(child)
        await self.menus.delete(menu)
        await self.session.commit()
        await invalidate_catalog(PERMISSION_LIST_KEY)
        await invalidate_all_auth_contexts()


async def resolve_menus(repository: MenuRepository, menu_ids: list[int]) -> list[Menu]:
    """按 ID 列表查询菜单，存在无效 ID 时拒绝授权。"""
    if not menu_ids:
        return []
    result = await repository.get_by_ids(menu_ids)
    if len(result) != len(set(menu_ids)):
        raise BadRequestError("存在无效的菜单 ID")
    return result
