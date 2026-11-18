"""FastAPI 应用入口：生命周期、中间件、异常处理与路由注册。"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.core.config import get_settings
from src.core.exceptions import install_exception_handlers
from src.core.logging import configure_logging
from src.core.mq import get_event_publisher
from src.core.response import ApiResponse
from src.db.seed import seed_initial_data
from src.db.session import dispose_engine, get_db_session, init_engine, init_models
from src.routers.v1 import api_router
from src.routers.v1.system import build_health
from src.schemas.system import HealthOut
import src.models  # noqa: F401  确保所有 ORM 模型注册到 metadata

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """启动时初始化数据库与种子数据，关闭时释放基础设施连接。"""
    settings = get_settings()
    configure_logging(settings)
    init_engine(settings)
    await init_models()
    async with get_db_session() as session:
        await seed_initial_data(session, settings)
    logger.info("%s v%s 启动完成", settings.app_name, __version__)
    try:
        yield
    finally:
        await get_event_publisher().close()
        await dispose_engine()


def create_app() -> FastAPI:
    """构建并返回 FastAPI 应用实例。"""
    settings = get_settings()
    app = FastAPI(
        title="在线文档管理系统 API",
        version=__version__,
        description="用户管理、系统管理与文档管理能力，统一 {code, message, data} 响应结构",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )
    install_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get(
        "/health",
        response_model=ApiResponse[HealthOut],
        include_in_schema=False,
        tags=["系统管理"],
    )
    async def health() -> ApiResponse[HealthOut]:
        """存活探针，不需要认证。"""
        return ApiResponse[HealthOut](data=build_health(get_settings()))

    return app


app = create_app()
