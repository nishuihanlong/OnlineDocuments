"""文档分享仓储。"""

from __future__ import annotations

from sqlalchemy import select

from src.models.share import DocumentShare
from src.repositories.base import BaseRepository


class ShareRepository(BaseRepository[DocumentShare]):
    """分享记录查询与维护。"""

    model = DocumentShare

    async def get_by_token(self, token: str) -> DocumentShare | None:
        """按分享 token 查询记录。"""
        statement = select(DocumentShare).where(DocumentShare.token == token)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_by_document(self, document_id: int) -> list[DocumentShare]:
        """查询某文档的全部分享记录，创建时间倒序。"""
        statement = (
            select(DocumentShare)
            .where(DocumentShare.document_id == document_id)
            .order_by(DocumentShare.created_at.desc(), DocumentShare.id.desc())
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def find_active_for_user(
        self, document_id: int, granted_user_id: int | None
    ) -> DocumentShare | None:
        """查询某文档对某对象（用户或公开）的未撤销分享，用于复用。"""
        statement = select(DocumentShare).where(
            DocumentShare.document_id == document_id,
            DocumentShare.granted_user_id == granted_user_id,
            DocumentShare.revoked_at.is_(None),
        )
        return (await self.session.execute(statement)).scalar_one_or_none()
