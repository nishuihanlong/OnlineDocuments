"""通用 DTO：分页、ISO 8601 时间类型。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field, PlainSerializer

ItemT = TypeVar("ItemT")


def as_utc(value: datetime) -> datetime:
    """把 datetime 归一化为 UTC。

    达梦等驱动读取 DateTime 列时可能丢失 tzinfo 并返回 naive datetime，
    而项目写入的时间均为 UTC，因此 naive 值按 UTC 解释，避免与带时区的
    时间比较时抛出 TypeError，也避免序列化时被误当作系统本地时间。
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_iso8601(value: datetime) -> str:
    """把 datetime 转成 UTC 的 ISO 8601 字符串，例如 2026-11-13T10:00:00Z。"""
    return as_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


Iso8601DateTime = Annotated[
    datetime,
    PlainSerializer(to_iso8601, return_type=str, when_used="json"),
]


class PageQuery(BaseModel):
    """分页查询参数。"""

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")

    @property
    def offset(self) -> int:
        """计算 SQL OFFSET。"""
        return (self.page - 1) * self.page_size


class PageResult(BaseModel, Generic[ItemT]):
    """分页响应结构。"""

    items: list[ItemT]
    total: int = Field(description="总记录数")
    page: int
    page_size: int
