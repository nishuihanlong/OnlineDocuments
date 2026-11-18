"""按钮权限落库与粗码展开校验。"""

from __future__ import annotations

from httpx import AsyncClient

from src.core.permissions import ALL_FINE_PERMISSIONS, COARSE_TO_FINE, expand_permissions
from src.schemas.menu import MenuOut


async def _menu_map(
    client: AsyncClient, auth_headers: dict[str, str]
) -> dict[str, MenuOut]:
    """读取权限列表并按 name 建索引。"""
    response = await client.get("/v1/permissions", headers=auth_headers)
    assert response.status_code == 200
    return {
        item.name: item
        for item in (MenuOut.model_validate(raw) for raw in response.json()["data"])
    }


def test_expand_permissions_coarse_codes() -> None:
    """粗码展开为自身加全部所属细码，细码不反向推导粗码。"""
    expanded = expand_permissions({"document:write"})
    assert "document:write" in expanded
    assert set(COARSE_TO_FINE["document:write"]).issubset(expanded)

    only_create = expand_permissions({"document:create"})
    assert only_create == {"document:create"}


async def test_all_fine_permissions_seeded(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """所有细粒度按钮权限都应作为隐藏菜单落库。"""
    menus = await _menu_map(client, auth_headers)
    by_code = {item.permission_code: item for item in menus.values() if item.permission_code}
    for code in ALL_FINE_PERMISSIONS:
        assert code in by_code, f"权限码未落库: {code}"
        assert by_code[code].hidden is True, code
        assert by_code[code].component == "##", code


async def test_user_role_gets_expanded_document_permissions(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """仅授予 document:write 的用户，登录后应拿到全部文档细码。"""
    await client.post(
        "/v1/auth/register",
        json={"username": "btn_perm_user", "password": "Btn@12345"},
    )
    listing = await client.get("/v1/users", headers=auth_headers)
    user_id = next(
        item["id"] for item in listing.json()["data"]["items"]
        if item["username"] == "btn_perm_user"
    )
    await client.post(f"/v1/users/{user_id}/activate", headers=auth_headers)
    login = await client.post(
        "/v1/auth/login",
        json={"username": "btn_perm_user", "password": "Btn@12345"},
    )
    permissions = login.json()["data"]["user"]["permissions"]
    assert set(COARSE_TO_FINE["document:write"]).issubset(set(permissions))
    assert "document:write" in permissions
    assert "user:create" not in permissions
