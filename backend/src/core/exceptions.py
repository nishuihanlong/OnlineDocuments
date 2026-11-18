"""业务异常定义与全局异常处理器，保证任何错误都返回统一响应结构。"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.response import failure

logger = logging.getLogger(__name__)


class BizError(Exception):
    """业务异常基类，code 使用标准 HTTP 状态码。"""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class BadRequestError(BizError):
    """请求参数或业务规则校验失败（400）。"""

    def __init__(self, message: str = "请求参数错误") -> None:
        super().__init__(400, message)


class UnauthorizedError(BizError):
    """未认证或凭证失效（401）。"""

    def __init__(self, message: str = "未登录或登录已过期") -> None:
        super().__init__(401, message)


class ForbiddenError(BizError):
    """已认证但无权限（403）。"""

    def __init__(self, message: str = "没有操作权限") -> None:
        super().__init__(403, message)


class NotFoundError(BizError):
    """资源不存在（404）。"""

    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(404, message)


class ConflictError(BizError):
    """资源冲突，例如唯一键重复（409）。"""

    def __init__(self, message: str = "资源已存在") -> None:
        super().__init__(409, message)


def install_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，将业务异常、校验异常、HTTP 异常与未知异常统一包装。"""

    @app.exception_handler(BizError)
    async def handle_biz_error(_request: Request, exc: BizError) -> JSONResponse:
        return JSONResponse(status_code=exc.code, content=failure(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = exc.errors()
        hint = details[0].get("msg", "请求参数不合法") if details else "请求参数不合法"
        return JSONResponse(status_code=422, content=failure(422, f"请求参数不合法: {hint}"))

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=failure(exc.status_code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理的异常: %s", exc)
        return JSONResponse(status_code=500, content=failure(500, "服务器内部错误"))
