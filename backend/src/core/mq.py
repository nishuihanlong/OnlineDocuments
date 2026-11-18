"""领域事件发布抽象：RabbitMQ 可用时发布，否则仅记录日志。"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from pydantic import BaseModel, Field

from src.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class DomainEvent(BaseModel):
    """发布到消息队列的领域事件结构，禁止使用裸 dict 传递。"""

    event_type: str = Field(description="事件类型，如 document.created")
    aggregate_id: int = Field(description="聚合根 ID")
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    occurred_at: str = Field(description="事件发生时间，ISO 8601")


class EventPublisher(Protocol):
    """事件发布器接口。"""

    async def publish(self, event: DomainEvent) -> None: ...

    async def close(self) -> None: ...


class NoopEventPublisher:
    """未配置 RabbitMQ 时的空实现，保留日志便于排查。"""

    async def publish(self, event: DomainEvent) -> None:
        """仅记录事件日志。"""
        logger.debug("领域事件(未配置 MQ): %s", event.event_type)

    async def close(self) -> None:
        """无需释放资源。"""
        return None


class RabbitMQEventPublisher:
    """基于 aio-pika 的 RabbitMQ 事件发布器，采用 topic 交换机。"""

    def __init__(self, amqp_url: str, exchange_name: str) -> None:
        self._amqp_url = amqp_url
        self._exchange_name = exchange_name
        self._connection: Any = None
        self._channel: Any = None
        self._exchange: Any = None
        self._degraded = False

    async def _ensure_exchange(self) -> Any:
        """懒建立连接并声明交换机。"""
        if self._exchange is None:
            import aio_pika

            self._connection = await aio_pika.connect_robust(self._amqp_url)
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
            )
        return self._exchange

    async def publish(self, event: DomainEvent) -> None:
        """把领域事件序列化为 JSON 并发布；broker 异常时降级为日志，不影响业务。"""
        try:
            import aio_pika

            exchange = await self._ensure_exchange()
            message = aio_pika.Message(
                body=json.dumps(event.model_dump(mode="json"), ensure_ascii=False).encode("utf-8"),
                content_type="application/json",
            )
            await exchange.publish(message, routing_key=event.event_type)
            if self._degraded:
                logger.info("RabbitMQ 已恢复，事件 %s 发布成功", event.event_type)
                self._degraded = False
        except Exception as exc:  # noqa: BLE001 - 事件发布失败不应使业务写操作失败
            if not self._degraded:
                logger.warning("事件 %s 发布失败，降级为日志: %s", event.event_type, exc)
                self._degraded = True

    async def close(self) -> None:
        """关闭 MQ 连接。"""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None


_publisher: EventPublisher | None = None


def get_event_publisher(settings: Settings | None = None) -> EventPublisher:
    """返回事件发布器单例。"""
    global _publisher
    if _publisher is None:
        current = settings or get_settings()
        _publisher = (
            RabbitMQEventPublisher(current.rabbitmq_url, current.event_exchange)
            if current.rabbitmq_url
            else NoopEventPublisher()
        )
    return _publisher
