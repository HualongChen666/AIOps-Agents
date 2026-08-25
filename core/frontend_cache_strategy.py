# -*- coding: utf-8 -*-
"""
Frontend Cache Strategy Module
前端缓存策略模块

提供前端缓存策略配置和缓存头设置。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Response

logger = logging.getLogger(__name__)


class CacheStrategy:
    """缓存策略"""

    def __init__(
        self,
        max_age: int = 300,
        stale_while_revalidate: int = 60,
        stale_if_error: int = 86400,
        must_revalidate: bool = False,
        no_cache: bool = False,
        no_store: bool = False,
        private: bool = False,
    ):
        """
        初始化缓存策略

        Args:
            max_age: 缓存最大时间（秒）
            stale_while_revalidate: 过期后可使用时间（秒）
            stale_if_error: 错误时可使用时间（秒）
            must_revalidate: 必须重新验证
            no_cache: 不缓存
            no_store: 不存储
            private: 私有缓存
        """
        self.max_age = max_age
        self.stale_while_revalidate = stale_while_revalidate
        self.stale_if_error = stale_if_error
        self.must_revalidate = must_revalidate
        self.no_cache = no_cache
        self.no_store = no_store
        self.private = private

    def to_cache_control_header(self) -> str:
        """
        转换为Cache-Control头

        Returns:
            Cache-Control头字符串
        """
        directives = []

        if self.no_store:
            directives.append("no-store")
        elif self.no_cache:
            directives.append("no-cache")
        else:
            directives.append(f"max-age={self.max_age}")

            if self.stale_while_revalidate > 0:
                directives.append(f"stale-while-revalidate={self.stale_while_revalidate}")

            if self.stale_if_error > 0:
                directives.append(f"stale-if-error={self.stale_if_error}")

            if self.must_revalidate:
                directives.append("must-revalidate")

        if self.private:
            directives.append("private")
        else:
            directives.append("public")

        return ", ".join(directives)


class FrontendCacheStrategies:
    """前端缓存策略配置"""

    # 静态资源 - 长期缓存
    STATIC_RESOURCES = CacheStrategy(
        max_age=31536000,  # 1年
        stale_while_revalidate=86400,  # 1天
        stale_if_error=86400,
        must_revalidate=False,
    )

    # 仪表盘数据 - 中期缓存
    DASHBOARD_DATA = CacheStrategy(
        max_age=300,  # 5分钟
        stale_while_revalidate=60,  # 1分钟
        stale_if_error=300,
        must_revalidate=False,
    )

    # 告警列表 - 短期缓存
    ALERT_LIST = CacheStrategy(
        max_age=60,  # 1分钟
        stale_while_revalidate=30,  # 30秒
        stale_if_error=120,
        must_revalidate=False,
    )

    # 实时数据 - 不缓存
    REALTIME_DATA = CacheStrategy(
        max_age=0, stale_while_revalidate=0, stale_if_error=0, no_cache=True
    )

    # 用户配置 - 私有缓存
    USER_CONFIG = CacheStrategy(
        max_age=3600,  # 1小时
        stale_while_revalidate=300,  # 5分钟
        stale_if_error=3600,
        private=True,
    )

    # API元数据 - 长期缓存
    API_METADATA = CacheStrategy(
        max_age=86400, stale_while_revalidate=3600, stale_if_error=86400  # 1天  # 1小时
    )

    # 敏感数据 - 不存储
    SENSITIVE_DATA = CacheStrategy(max_age=0, no_store=True, no_cache=True, private=True)

    @classmethod
    def get_strategy_for_endpoint(cls, endpoint: str) -> CacheStrategy:
        """
        根据端点获取缓存策略

        Args:
            endpoint: API端点

        Returns:
            缓存策略
        """
        # 根据端点路径匹配缓存策略
        if "/api/v1/alerts" in endpoint:
            return cls.ALERT_LIST
        elif "/api/v1/metrics" in endpoint:
            return cls.DASHBOARD_DATA
        elif "/api/v1/realtime" in endpoint:
            return cls.REALTIME_DATA
        elif "/api/v1/config" in endpoint:
            return cls.USER_CONFIG
        elif "/api/v1/health" in endpoint:
            return cls.REALTIME_DATA
        elif "/api/v1/auth" in endpoint:
            return cls.SENSITIVE_DATA
        else:
            # 默认策略
            return cls.DASHBOARD_DATA


def apply_cache_headers(
    response: Response,
    strategy: CacheStrategy,
    etag: Optional[str] = None,
    last_modified: Optional[datetime] = None,
) -> Response:
    """
    应用缓存头到响应

    Args:
        response: FastAPI响应对象
        strategy: 缓存策略
        etag: ETag值
        last_modified: 最后修改时间

    Returns:
        带有缓存头的响应
    """
    # 设置Cache-Control头
    response.headers["Cache-Control"] = strategy.to_cache_control_header()

    # 设置ETag
    if etag:
        response.headers["ETag"] = etag

    # 设置Last-Modified
    if last_modified:
        response.headers["Last-Modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 设置Expires（向后兼容）
    if strategy.max_age > 0:
        expires = datetime.now(timezone.utc) + timedelta(seconds=strategy.max_age)
        response.headers["Expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    return response


def get_etag_for_data(data: Any) -> str:
    """
    为数据生成ETag

    Args:
        data: 要生成ETag的数据

    Returns:
        ETag字符串
    """
    import hashlib
    import json

    # 序列化数据为JSON字符串
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)

    # 生成SHA256哈希
    hash_obj = hashlib.sha256(data_str.encode())
    return hash_obj.hexdigest()


def setup_cache_headers_middleware():
    """
    设置缓存头中间件配置

    Returns:
        配置信息
    """
    try:
        logger.info("Frontend cache strategies configured")

        return {
            "status": "success",
            "strategies": {
                "STATIC_RESOURCES": "max-age=31536000",
                "DASHBOARD_DATA": "max-age=300",
                "ALERT_LIST": "max-age=60",
                "REALTIME_DATA": "no-cache",
                "USER_CONFIG": "private, max-age=3600",
                "API_METADATA": "max-age=86400",
                "SENSITIVE_DATA": "no-store, no-cache",
            },
        }

    except Exception as e:
        logger.error(f"Cache headers middleware setup failed: {e}")
        return {"status": "error", "error": str(e)}


# 缓存策略装饰器
def cache_response(strategy: CacheStrategy):
    """
    缓存响应装饰器

    Args:
        strategy: 缓存策略

    Returns:
        装饰器函数
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 调用原函数
            result = await func(*args, **kwargs)

            # 如果是FastAPI响应对象，应用缓存头
            if hasattr(result, "headers"):
                etag = get_etag_for_data(getattr(result, "body", None))
                apply_cache_headers(result, strategy, etag=etag)

            return result

        return wrapper

    return decorator
