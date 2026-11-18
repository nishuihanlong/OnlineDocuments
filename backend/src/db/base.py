"""SQLAlchemy 声明式基类与通用列 Mixin。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """返回带 UTC 时区的当前时间，供所有时间字段统一使用。"""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


class PrimaryKeyMixin:
    """自增主键。"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class TimestampMixin:
    """创建时间与更新时间，序列化时由 Schema 统一转成 ISO 8601。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class SoftDeleteMixin:
    """软删除标记，用于文档删除与恢复。"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True
    )
