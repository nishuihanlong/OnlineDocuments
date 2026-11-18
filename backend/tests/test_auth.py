"""认证与动态菜单测试。"""

from __future__ import annotations

from httpx import AsyncClient

from src.core.config import get_settings


async def test_login_with_wrong_password(client: AsyncClient) -> None:
    """口令错误返回 401 业务码。"""
    response = await client.post(
        "/v1/auth/login", json={"username": "admin", "password": "invalid-password"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == 401


async def test_login_and_profile(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """登录后可查询当前用户资料与权限。"""
    response = await client.get("/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "admin"
    assert data["is_superuser"] is True
    assert get_settings().initial_admin_password not in str(data)


async def test_dynamic_menus(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """动态菜单应包含文档管理路由且不下发 hidden 权限菜单。"""
    response = await client.get("/v1/system/menus", headers=auth_headers)
    assert response.status_code == 200
    routes = response.json()["data"]
    assert any(route["name"] == "Document" for route in routes)
    document_route = next(route for route in routes if route["name"] == "Document")
    assert document_route["component"] == "#"
    assert document_route["children"][0]["component"] == "views/Document/DocumentList"
    assert all(
        route["name"] != "DocumentWritePermission"
        for route in routes
    )
