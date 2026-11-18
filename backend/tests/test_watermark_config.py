"""水印开关配置测试：内置参数、公开接口与写保护。"""

from __future__ import annotations

from httpx import AsyncClient


async def test_builtin_watermark_config_seeded(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """内置水印参数应随种子落库。"""
    res = await client.get(
        "/v1/system/configs", headers=auth_headers, params={"keyword": "watermark.enabled"}
    )
    assert res.json()["code"] == 200
    items = res.json()["data"]["items"]
    assert any(item["key"] == "watermark.enabled" for item in items)


async def test_public_config_no_auth_default_enabled(client: AsyncClient) -> None:
    """公开配置接口免登录可读，水印默认开启。"""
    res = await client.get("/v1/system/public-configs")
    assert res.json()["code"] == 200
    assert res.json()["data"]["watermark_enabled"] is True


async def test_toggle_watermark_reflects_in_public_config(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """更新参数为 0 后公开接口应立即反映关闭状态（缓存失效生效）。"""
    listing = await client.get(
        "/v1/system/configs", headers=auth_headers, params={"keyword": "watermark.enabled"}
    )
    item = next(
        row for row in listing.json()["data"]["items"]
        if row["key"] == "watermark.enabled"
    )
    res = await client.put(
        f"/v1/system/configs/{item['id']}", headers=auth_headers, json={"value": "0"}
    )
    assert res.json()["code"] == 200

    public = await client.get("/v1/system/public-configs")
    assert public.json()["data"]["watermark_enabled"] is False


async def test_builtin_watermark_config_cannot_delete(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """内置水印参数禁止删除。"""
    listing = await client.get(
        "/v1/system/configs", headers=auth_headers, params={"keyword": "watermark.enabled"}
    )
    item = next(
        row for row in listing.json()["data"]["items"]
        if row["key"] == "watermark.enabled"
    )
    res = await client.delete(f"/v1/system/configs/{item['id']}", headers=auth_headers)
    assert res.json()["code"] == 409
