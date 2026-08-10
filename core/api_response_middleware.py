# -*- coding: utf-8 -*-
"""
API Response Middleware
API响应中间件

自动为所有API响应应用统一格式。
"""

import json
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.api_response_standard import create_error_response, create_success_response

logger = logging.getLogger(__name__)


class APIResponseMiddleware(BaseHTTPMiddleware):
    """API响应统一格式中间件"""

    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        """
        初始化中间件

        Args:
            app: ASGI应用
            exclude_paths: 排除的路径列表
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
        ]

    async def dispatch(self, request: Request, call_next):
        """
        处理请求

        Args:
            request: FastAPI请求
            call_next: 下一个中间件/路由

        Returns:
            响应
        """
        # Skip CORS preflight requests (OPTIONS method)
        if request.method == "OPTIONS":
            return await call_next(request)

        # 排除特定路径
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # 只处理API路径
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        try:
            response = await call_next(request)

            # 如果已经是JSONResponse，检查是否需要包装
            if isinstance(response, JSONResponse):
                try:
                    body_bytes = (
                        response.body if isinstance(response.body, bytes) else bytes(response.body)
                    )
                    body = json.loads(body_bytes.decode())

                    # 如果响应已经是统一格式，直接返回
                    if isinstance(body, dict) and "success" in body:
                        return response

                    # 否则包装为统一格式
                    wrapped_body = create_success_response(body)
                    return JSONResponse(content=wrapped_body, status_code=response.status_code)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # 如果不是JSON，直接返回
                    return response

            return response

        except Exception as e:
            logger.error(f"API response middleware error: {e}")
            # 返回错误响应
            error_response = create_error_response(error=str(e), error_code="MIDDLEWARE_ERROR")
            return JSONResponse(content=error_response, status_code=500)


def setup_api_response_middleware(app):
    """
    设置API响应中间件

    Args:
        app: FastAPI应用
    """
    app.add_middleware(APIResponseMiddleware)
    logger.info("API response middleware configured")
