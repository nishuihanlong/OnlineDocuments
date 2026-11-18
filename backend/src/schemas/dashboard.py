"""仪表盘统计 DTO，字段与前端图表数据结构对齐。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisTotalOut(BaseModel):
    """概览四项指标。"""

    users: int = Field(description="用户数")
    documents: int = Field(description="有效文档数（不含回收站）")
    versions: int = Field(description="文档版本数")
    operation_logs: int = Field(description="操作日志数")


class NameValueOut(BaseModel):
    """单系列图表数据点。"""

    name: str
    value: int


class MonthlySalesOut(BaseModel):
    """双系列折线图数据点：累计值与实际新增值。"""

    name: str
    estimate: int = Field(description="截至当月的累计文档数")
    actual: int = Field(description="当月新增文档数")
