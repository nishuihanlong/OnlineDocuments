"""用户注册与管理员激活用例。"""

from __future__ import annotations

from httpx import AsyncClient

REGISTER_USER = "newcomer"
REGISTER_PASSWORD = "Register@123"


async def test_register_creates_pending_user_with_user_role(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """注册创建待激活用户，绑定内置 user 角色，且不能登录。"""
    response = await client.post(
        "/v1/auth/register",
        json={"username": REGISTER_USER, "password": REGISTER_PASSWORD, "real_name": "新用户"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["username"] == REGISTER_USER

    # 待激活用户不能登录。
    login = await client.post(
        "/v1/auth/login",
        json={"username": REGISTER_USER, "password": REGISTER_PASSWORD},
    )
    assert login.status_code == 401

    # 管理员能看到该用户，状态为待激活(2)，角色为 user。
    listing = await client.get("/v1/users", headers=auth_headers)
    assert listing.status_code == 200
    registered = next(
        item for item in listing.json()["data"]["items"] if item["username"] == REGISTER_USER
    )
    assert registered["status"] == 2
    assert [role["code"] for role in registered["roles"]] == ["user"]


async def test_activate_user_allows_login(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """管理员激活后，用户状态恢复为 1 且可登录。"""
    await client.post(
        "/v1/auth/register",
        json={"username": REGISTER_USER, "password": REGISTER_PASSWORD},
    )
    listing = await client.get("/v1/users", headers=auth_headers)
    user_id = next(
        item["id"] for item in listing.json()["data"]["items"]
        if item["username"] == REGISTER_USER
    )

    activated = await client.post(f"/v1/users/{user_id}/activate", headers=auth_headers)
    assert activated.status_code == 200
    assert activated.json()["data"]["status"] == 1

    login = await client.post(
        "/v1/auth/login",
        json={"username": REGISTER_USER, "password": REGISTER_PASSWORD},
    )
    assert login.status_code == 200


async def test_register_rejects_duplicate_username(client: AsyncClient) -> None:
    """重复用户名注册应被拒绝。"""
    payload = {"username": "dup_user", "password": REGISTER_PASSWORD}
    assert (await client.post("/v1/auth/register", json=payload)).status_code == 200
    assert (await client.post("/v1/auth/register", json=payload)).status_code == 400


async def test_builtin_user_role_cannot_be_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """内置 user 角色不可删除。"""
    roles = await client.get("/v1/roles", headers=auth_headers)
    user_role = next(role for role in roles.json()["data"] if role["code"] == "user")
    response = await client.delete(f"/v1/roles/{user_role['id']}", headers=auth_headers)
    assert response.status_code == 400
