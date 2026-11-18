"""操作日志与登录日志模型。"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, PrimaryKeyMixin, TimestampMixin


class OperationLog(Base, PrimaryKeyMixin, TimestampMixin):
    """用户操作审计日志。"""

    __tablename__ = "sys_operation_log"

    user_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    module: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(128), default="")
    method: Mapped[str] = mapped_column(String(16), default="")
    path: Mapped[str] = mapped_column(String(256), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    detail: Mapped[str | None] = mapped_column(Text, default=None)


class LoginLog(Base, PrimaryKeyMixin, TimestampMixin):
    """登录审计日志，包含失败尝试。"""

    __tablename__ = "sys_login_log"

    username: Mapped[str] = mapped_column(String(64), default="", index=True)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[str] = mapped_column(String(256), default="")
