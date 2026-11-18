"""认证接口。"""

from __future__ import annotations

from fastapi import APIRouter

from src.core.deps import CurrentUserDep
from src.core.response import ApiResponse
from src.routers.deps import AuthServiceDep, RequestMetaDep
from src.schemas.auth import CurrentUserOut, LoginIn, LoginOut, RegisterIn, RegisterOut

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse[RegisterOut], summary="用户注册")
async def register(
    payload: RegisterIn, meta: RequestMetaDep, service: AuthServiceDep
) -> ApiResponse[RegisterOut]:
    """自助注册普通用户，注册后处于待激活状态，需管理员激活。"""
    return ApiResponse[RegisterOut](data=await service.register(payload, meta))


@router.post("/login", response_model=ApiResponse[LoginOut], summary="用户登录")
async def login(
    payload: LoginIn, meta: RequestMetaDep, service: AuthServiceDep
) -> ApiResponse[LoginOut]:
    """校验账号口令并返回 JWT 访问令牌。"""
    return ApiResponse[LoginOut](data=await service.login(payload, meta))


@router.get("/me", response_model=ApiResponse[CurrentUserOut], summary="当前用户")
async def get_me(principal: CurrentUserDep, service: AuthServiceDep) -> ApiResponse[CurrentUserOut]:
    """返回当前登录用户的资料与权限。"""
    return ApiResponse[CurrentUserOut](data=await service.get_profile(principal.id))


@router.post("/logout", response_model=ApiResponse[None], summary="用户登出")
async def logout(
    principal: CurrentUserDep, meta: RequestMetaDep, service: AuthServiceDep
) -> ApiResponse[None]:
    """记录登出日志，客户端需自行清除本地令牌。"""
    await service.logout(principal.username, meta)
    return ApiResponse[None](message="success")
