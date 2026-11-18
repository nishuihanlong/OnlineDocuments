"""组织管理 DTO：机构与部门。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.common import Iso8601DateTime


class OrgOut(BaseModel):
    """机构输出。"""

    id: int
    name: str
    code: str
    parent_id: int | None = None
    sort: int
    leader: str | None = None
    phone: str | None = None
    remark: str | None = None
    created_at: Iso8601DateTime
    updated_at: Iso8601DateTime


class OrgCreateIn(BaseModel):
    """新增机构请求。"""

    name: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    parent_id: int | None = None
    sort: int = 0
    leader: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    remark: str | None = Field(default=None, max_length=256)


class OrgUpdateIn(BaseModel):
    """更新机构请求，编码不可修改。"""

    name: str | None = Field(default=None, max_length=64)
    parent_id: int | None = None
    sort: int | None = None
    leader: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    remark: str | None = Field(default=None, max_length=256)


class DeptOut(BaseModel):
    """部门输出。"""

    id: int
    name: str
    code: str
    org_id: int | None = None
    parent_id: int | None = None
    sort: int
    leader: str | None = None
    phone: str | None = None
    created_at: Iso8601DateTime
    updated_at: Iso8601DateTime


class DeptCreateIn(BaseModel):
    """新增部门请求。"""

    name: str = Field(min_length=1, max_length=64)
    code: str = Field(default="", max_length=64)
    org_id: int | None = None
    parent_id: int | None = None
    sort: int = 0
    leader: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)


class DeptUpdateIn(BaseModel):
    """更新部门请求。"""

    name: str | None = Field(default=None, max_length=64)
    code: str | None = Field(default=None, max_length=64)
    org_id: int | None = None
    parent_id: int | None = None
    sort: int | None = None
    leader: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
