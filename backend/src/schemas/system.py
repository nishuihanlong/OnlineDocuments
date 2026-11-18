"""系统管理 DTO：参数、公告、日志、监控与在线用户。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.common import Iso8601DateTime, PageQuery


class RedisMonitorOut(BaseModel):
    """Redis 只读监控指标。"""

    configured: bool = False
    reachable: bool = False
    version: str | None = None
    uptime_seconds: int = 0
    used_memory_mb: float = 0
    connected_clients: int = 0
    total_keys: int = 0
    hit_rate: float = 0
    error: str | None = None


class QueueInfo(BaseModel):
    """RabbitMQ 队列摘要。"""

    name: str
    vhost: str = ""
    messages: int = 0
    messages_ready: int = 0
    messages_unacknowledged: int = 0
    consumers: int = 0


class RabbitMQMonitorOut(BaseModel):
    """RabbitMQ 只读监控指标。"""

    configured: bool = False
    reachable: bool = False
    version: str | None = None
    exchange_count: int = 0
    queue_count: int = 0
    total_messages: int = 0
    queues: list[QueueInfo] = Field(default_factory=list)
    error: str | None = None


class PublicConfigOut(BaseModel):
    """可公开给前端的少量配置项（不含敏感信息）。

    水印组件在登录页也会渲染，需免登录读取这些开关，因此单独定义白名单 DTO。
    """

    watermark_enabled: bool = True


class ConfigOut(BaseModel):
    """参数输出。"""

    id: int
    key: str
    value: str | None = None
    name: str
    remark: str | None = None
    created_at: Iso8601DateTime
    updated_at: Iso8601DateTime


class ConfigCreateIn(BaseModel):
    """新增参数请求。"""

    key: str = Field(min_length=1, max_length=128)
    value: str | None = None
    name: str = Field(default="", max_length=128)
    remark: str | None = Field(default=None, max_length=256)


class ConfigUpdateIn(BaseModel):
    """更新参数请求。"""

    value: str | None = None
    name: str | None = Field(default=None, max_length=128)
    remark: str | None = Field(default=None, max_length=256)


class NoticeOut(BaseModel):
    """公告输出。"""

    id: int
    title: str
    content: str | None = None
    type: str
    enabled: bool
    created_at: Iso8601DateTime
    updated_at: Iso8601DateTime


class NoticeCreateIn(BaseModel):
    """新增公告请求。"""

    title: str = Field(min_length=1, max_length=256)
    content: str | None = None
    type: Literal["notice", "announcement"] = "notice"
    enabled: bool = True


class NoticeUpdateIn(BaseModel):
    """更新公告请求。"""

    title: str | None = Field(default=None, min_length=1, max_length=256)
    content: str | None = None
    type: Literal["notice", "announcement"] | None = None
    enabled: bool | None = None


class JobOut(BaseModel):
    """定时任务输出。"""

    id: int
    name: str
    code: str
    interval_seconds: int
    enabled: bool
    last_run_at: str | None = None
    created_at: Iso8601DateTime


class JobCreateIn(BaseModel):
    """新增定时任务请求。"""

    name: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=128)
    interval_seconds: int = Field(default=60, ge=10)
    enabled: bool = False


class JobUpdateIn(BaseModel):
    """更新定时任务请求。"""

    name: str | None = Field(default=None, max_length=128)
    interval_seconds: int | None = Field(default=None, ge=10)
    enabled: bool | None = None


class LogQuery(PageQuery):
    """日志查询条件。"""

    keyword: str | None = None
    username: str | None = None
    user_id: int | None = None


class OperationLogOut(BaseModel):
    """操作日志输出。"""

    id: int
    user_id: int | None = None
    username: str
    module: str
    action: str
    method: str
    path: str
    ip: str
    status_code: int
    detail: str | None = None
    created_at: Iso8601DateTime


class LoginLogOut(BaseModel):
    """登录日志输出。"""

    id: int
    username: str
    ip: str
    user_agent: str
    success: bool
    message: str
    created_at: Iso8601DateTime


class OnlineUserOut(BaseModel):
    """在线用户输出。"""

    id: int
    username: str
    real_name: str
    ip: str
    login_at: Iso8601DateTime | None = None


class MonitorOut(BaseModel):
    """服务与服务器监控指标。"""

    app_name: str
    env: str
    cpu_percent: float
    memory_percent: float
    memory_total_mb: int
    disk_percent: float
    python_version: str
    database: str
    storage: str


class FileOut(BaseModel):
    """文件管理条目。"""

    name: str
    path: str
    size: int
    is_dir: bool
    modified_at: Iso8601DateTime


class ApiRouteOut(BaseModel):
    """系统接口清单条目。"""

    path: str
    methods: list[str]
    summary: str
    tags: list[str]


class HealthOut(BaseModel):
    """健康检查输出。"""

    status: str
    app_name: str
    environment: str
    database: str
    cache: str
    storage: str
    server_time: Iso8601DateTime


class MenuMetaOut(BaseModel):
    """动态菜单元信息。"""

    title: str
    icon: str = ""
    hidden: bool = False


class MenuRouteOut(BaseModel):
    """前端动态路由节点。"""

    path: str
    name: str
    component: str
    redirect: str | None = None
    meta: MenuMetaOut
    children: list["MenuRouteOut"] | None = None
