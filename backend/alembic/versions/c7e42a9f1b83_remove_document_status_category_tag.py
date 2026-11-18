"""remove document status, category and tag

Revision ID: c7e42a9f1b83
Revises: 4358ea7c2830
Create Date: 2026-11-18
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c7e42a9f1b83'
down_revision: Union[str, None] = '4358ea7c2830'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_foreign_key(table_name: str, column_name: str) -> None:
    """按列名删除外键约束。

    达梦数据库会自动生成外键名称，这里通过反射按列名定位后删除，
    避免在不同环境之间硬编码约束名。
    """
    inspector = sa.inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table_name):
        if column_name in foreign_key.get("constrained_columns", []):
            constraint_name = foreign_key.get("name")
            if constraint_name:
                op.drop_constraint(constraint_name, table_name, type_="foreignkey")
            return


def upgrade() -> None:
    """移除文档状态列、分类外键与标签相关表。"""
    _drop_foreign_key("doc_document", "category_id")
    op.drop_column("doc_document", "status")
    op.drop_column("doc_document", "category_id")
    op.drop_table("doc_document_tag")
    op.drop_table("doc_tag")
    op.drop_table("doc_category")


def downgrade() -> None:
    """重建状态列、分类关联与标签相关表；被移除的业务数据不可恢复。"""
    op.create_table(
        "doc_category",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_doc_category_parent_id"), "doc_category", ["parent_id"], unique=False)
    op.create_table(
        "doc_tag",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.add_column("doc_document", sa.Column("category_id", sa.Integer(), nullable=True))
    op.add_column(
        "doc_document",
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
            comment="draft/pending/published/archived",
        ),
    )
    op.create_foreign_key(
        "fk_doc_document_category", "doc_document", "doc_category", ["category_id"], ["id"]
    )
    op.create_table(
        "doc_document_tag",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["doc_document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["doc_tag.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "tag_id"),
    )
