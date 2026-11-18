"""用户管理接口。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.deps import CurrentUser, CurrentUserDep, require_permissions
from src.core.response import ApiResponse
from src.routers.deps import RequestMetaDep, UserQueryDep, UserServiceDep
from src.schemas.common import PageResult
from src.schemas.user import UserCreateIn, UserOut, UserUpdateIn

router = APIRouter(prefix="/users", tags=["用户管理"])

CreateDep = Annotated[CurrentUser, Depends(require_permissions("user:create"))]
UpdateDep = Annotated[CurrentUser, Depends(require_permissions("user:update"))]
ActivateDep = Annotated[CurrentUser, Depends(require_permissions("user:activate"))]


@router.get("", response_model=ApiResponse[PageResult[UserOut]], summary="用户列表")
async def list_users(
    query: UserQueryDep, principal: CurrentUserDep, service: UserServiceDep
) -> ApiResponse[PageResult[UserOut]]:
    """按数据范围分页查询用户。"""
    return ApiResponse[PageResult[UserOut]](
        data=await service.list_users(query, principal)
    )


@router.post("", response_model=ApiResponse[UserOut], summary="新增用户")
async def create_user(
    payload: UserCreateIn,
    principal: CreateDep,
    meta: RequestMetaDep,
    service: UserServiceDep,
) -> ApiResponse[UserOut]:
    """创建用户并绑定角色。"""
    return ApiResponse[UserOut](data=await service.create_user(payload, principal, meta))


@router.get("/{user_id}", response_model=ApiResponse[UserOut], summary="用户详情")
async def get_user(
    user_id: int, principal: CurrentUserDep, service: UserServiceDep
) -> ApiResponse[UserOut]:
    """按数据范围查询单个用户详情。"""
    return ApiResponse[UserOut](data=await service.get_user(user_id, principal))


@router.put("/{user_id}", response_model=ApiResponse[UserOut], summary="更新用户")
async def update_user(
    user_id: int,
    payload: UserUpdateIn,
    principal: UpdateDep,
    meta: RequestMetaDep,
    service: UserServiceDep,
) -> ApiResponse[UserOut]:
    """更新用户资料、状态与角色。"""
    return ApiResponse[UserOut](
        data=await service.update_user(user_id, payload, principal, meta)
    )


@router.post("/{user_id}/activate", response_model=ApiResponse[UserOut], summary="激活用户")
async def activate_user(
    user_id: int,
    principal: ActivateDep,
    meta: RequestMetaDep,
    service: UserServiceDep,
) -> ApiResponse[UserOut]:
    """激活待激活或已停用的用户。"""
    return ApiResponse[UserOut](
        data=await service.activate_user(user_id, principal, meta)
    )


@router.delete("/{user_id}", response_model=ApiResponse[None], summary="停用用户")
async def disable_user(
    user_id: int,
    principal: ActivateDep,
    meta: RequestMetaDep,
    service: UserServiceDep,
) -> ApiResponse[None]:
    """停用用户而非物理删除。"""
    await service.disable_user(user_id, principal, meta)
    return ApiResponse[None](message="success")
