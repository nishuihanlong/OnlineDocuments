"""统一响应结构：所有接口均返回 {code, message, data}。"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")

SUCCESS_CODE = 200


class ApiResponse(BaseModel, Generic[DataT]):
    """统一响应包装体，code 使用标准 HTTP 状态码，200 表示业务成功。"""

    code: int = Field(default=SUCCESS_CODE, description="业务状态码（标准 HTTP 状态码）")
    message: str = Field(default="success", description="提示信息")
    data: DataT | None = Field(default=None, description="实际数据")


def success(data: Any = None, message: str = "success") -> dict[str, Any]:
    """构造成功响应字典，供异常处理器与中间件使用。"""
    return {"code": SUCCESS_CODE, "message": message, "data": data}


def failure(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """构造失败响应字典，code 必须为标准 HTTP 状态码。"""
    return {"code": code, "message": message, "data": data}
