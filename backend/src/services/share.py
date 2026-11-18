"""文档分享业务逻辑：创建、列举、撤销与公开访问。"""

from __future__ import annotations

import base64
import mimetypes
import secrets
from datetime import timedelta
from io import BytesIO

from fastapi import UploadFile
from sqlalchemy import select
from starlette.datastructures import Headers

from src.core.deps import CurrentUser
from src.core.exceptions import BadRequestError, NotFoundError
from src.core.mq import DomainEvent, EventPublisher
from src.db.base import utc_now
from src.db.session import DatabaseSession
from src.models.share import DocumentShare
from src.models.user import User
from src.repositories.share import ShareRepository
from src.repositories.user import LogRepository
from src.schemas.auth import RequestMeta
from src.schemas.common import as_utc, to_iso8601
from src.schemas.document import DocumentUploadOut
from src.schemas.share import (
    DocumentShareCreateIn,
    DocumentShareOut,
    PublicShareOut,
    PublicShareSaveIn,
)
from src.services.document import DocumentService
from src.services.storage import ObjectStorage

SHARE_BASE_PATH = "/share"


def to_share_out(share: DocumentShare, username: str | None = None) -> DocumentShareOut:
    """分享 ORM 转 DTO。"""
    return DocumentShareOut(
        id=share.id,
        document_id=share.document_id,
        permission=share.permission,  # type: ignore[arg-type]
        granted_user_id=share.granted_user_id,
        granted_username=username,
        is_public=share.granted_user_id is None,
        token=share.token,
        share_path=f"{SHARE_BASE_PATH}/{share.token}",
        expires_at=as_utc(share.expires_at) if share.expires_at else None,
        revoked_at=as_utc(share.revoked_at) if share.revoked_at else None,
        created_by=share.created_by,
        created_at=share.created_at,
    )


class ShareService:
    """分享用例编排；公开保存复用文档上传逻辑，版本归属记为分享创建者。"""

    def __init__(
        self,
        session: DatabaseSession,
        storage: ObjectStorage,
        publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.storage = storage
        self.publisher = publisher
        self.shares = ShareRepository(session)
        self.logs = LogRepository(session)

    async def _publish(self, event_type: str, document_id: int) -> None:
        """发布分享领域事件，MQ 不可用时自动降级为空实现。"""
        await self.publisher.publish(
            DomainEvent(
                event_type=f"share.{event_type}",
                aggregate_id=document_id,
                payload={"document_id": document_id},
                occurred_at=to_iso8601(utc_now()),
            )
        )

    async def create_share(
        self, payload: DocumentShareCreateIn, principal: CurrentUser, meta: RequestMeta
    ) -> DocumentShareOut:
        """创建分享；同一文档对同一对象只保留一条未撤销分享，重复创建直接复用。"""
        document_service = DocumentService(self.session, self.storage, self.publisher)
        if await document_service.documents.get_detail(payload.document_id, principal) is None:
            raise NotFoundError("文档不存在或已删除")

        username: str | None = None
        if payload.granted_user_id is not None:
            user = await self.session.get(User, payload.granted_user_id)
            if user is None or user.status != 1:
                raise BadRequestError("被分享用户不存在或已停用")
            username = user.username

        existing = await self.shares.find_active_for_user(
            payload.document_id, payload.granted_user_id
        )
        if existing is not None:
            existing.permission = payload.permission
            existing.expires_at = (
                utc_now() + timedelta(hours=payload.expires_in_hours)
                if payload.expires_in_hours
                else None
            )
            await self.session.commit()
            return to_share_out(existing, username)

        share = DocumentShare(
            document_id=payload.document_id,
            token=secrets.token_urlsafe(24),
            permission=payload.permission,
            granted_user_id=payload.granted_user_id,
            expires_at=(
                utc_now() + timedelta(hours=payload.expires_in_hours)
                if payload.expires_in_hours
                else None
            ),
            created_by=principal.id,
        )
        await self.shares.add(share)
        await self.logs.add_operation_log(
            principal.id,
            principal.username,
            "文档分享",
            f"创建分享：文档 {payload.document_id} -> {'公开链接' if username is None else username}",
            meta,
        )
        await self.session.commit()
        await self._publish("created", payload.document_id)
        return to_share_out(share, username)

    async def list_shares(self, document_id: int) -> list[DocumentShareOut]:
        """查询某文档的全部分享记录，附带被分享用户名。"""
        rows = await self.shares.list_by_document(document_id)
        user_ids = {row.granted_user_id for row in rows if row.granted_user_id is not None}
        names: dict[int, str] = {}
        if user_ids:
            statement = select(User.id, User.username).where(User.id.in_(user_ids))
            names = dict((await self.session.execute(statement)).all())
        return [to_share_out(row, names.get(row.granted_user_id)) for row in rows]

    async def revoke_share(
        self, share_id: int, principal: CurrentUser, meta: RequestMeta
    ) -> None:
        """撤销分享（软标记），已撤销的重复撤销保持幂等。"""
        share = await self.shares.get_by_id(share_id)
        if share is None:
            raise NotFoundError("分享记录不存在")
        if share.revoked_at is None:
            share.revoked_at = utc_now()
            await self.logs.add_operation_log(
                principal.id, principal.username, "文档分享", f"撤销分享 {share.token[:8]}…", meta
            )
            await self.session.commit()
            await self._publish("revoked", share.document_id)

    async def _get_active_share(self, token: str) -> DocumentShare:
        """校验 token 有效：存在、未撤销、未过期，否则统一 404 避免泄露状态。"""
        share = await self.shares.get_by_token(token)
        if share is None or share.revoked_at is not None:
            raise NotFoundError("分享不存在或已失效")
        if share.expires_at is not None and as_utc(share.expires_at) <= utc_now():
            raise NotFoundError("分享不存在或已失效")
        return share

    async def resolve_public(self, token: str) -> PublicShareOut:
        """公开访问分享：返回文档元信息与当前版本内容。"""
        share = await self._get_active_share(token)
        document_service = DocumentService(self.session, self.storage, self.publisher)
        document = await document_service.documents.get_detail_unscoped(share.document_id)
        if document is None:
            raise NotFoundError("分享不存在或已失效")

        content_base64: str | None = None
        size = 0
        if document.storage_key:
            content = await self.storage.get(document.storage_key)
            size = len(content)
            content_base64 = base64.b64encode(content).decode("ascii")

        return PublicShareOut(
            token=share.token,
            permission=share.permission,  # type: ignore[arg-type]
            document_id=document.id,
            document_title=document.title,
            file_name=document.file_name,
            mime_type=document.mime_type,
            size=size,
            content_base64=content_base64,
        )

    async def save_public(
        self, token: str, payload: PublicShareSaveIn, meta: RequestMeta
    ) -> DocumentUploadOut:
        """公开链接编辑保存：仅 write 分享可用，版本归属记为分享创建者。"""
        share = await self._get_active_share(token)
        if share.permission != "write":
            raise BadRequestError("该分享为只读，不能保存修改")

        try:
            content = base64.b64decode(payload.content_base64, validate=True)
        except Exception as exc:  # noqa: BLE001 - 统一转为业务错误
            raise BadRequestError("文件内容不是有效的 Base64 数据") from exc
        if not content:
            raise BadRequestError("上传文件不能为空")

        creator = await self.session.get(User, share.created_by)
        if creator is None or creator.status != 1:
            raise NotFoundError("分享不存在或已失效")

        mime = payload.mime_type or (
            mimetypes.guess_type(payload.file_name)[0] or "application/octet-stream"
        )
        upload = UploadFile(
            file=BytesIO(content),
            size=len(content),
            filename=payload.file_name,
            headers=Headers({"content-type": mime}),
        )
        document_service = DocumentService(self.session, self.storage, self.publisher)
        # 公开 token 已完成授权，以系统上下文执行写入；审计信息仍记录分享创建者。
        sharer = CurrentUser(
            id=creator.id,
            username=creator.username,
            real_name=creator.real_name,
            is_superuser=True,
        )
        result = await document_service.upload_file(
            share.document_id,
            upload,
            sharer,
            meta,
            change_log=payload.change_log or "公开分享链接编辑",
        )
        await self._publish("public_saved", share.document_id)
        return result
