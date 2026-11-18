"""文档分享端到端用例：创建、公开访问、公开保存、撤销。"""

from __future__ import annotations

import base64

from httpx import AsyncClient


async def _create_document(client: AsyncClient, headers: dict[str, str]) -> int:
    """创建一个测试文档并返回 ID。"""
    response = await client.post(
        "/v1/documents", headers=headers, json={"title": "待分享文档"}
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


async def _upload_content(
    client: AsyncClient, headers: dict[str, str], document_id: int
) -> None:
    """给文档写入初始内容。"""
    response = await client.post(
        f"/v1/documents/{document_id}/upload",
        headers=headers,
        files={"file": ("note.txt", b"share me", "text/plain")},
    )
    assert response.status_code == 200


async def test_public_share_read_and_revoke(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """公开只读分享：免登录可读、不可写、撤销后失效。"""
    document_id = await _create_document(client, auth_headers)
    await _upload_content(client, auth_headers, document_id)

    create_response = await client.post(
        "/v1/shares",
        headers=auth_headers,
        json={"document_id": document_id, "permission": "read"},
    )
    assert create_response.status_code == 200
    share = create_response.json()["data"]
    assert share["is_public"] is True
    assert share["share_path"].startswith("/share/")
    token = share["token"]

    public_response = await client.get(f"/v1/shares/public/{token}")
    assert public_response.status_code == 200
    payload = public_response.json()["data"]
    assert payload["permission"] == "read"
    assert base64.b64decode(payload["content_base64"]) == b"share me"

    denied = await client.post(
        f"/v1/shares/public/{token}/save",
        json={"file_name": "hack.txt", "content_base64": base64.b64encode(b"x").decode()},
    )
    assert denied.status_code == 400

    revoke_response = await client.delete(
        f"/v1/shares/{share['id']}", headers=auth_headers
    )
    assert revoke_response.status_code == 200
    gone = await client.get(f"/v1/shares/public/{token}")
    assert gone.status_code == 404


async def test_public_share_write_saves_version(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """公开可写分享：免登录保存生成新版本。"""
    document_id = await _create_document(client, auth_headers)
    await _upload_content(client, auth_headers, document_id)

    create_response = await client.post(
        "/v1/shares",
        headers=auth_headers,
        json={"document_id": document_id, "permission": "write"},
    )
    token = create_response.json()["data"]["token"]

    save_response = await client.post(
        f"/v1/shares/public/{token}/save",
        json={
            "file_name": "note.txt",
            "content_base64": base64.b64encode(b"edited via public link").decode(),
            "change_log": "链接协作编辑",
        },
    )
    assert save_response.status_code == 200
    assert save_response.json()["data"]["version_no"] == 3

    verify_response = await client.get(f"/v1/shares/public/{token}")
    assert base64.b64decode(verify_response.json()["data"]["content_base64"]) == (
        b"edited via public link"
    )


async def test_duplicate_share_for_user_is_reused(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """同一文档对同一用户重复创建分享应复用记录而不是无限新增。"""
    document_id = await _create_document(client, auth_headers)
    first = await client.post(
        "/v1/shares",
        headers=auth_headers,
        json={"document_id": document_id, "permission": "write", "granted_user_id": 1},
    )
    second = await client.post(
        "/v1/shares",
        headers=auth_headers,
        json={"document_id": document_id, "permission": "read", "granted_user_id": 1},
    )
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert second.json()["data"]["permission"] == "read"

    list_response = await client.get(
        f"/v1/shares?document_id={document_id}", headers=auth_headers
    )
    assert len(list_response.json()["data"]) == 1


async def test_invalid_token_returns_404(client: AsyncClient) -> None:
    """无效 token 统一 404，避免泄露分享状态。"""
    response = await client.get("/v1/shares/public/not-a-real-token")
    assert response.status_code == 404
