# -*- coding: utf-8 -*-
"""
API Performance Monitoring
API性能监控
"""

import logging
import time
from functools import wraps
from typing import Any, Dict

logger = logging.getLogger(__name__)

API_PERFORMANCE_STATS: Dict[str, Any] = {}


def monitor_api_performance(func):
    """API性能监控装饰器"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start
            func_name = func.__name__
            if func_name not in API_PERFORMANCE_STATS:
                API_PERFORMANCE_STATS[func_name] = []
            API_PERFORMANCE_STATS[func_name].append(duration)

            # 慢API告警
            if duration > 1.0:
                logger.warning(f"Slow API: {func_name} took {duration:.2f}s")

    return wrapper
