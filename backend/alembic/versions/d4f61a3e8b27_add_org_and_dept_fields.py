"""add organization table and extend department

Revision ID: d4f61a3e8b27
Revises: b2e83c7a1d94
Create Date: 2026-11-18
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4f61a3e8b27'
down_revision: Union[str, None] = 'b2e83c7a1d94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建机构表并扩展部门字段。"""
    op.create_table(
        "sys_org",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("leader", sa.String(length=64), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("remark", sa.String(length=256), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_sys_org_parent_id"), "sys_org", ["parent_id"], unique=False)
    for column in (
        sa.Column("code", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("leader", sa.String(length=64), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
    ):
        op.add_column("sys_dept", column)
    op.create_index(op.f("ix_sys_dept_org_id"), "sys_dept", ["org_id"], unique=False)


def downgrade() -> None:
    """移除部门扩展字段并删除机构表。"""
    op.drop_index(op.f("ix_sys_dept_org_id"), table_name="sys_dept")
    for name in ("phone", "leader", "org_id", "code"):
        op.drop_column("sys_dept", name)
    op.drop_index(op.f("ix_sys_org_parent_id"), table_name="sys_org")
    op.drop_table("sys_org")
