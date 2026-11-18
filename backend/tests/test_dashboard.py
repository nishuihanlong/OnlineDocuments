"""仪表盘统计接口测试。"""

from __future__ import annotations

from httpx import AsyncClient


async def test_dashboard_total(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """概览指标应返回真实的用户、文档、版本与日志数量。"""
    created = await client.post(
        "/v1/documents", headers=auth_headers, json={"title": "统计测试文档"}
    )
    assert created.status_code == 200

    response = await client.get("/v1/system/dashboard/total", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["users"] == 1
    assert data["documents"] == 3
    assert data["versions"] == 3
    assert data["operation_logs"] >= 1


async def test_dashboard_charts(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """两组图表数据返回明确结构，且长度固定。"""
    activity_response = await client.get("/v1/system/dashboard/activity", headers=auth_headers)
    assert len(activity_response.json()["data"]) == 7

    trend_response = await client.get("/v1/system/dashboard/trend", headers=auth_headers)
    assert len(trend_response.json()["data"]) == 12
