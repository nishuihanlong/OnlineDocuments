"""验证同步驱动门面（与达梦 8 dmPython 同构的路径）行为正确。

直接使用同步 DBAPI（SQLite 同步引擎）构建 SyncDatabaseSession，
走与达梦 8 完全一致的代码路径，确保线程池适配层可用且业务代码无需改动。
"""

from __future__ import annotations

from io import BytesIO

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.config import get_settings
from src.core.deps import CurrentUser
from src.db.base import Base
from src.db.seed import seed_initial_data
from src.db.session import SyncDatabaseSession
from src.schemas.auth import LoginIn, RequestMeta
from src.schemas.document import DocumentCreateIn, DocumentQuery
from src.schemas.user import UserQuery
from src.services.auth import AuthService
from src.services.dashboard import DashboardService
from src.services.document import DocumentService
from src.services.menu import MenuService
from src.core.mq import get_event_publisher
from src.services.storage import get_object_storage
from src.services.user import UserService


def _make_sync_session() -> SyncDatabaseSession:
    """使用内存 SQLite 同步引擎，模拟达梦 8 的同步驱动场景。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    return SyncDatabaseSession(maker())


async def test_sync_facade_runs_full_flow() -> None:
    """登录、动态菜单、仪表盘、文档 CRUD、上传、下载、恢复全链路在同步门面下可用。"""
    db = _make_sync_session()
    settings = get_settings()
    try:
        await seed_initial_data(db, settings)

        meta = RequestMeta(
            ip="127.0.0.1", user_agent="test", method="POST", path="/v1/auth/login"
        )
        auth = AuthService(db, settings)
        login = await auth.login(
            LoginIn(username="admin", password=settings.initial_admin_password), meta
        )
        assert login.accessToken

        principal = CurrentUser(
            id=1, username="admin", is_superuser=True, roles=[], permissions=["*"], menu_ids=[]
        )
        routes = await MenuService(db, principal).build_routes()
        assert any(route.name == "Document" for route in routes)

        total = await DashboardService(db).get_total()
        assert total.users == 1

        docs = DocumentService(db, get_object_storage(), get_event_publisher())
        created = await docs.create_document(
            DocumentCreateIn(title="同步驱动文档"),
            principal,
            meta,
        )
        assert created.id

        listing = await docs.list_documents(DocumentQuery(page=1, page_size=10), principal)
        assert listing.total >= 1

        upload = UploadFile(filename="hello.txt", file=BytesIO(b"hello dameng"))
        uploaded = await docs.upload_file(created.id, upload, principal, meta)
        assert uploaded.version_no == 2

        downloaded = await docs.download_file(created.id, principal)
        assert downloaded.content_base64

        restored = await docs.restore_document(created.id, principal, meta)
        assert restored is not None

        users = await UserService(db).list_users(UserQuery(page=1, page_size=10), principal)
        assert users.total >= 1
    finally:
        db.close()
