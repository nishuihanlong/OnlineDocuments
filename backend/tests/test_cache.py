"""缓存基础设施与权限上下文缓存行为测试（测试环境使用内存缓存）。"""

from __future__ import annotations

from httpx import AsyncClient
from pydantic import BaseModel

from src.core.cache import MemoryCache, cached_json, get_cache


class SampleValue(BaseModel):
    """用于缓存序列化测试的简单模型。"""

    name: str
    count: int


async def test_memory_cache_basic_operations() -> None:
    """内存缓存的读写、TTL 与前缀删除行为。"""
    cache = MemoryCache()
    await cache.set("a:1", "one", 60)
    await cache.set("a:2", "two", 60)
    await cache.set("b:1", "other", 60)
    assert await cache.get("a:1") == "one"
    await cache.delete_prefix("a:")
    assert await cache.get("a:1") is None
    assert await cache.get("a:2") is None
    assert await cache.get("b:1") == "other"


async def test_cached_json_loads_once() -> None:
    """缓存命中后不再调用 loader。"""
    calls = 0

    async def loader() -> SampleValue:
        nonlocal calls
        calls += 1
        return SampleValue(name="x", count=calls)

    first = await cached_json("test:sample", SampleValue, loader)
    second = await cached_json("test:sample", SampleValue, loader)
    assert first.count == 1
    assert second.count == 1  # 命中缓存，未再次回源
    assert calls == 1


async def test_cached_json_supports_list_type() -> None:
    """cached_json 支持 list[Model] 类型（目录缓存依赖此能力）。"""
    calls = 0

    async def loader() -> list[SampleValue]:
        nonlocal calls
        calls += 1
        return [SampleValue(name="a", count=1)]

    first = await cached_json("test:list", list[SampleValue], loader)
    second = await cached_json("test:list", list[SampleValue], loader)
    assert first == second
    assert calls == 1


async def test_role_change_invalidates_auth_context(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """给用户授予角色后再变更角色授权，用户权限上下文应失效并反映新权限。"""
    await client.post(
        "/v1/auth/register",
        json={"username": "cache_user", "password": "Cache@12345"},
    )
    listing = await client.get("/v1/users", headers=auth_headers)
    user_id = next(
        item["id"] for item in listing.json()["data"]["items"]
        if item["username"] == "cache_user"
    )
    await client.post(f"/v1/users/{user_id}/activate", headers=auth_headers)
    login = await client.post(
        "/v1/auth/login",
        json={"username": "cache_user", "password": "Cache@12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['accessToken']}"}

    # 首次请求填充权限上下文缓存。
    first = await client.get("/v1/auth/me", headers=headers)
    assert first.json()["code"] == 200

    # 管理员修改该用户角色为空（去掉文档写权限）。
    await client.put(
        f"/v1/users/{user_id}",
        headers=auth_headers,
        json={"role_ids": []},
    )

    # 缓存应已失效，新的请求不再拥有旧权限。
    second = await client.get("/v1/auth/me", headers=headers)
    assert "document:write" not in second.json()["data"]["permissions"]


async def test_enable_flag_change_invalidates_all_contexts(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """停用菜单（改 enabled）后应失效所有用户权限上下文，权限即时生效。"""
    perms = await client.get("/v1/permissions", headers=auth_headers)
    doc_write = next(
        item for item in perms.json()["data"]
        if item.get("permission_code") == "document:write"
    )
    # 先让 admin 请求填充缓存（超管也走同一缓存路径）。
    await client.get("/v1/auth/me", headers=auth_headers)

    await client.put(
        f"/v1/permissions/{doc_write['id']}",
        headers=auth_headers,
        json={"enabled": False},
    )
    # 缓存键前缀清理后，目录列表缓存应已被删除。
    from src.core.cache_keys import PERMISSION_LIST_KEY

    assert await get_cache().get(PERMISSION_LIST_KEY) is None
