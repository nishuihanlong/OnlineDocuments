"""应用生命周期测试：验证真实启动路径会建表、写入种子数据并可用口令登录。"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from src.core.config import get_settings
from src.main import app


async def test_lifespan_boots_application() -> None:
    """通过 lifespan 上下文启动应用，健康检查与登录均应成功。"""
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            health = await client.get("/health")
            assert health.json()["code"] == 200

            login = await client.post(
                "/v1/auth/login",
                json={
                    "username": "admin",
                    "password": get_settings().initial_admin_password,
                },
            )
            assert login.status_code == 200
            assert login.json()["data"]["accessToken"]
