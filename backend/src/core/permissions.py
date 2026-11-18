"""权限码定义与展开：粗粒度模块权限自动蕴含其下所有细粒度按钮权限。

权限模型分两层：
- 粗码（``*:write``）代表一个模块的完整写权限，主要为了兼容旧角色授权；
- 细码（``resource:action``）对应页面上的一个具体写按钮，是后端接口实际校验的单元。

为避免给老角色重新授权，鉴权时调用 :func:`expand_permissions` 把用户持有的
粗码展开成全部细码；粗码本身保留在结果中，因此 ``document:write`` 既是权限组，
也可被 ``require_permissions`` 直接校验。
"""

from __future__ import annotations

from collections.abc import Iterable

# 粗粒度模块权限 -> 该模块下全部细粒度按钮权限。
COARSE_TO_FINE: dict[str, tuple[str, ...]] = {
    "document:write": (
        "document:create",
        "document:upload",
        "document:update",
        "document:delete",
        "document:restore",
        "document:share",
    ),
    "user:write": (
        "user:create",
        "user:update",
        "user:activate",
        "user:delete",
    ),
    "system:write": (
        "role:create",
        "role:update",
        "role:delete",
        "permission:create",
        "permission:update",
        "permission:delete",
        "config:create",
        "config:update",
        "config:delete",
        "notice:create",
        "notice:update",
        "notice:delete",
        "job:create",
        "job:update",
        "job:delete",
        "job:run",
        "org:create",
        "org:update",
        "org:delete",
        "dept:create",
        "dept:update",
        "dept:delete",
    ),
}

# 所有细粒度按钮权限码，供种子与测试校验完整性。
ALL_FINE_PERMISSIONS: frozenset[str] = frozenset(
    code for codes in COARSE_TO_FINE.values() for code in codes
)


def expand_permissions(codes: Iterable[str]) -> set[str]:
    """把粗码展开为「粗码本身 + 其蕴含的全部细码」，细码保持不变。

    Args:
        codes: 用户角色菜单上配置的权限码集合。

    Returns:
        展开后的权限码集合，可直接用于 ``require_permissions`` 校验与前端下发。
    """
    expanded = set(codes)
    for code in codes:
        expanded.update(COARSE_TO_FINE.get(code, ()))
    return expanded
