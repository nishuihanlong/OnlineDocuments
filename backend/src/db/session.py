"""数据库引擎与会话管理，统一支持原生异步与同步（达梦 8）两种驱动。

业务代码只依赖 `DatabaseSession`（即 `AsyncSession | SyncDatabaseSession`）。
- 开发环境使用 `sqlite+aiosqlite` 原生异步引擎；
- 生产达梦 8 使用官方 `dmSQLAlchemy` 方言（`dm+dmPython://`，同步 DBAPI），
  通过 `SyncDatabaseSession` 把同步 `Session` 适配为异步门面（操作经线程池执行），
  使同一套 `await session.execute(...)` 代码无需改动即可运行在达梦 8 上。
"""

from __future__ import annotations

import asyncio
import logging

import src.db.dameng_compat  # noqa: F401  在加载 dmSQLAlchemy 前打达梦方言反射补丁
from collections.abc import AsyncGenerator, Iterable, Sequence
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import Result, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.config import Settings, get_settings
from src.db.base import Base

logger = logging.getLogger(__name__)

_engine: Any = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None
_sync_session_maker: sessionmaker[Session] | None = None


class QueryResult:
    """执行结果协议：统一异步 Result 与同步物化结果的方法集合。"""

    def all(self) -> Sequence[Any]:
        raise NotImplementedError

    def scalar_one(self) -> Any:
        raise NotImplementedError

    def scalar_one_or_none(self) -> Any:
        raise NotImplementedError

    def scalars(self) -> ScalarResult:
        raise NotImplementedError


class ScalarResult:
    """列投影结果协议，对应 Result.scalars() 的返回。"""

    def all(self) -> Sequence[Any]:
        raise NotImplementedError

    def first(self) -> Any:
        raise NotImplementedError

    def unique(self) -> ScalarResult:
        raise NotImplementedError


class MaterializedResult(QueryResult):
    """把同步执行结果物化为普通数据，便于在线程边界之外安全访问。"""

    __slots__ = ("_rows",)

    def __init__(self, rows: Sequence[Any]) -> None:
        self._rows = rows

    def all(self) -> Sequence[Any]:
        return self._rows

    def scalar_one(self) -> Any:
        return self._rows[0][0]

    def scalar_one_or_none(self) -> Any:
        if not self._rows:
            return None
        return self._rows[0][0]

    def scalars(self) -> ScalarResult:
        return MaterializedScalars(self._rows)


class MaterializedScalars(ScalarResult):
    """物化结果对应的列投影，提供 all/first/unique。"""

    __slots__ = ("_rows",)

    def __init__(self, rows: Sequence[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return [row[0] for row in self._rows]

    def first(self) -> Any:
        return self._rows[0][0] if self._rows else None

    def unique(self) -> ScalarResult:
        seen: dict[int, Any] = {}
        for row in self._rows:
            seen[id(row[0])] = row[0]
        return MaterializedScalars([(value,) for value in seen.values()])


class SyncDatabaseSession:
    """同步驱动（达梦 8 dmPython）的异步门面，所有操作经线程池执行。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> QueryResult:
        result: Result[Any] = await asyncio.to_thread(self._session.execute, statement, *args, **kwargs)
        return MaterializedResult(result.all())

    async def get(self, entity: Any, ident: Any, **kwargs: Any) -> Any | None:
        return await asyncio.to_thread(self._session.get, entity, ident, **kwargs)

    def add(self, instance: Any) -> None:
        self._session.add(instance)

    def add_all(self, instances: Iterable[Any]) -> None:
        self._session.add_all(instances)

    def delete(self, instance: Any) -> None:
        self._session.delete(instance)

    async def flush(self, *objects: Any) -> None:
        await asyncio.to_thread(self._session.flush, *objects)

    async def commit(self) -> None:
        await asyncio.to_thread(self._session.commit)

    async def rollback(self) -> None:
        await asyncio.to_thread(self._session.rollback)

    async def refresh(self, instance: Any, *attribute_names: Any) -> None:
        await asyncio.to_thread(self._session.refresh, instance, *attribute_names)

    def close(self) -> None:
        self._session.close()


# 业务层统一依赖的会话类型：原生异步会话或同步驱动门面
DatabaseSession = AsyncSession | SyncDatabaseSession


def build_engine(settings: Settings) -> Any:
    """按数据库 URL 创建引擎。

    - `sqlite+aiosqlite` 或达梦 8 原生异步方言 `dm+dmAsync://`（需安装 `dmAsync` 异步驱动）：
      使用 `create_async_engine`，业务层直接拿到真正的 `AsyncSession`，无需线程池。
    - 其它（达梦 8 同步方言 `dm+dmPython://`、同步 `sqlite://` 等）：创建同步引擎，
      由 `SyncDatabaseSession` 在线程池中适配为异步会话门面。
    """
    url = settings.database_url
    if url.startswith("sqlite+aiosqlite") or url.startswith("dm+dmAsync"):
        engine_kwargs: dict[str, Any] = {"echo": settings.sql_echo}
        if ":memory:" in url:
            engine_kwargs["poolclass"] = StaticPool
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        return create_async_engine(url, **engine_kwargs)

    engine_kwargs = {"echo": settings.sql_echo, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **engine_kwargs)


def init_engine(settings: Settings | None = None) -> None:
    """初始化全局引擎与会话工厂，由应用 lifespan 调用。"""
    global _engine, _async_session_maker, _sync_session_maker
    current = settings or get_settings()
    _engine = build_engine(current)
    if isinstance(_engine, AsyncEngine):
        _async_session_maker = async_sessionmaker(
            bind=_engine, expire_on_commit=False, autoflush=False
        )
        _sync_session_maker = None
    else:
        _sync_session_maker = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
        _async_session_maker = None
    logger.info("数据库引擎已初始化: %s", current.database_url.split("@")[-1])


def get_session_factory() -> Any:
    """返回会话工厂，未初始化时给出明确错误。"""
    if _async_session_maker is None and _sync_session_maker is None:
        raise RuntimeError("数据库会话工厂未初始化，请先调用 init_engine()")
    return _async_session_maker or _sync_session_maker


async def get_db() -> AsyncGenerator[DatabaseSession, None]:
    """FastAPI 依赖：每个请求一个会话，异常时回滚。"""
    if _async_session_maker is not None:
        async with _async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
    else:
        assert _sync_session_maker is not None
        sync_session = _sync_session_maker()
        wrapper = SyncDatabaseSession(sync_session)
        try:
            yield wrapper
            await wrapper.commit()
        except Exception:
            await wrapper.rollback()
            raise
        finally:
            wrapper.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[DatabaseSession, None]:
    """供应用 lifespan 与测试初始化种子数据使用，兼容异步与同步引擎。"""
    if _async_session_maker is not None:
        async with _async_session_maker() as session:
            yield session
    else:
        assert _sync_session_maker is not None
        sync_session = _sync_session_maker()
        wrapper = SyncDatabaseSession(sync_session)
        try:
            yield wrapper
        finally:
            wrapper.close()


async def init_models() -> None:
    """开发环境自动建表；生产环境应改用 Alembic 迁移。"""
    if _engine is None:
        raise RuntimeError("数据库引擎未初始化")
    if isinstance(_engine, AsyncEngine):
        async with _engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    else:
        await asyncio.to_thread(Base.metadata.create_all, _engine)
    logger.info("数据表已就绪")


async def dispose_engine() -> None:
    """关闭连接池，由应用 shutdown 时调用。"""
    global _engine
    if isinstance(_engine, AsyncEngine):
        await _engine.dispose()
    elif _engine is not None:
        await asyncio.to_thread(_engine.dispose)
    _engine = None
