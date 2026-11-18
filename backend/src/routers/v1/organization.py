"""组织管理接口：机构与部门。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.deps import CurrentUser, CurrentUserDep, require_permissions
from src.core.response import ApiResponse
from src.routers.deps import OrganizationServiceDep
from src.schemas.organization import (
    DeptCreateIn,
    DeptOut,
    DeptUpdateIn,
    OrgCreateIn,
    OrgOut,
    OrgUpdateIn,
)

router = APIRouter(tags=["组织管理"])

OrgCreateDep = Annotated[CurrentUser, Depends(require_permissions("org:create"))]
OrgUpdateDep = Annotated[CurrentUser, Depends(require_permissions("org:update"))]
OrgDeleteDep = Annotated[CurrentUser, Depends(require_permissions("org:delete"))]
DeptCreateDep = Annotated[CurrentUser, Depends(require_permissions("dept:create"))]
DeptUpdateDep = Annotated[CurrentUser, Depends(require_permissions("dept:update"))]
DeptDeleteDep = Annotated[CurrentUser, Depends(require_permissions("dept:delete"))]


@router.get("/orgs", response_model=ApiResponse[list[OrgOut]], summary="机构列表")
async def list_orgs(
    _principal: CurrentUserDep, service: OrganizationServiceDep
) -> ApiResponse[list[OrgOut]]:
    """查询全部机构。"""
    return ApiResponse[list[OrgOut]](data=await service.list_orgs())


@router.post("/orgs", response_model=ApiResponse[OrgOut], summary="新增机构")
async def create_org(
    payload: OrgCreateIn, _principal: OrgCreateDep, service: OrganizationServiceDep
) -> ApiResponse[OrgOut]:
    """新建机构。"""
    return ApiResponse[OrgOut](data=await service.create_org(payload))


@router.put("/orgs/{org_id}", response_model=ApiResponse[OrgOut], summary="更新机构")
async def update_org(
    org_id: int, payload: OrgUpdateIn,
    _principal: OrgUpdateDep, service: OrganizationServiceDep,
) -> ApiResponse[OrgOut]:
    """更新机构。"""
    return ApiResponse[OrgOut](data=await service.update_org(org_id, payload))


@router.delete("/orgs/{org_id}", response_model=ApiResponse[None], summary="删除机构")
async def delete_org(
    org_id: int, _principal: OrgDeleteDep, service: OrganizationServiceDep
) -> ApiResponse[None]:
    """删除机构。"""
    await service.delete_org(org_id)
    return ApiResponse[None](message="success")


@router.get("/depts", response_model=ApiResponse[list[DeptOut]], summary="部门列表")
async def list_depts(
    _principal: CurrentUserDep, service: OrganizationServiceDep
) -> ApiResponse[list[DeptOut]]:
    """查询全部部门。"""
    return ApiResponse[list[DeptOut]](data=await service.list_depts())


@router.post("/depts", response_model=ApiResponse[DeptOut], summary="新增部门")
async def create_dept(
    payload: DeptCreateIn, _principal: DeptCreateDep, service: OrganizationServiceDep
) -> ApiResponse[DeptOut]:
    """新建部门。"""
    return ApiResponse[DeptOut](data=await service.create_dept(payload))


@router.put("/depts/{dept_id}", response_model=ApiResponse[DeptOut], summary="更新部门")
async def update_dept(
    dept_id: int, payload: DeptUpdateIn,
    _principal: DeptUpdateDep, service: OrganizationServiceDep,
) -> ApiResponse[DeptOut]:
    """更新部门。"""
    return ApiResponse[DeptOut](data=await service.update_dept(dept_id, payload))


@router.delete("/depts/{dept_id}", response_model=ApiResponse[None], summary="删除部门")
async def delete_dept(
    dept_id: int, _principal: DeptDeleteDep, service: OrganizationServiceDep
) -> ApiResponse[None]:
    """删除部门。"""
    await service.delete_dept(dept_id)
    return ApiResponse[None](message="success")
