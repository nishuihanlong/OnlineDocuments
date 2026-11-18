"""基础设施只读监控：Redis 与 RabbitMQ 健康与指标采集。

只读取指标，不执行任何写操作（不删 key、不发消息、不改队列）。
Redis 用 INFO/DBSIZE；RabbitMQ 用 management HTTP API，地址与凭据从
``rabbitmq_url``（amqp://user:pass@host:port/vhost）推导，不可达时降级为
``reachable=false`` 而非抛错，避免监控页整体失败。
"""

from __future__ import annotations

import logging
from urllib.parse import unquote, urlsplit

import httpx

from src.core.cache import cached_json
from src.core.cache_keys import REDIS_MONITOR_KEY, RABBITMQ_MONITOR_KEY
from src.core.config import Settings
from src.schemas.system import (
    QueueInfo,
    RabbitMQMonitorOut,
    RedisMonitorOut,
)

logger = logging.getLogger(__name__)


class MonitorService:
    """Redis / RabbitMQ 只读监控服务。"""

    CACHE_TTL = 30

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def get_redis(self) -> RedisMonitorOut:
        """采集 Redis 指标（带缓存）。"""
        return await cached_json(
            REDIS_MONITOR_KEY, RedisMonitorOut, self._load_redis, self.CACHE_TTL
        )

    async def _load_redis(self) -> RedisMonitorOut:
        """通过 INFO/DBSIZE 采集 Redis 指标。"""
        if not self.settings.redis_url:
            return RedisMonitorOut(configured=False)
        try:
            import redis.asyncio as redis

            client = redis.from_url(self.settings.redis_url, decode_responses=True)
            try:
                info = await client.info()
                db_size = await client.dbsize()
            finally:
                await client.aclose()
            hits = int(info.get("keyspace_hits", 0))
            misses = int(info.get("keyspace_misses", 0))
            total = hits + misses
            return RedisMonitorOut(
                configured=True,
                reachable=True,
                version=str(info.get("redis_version", "")),
                uptime_seconds=int(info.get("uptime_in_seconds", 0)),
                used_memory_mb=round(int(info.get("used_memory", 0)) / 1024 / 1024, 2),
                connected_clients=int(info.get("connected_clients", 0)),
                total_keys=int(db_size),
                hit_rate=round(hits / total * 100, 2) if total else 0.0,
            )
        except Exception as exc:  # noqa: BLE001 - 监控探测失败降级返回
            logger.warning("Redis 监控采集失败: %s", exc)
            return RedisMonitorOut(configured=True, reachable=False, error=str(exc)[:200])

    async def get_rabbitmq(self) -> RabbitMQMonitorOut:
        """采集 RabbitMQ 指标（带缓存）。"""
        return await cached_json(
            RABBITMQ_MONITOR_KEY,
            RabbitMQMonitorOut,
            self._load_rabbitmq,
            self.CACHE_TTL,
        )

    @staticmethod
    def _management_target(amqp_url: str) -> tuple[str, tuple[str, str]] | None:
        """从 amqp URL 推导 management API 基址与凭据。"""
        parsed = urlsplit(amqp_url)
        if parsed.scheme not in {"amqp", "amqps"} or not parsed.hostname:
            return None
        user = unquote(parsed.username) if parsed.username else "guest"
        password = unquote(parsed.password) if parsed.password else "guest"
        return f"http://{parsed.hostname}:15672", (user, password)

    async def _load_rabbitmq(self) -> RabbitMQMonitorOut:
        """通过 management HTTP API 采集 RabbitMQ 指标。"""
        if not self.settings.rabbitmq_url:
            return RabbitMQMonitorOut(configured=False)
        target = self._management_target(self.settings.rabbitmq_url)
        if target is None:
            return RabbitMQMonitorOut(configured=True, reachable=False, error="RabbitMQ URL 格式无效")
        base_url, auth = target
        try:
            async with httpx.AsyncClient(timeout=5, auth=auth) as client:
                overview = (await client.get(f"{base_url}/api/overview")).json()
                queues_raw = (await client.get(f"{base_url}/api/queues")).json()
                exchanges_raw = (await client.get(f"{base_url}/api/exchanges")).json()
            queues = [
                QueueInfo(
                    name=str(item.get("name", "")),
                    vhost=str(item.get("vhost", "")),
                    messages=int(item.get("messages", 0)),
                    messages_ready=int(item.get("messages_ready", 0)),
                    messages_unacknowledged=int(item.get("messages_unacknowledged", 0)),
                    consumers=int(item.get("consumers", 0)),
                )
                for item in queues_raw
            ]
            return RabbitMQMonitorOut(
                configured=True,
                reachable=True,
                version=str(overview.get("rabbitmq_version", "")),
                exchange_count=len(exchanges_raw),
                queue_count=len(queues),
                total_messages=sum(q.messages for q in queues),
                queues=queues,
            )
        except Exception as exc:  # noqa: BLE001 - management API 不可达时降级
            logger.warning("RabbitMQ 监控采集失败: %s", exc)
            return RabbitMQMonitorOut(configured=True, reachable=False, error=str(exc)[:200])
