"""仪表盘统计接口（替代脚手架自带的 mock 数据）。"""

from __future__ import annotations

from fastapi import APIRouter

from src.core.deps import CurrentUserDep
from src.core.response import ApiResponse
from src.routers.deps import DashboardServiceDep
from src.schemas.dashboard import AnalysisTotalOut, MonthlySalesOut, NameValueOut

router = APIRouter(prefix="/system/dashboard", tags=["服务监控"])


@router.get("/total", response_model=ApiResponse[AnalysisTotalOut], summary="概览指标")
async def get_total(
    principal: CurrentUserDep, service: DashboardServiceDep
) -> ApiResponse[AnalysisTotalOut]:
    """按数据范围返回用户数、文档数、版本数与操作日志数。"""
    return ApiResponse[AnalysisTotalOut](data=await service.get_total(principal))


@router.get(
    "/activity", response_model=ApiResponse[list[NameValueOut]], summary="近 7 天操作活跃度"
)
async def get_daily_activity(
    principal: CurrentUserDep, service: DashboardServiceDep
) -> ApiResponse[list[NameValueOut]]:
    """按数据范围返回近 7 天每日操作日志数量。"""
    return ApiResponse[list[NameValueOut]](data=await service.get_daily_activity(principal))


@router.get(
    "/trend", response_model=ApiResponse[list[MonthlySalesOut]], summary="近 12 月文档趋势"
)
async def get_monthly_trend(
    principal: CurrentUserDep, service: DashboardServiceDep
) -> ApiResponse[list[MonthlySalesOut]]:
    """按数据范围返回近 12 个月文档新增与累计数量。"""
    return ApiResponse[list[MonthlySalesOut]](data=await service.get_monthly_trend(principal))
