"""系统管理接口：参数、公告、日志、监控、在线用户与接口清单。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.cache import cached_json
from src.core.cache_keys import API_ROUTES_KEY
from src.core.deps import CurrentUser, CurrentUserDep, require_permissions
from src.core.response import ApiResponse
from src.routers.deps import MonitorServiceDep, SystemServiceDep
from src.schemas.common import PageResult
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
    RabbitMQMonitorOut,
    RedisMonitorOut,
    NoticeOut,
    NoticeUpdateIn,
    OnlineUserOut,
    OperationLogOut,
)

router = APIRouter(prefix="/system", tags=["系统管理"])

ConfigCreateDep = Annotated[CurrentUser, Depends(require_permissions("config:create"))]
ConfigUpdateDep = Annotated[CurrentUser, Depends(require_permissions("config:update"))]
ConfigDeleteDep = Annotated[CurrentUser, Depends(require_permissions("config:delete"))]
NoticeCreateDep = Annotated[CurrentUser, Depends(require_permissions("notice:create"))]
NoticeUpdateDep = Annotated[CurrentUser, Depends(require_permissions("notice:update"))]
NoticeDeleteDep = Annotated[CurrentUser, Depends(require_permissions("notice:delete"))]
JobCreateDep = Annotated[CurrentUser, Depends(require_permissions("job:create"))]
JobUpdateDep = Annotated[CurrentUser, Depends(require_permissions("job:update"))]
JobRunDep = Annotated[CurrentUser, Depends(require_permissions("job:run"))]
JobDeleteDep = Annotated[CurrentUser, Depends(require_permissions("job:delete"))]


@router.get("/configs", response_model=ApiResponse[PageResult[ConfigOut]], summary="参数列表")
async def list_configs(
    service: SystemServiceDep,
    _principal: CurrentUserDep,
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ApiResponse[PageResult[ConfigOut]]:
    """分页查询系统参数。"""
    return ApiResponse[PageResult[ConfigOut]](
        data=await service.list_configs(keyword, page, page_size)
    )


@router.post("/configs", response_model=ApiResponse[ConfigOut], summary="新增参数")
async def create_config(
    payload: ConfigCreateIn, _principal: ConfigCreateDep, service: SystemServiceDep
) -> ApiResponse[ConfigOut]:
    """新增系统参数。"""
    return ApiResponse[ConfigOut](data=await service.create_config(payload))


@router.put("/configs/{config_id}", response_model=ApiResponse[ConfigOut], summary="更新参数")
async def update_config(
    config_id: int, payload: ConfigUpdateIn,
    _principal: ConfigUpdateDep, service: SystemServiceDep,
) -> ApiResponse[ConfigOut]:
    """更新系统参数。"""
    return ApiResponse[ConfigOut](data=await service.update_config(config_id, payload))


@router.delete("/configs/{config_id}", response_model=ApiResponse[None], summary="删除参数")
async def delete_config(
    config_id: int, _principal: ConfigDeleteDep, service: SystemServiceDep
) -> ApiResponse[None]:
    """删除系统参数。"""
    await service.delete_config(config_id)
    return ApiResponse[None](message="success")


@router.get("/notices", response_model=ApiResponse[PageResult[NoticeOut]], summary="公告列表")
async def list_notices(
    service: SystemServiceDep,
    _principal: CurrentUserDep,
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ApiResponse[PageResult[NoticeOut]]:
    """分页查询通知公告。"""
    return ApiResponse[PageResult[NoticeOut]](
        data=await service.list_notices(keyword, page, page_size)
    )


@router.post("/notices", response_model=ApiResponse[NoticeOut], summary="新增公告")
async def create_notice(
    payload: NoticeCreateIn, _principal: NoticeCreateDep, service: SystemServiceDep
) -> ApiResponse[NoticeOut]:
    """新增通知公告。"""
    return ApiResponse[NoticeOut](data=await service.create_notice(payload))


@router.put("/notices/{notice_id}", response_model=ApiResponse[NoticeOut], summary="更新公告")
async def update_notice(
    notice_id: int, payload: NoticeUpdateIn,
    _principal: NoticeUpdateDep, service: SystemServiceDep,
) -> ApiResponse[NoticeOut]:
    """更新通知公告。"""
    return ApiResponse[NoticeOut](data=await service.update_notice(notice_id, payload))


@router.delete("/notices/{notice_id}", response_model=ApiResponse[None], summary="删除公告")
async def delete_notice(
    notice_id: int, _principal: NoticeDeleteDep, service: SystemServiceDep
) -> ApiResponse[None]:
    """删除通知公告。"""
    await service.delete_notice(notice_id)
    return ApiResponse[None](message="success")


@router.get("/jobs", response_model=ApiResponse[list[JobOut]], summary="定时任务列表")
async def list_jobs(
    _principal: CurrentUserDep, service: SystemServiceDep
) -> ApiResponse[list[JobOut]]:
    """查询全部定时任务。"""
    return ApiResponse[list[JobOut]](data=await service.list_jobs())


@router.post("/jobs", response_model=ApiResponse[JobOut], summary="新增定时任务")
async def create_job(
    payload: JobCreateIn, _principal: JobCreateDep, service: SystemServiceDep
) -> ApiResponse[JobOut]:
    """新增定时任务。"""
    return ApiResponse[JobOut](data=await service.create_job(payload))


@router.put("/jobs/{job_id}", response_model=ApiResponse[JobOut], summary="更新定时任务")
async def update_job(
    job_id: int, payload: JobUpdateIn,
    _principal: JobUpdateDep, service: SystemServiceDep,
) -> ApiResponse[JobOut]:
    """更新定时任务。"""
    return ApiResponse[JobOut](data=await service.update_job(job_id, payload))


@router.post("/jobs/{job_id}/run", response_model=ApiResponse[JobOut], summary="执行定时任务")
async def run_job(
    job_id: int, _principal: JobRunDep, service: SystemServiceDep
) -> ApiResponse[JobOut]:
    """手动执行定时任务。"""
    return ApiResponse[JobOut](data=await service.run_job(job_id))


@router.delete("/jobs/{job_id}", response_model=ApiResponse[None], summary="删除定时任务")
async def delete_job(
    job_id: int, _principal: JobDeleteDep, service: SystemServiceDep
) -> ApiResponse[None]:
    """删除定时任务。"""
    await service.delete_job(job_id)
    return ApiResponse[None](message="success")


@router.get("/logs/operation", response_model=ApiResponse[PageResult[OperationLogOut]], summary="操作日志")
async def list_operation_logs(
    service: SystemServiceDep,
    principal: CurrentUserDep,
    keyword: str | None = Query(None),
    username: str | None = Query(None),
    user_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ApiResponse[PageResult[OperationLogOut]]:
    """按数据范围分页查询操作日志。"""
    query = LogQuery(
        keyword=keyword, username=username, user_id=user_id,
        page=page, page_size=page_size,
    )
    return ApiResponse[PageResult[OperationLogOut]](
        data=await service.list_operation_logs(query, principal)
    )


@router.get("/logs/login", response_model=ApiResponse[PageResult[LoginLogOut]], summary="登录日志")
async def list_login_logs(
    service: SystemServiceDep,
    principal: CurrentUserDep,
    keyword: str | None = Query(None),
    username: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ApiResponse[PageResult[LoginLogOut]]:
    """按数据范围分页查询登录日志。"""
    query = LogQuery(keyword=keyword, username=username, page=page, page_size=page_size)
    return ApiResponse[PageResult[LoginLogOut]](
        data=await service.list_login_logs(query, principal)
    )


@router.get("/online-users", response_model=ApiResponse[list[OnlineUserOut]], summary="在线用户")
async def list_online_users(
    _principal: CurrentUserDep, service: SystemServiceDep
) -> ApiResponse[list[OnlineUserOut]]:
    """查询近期在线用户。"""
    return ApiResponse[list[OnlineUserOut]](data=await service.list_online_users())


@router.get("/monitor", response_model=ApiResponse[MonitorOut], summary="服务与服务器监控")
async def get_monitor(
    _principal: CurrentUserDep, service: SystemServiceDep
) -> ApiResponse[MonitorOut]:
    """查询服务与服务器基础指标。"""
    return ApiResponse[MonitorOut](data=service.get_monitor())


@router.get("/files", response_model=ApiResponse[list[FileOut]], summary="文件管理")
async def list_files(
    _principal: CurrentUserDep, service: SystemServiceDep
) -> ApiResponse[list[FileOut]]:
    """列出对象存储中的文件。"""
    return ApiResponse[list[FileOut]](data=service.list_files())


@router.get("/api-routes", response_model=ApiResponse[list[ApiRouteOut]], summary="系统接口清单")
async def list_api_routes(
    _principal: CurrentUserDep, service: SystemServiceDep
) -> ApiResponse[list[ApiRouteOut]]:
    """列出已注册的 API 路由（路由表启动后不变，长时缓存）。"""
    async def load():
        return service.list_api_routes()

    data = await cached_json(API_ROUTES_KEY, list[ApiRouteOut], load, 3600)
    return ApiResponse[list[ApiRouteOut]](data=data)


@router.get("/monitor/redis", response_model=ApiResponse[RedisMonitorOut], summary="Redis 监控")
async def monitor_redis(
    _principal: CurrentUserDep, service: MonitorServiceDep
) -> ApiResponse[RedisMonitorOut]:
    """查询 Redis 只读监控指标。"""
    return ApiResponse[RedisMonitorOut](data=await service.get_redis())


@router.get("/monitor/rabbitmq", response_model=ApiResponse[RabbitMQMonitorOut], summary="RabbitMQ 监控")
async def monitor_rabbitmq(
    _principal: CurrentUserDep, service: MonitorServiceDep
) -> ApiResponse[RabbitMQMonitorOut]:
    """查询 RabbitMQ 只读监控指标。"""
    return ApiResponse[RabbitMQMonitorOut](data=await service.get_rabbitmq())
