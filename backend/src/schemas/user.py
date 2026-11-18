"""用户与角色管理 DTO。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.common import Iso8601DateTime, PageQuery

DataScope = Literal["all", "self", "dept"]


class RoleOut(BaseModel):
    """角色输出。"""

    id: int
    code: str
    name: str
    description: str | None = None


class RoleDetailOut(BaseModel):
    """角色详情，含已授权菜单。"""

    id: int
    code: str
    name: str
    description: str | None = None
    menu_ids: list[int] = Field(default_factory=list)
    created_at: Iso8601DateTime


class RoleCreateIn(BaseModel):
    """新增角色请求。"""

    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=256)
    menu_ids: list[int] = Field(default_factory=list)


class RoleUpdateIn(BaseModel):
    """更新角色请求。"""

    name: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=256)
    menu_ids: list[int] | None = None


class UserOut(BaseModel):
    """用户输出，禁止暴露 password_hash。"""

    id: int
    username: str
    real_name: str
    email: str | None = None
    phone: str | None = None
    dept_id: int | None = None
    data_scope: DataScope = "self"
    post_id: int | None = None
    status: int
    is_superuser: bool
    roles: list[RoleOut] = Field(default_factory=list)
    last_login_at: Iso8601DateTime | None = None
    created_at: Iso8601DateTime


class UserQuery(PageQuery):
    """用户分页查询条件。"""

    keyword: str | None = Field(default=None, description="用户名或姓名模糊匹配")
    status: int | None = Field(default=None, ge=0, le=2, description="0 停用 / 1 启用 / 2 待激活")


class UserCreateIn(BaseModel):
    """新增用户请求。"""

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    real_name: str = Field(default="", max_length=64)
    email: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    dept_id: int | None = None
    data_scope: DataScope = "self"
    post_id: int | None = None
    role_ids: list[int] = Field(default_factory=list)


class UserUpdateIn(BaseModel):
    """更新用户请求，所有字段可选。"""

    real_name: str | None = None
    email: str | None = None
    phone: str | None = None
    dept_id: int | None = None
    data_scope: DataScope | None = None
    post_id: int | None = None
    status: int | None = Field(default=None, ge=0, le=2, description="0 停用 / 1 启用 / 2 待激活")
    role_ids: list[int] | None = None
