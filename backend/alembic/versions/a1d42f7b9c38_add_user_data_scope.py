"""add user data scope

Revision ID: a1d42f7b9c38
Revises: c7e42a9f1b83
Create Date: 2026-11-18
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1d42f7b9c38'
down_revision: Union[str, None] = 'c7e42a9f1b83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为用户增加数据范围字段，已有用户默认为仅本人。"""
    op.add_column(
        "sys_user",
        sa.Column(
            "data_scope",
            sa.String(length=16),
            nullable=False,
            server_default="self",
            comment="数据范围 all/self/dept",
        ),
    )


def downgrade() -> None:
    """移除用户数据范围字段。"""
    op.drop_column("sys_user", "data_scope")
