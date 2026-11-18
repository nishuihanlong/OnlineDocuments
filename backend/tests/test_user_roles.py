"""用户角色设置用例：创建用户绑定角色、更新用户替换角色。"""

from __future__ import annotations

from httpx import AsyncClient


async def _create_role(client: AsyncClient, headers: dict[str, str], code: str, name: str) -> int:
    """创建一个角色并返回其 id。"""
    response = await client.post(
        "/v1/roles",
        headers=headers,
        json={"code": code, "name": name, "menu_ids": []},
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


async def test_create_user_binds_roles(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """创建用户时传入的 role_ids 应绑定到用户并在详情中返回。"""
    role_id = await _create_role(client, auth_headers, "editor", "编辑")

    created = await client.post(
        "/v1/users",
        headers=auth_headers,
        json={
            "username": "role_user",
            "password": "Role@12345",
            "real_name": "角色用户",
            "role_ids": [role_id],
        },
    )
    assert created.status_code == 200
    roles = created.json()["data"]["roles"]
    assert [role["id"] for role in roles] == [role_id]
    assert roles[0]["code"] == "editor"


async def test_update_user_replaces_roles(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """更新用户 role_ids 应整体替换已有角色。"""
    role_a = await _create_role(client, auth_headers, "role_a", "角色A")
    role_b = await _create_role(client, auth_headers, "role_b", "角色B")

    created = await client.post(
        "/v1/users",
        headers=auth_headers,
        json={
            "username": "role_switch",
            "password": "Role@12345",
            "role_ids": [role_a],
        },
    )
    assert created.status_code == 200
    user_id = created.json()["data"]["id"]

    updated = await client.put(
        f"/v1/users/{user_id}",
        headers=auth_headers,
        json={"role_ids": [role_b]},
    )
    assert updated.status_code == 200
    roles = updated.json()["data"]["roles"]
    assert [role["id"] for role in roles] == [role_b]
