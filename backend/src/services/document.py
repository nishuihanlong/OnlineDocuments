"""文档管理业务逻辑：元数据 CRUD、版本、上传下载、删除与恢复。"""

from __future__ import annotations

import base64
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.core.deps import CurrentUser
from src.db.session import DatabaseSession
from src.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.core.mq import DomainEvent, EventPublisher
from src.db.base import utc_now
from src.models.document import Document, DocumentVersion
from src.repositories.document import DocumentRepository, VersionRepository
from src.repositories.user import LogRepository
from src.schemas.auth import RequestMeta
from src.schemas.common import PageResult, to_iso8601
from src.schemas.document import (
    DocumentCreateIn,
    DocumentDownloadOut,
    DocumentOut,
    DocumentQuery,
    DocumentUpdateIn,
    DocumentUploadOut,
    DocumentVersionOut,
)
from src.services.storage import ObjectStorage


def to_document_out(document: Document) -> DocumentOut:
    """文档 ORM 转 DTO。"""
    return DocumentOut(
        id=document.id,
        title=document.title,
        description=document.description,
        owner_id=document.owner_id,
        current_version=document.current_version,
        file_name=document.file_name,
        file_size=document.file_size,
        mime_type=document.mime_type,
        download_count=document.download_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
        deleted_at=document.deleted_at,
    )


class DocumentService:
    """文档用例编排，负责事务提交、对象存储与领域事件发布。"""

    def __init__(
        self,
        session: DatabaseSession,
        storage: ObjectStorage,
        publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.storage = storage
        self.publisher = publisher
        self.documents = DocumentRepository(session)
        self.versions = VersionRepository(session)
        self.logs = LogRepository(session)

    async def _publish(self, event_type: str, document_id: int) -> None:
        """发布文档领域事件，MQ 不可用时自动降级为空实现。"""
        event = DomainEvent(
            event_type=f"document.{event_type}",
            aggregate_id=document_id,
            payload={"document_id": document_id},
            occurred_at=to_iso8601(utc_now()),
        )
        await self.publisher.publish(event)

    async def _require_document(
        self, document_id: int, principal: CurrentUser, include_deleted: bool = False
    ) -> Document:
        """按数据范围读取文档，越权与不存在统一返回 404 避免探测。"""
        document = await self.documents.get_detail(document_id, principal, include_deleted)
        if document is None:
            raise NotFoundError("文档不存在或已删除")
        return document

    async def list_documents(
        self, query: DocumentQuery, principal: CurrentUser
    ) -> PageResult[DocumentOut]:
        """按数据范围分页查询文档。"""
        rows, total = await self.documents.paginate(
            self.documents.build_query(query, principal), query.page, query.page_size
        )
        return PageResult(
            items=[to_document_out(row) for row in rows],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_document(
        self, document_id: int, principal: CurrentUser, include_deleted: bool = False
    ) -> DocumentOut:
        """按数据范围查询文档详情。"""
        return to_document_out(
            await self._require_document(document_id, principal, include_deleted)
        )

    async def create_document(
        self, payload: DocumentCreateIn, principal: CurrentUser, meta: RequestMeta
    ) -> DocumentOut:
        """新建文档元数据并生成 v1 版本记录。"""
        document = Document(
            title=payload.title,
            description=payload.description,
            owner_id=principal.id,
            current_version=1,
        )
        await self.documents.add(document)
        self.session.add(
            DocumentVersion(
                document_id=document.id,
                version_no=1,
                change_log="创建文档",
                created_by=principal.id,
            )
        )
        await self.logs.add_operation_log(
            principal.id, principal.username, "文档管理", f"新建文档 {document.title}", meta
        )
        await self.session.commit()
        await self._publish("created", document.id)
        return await self.get_document(document.id, principal)

    async def update_document(
        self,
        document_id: int,
        payload: DocumentUpdateIn,
        principal: CurrentUser,
        meta: RequestMeta,
    ) -> DocumentOut:
        """更新文档元数据。"""
        document = await self._require_document(document_id, principal)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(document, field, value)
        await self.session.flush()
        await self.logs.add_operation_log(
            principal.id, principal.username, "文档管理", f"更新文档 {document.title}", meta
        )
        await self.session.commit()
        await self._publish("updated", document.id)
        return await self.get_document(document.id, principal)

    async def delete_document(
        self, document_id: int, principal: CurrentUser, meta: RequestMeta
    ) -> None:
        """软删除文档，可通过恢复接口找回。"""
        document = await self._require_document(document_id, principal)
        document.deleted_at = utc_now()
        await self.logs.add_operation_log(
            principal.id, principal.username, "文档管理", f"删除文档 {document.title}", meta
        )
        await self.session.commit()
        await self._publish("deleted", document.id)

    async def restore_document(
        self, document_id: int, principal: CurrentUser, meta: RequestMeta
    ) -> DocumentOut:
        """从回收站恢复文档。"""
        document = await self._require_document(document_id, principal, include_deleted=True)
        document.deleted_at = None
        await self.logs.add_operation_log(
            principal.id, principal.username, "文档管理", f"恢复文档 {document.title}", meta
        )
        await self.session.commit()
        await self._publish("restored", document.id)
        return await self.get_document(document.id, principal)

    async def list_versions(
        self, document_id: int, principal: CurrentUser
    ) -> list[DocumentVersionOut]:
        """按数据范围查询文档版本历史。"""
        await self._require_document(document_id, principal, include_deleted=True)
        versions = await self.versions.list_by_document(document_id)
        return [
            DocumentVersionOut(
                id=item.id,
                document_id=item.document_id,
                version_no=item.version_no,
                file_size=item.file_size,
                change_log=item.change_log,
                created_by=item.created_by,
                created_at=item.created_at,
            )
            for item in versions
        ]

    async def upload_file(
        self,
        document_id: int,
        upload: UploadFile,
        principal: CurrentUser,
        meta: RequestMeta,
        change_log: str | None = None,
    ) -> DocumentUploadOut:
        """上传文件内容，生成新版本并写入对象存储。"""
        document = await self._require_document(document_id, principal)
        content = await upload.read()
        if not content:
            raise BadRequestError("上传文件不能为空")
        file_name = Path(upload.filename or "untitled.bin").name
        content_type = upload.content_type or "application/octet-stream"
        version_no = document.current_version + 1
        storage_key = (
            f"documents/{document.id}/v{version_no}/{uuid4().hex}/{file_name}"
        )
        stored = await self.storage.put(storage_key, content, content_type)

        document.current_version = version_no
        document.storage_key = stored.key
        document.file_name = file_name
        document.file_size = stored.size
        document.mime_type = content_type
        self.session.add(
            DocumentVersion(
                document_id=document.id,
                version_no=version_no,
                storage_key=stored.key,
                file_size=stored.size,
                change_log=change_log or f"上传文件 {file_name}",
                created_by=principal.id,
            )
        )
        await self.logs.add_operation_log(
            principal.id, principal.username, "文档管理", f"上传文档版本 v{version_no}", meta
        )
        await self.session.commit()
        await self._publish("uploaded", document.id)
        return DocumentUploadOut(
            document_id=document.id,
            version_no=version_no,
            storage_key=stored.key,
            file_name=file_name,
            file_size=stored.size,
        )

    async def download_file(
        self, document_id: int, principal: CurrentUser
    ) -> DocumentDownloadOut:
        """按数据范围读取文档内容、累加下载次数并以 Base64 返回。"""
        document = await self._require_document(document_id, principal)
        if not document.storage_key:
            raise ConflictError("该文档尚未上传文件")
        content = await self.storage.get(document.storage_key)
        document.download_count += 1
        await self.session.commit()
        return DocumentDownloadOut(
            file_name=document.file_name or f"document-{document.id}",
            mime_type=document.mime_type or "application/octet-stream",
            size=len(content),
            content_base64=base64.b64encode(content).decode("ascii"),
        )
