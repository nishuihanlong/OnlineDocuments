"""系统信息、健康检查与动态菜单接口。"""

from __future__ import annotations

from fastapi import APIRouter

from src.core.config import Settings
from src.core.deps import CurrentUserDep, SettingsDep
from src.core.response import ApiResponse
from src.db.base import utc_now
from src.routers.deps import MenuServiceDep, SystemServiceDep
from src.schemas.system import HealthOut, MenuRouteOut, PublicConfigOut

router = APIRouter(prefix="/system", tags=["系统管理"])


def build_health(settings: Settings) -> HealthOut:
    """构造健康检查结果，不暴露数据库凭据等敏感信息。"""
    return HealthOut(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
        database=settings.database_url.split("://")[0],
        cache="redis" if settings.redis_url else "memory",
        storage=settings.storage_backend,
        server_time=utc_now(),
    )


@router.get("/health", response_model=ApiResponse[HealthOut], summary="健康检查")
async def health(settings: SettingsDep) -> ApiResponse[HealthOut]:
    """返回服务与各基础设施状态。"""
    return ApiResponse[HealthOut](data=build_health(settings))


@router.get(
    "/public-configs",
    response_model=ApiResponse[PublicConfigOut],
    summary="公开前端配置",
)
async def get_public_configs(service: SystemServiceDep) -> ApiResponse[PublicConfigOut]:
    """返回前端所需的公开开关（如水印），无需认证。"""
    return ApiResponse[PublicConfigOut](data=await service.get_public_config())


@router.get(
    "/menus",
    response_model=ApiResponse[list[MenuRouteOut]],
    response_model_exclude_none=True,
    summary="动态菜单路由",
)
async def get_menus(
    _principal: CurrentUserDep, service: MenuServiceDep
) -> ApiResponse[list[MenuRouteOut]]:
    """返回当前用户可访问的前端动态路由树。"""
    return ApiResponse[list[MenuRouteOut]](data=await service.build_routes())
