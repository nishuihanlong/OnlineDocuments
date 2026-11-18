"""基础设施只读监控测试：Redis/RabbitMQ 接口与降级行为。"""

from __future__ import annotations

from httpx import AsyncClient

from src.core.config import Settings
from src.services.monitor import MonitorService


async def test_redis_monitor_endpoint(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Redis 监控接口返回只读指标结构。"""
    res = await client.get("/v1/system/monitor/redis", headers=auth_headers)
    assert res.json()["code"] == 200
    data = res.json()["data"]
    assert "configured" in data and "reachable" in data
    assert "total_keys" in data and "hit_rate" in data


async def test_rabbitmq_monitor_endpoint(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """RabbitMQ 监控接口返回只读指标结构。"""
    res = await client.get("/v1/system/monitor/rabbitmq", headers=auth_headers)
    assert res.json()["code"] == 200
    data = res.json()["data"]
    assert "configured" in data and "reachable" in data
    assert isinstance(data.get("queues"), list)


async def test_redis_monitor_unconfigured_falls_back() -> None:
    """未配置 Redis 时返回 configured=false，不抛错。"""
    service = MonitorService(Settings(redis_url="", rabbitmq_url=""))
    result = await service._load_redis()
    assert result.configured is False
    assert result.reachable is False


async def test_rabbitmq_monitor_unconfigured_falls_back() -> None:
    """未配置 RabbitMQ 时返回 configured=false，不抛错。"""
    service = MonitorService(Settings(redis_url="", rabbitmq_url=""))
    result = await service._load_rabbitmq()
    assert result.configured is False
    assert result.reachable is False


def test_management_target_from_amqp_url() -> None:
    """从 amqp URL 正确推导 management API 地址与凭据。"""
    target = MonitorService._management_target("amqp://user:pass@localhost:5672/vhost")
    assert target is not None
    base_url, (user, password) = target
    assert base_url == "http://localhost:15672"
    assert (user, password) == ("user", "pass")
