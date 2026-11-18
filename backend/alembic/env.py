"""Alembic 迁移环境，目标 metadata 来自 src.db.base.Base。"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from alembic.ddl import DefaultImpl
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.db.dameng_compat import compare_dameng_type
from src.core.config import get_settings
from src.db.base import Base
import src.models  # noqa: F401  确保模型表注册到 metadata


# 达梦方言 dialect.name == "dm"，Alembic 默认未注册对应 DDL 实现，
# 会在 MigrationContext.configure 处抛 KeyError: 'dm'。按其扩展约定定义一个
# 基于 DefaultImpl 的实现，ImplMeta 元类会在导入时自动注册到 _impls["dm"]。
class DamengImpl(DefaultImpl):
    __dialect__ = "dm"

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))


def _skip_empty_revision(context, revision, directives) -> None:
    """autogenerate 无 schema 变更时不生成空迁移文件。"""
    if directives and directives[0].upgrade_ops.is_empty():
        directives[:] = []


def do_run_migrations(connection: Connection) -> None:
    """在指定连接上执行迁移。"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=_skip_empty_revision,
        compare_type=compare_dameng_type,
        # 达梦自增列反射为 Identity，Alembic 比较 server_default 会渲染崩溃；
        # 项目模型未使用 server_default，关闭该比较无实际损失。
        compare_server_default=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本而不连接数据库。"""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=compare_dameng_type,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """在线模式：通过异步引擎执行迁移。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式入口：异步驱动走 async 引擎，达梦 8 等同步驱动走同步引擎。"""
    url = config.get_main_option("sqlalchemy.url")
    if url.startswith("sqlite+aiosqlite") or url.startswith("dm+dmAsync"):
        asyncio.run(run_async_migrations())
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
