"""文档管理端到端用例：列表、增删改、版本、上传下载。"""

from __future__ import annotations

import base64

from httpx import AsyncClient


async def test_document_crud_and_restore(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """文档创建、列表、更新、软删除与恢复链路。"""
    list_response = await client.get("/v1/documents", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 2

    create_response = await client.post(
        "/v1/documents",
        headers=auth_headers,
        json={"title": "测试文档", "description": "端到端测试"},
    )
    assert create_response.status_code == 200
    document = create_response.json()["data"]
    assert document["current_version"] == 1
    assert document["created_at"].endswith("Z")
    document_id = document["id"]

    update_response = await client.put(
        f"/v1/documents/{document_id}",
        headers=auth_headers,
        json={"title": "测试文档-已更新"},
    )
    assert update_response.json()["data"]["title"] == "测试文档-已更新"

    versions_response = await client.get(
        f"/v1/documents/{document_id}/versions", headers=auth_headers
    )
    assert versions_response.json()["data"][0]["version_no"] == 1

    delete_response = await client.delete(
        f"/v1/documents/{document_id}", headers=auth_headers
    )
    assert delete_response.json()["code"] == 200
    detail_response = await client.get(
        f"/v1/documents/{document_id}", headers=auth_headers
    )
    assert detail_response.status_code == 404

    restore_response = await client.post(
        f"/v1/documents/{document_id}/restore", headers=auth_headers
    )
    assert restore_response.json()["data"]["deleted_at"] is None


async def test_upload_and_download(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """上传文件生成新版本，下载内容保持一致。"""
    create_response = await client.post(
        "/v1/documents", headers=auth_headers, json={"title": "带附件的文档"}
    )
    document_id = create_response.json()["data"]["id"]

    upload_response = await client.post(
        f"/v1/documents/{document_id}/upload",
        headers=auth_headers,
        files={"file": ("hello.txt", b"hello online documents", "text/plain")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["data"]["version_no"] == 2

    download_response = await client.get(
        f"/v1/documents/{document_id}/download", headers=auth_headers
    )
    assert download_response.status_code == 200
    payload = download_response.json()["data"]
    assert base64.b64decode(payload["content_base64"]) == b"hello online documents"


async def test_not_found_returns_unified_error(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """不存在的文档返回 404 业务码与统一结构。"""
    response = await client.get("/v1/documents/999999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["code"] == 404
