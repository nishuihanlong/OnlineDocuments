"""菜单与权限管理 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.common import Iso8601DateTime


class MenuOut(BaseModel):
    """菜单输出，供权限管理树形展示。"""

    id: int
    name: str
    title: str
    path: str
    component: str
    redirect: str | None = None
    icon: str | None = None
    parent_id: int | None = None
    sort: int
    permission_code: str | None = None
    hidden: bool
    enabled: bool
    created_at: Iso8601DateTime


class MenuCreateIn(BaseModel):
    """新增菜单请求。"""

    name: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=128)
    component: str = Field(min_length=1, max_length=256)
    parent_id: int | None = None
    redirect: str | None = Field(default=None, max_length=128)
    icon: str | None = Field(default=None, max_length=128)
    sort: int = 0
    permission_code: str | None = Field(default=None, max_length=128)
    hidden: bool = False
    enabled: bool = True


class MenuUpdateIn(BaseModel):
    """更新菜单请求。"""

    title: str | None = Field(default=None, max_length=128)
    path: str | None = Field(default=None, max_length=128)
    component: str | None = Field(default=None, max_length=256)
    parent_id: int | None = None
    redirect: str | None = Field(default=None, max_length=128)
    icon: str | None = Field(default=None, max_length=128)
    sort: int | None = None
    permission_code: str | None = Field(default=None, max_length=128)
    hidden: bool | None = None
    enabled: bool | None = None
