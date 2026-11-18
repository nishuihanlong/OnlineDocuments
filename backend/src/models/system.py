"""系统管理模型：参数配置、通知公告与定时任务。"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, PrimaryKeyMixin, TimestampMixin


class SysConfig(Base, PrimaryKeyMixin, TimestampMixin):
    """系统参数配置。"""

    __tablename__ = "sys_config"

    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    value: Mapped[str | None] = mapped_column(Text, default=None)
    name: Mapped[str] = mapped_column(String(128), default="")
    remark: Mapped[str | None] = mapped_column(String(256), default=None)


class SysNotice(Base, PrimaryKeyMixin, TimestampMixin):
    """通知公告与系统公告。"""

    __tablename__ = "sys_notice"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    type: Mapped[str] = mapped_column(String(16), default="notice", comment="notice/announcement")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SysJob(Base, PrimaryKeyMixin, TimestampMixin):
    """定时任务定义；执行由调度器轮询 enabled 记录完成。"""

    __tablename__ = "sys_job"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[str | None] = mapped_column(String(32), default=None)
