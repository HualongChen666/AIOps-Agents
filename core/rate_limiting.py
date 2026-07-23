# -*- coding: utf-8 -*-
"""
Rate Limiting Strategies
限流策略配置
"""

ENDPOINT_LIMITS = {
    "/api/v1/alerts": {"requests": 100, "window": 60},
    "/api/v1/ai/analyze": {"requests": 10, "window": 60},
    "/api/v1/metrics": {"requests": 1000, "window": 60},
    "/api/v1/health": {"requests": 1000, "window": 60},
}

USER_LIMITS = {
    "default": {"requests": 100, "window": 60},
    "admin": {"requests": 1000, "window": 60},
}
