"""user 角色权限用例：可在自身数据域完整操作文档，不越权。"""

from __future__ import annotations

from httpx import AsyncClient

USERNAME = "perm_user"
PASSWORD = "Perm@12345"


async def _register_activate_login(
    client: AsyncClient, admin_headers: dict[str, str]
) -> dict[str, str]:
    """注册一个用户、由管理员激活并返回其登录请求头。"""
    await client.post(
        "/v1/auth/register", json={"username": USERNAME, "password": PASSWORD}
    )
    listing = await client.get("/v1/users", headers=admin_headers)
    user_id = next(
        item["id"] for item in listing.json()["data"]["items"]
        if item["username"] == USERNAME
    )
    await client.post(f"/v1/users/{user_id}/activate", headers=admin_headers)
    login = await client.post(
        "/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['accessToken']}"}


async def test_login_carries_user_role_and_permissions(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """登录响应应携带角色与权限码，user 角色含 document:write。"""
    headers = await _register_activate_login(client, auth_headers)
    profile = await client.get("/v1/auth/me", headers=headers)
    assert profile.status_code == 200
    data = profile.json()["data"]
    assert "user" in data["roles"]
    assert "document:write" in data["permissions"]
    assert "user:write" not in data["permissions"]
    assert "system:write" not in data["permissions"]


async def test_user_can_create_and_manage_own_document(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """user 角色可创建、编辑、删除自己的文档。"""
    headers = await _register_activate_login(client, auth_headers)

    created = await client.post("/v1/documents", headers=headers, json={"title": "我的文档"})
    assert created.status_code == 200
    doc_id = created.json()["data"]["id"]

    updated = await client.put(
        f"/v1/documents/{doc_id}", headers=headers, json={"title": "改名"}
    )
    assert updated.status_code == 200

    deleted = await client.delete(f"/v1/documents/{doc_id}", headers=headers)
    assert deleted.status_code == 200


async def test_user_cannot_access_admin_document(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """user 角色访问管理员文档应返回 404（数据隔离）。"""
    admin_doc = await client.post(
        "/v1/documents", headers=auth_headers, json={"title": "管理员文档"}
    )
    admin_doc_id = admin_doc.json()["data"]["id"]

    headers = await _register_activate_login(client, auth_headers)
    detail = await client.get(f"/v1/documents/{admin_doc_id}", headers=headers)
    assert detail.status_code == 404

    update = await client.put(
        f"/v1/documents/{admin_doc_id}", headers=headers, json={"title": "越权"}
    )
    assert update.status_code == 404
