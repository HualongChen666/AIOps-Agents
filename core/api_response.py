# -*- coding: utf-8 -*-
"""
统一 API 响应格式中间件

提供标准化的响应结构，确保所有 API 端点返回一致的格式。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class APIResponse:
    """统一 API 响应格式"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        成功响应格式

        Args:
            data: 响应数据
            message: 成功消息
            meta: 元数据（分页、时间戳等）

        Returns:
            标准响应字典
        """
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        if meta:
            response["meta"] = meta
        return response

    @staticmethod
    def error(
        code: str,
        message: str,
        details: Optional[str] = None,
        status_code: int = 500,
    ) -> dict[str, Any]:
        """
        错误响应格式

        Args:
            code: 错误代码
            message: 错误消息
            details: 详细错误信息
            status_code: HTTP 状态码

        Returns:
            标准错误响应字典
        """
        response = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        return response


async def api_response_middleware(request: Request, call_next):
    """
    API 响应中间件

    自动包装响应为统一格式，但不影响已使用 JSONResponse 的端点。
    """
    start_time = time.time()

    response = await call_next(request)

    # 只处理 JSON 响应
    if isinstance(response, JSONResponse):
        # 如果响应已经是统一格式，直接返回
        body_bytes = response.body if isinstance(response.body, bytes) else bytes(response.body)
        body = body_bytes.decode("utf-8")
        if body.startswith('{"success"'):
            return response

        # 否则包装为统一格式
        try:
            import json

            data = json.loads(body)
            wrapped = APIResponse.success(data=data)
            return JSONResponse(
                content=wrapped,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except Exception:
            # 解析失败，返回原响应
            return response

    # 计算处理时间
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response
