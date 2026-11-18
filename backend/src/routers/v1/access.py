"""角色与权限（菜单）管理接口。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.deps import CurrentUser, CurrentUserDep, require_permissions
from src.core.response import ApiResponse
from src.routers.deps import PermissionServiceDep, RoleServiceDep
from src.schemas.menu import MenuCreateIn, MenuOut, MenuUpdateIn
from src.schemas.user import RoleCreateIn, RoleDetailOut, RoleUpdateIn

router = APIRouter(tags=["权限管理"])

RoleCreateDep = Annotated[CurrentUser, Depends(require_permissions("role:create"))]
RoleUpdateDep = Annotated[CurrentUser, Depends(require_permissions("role:update"))]
RoleDeleteDep = Annotated[CurrentUser, Depends(require_permissions("role:delete"))]
PermissionCreateDep = Annotated[CurrentUser, Depends(require_permissions("permission:create"))]
PermissionUpdateDep = Annotated[CurrentUser, Depends(require_permissions("permission:update"))]
PermissionDeleteDep = Annotated[CurrentUser, Depends(require_permissions("permission:delete"))]


@router.get("/roles", response_model=ApiResponse[list[RoleDetailOut]], summary="角色列表")
async def list_roles(
    _principal: CurrentUserDep, service: RoleServiceDep
) -> ApiResponse[list[RoleDetailOut]]:
    """查询全部角色及其授权菜单。"""
    return ApiResponse[list[RoleDetailOut]](data=await service.list_roles())


@router.post("/roles", response_model=ApiResponse[RoleDetailOut], summary="新增角色")
async def create_role(
    payload: RoleCreateIn, _principal: RoleCreateDep, service: RoleServiceDep
) -> ApiResponse[RoleDetailOut]:
    """新建角色并绑定菜单权限。"""
    return ApiResponse[RoleDetailOut](data=await service.create_role(payload))


@router.put("/roles/{role_id}", response_model=ApiResponse[RoleDetailOut], summary="更新角色")
async def update_role(
    role_id: int, payload: RoleUpdateIn,
    _principal: RoleUpdateDep, service: RoleServiceDep,
) -> ApiResponse[RoleDetailOut]:
    """更新角色资料与菜单授权。"""
    return ApiResponse[RoleDetailOut](data=await service.update_role(role_id, payload))


@router.delete("/roles/{role_id}", response_model=ApiResponse[None], summary="删除角色")
async def delete_role(
    role_id: int, _principal: RoleDeleteDep, service: RoleServiceDep
) -> ApiResponse[None]:
    """删除角色。"""
    await service.delete_role(role_id)
    return ApiResponse[None](message="success")


@router.get("/permissions", response_model=ApiResponse[list[MenuOut]], summary="权限(菜单)列表")
async def list_menus(
    _principal: CurrentUserDep, service: PermissionServiceDep
) -> ApiResponse[list[MenuOut]]:
    """查询全部菜单与权限码。"""
    return ApiResponse[list[MenuOut]](data=await service.list_menus())


@router.post("/permissions", response_model=ApiResponse[MenuOut], summary="新增权限(菜单)")
async def create_menu(
    payload: MenuCreateIn, _principal: PermissionCreateDep, service: PermissionServiceDep
) -> ApiResponse[MenuOut]:
    """新建菜单或权限项。"""
    return ApiResponse[MenuOut](data=await service.create_menu(payload))


@router.put("/permissions/{menu_id}", response_model=ApiResponse[MenuOut], summary="更新权限(菜单)")
async def update_menu(
    menu_id: int, payload: MenuUpdateIn,
    _principal: PermissionUpdateDep, service: PermissionServiceDep,
) -> ApiResponse[MenuOut]:
    """更新菜单或权限项。"""
    return ApiResponse[MenuOut](data=await service.update_menu(menu_id, payload))


@router.delete("/permissions/{menu_id}", response_model=ApiResponse[None], summary="删除权限(菜单)")
async def delete_menu(
    menu_id: int, _principal: PermissionDeleteDep, service: PermissionServiceDep
) -> ApiResponse[None]:
    """删除菜单及其子项。"""
    await service.delete_menu(menu_id)
    return ApiResponse[None](message="success")
