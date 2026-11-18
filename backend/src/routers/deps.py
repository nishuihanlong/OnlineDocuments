"""路由层依赖工厂：服务实例、审计元信息与查询参数解析。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query, Request

from src.core.deps import CurrentUser, CurrentUserDep, DbSession, SettingsDep
from src.core.mq import get_event_publisher
from src.schemas.auth import RequestMeta
from src.schemas.user import UserQuery
from src.services.auth import AuthService
from src.services.dashboard import DashboardService
from src.services.document import DocumentService
from src.services.menu import MenuService
from src.services.monitor import MonitorService
from src.services.organization import OrganizationService
from src.services.access import PermissionService, RoleService
from src.services.share import ShareService
from src.services.storage import get_object_storage
from src.services.system import SystemService
from src.services.user import UserService


def get_request_meta(request: Request) -> RequestMeta:
    """从请求中提取审计信息。"""
    return RequestMeta(
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        method=request.method,
        path=request.url.path,
    )


RequestMetaDep = Annotated[RequestMeta, Depends(get_request_meta)]


def get_auth_service(session: DbSession, settings: SettingsDep) -> AuthService:
    """构造认证服务。"""
    return AuthService(session, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_user_service(session: DbSession) -> UserService:
    """构造用户管理服务。"""
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_document_service(session: DbSession) -> DocumentService:
    """构造文档管理服务，注入对象存储与事件发布器。"""
    return DocumentService(session, get_object_storage(), get_event_publisher())


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


def get_share_service(session: DbSession) -> ShareService:
    """构造文档分享服务，注入对象存储与事件发布器。"""
    return ShareService(session, get_object_storage(), get_event_publisher())


ShareServiceDep = Annotated[ShareService, Depends(get_share_service)]


def get_dashboard_service(session: DbSession) -> DashboardService:
    """构造仪表盘统计服务。"""
    return DashboardService(session)


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


def get_system_service(session: DbSession, settings: SettingsDep) -> SystemService:
    """构造系统管理服务，注入配置用于监控与文件管理。"""
    return SystemService(session, settings)


SystemServiceDep = Annotated[SystemService, Depends(get_system_service)]


def get_role_service(session: DbSession) -> RoleService:
    """构造角色管理服务。"""
    return RoleService(session)


def get_permission_service(session: DbSession) -> PermissionService:
    """构造权限（菜单）管理服务。"""
    return PermissionService(session)


RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]


def get_organization_service(session: DbSession) -> OrganizationService:
    """构造组织管理服务。"""
    return OrganizationService(session)


OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]


def get_menu_service(session: DbSession, principal: CurrentUserDep) -> MenuService:
    """构造动态菜单服务，依赖当前用户以过滤可见菜单。"""
    return MenuService(session, principal)


MenuServiceDep = Annotated[MenuService, Depends(get_menu_service)]


def get_monitor_service(settings: SettingsDep) -> MonitorService:
    """构造基础设施只读监控服务。"""
    return MonitorService(settings)


MonitorServiceDep = Annotated[MonitorService, Depends(get_monitor_service)]


def parse_user_query(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: int | None = Query(None, ge=0, le=2),
) -> UserQuery:
    """解析用户列表查询参数并做范围校验。"""
    return UserQuery(page=page, page_size=page_size, keyword=keyword, status=status)


UserQueryDep = Annotated[UserQuery, Depends(parse_user_query)]
