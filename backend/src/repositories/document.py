"""文档与版本仓储。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, select

from src.core.deps import DATA_SCOPE_ALL, DATA_SCOPE_DEPT, CurrentUser
from src.db.session import DatabaseSession
from src.models.document import Document, DocumentVersion
from src.models.user import User
from src.repositories.base import BaseRepository
from src.schemas.document import DocumentQuery


class DocumentRepository(BaseRepository[Document]):
    """文档表 CRUD 与组合查询。"""

    model = Document

    def apply_data_scope(self, statement: Select[Any], principal: CurrentUser) -> Select[Any]:
        """按用户数据范围追加文档归属过滤。

        admin 与 all 范围不做过滤；self 仅本人；dept 为本部门所有用户。
        部门为空时退化为仅本人，避免误放开全库数据。
        """
        if principal.is_superuser or principal.data_scope == DATA_SCOPE_ALL:
            return statement
        if principal.data_scope == DATA_SCOPE_DEPT and principal.dept_id is not None:
            dept_users = select(User.id).where(User.dept_id == principal.dept_id)
            return statement.where(Document.owner_id.in_(dept_users))
        return statement.where(Document.owner_id == principal.id)

    def build_query(self, query: DocumentQuery, principal: CurrentUser) -> Select[Any]:
        """构造文档列表查询语句，包含数据范围与软删除过滤。"""
        statement = select(Document)
        if not query.include_deleted:
            statement = statement.where(Document.deleted_at.is_(None))
        if query.keyword:
            keyword = f"%{query.keyword}%"
            statement = statement.where(
                Document.title.like(keyword) | Document.description.like(keyword)
            )
        statement = self.apply_data_scope(statement, principal)
        return statement.order_by(Document.created_at.desc(), Document.id.desc())

    async def get_detail(
        self,
        document_id: int,
        principal: CurrentUser,
        include_deleted: bool = False,
    ) -> Document | None:
        """按数据范围查询文档详情。"""
        statement = select(Document).where(Document.id == document_id)
        if not include_deleted:
            statement = statement.where(Document.deleted_at.is_(None))
        statement = self.apply_data_scope(statement, principal)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_detail_unscoped(
        self, document_id: int, include_deleted: bool = False
    ) -> Document | None:
        """系统内部读取文档，不套用数据范围。

        仅供已通过其它授权机制（如公开分享 token）校验的场景使用。
        """
        statement = select(Document).where(Document.id == document_id)
        if not include_deleted:
            statement = statement.where(Document.deleted_at.is_(None))
        return (await self.session.execute(statement)).scalar_one_or_none()


class VersionRepository(BaseRepository[DocumentVersion]):
    """文档版本 CRUD。"""

    model = DocumentVersion

    async def list_by_document(self, document_id: int) -> list[DocumentVersion]:
        """按版本号倒序查询文档的所有版本。"""
        statement = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_no.desc())
        )
        return list((await self.session.execute(statement)).scalars().all())
