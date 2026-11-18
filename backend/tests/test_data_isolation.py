"""数据隔离用例：普通用户仅见自身数据，管理员可见全库。"""

from __future__ import annotations

from httpx import AsyncClient

USERNAME = "normal_user"
PASSWORD = "Isolation@123"


async def test_document_and_user_data_isolation(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """普通用户默认仅本人范围，越权访问文档返回 404。"""
    admin_doc = await client.post(
        "/v1/documents", headers=auth_headers, json={"title": "管理员文档"}
    )
    assert admin_doc.status_code == 200
    admin_doc_id = admin_doc.json()["data"]["id"]

    created_user = await client.post(
        "/v1/users",
        headers=auth_headers,
        json={
            "username": USERNAME,
            "password": PASSWORD,
            "real_name": "普通用户",
            "role_ids": [1],
        },
    )
    assert created_user.status_code == 200

    login = await client.post(
        "/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}
    )
    assert login.status_code == 200
    user_headers = {"Authorization": f"Bearer {login.json()['data']['accessToken']}"}

    own_doc = await client.post(
        "/v1/documents", headers=user_headers, json={"title": "我的文档"}
    )
    assert own_doc.status_code == 200
    own_doc_id = own_doc.json()["data"]["id"]

    listing = await client.get("/v1/documents", headers=user_headers)
    assert listing.json()["data"]["total"] == 1
    assert [item["id"] for item in listing.json()["data"]["items"]] == [own_doc_id]

    forbidden_detail = await client.get(
        f"/v1/documents/{admin_doc_id}", headers=user_headers
    )
    assert forbidden_detail.status_code == 404

    admin_listing = await client.get("/v1/documents", headers=auth_headers)
    assert admin_listing.json()["data"]["total"] >= 4

    users = await client.get("/v1/users", headers=user_headers)
    assert users.json()["data"]["total"] == 1
    assert users.json()["data"]["items"][0]["username"] == USERNAME
