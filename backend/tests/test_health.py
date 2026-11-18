"""健康检查与统一响应契约测试。"""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_unified_response(client: AsyncClient) -> None:
    """健康检查应返回 code=200 且时间字段为 ISO 8601 UTC。"""
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["message"] == "success"
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["server_time"].endswith("Z")


async def test_protected_endpoint_requires_token(client: AsyncClient) -> None:
    """未携带令牌访问受保护接口应返回 401 与统一结构。"""
    response = await client.get("/v1/auth/me")
    assert response.status_code == 401
    payload = response.json()
    assert payload["code"] == 401
    assert payload["data"] is None
