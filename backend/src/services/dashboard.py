"""仪表盘统计业务逻辑：汇总用户、文档、版本与日志数据。"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, select

from src.core.cache import cached_json
from src.core.deps import DATA_SCOPE_ALL, DATA_SCOPE_DEPT, CurrentUser
from src.db.session import DatabaseSession
from src.models.document import Document, DocumentVersion
from src.models.log import OperationLog
from src.models.user import User
from src.schemas.dashboard import AnalysisTotalOut, MonthlySalesOut, NameValueOut


def document_owner_filter(principal: CurrentUser) -> Any:
    """根据数据范围生成文档归属过滤条件；admin 与 all 范围返回 None。"""
    if principal.is_superuser or principal.data_scope == DATA_SCOPE_ALL:
        return None
    if principal.data_scope == DATA_SCOPE_DEPT and principal.dept_id is not None:
        return Document.owner_id.in_(select(User.id).where(User.dept_id == principal.dept_id))
    return Document.owner_id == principal.id

class DashboardService:
    """只读统计查询，不修改任何业务数据。"""

    CACHE_TTL = 60  # 统计聚合较重但允许短暂延迟，缓存 60 秒

    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    @staticmethod
    def _cache_key(scope: str, principal: CurrentUser | None) -> str:
        """按数据范围、用户与当天日期构造缓存键，跨天自动失效。"""
        day = datetime.now(UTC).date().isoformat()
        if principal is None or principal.is_superuser:
            dimension = "all"
        elif principal.data_scope == DATA_SCOPE_ALL:
            dimension = "all"
        elif principal.data_scope == DATA_SCOPE_DEPT:
            dimension = f"dept:{principal.dept_id}"
        else:
            dimension = f"user:{principal.id}"
        return f"dash:{scope}:{dimension}:{day}"

    async def _count(self, statement: Select[tuple[int]]) -> int:
        """执行 count 查询并返回整数结果。"""
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def get_total(self, principal: CurrentUser | None = None) -> AnalysisTotalOut:
        """按数据范围查询四项概览指标（带缓存）。"""
        return await cached_json(
            self._cache_key("total", principal),
            AnalysisTotalOut,
            lambda: self._load_total(principal),
            self.CACHE_TTL,
        )

    async def _load_total(self, principal: CurrentUser | None = None) -> AnalysisTotalOut:
        """回源查询四项概览指标。"""
        is_admin = principal is None or principal.is_superuser or principal.data_scope == DATA_SCOPE_ALL
        user_statement = select(func.count()).select_from(User)
        log_statement = select(func.count()).select_from(OperationLog)
        document_filter = None if principal is None else document_owner_filter(principal)

        if not is_admin and principal is not None:
            if principal.data_scope == DATA_SCOPE_DEPT and principal.dept_id is not None:
                user_statement = user_statement.where(User.dept_id == principal.dept_id)
            else:
                user_statement = user_statement.where(User.id == principal.id)
            log_statement = log_statement.where(OperationLog.user_id == principal.id)

        document_statement = select(func.count()).select_from(Document).where(
            Document.deleted_at.is_(None)
        )
        version_statement = select(func.count()).select_from(DocumentVersion)
        if document_filter is not None:
            document_statement = document_statement.where(document_filter)
            version_statement = version_statement.where(
                DocumentVersion.document_id.in_(select(Document.id).where(document_filter))
            )

        return AnalysisTotalOut(
            users=await self._count(user_statement),
            documents=await self._count(document_statement),
            versions=await self._count(version_statement),
            operation_logs=await self._count(log_statement),
        )

    async def get_daily_activity(
        self, principal: CurrentUser | None = None
    ) -> list[NameValueOut]:
        """统计近 7 天的操作日志数量，用于柱状图（带缓存）。"""
        return await cached_json(
            self._cache_key("activity", principal),
            list[NameValueOut],
            lambda: self._load_daily_activity(principal),
            self.CACHE_TTL,
        )

    async def _load_daily_activity(
        self, principal: CurrentUser | None = None
    ) -> list[NameValueOut]:
        """回源统计近 7 天操作日志，在 Python 侧按日期聚合（兼容达梦 8）。"""
        statement = select(OperationLog.created_at)
        if principal is not None and not principal.is_superuser and principal.data_scope != DATA_SCOPE_ALL:
            statement = statement.where(OperationLog.user_id == principal.id)
        statement = statement.order_by(OperationLog.created_at.desc()).limit(1000)
        rows = (await self.session.execute(statement)).scalars().all()
        counter: Counter[str] = Counter()
        for value in rows:
            if isinstance(value, datetime):
                counter[value.date().isoformat()] += 1
        today = datetime.now(UTC).date()
        return [
            NameValueOut(
                name=(today - timedelta(days=offset)).strftime("%m-%d"),
                value=counter.get((today - timedelta(days=offset)).isoformat(), 0),
            )
            for offset in range(6, -1, -1)
        ]

    async def get_monthly_trend(
        self, principal: CurrentUser | None = None
    ) -> list[MonthlySalesOut]:
        """按数据范围统计近 12 个月文档新增与累计数量（带缓存）。"""
        return await cached_json(
            self._cache_key("trend", principal),
            list[MonthlySalesOut],
            lambda: self._load_monthly_trend(principal),
            self.CACHE_TTL,
        )

    async def _load_monthly_trend(
        self, principal: CurrentUser | None = None
    ) -> list[MonthlySalesOut]:
        """回源统计近 12 个月文档新增与累计数量。"""
        statement = select(Document.created_at)
        if principal is not None:
            document_filter = document_owner_filter(principal)
            if document_filter is not None:
                statement = statement.where(document_filter)
        rows = (await self.session.execute(statement)).scalars().all()
        counter: Counter[str] = Counter()
        for value in rows:
            if isinstance(value, datetime):
                counter[value.strftime("%Y-%m")] += 1
        today = datetime.now(UTC).date()
        months: list[str] = []
        for offset in range(11, -1, -1):
            year = today.year
            month = today.month - offset
            while month <= 0:
                month += 12
                year -= 1
            months.append(f"{year:04d}-{month:02d}")
        cumulative = 0
        trend: list[MonthlySalesOut] = []
        for month in months:
            current = counter.get(month, 0)
            cumulative += current
            trend.append(MonthlySalesOut(name=month, estimate=cumulative, actual=current))
        return trend
