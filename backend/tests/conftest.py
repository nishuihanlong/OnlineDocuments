"""测试环境：内存 SQLite、随机密钥与随机管理员口令。"""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncGenerator

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["INITIAL_ADMIN_PASSWORD"] = secrets.token_urlsafe(16)
os.environ["STORAGE_LOCAL_DIR"] = "./.test-storage"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["REDIS_URL"] = ""
os.environ["RABBITMQ_URL"] = ""

import pytest
from httpx import ASGITransport, AsyncClient

import src.services.storage as storage_module
from src.core.cache import reset_cache
from src.core.config import get_settings
from src.db.seed import seed_initial_data
from src.db.session import dispose_engine, get_db_session, init_engine, init_models
from src.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """每个用例重建内存数据库与种子数据，返回异步 HTTP 客户端。"""
    settings = get_settings()
    init_engine(settings)
    await init_models()
    async with get_db_session() as session:
        await seed_initial_data(session, settings)
    reset_cache(settings)
    storage_module._storage = None
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http_client:
        yield http_client
    await dispose_engine()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """使用种子管理员登录，返回带 Bearer 令牌的请求头。"""
    response = await client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": get_settings().initial_admin_password},
    )
    assert response.status_code == 200
    token = response.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}
