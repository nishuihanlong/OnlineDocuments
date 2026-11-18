"""文档管理接口：元数据、版本、上传下载、删除与恢复。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from src.core.deps import CurrentUser, CurrentUserDep, require_permissions
from src.core.response import ApiResponse
from src.routers.deps import DocumentServiceDep, RequestMetaDep
from src.schemas.common import PageResult
from src.schemas.document import (
    DocumentCreateIn,
    DocumentDownloadOut,
    DocumentOut,
    DocumentQuery,
    DocumentUpdateIn,
    DocumentUploadOut,
    DocumentVersionOut,
)

router = APIRouter(prefix="/documents", tags=["文档管理"])

CreateDep = Annotated[CurrentUser, Depends(require_permissions("document:create"))]
UpdateDep = Annotated[CurrentUser, Depends(require_permissions("document:update"))]
DeleteDep = Annotated[CurrentUser, Depends(require_permissions("document:delete"))]
RestoreDep = Annotated[CurrentUser, Depends(require_permissions("document:restore"))]
UploadDep = Annotated[CurrentUser, Depends(require_permissions("document:upload"))]


def parse_document_query(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, description="标题或描述关键词"),
    include_deleted: bool = Query(False, description="是否包含回收站文档"),
) -> DocumentQuery:
    """解析文档列表查询参数。"""
    return DocumentQuery(
        page=page,
        page_size=page_size,
        keyword=keyword,
        include_deleted=include_deleted,
    )


DocumentQueryDep = Annotated[DocumentQuery, Depends(parse_document_query)]


@router.get("", response_model=ApiResponse[PageResult[DocumentOut]], summary="文档列表")
async def list_documents(
    query: DocumentQueryDep, principal: CurrentUserDep, service: DocumentServiceDep
) -> ApiResponse[PageResult[DocumentOut]]:
    """按当前用户数据范围分页检索文档。"""
    return ApiResponse[PageResult[DocumentOut]](
        data=await service.list_documents(query, principal)
    )


@router.post("", response_model=ApiResponse[DocumentOut], summary="新建文档")
async def create_document(
    payload: DocumentCreateIn,
    principal: CreateDep,
    meta: RequestMetaDep,
    service: DocumentServiceDep,
) -> ApiResponse[DocumentOut]:
    """创建文档元数据与初始版本。"""
    return ApiResponse[DocumentOut](
        data=await service.create_document(payload, principal, meta)
    )


@router.get("/{document_id}", response_model=ApiResponse[DocumentOut], summary="文档详情")
async def get_document(
    document_id: int, principal: CurrentUserDep, service: DocumentServiceDep
) -> ApiResponse[DocumentOut]:
    """按数据范围查询单个文档详情。"""
    return ApiResponse[DocumentOut](data=await service.get_document(document_id, principal))


@router.put("/{document_id}", response_model=ApiResponse[DocumentOut], summary="更新文档")
async def update_document(
    document_id: int,
    payload: DocumentUpdateIn,
    principal: UpdateDep,
    meta: RequestMetaDep,
    service: DocumentServiceDep,
) -> ApiResponse[DocumentOut]:
    """更新文档元数据。"""
    return ApiResponse[DocumentOut](
        data=await service.update_document(document_id, payload, principal, meta)
    )


@router.delete("/{document_id}", response_model=ApiResponse[None], summary="删除文档")
async def delete_document(
    document_id: int,
    principal: DeleteDep,
    meta: RequestMetaDep,
    service: DocumentServiceDep,
) -> ApiResponse[None]:
    """软删除文档，进入回收站。"""
    await service.delete_document(document_id, principal, meta)
    return ApiResponse[None](message="success")


@router.post(
    "/{document_id}/restore", response_model=ApiResponse[DocumentOut], summary="恢复文档"
)
async def restore_document(
    document_id: int,
    principal: RestoreDep,
    meta: RequestMetaDep,
    service: DocumentServiceDep,
) -> ApiResponse[DocumentOut]:
    """从回收站恢复文档。"""
    return ApiResponse[DocumentOut](
        data=await service.restore_document(document_id, principal, meta)
    )


@router.get(
    "/{document_id}/versions",
    response_model=ApiResponse[list[DocumentVersionOut]],
    summary="文档版本历史",
)
async def list_versions(
    document_id: int, principal: CurrentUserDep, service: DocumentServiceDep
) -> ApiResponse[list[DocumentVersionOut]]:
    """按数据范围查询文档的版本记录。"""
    return ApiResponse[list[DocumentVersionOut]](
        data=await service.list_versions(document_id, principal)
    )


@router.post(
    "/{document_id}/upload",
    response_model=ApiResponse[DocumentUploadOut],
    summary="上传文档文件",
)
async def upload_document_file(
    document_id: int,
    principal: UploadDep,
    meta: RequestMetaDep,
    service: DocumentServiceDep,
    file: UploadFile = File(...),
    change_log: str | None = Form(None),
) -> ApiResponse[DocumentUploadOut]:
    """上传文件并生成新版本，写入对象存储。"""
    return ApiResponse[DocumentUploadOut](
        data=await service.upload_file(document_id, file, principal, meta, change_log)
    )


@router.get(
    "/{document_id}/download",
    response_model=ApiResponse[DocumentDownloadOut],
    summary="下载文档文件",
)
async def download_document_file(
    document_id: int, principal: CurrentUserDep, service: DocumentServiceDep
) -> ApiResponse[DocumentDownloadOut]:
    """按数据范围以 Base64 返回当前版本文件内容。"""
    return ApiResponse[DocumentDownloadOut](
        data=await service.download_file(document_id, principal)
    )
