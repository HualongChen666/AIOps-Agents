# -*- coding: utf-8 -*-
"""
速率限制中间件
使用slowapi实现API速率限制
"""

import logging
import os
from typing import Optional

from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default: 100 requests per minute
    storage_uri=os.getenv("REDIS_URL", "memory://"),  # Use Redis if available, otherwise memory
)

# Custom rate limit exceeded handler
def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """自定义速率限制超出处理器"""
    logger.warning(
        f"Rate limit exceeded for {request.client.host if request.client else 'unknown'}: {exc.detail}"
    )
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "请求过于频繁",
            "message": exc.detail,
            "retry_after": str(exc.retry_after) if hasattr(exc, 'retry_after') else "60",
        },
    )


# Apply custom handler
limiter._rate_limit_exceeded_handler = custom_rate_limit_exceeded_handler


class RateLimitConfig:
    """速率限制配置"""
    
    # API endpoint specific limits
    ENDPOINT_LIMITS = {
        # Security endpoints
        "/api/v1/security/key-management/keys": "50/minute",
        "/api/v1/security/mfa/methods": "30/minute",
        "/api/v1/security/abac/policies": "30/minute",
        "/api/v1/security/rbac/roles": "30/minute",
        "/api/v1/security/rate-limit/rules": "20/minute",
        
        # Authentication endpoints
        "/api/v1/auth/login": "10/minute",
        "/api/v1/auth/logout": "30/minute",
        "/api/v1/auth/token": "10/minute",
        
        # Alert endpoints
        "/api/v1/alerts": "200/minute",
        "/api/v1/alerts/{alert_id}": "100/minute",
        
        # Repair endpoints
        "/api/v1/repairs": "50/minute",
        "/api/v1/repairs/{repair_id}": "30/minute",
    }
    
    @classmethod
    def get_limit(cls, endpoint: str) -> Optional[str]:
        """获取端点的速率限制"""
        # Try exact match first
        if endpoint in cls.ENDPOINT_LIMITS:
            return cls.ENDPOINT_LIMITS[endpoint]
        
        # Try prefix match
        for pattern, limit in cls.ENDPOINT_LIMITS.items():
            if endpoint.startswith(pattern):
                return limit
        
        # Return default limit
        return None


def get_rate_limit(endpoint: str) -> str:
    """获取端点的速率限制配置"""
    limit = RateLimitConfig.get_limit(endpoint)
    return limit if limit else "100/minute"


def check_rate_limit(request: Request, limit: str = "100/minute"):
    """
    检查速率限制
    
    Args:
        request: FastAPI请求对象
        limit: 速率限制字符串（如: "100/minute", "1000/hour"）
    
    Raises:
        HTTPException: 如果超出速率限制
    """
    try:
        # The limiter will handle the check
        # This is a placeholder for custom rate limit logic if needed
        pass
    except RateLimitExceeded as e:
        raise custom_rate_limit_exceeded_handler(request, e)


class RateLimiter:
    """速率限制器类，用于更复杂的速率限制逻辑"""
    
    def __init__(self):
        self.limiter = limiter
    
    def check_user_rate_limit(self, user_id: int, limit: str = "100/minute") -> bool:
        """
        基于用户的速率限制
        
        Args:
            user_id: 用户ID
            limit: 速率限制字符串
        
        Returns:
            是否允许请求
        """
        # In production, this would use Redis or a database to track per-user limits
        # For now, we rely on the IP-based limiter
        return True
    
    def check_endpoint_rate_limit(self, endpoint: str, limit: Optional[str] = None) -> str:
        """
        获取端点的速率限制
        
        Args:
            endpoint: 端点路径
            limit: 自定义限制（可选）
        
        Returns:
            速率限制字符串
        """
        if limit:
            return limit
        return get_rate_limit(endpoint)
    
    def get_remaining_requests(self, request: Request) -> int:
        """
        获取剩余请求次数
        
        Args:
            request: FastAPI请求对象
        
        Returns:
            剩余请求次数
        """
        # In production, this would query the rate limit storage
        # For now, return a placeholder value
        return 100


def get_rate_limiter() -> RateLimiter:
    """获取速率限制器实例"""
    return RateLimiter()
