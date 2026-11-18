"""通用仓储基类，提供分页与基础 CRUD。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select

from src.db.base import Base
from src.db.session import DatabaseSession

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """面向单一 ORM 模型的通用仓储，会话由依赖注入传入。"""

    model: type[ModelT]

    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    async def get_by_id(self, entity_id: int) -> ModelT | None:
        """按主键查询单条记录。"""
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        """新增记录并刷新，使自增主键可用。"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """物理删除记录（业务删除请使用软删除字段）。"""
        await self.session.delete(entity)
        await self.session.flush()

    async def paginate(
        self,
        statement: Select[Any],
        page: int,
        page_size: int,
    ) -> tuple[Sequence[Any], int]:
        """执行分页查询，返回当前页数据与总记录数。"""
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = (await self.session.execute(count_statement)).scalar_one()
        rows = await self.session.execute(statement.offset((page - 1) * page_size).limit(page_size))
        return rows.scalars().unique().all(), int(total)

    async def commit(self) -> None:
        """提交当前事务。"""
        await self.session.commit()

    async def rollback(self) -> None:
        """回滚当前事务。"""
        await self.session.rollback()
