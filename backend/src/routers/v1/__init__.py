"""v1 版本 API 路由聚合。"""

from fastapi import APIRouter

from src.core.config import get_settings
from src.routers.v1 import (
    access,
    auth,
    collaboration,
    dashboard,
    documents,
    organization,
    shares,
    system,
    system_admin,
    users,
)

api_router = APIRouter(prefix=get_settings().api_prefix)
api_router.include_router(auth.router)
api_router.include_router(access.router)
api_router.include_router(organization.router)
api_router.include_router(system.router)
api_router.include_router(system_admin.router)
api_router.include_router(dashboard.router)
api_router.include_router(users.router)
api_router.include_router(documents.router)
api_router.include_router(collaboration.router)
api_router.include_router(shares.router)
