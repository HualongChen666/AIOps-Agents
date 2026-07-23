# -*- coding: utf-8 -*-
"""
API Deprecation Middleware
API弃用警告中间件
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Request

logger = logging.getLogger(__name__)

DEPRECATED_ENDPOINTS: Dict[str, Dict[str, Any]] = {}


def mark_deprecated(endpoint: str, sunset_date: datetime, replacement: str = None):
    """标记端点为弃用"""
    DEPRECATED_ENDPOINTS[endpoint] = {"sunset_date": sunset_date, "replacement": replacement}


async def deprecation_middleware(request: Request, call_next):
    """弃用中间件"""
    response = await call_next(request)

    endpoint = request.url.path
    if endpoint in DEPRECATED_ENDPOINTS:
        info = DEPRECATED_ENDPOINTS[endpoint]
        days_left = (info["sunset_date"] - datetime.now(timezone.utc)).days
        response.headers["X-API-Deprecated"] = "true"
        response.headers["X-API-Sunset-Date"] = info["sunset_date"].isoformat()
        response.headers["X-API-Days-Until-Sunset"] = str(days_left)
        if info["replacement"]:
            response.headers["X-API-Replacement"] = info["replacement"]
        logger.warning(f"Deprecated endpoint accessed: {endpoint}")

    return response
