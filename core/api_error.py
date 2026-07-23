# -*- coding: utf-8 -*-
"""
统一 API 错误处理中间件

提供标准化的错误处理，确保所有错误返回一致的格式。
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.api_response import APIResponse

logger = logging.getLogger(__name__)


class APIErrorCode:
    """API 错误代码常量"""

    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"

    # 业务错误
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    OPERATION_FAILED = "OPERATION_FAILED"
    STATE_INVALID = "STATE_INVALID"


async def api_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP 异常处理器
    """
    error_code = APIErrorCode.INTERNAL_ERROR
    if exc.status_code == 400:
        error_code = APIErrorCode.VALIDATION_ERROR
    elif exc.status_code == 401:
        error_code = APIErrorCode.UNAUTHORIZED
    elif exc.status_code == 403:
        error_code = APIErrorCode.FORBIDDEN
    elif exc.status_code == 404:
        error_code = APIErrorCode.NOT_FOUND
    elif exc.status_code == 409:
        error_code = APIErrorCode.CONFLICT

    error_response = APIResponse.error(
        code=error_code,
        message=str(exc.detail),
        status_code=exc.status_code,
    )

    logger.warning(
        f"HTTP {exc.status_code} | {request.method} {request.url.path} | "
        f"error_code={error_code} | message={exc.detail}"
    )

    return JSONResponse(
        content=error_response,
        status_code=exc.status_code,
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    请求验证异常处理器
    """
    errors = [
        {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    error_response = APIResponse.error(
        code=APIErrorCode.VALIDATION_ERROR,
        message="请求参数验证失败",
        details=str(errors),
        status_code=422,
    )

    logger.warning(f"Validation Error | {request.method} {request.url.path} | errors={errors}")

    return JSONResponse(
        content=error_response,
        status_code=422,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    通用异常处理器
    """
    error_response = APIResponse.error(
        code=APIErrorCode.INTERNAL_ERROR,
        message="服务器内部错误",
        details=str(exc) if logger.level <= logging.DEBUG else None,
        status_code=500,
    )

    logger.error(
        f"Unhandled Exception | {request.method} {request.url.path} | "
        f"error={type(exc).__name__} | message={exc}",
        exc_info=True,
    )

    return JSONResponse(
        content=error_response,
        status_code=500,
    )
