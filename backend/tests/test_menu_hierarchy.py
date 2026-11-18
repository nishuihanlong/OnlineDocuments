"""操作权限挂载层级与前后端菜单路径一致性校验。"""

from __future__ import annotations

from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import update

from src.core.config import get_settings
from src.db.seed import seed_initial_data
from src.db.session import get_db_session
from src.models.user import Menu
from src.schemas.menu import MenuOut

EXPECTED_PARENTS: dict[str, str] = {
    "DocumentWritePermission": "Document",
    "UserWritePermission": "SystemUser",
    "SystemWritePermission": "System",
}
FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "apps" / "admin" / "src"


async def _menu_map(
    client: AsyncClient, auth_headers: dict[str, str]
) -> dict[str, MenuOut]:
    """读取权限列表并按 name 建索引。"""
    response = await client.get("/v1/permissions", headers=auth_headers)
    assert response.status_code == 200
    items = [MenuOut.model_validate(raw) for raw in response.json()["data"]]
    return {item.name: item for item in items}


async def test_action_permissions_are_children_of_menus(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """三个写权限的 parent_id 指向各自对应的导航菜单。"""
    menus = await _menu_map(client, auth_headers)
    for name, parent_name in EXPECTED_PARENTS.items():
        item = menus[name]
        assert item.parent_id == menus[parent_name].id, name
        assert item.hidden is True, name
        assert item.permission_code, name


async def test_reseed_repairs_legacy_parent_links(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """模拟老库顶层权限节点：重新执行种子后应恢复正确的父子关系。"""
    async with get_db_session() as session:
        await session.execute(
            update(Menu).where(Menu.name.in_(EXPECTED_PARENTS)).values(parent_id=None)
        )
        await session.commit()

    settings = get_settings()
    async with get_db_session() as session:
        await seed_initial_data(session, settings)

    menus = await _menu_map(client, auth_headers)
    for name, parent_name in EXPECTED_PARENTS.items():
        assert menus[name].parent_id == menus[parent_name].id, name


async def test_builtin_menu_components_match_frontend_views(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """后端内置菜单的 component 路径应能在前端 views 目录找到对应文件。"""
    menus = await _menu_map(client, auth_headers)
    for item in menus.values():
        if item.component in ("#", "##"):
            continue
        target = FRONTEND_SRC / f"{item.component}.vue"
        assert target.is_file(), f"{item.name}: 缺少前端组件 {target}"
