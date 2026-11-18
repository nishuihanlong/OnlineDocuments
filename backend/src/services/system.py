"""系统管理业务逻辑：参数、公告、日志、监控与在线用户。"""

from __future__ import annotations

import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from src.core.cache import cached_json
from src.core.cache_keys import PUBLIC_CONFIG_KEY, invalidate_catalog
from src.core.config import Settings
from src.core.deps import CurrentUser
from src.core.exceptions import ConflictError, NotFoundError
from src.db.base import utc_now
from src.db.session import DatabaseSession
from src.models.log import LoginLog
from src.models.system import SysConfig, SysJob, SysNotice
from src.repositories.system import (
    ConfigRepository,
    JobRepository,
    LoginLogRepository,
    NoticeRepository,
    OperationLogRepository,
)
from src.schemas.common import PageResult, to_iso8601
from src.schemas.system import (
    ApiRouteOut,
    ConfigCreateIn,
    ConfigOut,
    ConfigUpdateIn,
    FileOut,
    JobCreateIn,
    JobOut,
    JobUpdateIn,
    LogQuery,
    LoginLogOut,
    MonitorOut,
    NoticeCreateIn,
    NoticeOut,
    NoticeUpdateIn,
    OnlineUserOut,
    OperationLogOut,
    PublicConfigOut,
)


def to_config_out(item: SysConfig) -> ConfigOut:
    """参数 ORM 转 DTO。"""
    return ConfigOut(
        id=item.id, key=item.key, value=item.value, name=item.name,
        remark=item.remark, created_at=item.created_at, updated_at=item.updated_at,
    )


def to_notice_out(item: SysNotice) -> NoticeOut:
    """公告 ORM 转 DTO。"""
    return NoticeOut(
        id=item.id, title=item.title, content=item.content, type=item.type,
        enabled=item.enabled, created_at=item.created_at, updated_at=item.updated_at,
    )


def to_job_out(item: SysJob) -> JobOut:
    """任务 ORM 转 DTO。"""
    return JobOut(
        id=item.id, name=item.name, code=item.code, interval_seconds=item.interval_seconds,
        enabled=item.enabled, last_run_at=item.last_run_at, created_at=item.created_at,
    )


class SystemService:
    """系统管理用例编排，所有统计与资源访问集中于此。"""

    def __init__(self, session: DatabaseSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.configs = ConfigRepository(session)
        self.notices = NoticeRepository(session)
        self.jobs = JobRepository(session)
        self.operation_logs = OperationLogRepository(session)
        self.login_logs = LoginLogRepository(session)

    async def get_public_config(self) -> PublicConfigOut:
        """读取可公开的前端开关配置（带缓存）。"""
        return await cached_json(
            PUBLIC_CONFIG_KEY,
            PublicConfigOut,
            self._load_public_config,
        )

    async def _load_public_config(self) -> PublicConfigOut:
        """回源读取公开配置，值为 '1'/'true'/'on' 视为开启。"""
        statement = select(SysConfig).where(SysConfig.key == "watermark.enabled")
        item = (await self.session.execute(statement)).scalar_one_or_none()
        enabled = item is None or (item.value or "").strip().lower() in {"1", "true", "on"}
        return PublicConfigOut(watermark_enabled=enabled)

    async def list_configs(
        self, keyword: str | None, page: int, page_size: int
    ) -> PageResult[ConfigOut]:
        """分页查询参数配置。"""
        rows, total = await self.configs.paginate(
            self.configs.build_query(keyword), page, page_size
        )
        return PageResult(
            items=[to_config_out(row) for row in rows],
            total=total, page=page, page_size=page_size,
        )

    async def create_config(self, payload: ConfigCreateIn) -> ConfigOut:
        """新增参数，键名重复时拒绝。"""
        statement = select(SysConfig).where(SysConfig.key == payload.key)
        if (await self.session.execute(statement)).scalar_one_or_none() is not None:
            raise ConflictError("参数键已存在")
        item = SysConfig(**payload.model_dump())
        await self.configs.add(item)
        await self.session.commit()
        await invalidate_catalog(PUBLIC_CONFIG_KEY)
        return to_config_out(item)

    async def update_config(self, config_id: int, payload: ConfigUpdateIn) -> ConfigOut:
        """更新参数值。"""
        item = await self.configs.get_by_id(config_id)
        if item is None:
            raise NotFoundError("参数不存在")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.commit()
        await invalidate_catalog(PUBLIC_CONFIG_KEY)
        return to_config_out(item)

    async def delete_config(self, config_id: int) -> None:
        """删除参数。"""
        item = await self.configs.get_by_id(config_id)
        if item is None:
            raise NotFoundError("参数不存在")
        if item.key == "watermark.enabled":
            raise ConflictError("内置水印开关不可删除")
        await self.configs.delete(item)
        await self.session.commit()
        await invalidate_catalog(PUBLIC_CONFIG_KEY)

    async def list_notices(
        self, keyword: str | None, page: int, page_size: int
    ) -> PageResult[NoticeOut]:
        """分页查询公告。"""
        rows, total = await self.notices.paginate(
            self.notices.build_query(keyword), page, page_size
        )
        return PageResult(
            items=[to_notice_out(row) for row in rows],
            total=total, page=page, page_size=page_size,
        )

    async def create_notice(self, payload: NoticeCreateIn) -> NoticeOut:
        """新增公告。"""
        item = SysNotice(**payload.model_dump())
        await self.notices.add(item)
        await self.session.commit()
        return to_notice_out(item)

    async def update_notice(self, notice_id: int, payload: NoticeUpdateIn) -> NoticeOut:
        """更新公告。"""
        item = await self.notices.get_by_id(notice_id)
        if item is None:
            raise NotFoundError("公告不存在")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.commit()
        return to_notice_out(item)

    async def delete_notice(self, notice_id: int) -> None:
        """删除公告。"""
        item = await self.notices.get_by_id(notice_id)
        if item is None:
            raise NotFoundError("公告不存在")
        await self.notices.delete(item)
        await self.session.commit()

    async def list_jobs(self) -> list[JobOut]:
        """查询全部定时任务。"""
        rows = (await self.session.execute(self.jobs.build_query())).scalars().all()
        return [to_job_out(row) for row in rows]

    async def create_job(self, payload: JobCreateIn) -> JobOut:
        """新增定时任务。"""
        item = SysJob(**payload.model_dump())
        await self.jobs.add(item)
        await self.session.commit()
        return to_job_out(item)

    async def update_job(self, job_id: int, payload: JobUpdateIn) -> JobOut:
        """更新定时任务。"""
        item = await self.jobs.get_by_id(job_id)
        if item is None:
            raise NotFoundError("任务不存在")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.commit()
        return to_job_out(item)

    async def run_job(self, job_id: int) -> JobOut:
        """手动执行一次任务，仅记录执行时间。"""
        item = await self.jobs.get_by_id(job_id)
        if item is None:
            raise NotFoundError("任务不存在")
        item.last_run_at = to_iso8601(utc_now())
        await self.session.commit()
        return to_job_out(item)

    async def delete_job(self, job_id: int) -> None:
        """删除定时任务。"""
        item = await self.jobs.get_by_id(job_id)
        if item is None:
            raise NotFoundError("任务不存在")
        await self.jobs.delete(item)
        await self.session.commit()

    async def list_operation_logs(
        self, query: LogQuery, principal: CurrentUser
    ) -> PageResult[OperationLogOut]:
        """分页查询操作日志，普通用户仅见自身记录。"""
        scoped = query
        if not principal.is_superuser:
            scoped = query.model_copy(update={"user_id": principal.id})
        rows, total = await self.operation_logs.paginate(
            self.operation_logs.build_query(scoped), query.page, query.page_size
        )
        return PageResult(
            items=[
                OperationLogOut(
                    id=row.id, user_id=row.user_id, username=row.username, module=row.module,
                    action=row.action, method=row.method, path=row.path, ip=row.ip,
                    status_code=row.status_code, detail=row.detail, created_at=row.created_at,
                )
                for row in rows
            ],
            total=total, page=query.page, page_size=query.page_size,
        )

    async def list_login_logs(
        self, query: LogQuery, principal: CurrentUser
    ) -> PageResult[LoginLogOut]:
        """分页查询登录日志，普通用户仅见自身记录。"""
        scoped = query
        if not principal.is_superuser:
            scoped = query.model_copy(update={"username": principal.username})
        rows, total = await self.login_logs.paginate(
            self.login_logs.build_query(scoped), query.page, query.page_size
        )
        return PageResult(
            items=[
                LoginLogOut(
                    id=row.id, username=row.username, ip=row.ip, user_agent=row.user_agent,
                    success=row.success, message=row.message, created_at=row.created_at,
                )
                for row in rows
            ],
            total=total, page=query.page, page_size=query.page_size,
        )

    async def list_online_users(self) -> list[OnlineUserOut]:
        """从近期成功登录日志汇总在线用户（按用户名去重）。"""
        statement = (
            select(LoginLog)
            .where(LoginLog.success == True)  # noqa: E712
            .order_by(LoginLog.created_at.desc())
            .limit(100)
        )
        rows = (await self.session.execute(statement)).scalars().all()
        result: list[OnlineUserOut] = []
        seen: set[str] = set()
        for row in rows:
            if row.username in seen:
                continue
            seen.add(row.username)
            result.append(
                OnlineUserOut(
                    id=row.id, username=row.username, real_name=row.username,
                    ip=row.ip, login_at=row.created_at,
                )
            )
        return result

    def get_monitor(self) -> MonitorOut:
        """采集服务与服务器基础指标。"""
        try:
            import psutil

            cpu_percent = float(psutil.cpu_percent())
            memory = psutil.virtual_memory()
            memory_percent = float(memory.percent)
            memory_total_mb = int(memory.total // 1024 // 1024)
        except ImportError:
            cpu_percent = 0.0
            memory_percent = 0.0
            memory_total_mb = 0
        disk = shutil.disk_usage(".")
        return MonitorOut(
            app_name=self.settings.app_name,
            env=self.settings.app_env,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_total_mb=memory_total_mb,
            disk_percent=round(disk.used / disk.total * 100, 2),
            python_version=platform.python_version(),
            database=self.settings.database_url.split("://")[0],
            storage=self.settings.storage_backend,
        )

    def list_files(self) -> list[FileOut]:
        """列出本地对象存储根目录下的文件与子目录。"""
        root = Path(self.settings.storage_local_dir).resolve()
        if not root.exists():
            return []
        result: list[FileOut] = []
        for path in sorted(root.iterdir()):
            stat = path.stat()
            result.append(
                FileOut(
                    name=path.name,
                    path=str(path.relative_to(root)).replace("\\", "/"),
                    size=stat.st_size,
                    is_dir=path.is_dir(),
                    modified_at=to_iso8601(datetime.fromtimestamp(stat.st_mtime, UTC)),
                )
            )
        return result

    def list_api_routes(self) -> list[ApiRouteOut]:
        """列出应用已注册的 API 路由。"""
        from src.main import app

        result: list[ApiRouteOut] = []
        for route in app.routes:
            methods = sorted(getattr(route, "methods", set()) - {"HEAD", "OPTIONS"})
            if not methods:
                continue
            result.append(
                ApiRouteOut(
                    path=getattr(route, "path", ""),
                    methods=methods,
                    summary=getattr(route, "summary", "") or "",
                    tags=list(getattr(route, "tags", []) or []),
                )
            )
        return sorted(result, key=lambda item: item.path)
