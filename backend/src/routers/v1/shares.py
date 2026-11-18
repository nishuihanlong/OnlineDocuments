"""文档分享接口：管理接口需登录，公开接口凭分享 token 免登录访问。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.deps import CurrentUser, require_permissions
from src.core.response import ApiResponse
from src.routers.deps import RequestMetaDep, ShareServiceDep
from src.schemas.document import DocumentUploadOut
from src.schemas.share import (
    DocumentShareCreateIn,
    DocumentShareOut,
    PublicShareOut,
    PublicShareSaveIn,
)

router = APIRouter(prefix="/shares", tags=["文档分享"])

ShareDep = Annotated[CurrentUser, Depends(require_permissions("document:share"))]


@router.post("", response_model=ApiResponse[DocumentShareOut], summary="创建分享")
async def create_share(
    payload: DocumentShareCreateIn,
    principal: ShareDep,
    meta: RequestMetaDep,
    service: ShareServiceDep,
) -> ApiResponse[DocumentShareOut]:
    """为文档创建公开链接或指定用户分享；重复创建复用未撤销记录。"""
    return ApiResponse[DocumentShareOut](
        data=await service.create_share(payload, principal, meta)
    )


@router.get("", response_model=ApiResponse[list[DocumentShareOut]], summary="分享列表")
async def list_shares(
    document_id: Annotated[int, Query(ge=1)],
    _principal: ShareDep,
    service: ShareServiceDep,
) -> ApiResponse[list[DocumentShareOut]]:
    """查询某文档的全部分享记录。"""
    return ApiResponse[list[DocumentShareOut]](data=await service.list_shares(document_id))


@router.delete("/{share_id}", response_model=ApiResponse[None], summary="撤销分享")
async def revoke_share(
    share_id: int,
    principal: ShareDep,
    meta: RequestMetaDep,
    service: ShareServiceDep,
) -> ApiResponse[None]:
    """撤销分享，撤销后公开链接与用户授权立即失效。"""
    await service.revoke_share(share_id, principal, meta)
    return ApiResponse[None](message="success")


@router.get(
    "/public/{token}",
    response_model=ApiResponse[PublicShareOut],
    summary="公开访问分享",
)
async def resolve_public_share(
    token: str, service: ShareServiceDep
) -> ApiResponse[PublicShareOut]:
    """凭 token 免登录读取分享文档元信息与内容；失效一律 404。"""
    return ApiResponse[PublicShareOut](data=await service.resolve_public(token))


@router.post(
    "/public/{token}/save",
    response_model=ApiResponse[DocumentUploadOut],
    summary="公开分享编辑保存",
)
async def save_public_share(
    token: str,
    payload: PublicShareSaveIn,
    meta: RequestMetaDep,
    service: ShareServiceDep,
) -> ApiResponse[DocumentUploadOut]:
    """凭 write 分享 token 免登录保存编辑内容，生成新版本。"""
    return ApiResponse[DocumentUploadOut](
        data=await service.save_public(token, payload, meta)
    )
