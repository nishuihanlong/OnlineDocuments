"""缓存抽象：Redis 可用时使用 Redis，否则降级为进程内缓存。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

from src.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class CacheClient(Protocol):
    """缓存客户端接口。"""

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def delete_prefix(self, prefix: str) -> None: ...


class MemoryCache:
    """进程内缓存，仅用于开发与单实例测试环境。"""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        """读取缓存，过期后自动删除。"""
        async with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at < asyncio.get_running_loop().time():
                del self._data[key]
                return None
            return value

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        """写入带过期时间的缓存。"""
        async with self._lock:
            expires_at = asyncio.get_running_loop().time() + ttl_seconds
            self._data[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """删除指定缓存键。"""
        async with self._lock:
            self._data.pop(key, None)

    async def delete_prefix(self, prefix: str) -> None:
        """删除所有以 prefix 开头的缓存键。"""
        async with self._lock:
            for key in [key for key in self._data if key.startswith(prefix)]:
                del self._data[key]


class RedisCache:
    """基于 redis.asyncio 的缓存实现。

    运行期 Redis 故障时降级到进程内缓存，避免缓存问题拖垮业务接口。
    """

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis

        self._client = redis.from_url(redis_url, decode_responses=True)
        self._fallback = MemoryCache()
        self._degraded = False

    async def get(self, key: str) -> str | None:
        """读取缓存值，Redis 异常时回退内存缓存。"""
        try:
            return await self._client.get(key)
        except Exception as exc:  # noqa: BLE001 - 缓存故障不应影响业务
            if not self._degraded:
                logger.warning("Redis 读取失败，临时降级为内存缓存: %s", exc)
                self._degraded = True
            return await self._fallback.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        """写入带过期时间的缓存值，Redis 异常时回退内存缓存。"""
        if self._degraded:
            await self._fallback.set(key, value, ttl_seconds)
            return
        try:
            await self._client.set(key, value, ex=ttl_seconds)
        except Exception as exc:  # noqa: BLE001
            if not self._degraded:
                logger.warning("Redis 写入失败，临时降级为内存缓存: %s", exc)
                self._degraded = True
            await self._fallback.set(key, value, ttl_seconds)

    async def delete(self, key: str) -> None:
        """删除缓存键，Redis 异常时同时清理内存缓存。"""
        try:
            await self._client.delete(key)
        except Exception as exc:  # noqa: BLE001
            if not self._degraded:
                logger.warning("Redis 删除失败，临时降级为内存缓存: %s", exc)
                self._degraded = True
        await self._fallback.delete(key)

    async def delete_prefix(self, prefix: str) -> None:
        """按前缀批量删除，Redis 用扫描游标，异常时回退内存缓存。"""
        try:
            async for key in self._client.scan_iter(match=f"{prefix}*"):
                await self._client.delete(key)
        except Exception as exc:  # noqa: BLE001
            if not self._degraded:
                logger.warning("Redis 前缀删除失败，临时降级为内存缓存: %s", exc)
                self._degraded = True
        await self._fallback.delete_prefix(prefix)


_cache_client: CacheClient | None = None


def get_cache(settings: Settings | None = None) -> CacheClient:
    """返回缓存客户端单例；Redis 不可用时安全降级。"""
    global _cache_client
    if _cache_client is None:
        current = settings or get_settings()
        if current.redis_url:
            try:
                _cache_client = RedisCache(current.redis_url)
                logger.info("缓存后端: Redis")
            except (ImportError, ValueError) as exc:
                logger.warning("Redis 初始化失败，降级为进程内缓存: %s", exc)
                _cache_client = MemoryCache()
        else:
            _cache_client = MemoryCache()
    return _cache_client


def reset_cache(settings: Settings | None = None) -> CacheClient:
    """重建缓存客户端单例（用于测试隔离或服务重启后的干净状态）。"""
    global _cache_client
    _cache_client = None
    return get_cache(settings)


async def cached_json(
    key: str,
    model_type: Any,
    loader,
    ttl_seconds: int = 300,
    settings: Settings | None = None,
):
    """读取并反序列化缓存；未命中时调用 loader 回源并写入缓存。

    Args:
        key: 缓存键，调用方需保证带业务前缀与维度（如 ``perm:ctx:3``）。
        model_type: Pydantic 模型或可被 ``TypeAdapter`` 处理的类型（含 ``list[X]``）。
        loader: 无参异步可调用，缓存未命中时加载数据并返回该类型的值。
        ttl_seconds: 缓存有效期，默认 5 分钟。
        settings: 可选配置，用于注入缓存客户端（便于测试）。

    Returns:
        model_type 对应类型的值。
    """
    from pydantic import TypeAdapter

    cache = get_cache(settings)
    adapter = TypeAdapter(model_type)
    raw = await cache.get(key)
    if raw is not None:
        try:
            return adapter.validate_json(raw)
        except Exception as exc:  # noqa: BLE001 - 缓存内容损坏时回源
            logger.warning("缓存 %s 反序列化失败，回源重建: %s", key, exc)
    value = await loader()
    try:
        await cache.set(key, adapter.dump_json(value).decode("utf-8"), ttl_seconds)
    except Exception as exc:  # noqa: BLE001 - 写入失败不影响返回
        logger.warning("缓存 %s 写入失败: %s", key, exc)
    return value
