"""文档分享模型：公开链接与指定用户授权共用一张表。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, PrimaryKeyMixin, TimestampMixin


class DocumentShare(Base, PrimaryKeyMixin, TimestampMixin):
    """文档分享记录。

    granted_user_id 为空表示公开链接（免登录凭 token 访问）；
    非空表示分享给指定系统用户。撤销采用 revoked_at 软标记。
    """

    __tablename__ = "doc_share"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("doc_document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    permission: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="read/write"
    )
    granted_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("sys_user.id"), default=None, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_by: Mapped[int] = mapped_column(ForeignKey("sys_user.id"), nullable=False)
