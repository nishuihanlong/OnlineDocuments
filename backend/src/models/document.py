"""文档与版本模型（文档管理域）。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, PrimaryKeyMixin, SoftDeleteMixin, TimestampMixin


class Document(Base, PrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """文档主表，删除采用软删除以支持恢复。"""

    __tablename__ = "doc_document"

    title: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    owner_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    storage_key: Mapped[str | None] = mapped_column(String(512), default=None)
    file_name: Mapped[str | None] = mapped_column(String(256), default=None)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(128), default=None)
    download_count: Mapped[int] = mapped_column(Integer, default=0)


class DocumentVersion(Base, PrimaryKeyMixin, TimestampMixin):
    """文档版本快照，每次上传或更新生成新版本。"""

    __tablename__ = "doc_version"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("doc_document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(512), default=None)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    change_log: Mapped[str | None] = mapped_column(String(512), default=None)
    created_by: Mapped[int] = mapped_column(ForeignKey("sys_user.id"), nullable=False)
