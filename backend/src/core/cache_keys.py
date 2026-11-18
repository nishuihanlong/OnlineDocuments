"""缓存键约定与失效辅助。

集中管理缓存 key 前缀与失效逻辑，避免各 writes 路径散落硬编码字符串，
确保用户权限、角色菜单、组织部门等变更能即时反映到缓存。
"""

from __future__ import annotations

from src.core.cache import get_cache

# 缓存键前缀（命名空间）
AUTH_CONTEXT_PREFIX = "auth:ctx:"  # 用户权限上下文，按 user_id 分键
ROLE_LIST_KEY = "catalog:roles"  # 角色列表
PERMISSION_LIST_KEY = "catalog:permissions"  # 菜单权限列表
ORG_LIST_KEY = "catalog:orgs"  # 机构列表
DEPT_LIST_KEY = "catalog:depts"  # 部门列表
CONFIG_LIST_PREFIX = "catalog:configs:"  # 参数分页列表，按查询条件分键
API_ROUTES_KEY = "catalog:api-routes"  # API 路由清单（应用启动后不变）
PUBLIC_CONFIG_KEY = "catalog:public-config"  # 公开前端开关配置（水印等）
REDIS_MONITOR_KEY = "monitor:redis"  # Redis 只读监控指标
RABBITMQ_MONITOR_KEY = "monitor:rabbitmq"  # RabbitMQ 只读监控指标


async def invalidate_user_context(user_id: int) -> None:
    """失效指定用户的权限上下文（资料、状态、角色变更后调用）。"""
    await get_cache().delete(f"{AUTH_CONTEXT_PREFIX}{user_id}")


async def invalidate_all_auth_contexts() -> None:
    """失效全部用户权限上下文。

    角色菜单授权或菜单权限码变更会影响所有持有者，无法精确定位用户时调用。
    """
    await get_cache().delete_prefix(AUTH_CONTEXT_PREFIX)


async def invalidate_catalog(*keys: str) -> None:
    """失效目录类缓存（角色/权限/组织/部门/参数/路由）。"""
    cache = get_cache()
    for key in keys:
        if key.endswith("*"):
            await cache.delete_prefix(key.rstrip("*"))
        else:
            await cache.delete(key)
