"""组织管理业务逻辑：机构与部门的层级维护。"""

from __future__ import annotations

from src.core.cache import cached_json
from src.core.cache_keys import (
    DEPT_LIST_KEY,
    ORG_LIST_KEY,
    invalidate_catalog,
)
from src.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.db.session import DatabaseSession
from src.models.user import Dept, Org
from src.repositories.organization import DeptRepository, OrgRepository
from src.schemas.organization import (
    DeptCreateIn,
    DeptOut,
    DeptUpdateIn,
    OrgCreateIn,
    OrgOut,
    OrgUpdateIn,
)


def to_org_out(item: Org) -> OrgOut:
    """机构 ORM 转 DTO。"""
    return OrgOut(
        id=item.id, name=item.name, code=item.code, parent_id=item.parent_id,
        sort=item.sort, leader=item.leader, phone=item.phone, remark=item.remark,
        created_at=item.created_at, updated_at=item.updated_at,
    )


def to_dept_out(item: Dept) -> DeptOut:
    """部门 ORM 转 DTO。"""
    return DeptOut(
        id=item.id, name=item.name, code=item.code, org_id=item.org_id,
        parent_id=item.parent_id, sort=item.sort, leader=item.leader, phone=item.phone,
        created_at=item.created_at, updated_at=item.updated_at,
    )


class OrganizationService:
    """机构与部门用例编排。"""

    def __init__(self, session: DatabaseSession) -> None:
        self.session = session
        self.orgs = OrgRepository(session)
        self.depts = DeptRepository(session)

    async def list_orgs(self) -> list[OrgOut]:
        """查询全部机构（带缓存）。"""
        return await cached_json(ORG_LIST_KEY, list[OrgOut], self._load_orgs)

    async def _load_orgs(self) -> list[OrgOut]:
        """回源查询全部机构。"""
        return [to_org_out(item) for item in await self.orgs.list_all()]

    async def create_org(self, payload: OrgCreateIn) -> OrgOut:
        """新建机构，编码需唯一。"""
        if await self.orgs.get_by_code(payload.code) is not None:
            raise ConflictError("机构编码已存在")
        item = Org(**payload.model_dump())
        await self.orgs.add(item)
        await self.session.commit()
        await invalidate_catalog(ORG_LIST_KEY)
        return to_org_out(item)

    async def update_org(self, org_id: int, payload: OrgUpdateIn) -> OrgOut:
        """更新机构资料。"""
        item = await self.orgs.get_by_id(org_id)
        if item is None:
            raise NotFoundError("机构不存在")
        if item.id == payload.parent_id:
            raise BadRequestError("机构不能将自身设为上级")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.commit()
        await invalidate_catalog(ORG_LIST_KEY)
        return to_org_out(item)

    async def delete_org(self, org_id: int) -> None:
        """删除机构，存在子机构或部门时拒绝。"""
        item = await self.orgs.get_by_id(org_id)
        if item is None:
            raise NotFoundError("机构不存在")
        if any(org.parent_id == org_id for org in await self.orgs.list_all()):
            raise BadRequestError("请先删除子机构")
        if any(dept.org_id == org_id for dept in await self.depts.list_all()):
            raise BadRequestError("该机构下存在部门，无法删除")
        await self.orgs.delete(item)
        await self.session.commit()
        await invalidate_catalog(ORG_LIST_KEY)

    async def list_depts(self) -> list[DeptOut]:
        """查询全部部门（带缓存）。"""
        return await cached_json(DEPT_LIST_KEY, list[DeptOut], self._load_depts)

    async def _load_depts(self) -> list[DeptOut]:
        """回源查询全部部门。"""
        return [to_dept_out(item) for item in await self.depts.list_all()]

    async def create_dept(self, payload: DeptCreateIn) -> DeptOut:
        """新建部门。"""
        item = Dept(**payload.model_dump())
        await self.depts.add(item)
        await self.session.commit()
        await invalidate_catalog(DEPT_LIST_KEY)
        return to_dept_out(item)

    async def update_dept(self, dept_id: int, payload: DeptUpdateIn) -> DeptOut:
        """更新部门资料。"""
        item = await self.depts.get_by_id(dept_id)
        if item is None:
            raise NotFoundError("部门不存在")
        if item.id == payload.parent_id:
            raise BadRequestError("部门不能将自身设为上级")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.commit()
        await invalidate_catalog(DEPT_LIST_KEY)
        return to_dept_out(item)

    async def delete_dept(self, dept_id: int) -> None:
        """删除部门，存在子部门时拒绝。"""
        item = await self.depts.get_by_id(dept_id)
        if item is None:
            raise NotFoundError("部门不存在")
        if any(dept.parent_id == dept_id for dept in await self.depts.list_all()):
            raise BadRequestError("请先删除子部门")
        await self.depts.delete(item)
        await self.session.commit()
        await invalidate_catalog(DEPT_LIST_KEY)
