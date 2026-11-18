"""系统管理仓储：参数、公告、定时任务与日志查询。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, or_, select

from src.db.session import DatabaseSession
from src.models.log import LoginLog, OperationLog
from src.models.system import SysConfig, SysJob, SysNotice
from src.repositories.base import BaseRepository
from src.schemas.system import LogQuery


class ConfigRepository(BaseRepository[SysConfig]):
    """系统参数仓储。"""

    model = SysConfig

    def build_query(self, keyword: str | None = None) -> Select[Any]:
        """按关键字构造参数查询。"""
        statement = select(SysConfig)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(SysConfig.key.like(pattern), SysConfig.name.like(pattern))
            )
        return statement.order_by(SysConfig.id)


class NoticeRepository(BaseRepository[SysNotice]):
    """通知公告仓储。"""

    model = SysNotice

    def build_query(self, keyword: str | None = None) -> Select[Any]:
        """按标题关键字构造公告查询。"""
        statement = select(SysNotice)
        if keyword:
            statement = statement.where(SysNotice.title.like(f"%{keyword}%"))
        return statement.order_by(SysNotice.id.desc())


class JobRepository(BaseRepository[SysJob]):
    """定时任务仓储。"""

    model = SysJob

    def build_query(self) -> Select[Any]:
        """构造任务查询。"""
        return select(SysJob).order_by(SysJob.id)


class OperationLogRepository(BaseRepository[OperationLog]):
    """操作日志仓储。"""

    model = OperationLog

    def build_query(self, query: LogQuery) -> Select[Any]:
        """按条件构造操作日志查询。"""
        statement = select(OperationLog)
        if query.keyword:
            pattern = f"%{query.keyword}%"
            statement = statement.where(
                or_(
                    OperationLog.username.like(pattern),
                    OperationLog.module.like(pattern),
                    OperationLog.path.like(pattern),
                )
            )
        if query.username:
            statement = statement.where(OperationLog.username == query.username)
        if query.user_id is not None:
            statement = statement.where(OperationLog.user_id == query.user_id)
        return statement.order_by(OperationLog.id.desc())


class LoginLogRepository(BaseRepository[LoginLog]):
    """登录日志仓储。"""

    model = LoginLog

    def build_query(self, query: LogQuery) -> Select[Any]:
        """按条件构造登录日志查询。"""
        statement = select(LoginLog)
        if query.keyword:
            pattern = f"%{query.keyword}%"
            statement = statement.where(
                or_(LoginLog.username.like(pattern), LoginLog.ip.like(pattern))
            )
        if query.username:
            statement = statement.where(LoginLog.username == query.username)
        return statement.order_by(LoginLog.id.desc())
