"""动态菜单业务逻辑：把菜单表转换为前端可注册的动态路由树。"""

from __future__ import annotations

from src.core.deps import CurrentUser
from src.db.session import DatabaseSession
from src.models.user import Menu
from src.repositories.user import MenuRepository
from src.schemas.system import MenuMetaOut, MenuRouteOut


def to_route_node(menu: Menu) -> MenuRouteOut:
    """把单条菜单记录转换为前端路由节点。"""
    return MenuRouteOut(
        path=menu.path,
        name=menu.name,
        component=menu.component,
        redirect=menu.redirect,
        meta=MenuMetaOut(
            title=menu.title,
            icon=menu.icon,
            hidden=menu.hidden,
        ),
    )


class MenuService:
    """按用户可见菜单构造路由树。"""

    def __init__(self, session: DatabaseSession, principal: CurrentUser) -> None:
        self.session = session
        self.principal = principal

    async def build_routes(self) -> list[MenuRouteOut]:
        """查询启用且未隐藏的菜单，组装成父子层级的路由列表。"""
        menus = await MenuRepository(self.session).list_enabled()
        if not self.principal.is_superuser:
            allowed = set(self.principal.menu_ids)
            menus = [menu for menu in menus if menu.id in allowed]

        visible = [menu for menu in menus if not menu.hidden]
        nodes = {menu.id: to_route_node(menu) for menu in visible}
        roots: list[MenuRouteOut] = []
        for menu in visible:
            node = nodes[menu.id]
            parent = nodes.get(menu.parent_id) if menu.parent_id else None
            if parent is None:
                roots.append(node)
            else:
                parent.children = (parent.children or []) + [node]
        return roots
