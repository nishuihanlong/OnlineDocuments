"""用户、角色、部门、岗位与菜单模型（系统管理域）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, PrimaryKeyMixin, TimestampMixin

# 用户状态：待激活用户不能登录，需管理员激活。
USER_STATUS_DISABLED = 0
USER_STATUS_ACTIVE = 1
USER_STATUS_PENDING = 2


user_role = Table(
    "sys_user_role",
    Base.metadata,
    Column("user_id", ForeignKey("sys_user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
)

role_menu = Table(
    "sys_role_menu",
    Base.metadata,
    Column("role_id", ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_id", ForeignKey("sys_menu.id", ondelete="CASCADE"), primary_key=True),
)


class Org(Base, PrimaryKeyMixin, TimestampMixin):
    """机构，组织树的最上层节点，支持多级子机构。"""

    __tablename__ = "sys_org"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    leader: Mapped[str | None] = mapped_column(String(64), default=None)
    phone: Mapped[str | None] = mapped_column(String(32), default=None)
    remark: Mapped[str | None] = mapped_column(String(256), default=None)


class Dept(Base, PrimaryKeyMixin, TimestampMixin):
    """部门，可挂靠在某个机构下并支持父子层级。"""

    __tablename__ = "sys_dept"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), default="")
    org_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    leader: Mapped[str | None] = mapped_column(String(64), default=None)
    phone: Mapped[str | None] = mapped_column(String(32), default=None)


class Post(Base, PrimaryKeyMixin, TimestampMixin):
    """岗位。"""

    __tablename__ = "sys_post"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Menu(Base, PrimaryKeyMixin, TimestampMixin):
    """菜单与动态路由定义；component 与前端 src/views 下的组件路径对应。"""

    __tablename__ = "sys_menu"

    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    path: Mapped[str] = mapped_column(String(128), nullable=False)
    component: Mapped[str] = mapped_column(String(256), nullable=False)
    redirect: Mapped[str | None] = mapped_column(String(128), default=None)
    icon: Mapped[str | None] = mapped_column(String(128), default=None)
    parent_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    permission_code: Mapped[str | None] = mapped_column(String(128), default=None)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Role(Base, PrimaryKeyMixin, TimestampMixin):
    """角色，关联菜单用于动态路由与权限控制。"""

    __tablename__ = "sys_role"

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256), default=None)
    menus: Mapped[list[Menu]] = relationship(secondary=role_menu, lazy="selectin")


class User(Base, PrimaryKeyMixin, TimestampMixin):
    """系统用户。"""

    __tablename__ = "sys_user"

    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    real_name: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str | None] = mapped_column(String(128), default=None)
    phone: Mapped[str | None] = mapped_column(String(32), default=None)
    dept_id: Mapped[int | None] = mapped_column(ForeignKey("sys_dept.id"), default=None)
    data_scope: Mapped[str] = mapped_column(
        String(16), default="self", comment="数据范围 all/self/dept"
    )
    post_id: Mapped[int | None] = mapped_column(ForeignKey("sys_post.id"), default=None)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1 启用 / 0 停用 / 2 待激活")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    roles: Mapped[list[Role]] = relationship(secondary=user_role, lazy="selectin")
