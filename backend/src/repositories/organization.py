"""组织管理仓储：机构与部门。"""

from __future__ import annotations

from sqlalchemy import select

from src.db.session import DatabaseSession
from src.models.user import Dept, Org
from src.repositories.base import BaseRepository


class OrgRepository(BaseRepository[Org]):
    """机构 CRUD。"""

    model = Org

    async def list_all(self) -> list[Org]:
        """查询全部机构，按排序返回。"""
        statement = select(Org).order_by(Org.sort, Org.id)
        return list((await self.session.execute(statement)).scalars().all())

    async def get_by_code(self, code: str) -> Org | None:
        """按机构编码查询。"""
        statement = select(Org).where(Org.code == code)
        return (await self.session.execute(statement)).scalar_one_or_none()


class DeptRepository(BaseRepository[Dept]):
    """部门 CRUD。"""

    model = Dept

    async def list_all(self) -> list[Dept]:
        """查询全部部门，按排序返回。"""
        statement = select(Dept).order_by(Dept.sort, Dept.id)
        return list((await self.session.execute(statement)).scalars().all())
