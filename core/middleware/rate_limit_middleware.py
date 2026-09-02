# -*- coding: utf-8 -*-
# core/middleware/rate_limit_middleware.py
# 速率限制中间件 - 防止API滥用

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Callable, Dict, Optional, Tuple

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器 - 使用滑动窗口算法"""
    
    def __init__(self):
        """初始化速率限制器"""
        # 存储每个客户端的请求记录
        # 结构: {client_id: [(timestamp, count), ...]}
        self._requests: Dict[str, list[Tuple[float, int]]] = defaultdict(list)
        
        # 默认速率限制配置
        self._default_limits = {
            "default": (100, 60),  # 100 requests per 60 seconds
            "strict": (50, 60),    # 50 requests per 60 seconds
            "lenient": (200, 60),  # 200 requests per 60 seconds
        }
        
        # 端点特定的速率限制
        self._endpoint_limits: Dict[str, Tuple[int, int]] = {
            # 用户管理端点 - 更严格的限制
            "/api/v1/users": (20, 60),
            "/api/v1/users/": (20, 60),
            
            # 认证端点 - 更严格的限制
            "/api/v1/auth/token": (10, 60),
            "/api/v1/auth/login": (10, 60),
            
            # 告警端点 - 中等限制
            "/api/v1/alerts": (50, 60),
            
            # 修复端点 - 严格限制
            "/api/v1/repairs": (10, 60),
        }
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识符
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            客户端标识符（IP地址或用户ID）
        """
        # 优先使用用户ID（如果已认证）
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        # 否则使用IP地址
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    def _get_limit(self, path: str) -> Tuple[int, int]:
        """获取端点的速率限制
        
        Args:
            path: 请求路径
            
        Returns:
            (max_requests, time_window) 元组
        """
        # 检查端点特定限制
        for endpoint_pattern, limit in self._endpoint_limits.items():
            if path.startswith(endpoint_pattern):
                return limit
        
        # 使用默认限制
        return self._default_limits["default"]
    
    def _clean_old_requests(self, client_id: str, current_time: float, time_window: int):
        """清理过期的请求记录
        
        Args:
            client_id: 客户端标识符
            current_time: 当前时间戳
            time_window: 时间窗口（秒）
        """
        cutoff_time = current_time - time_window
        self._requests[client_id] = [
            (ts, count) for ts, count in self._requests[client_id]
            if ts > cutoff_time
        ]
    
    def _count_requests(self, client_id: str, current_time: float, time_window: int) -> int:
        """统计时间窗口内的请求数量
        
        Args:
            client_id: 客户端标识符
            current_time: 当前时间戳
            time_window: 时间窗口（秒）
            
        Returns:
            请求数量
        """
        self._clean_old_requests(client_id, current_time, time_window)
        return sum(count for _, count in self._requests[client_id])
    
    def is_allowed(
        self, client_id: str, path: str, current_time: Optional[float] = None
    ) -> Tuple[bool, int, int]:
        """检查是否允许请求
        
        Args:
            client_id: 客户端标识符
            path: 请求路径
            current_time: 当前时间戳（可选）
            
        Returns:
            (is_allowed, remaining_requests, reset_time) 元组
        """
        if current_time is None:
            current_time = time.time()
        
        max_requests, time_window = self._get_limit(path)
        
        # 统计当前时间窗口内的请求数
        request_count = self._count_requests(client_id, current_time, time_window)
        
        # 检查是否超过限制
        if request_count >= max_requests:
            # 计算重置时间
            if self._requests[client_id]:
                oldest_request = min(ts for ts, _ in self._requests[client_id])
                reset_time = int(oldest_request + time_window)
            else:
                reset_time = int(current_time + time_window)
            
            return False, 0, reset_time
        
        # 记录此次请求
        self._requests[client_id].append((current_time, 1))
        
        # 计算剩余请求数
        remaining = max_requests - request_count - 1
        
        # 计算重置时间
        if self._requests[client_id]:
            oldest_request = min(ts for ts, _ in self._requests[client_id])
            reset_time = int(oldest_request + time_window)
        else:
            reset_time = int(current_time + time_window)
        
        return True, remaining, reset_time
    
    def reset(self, client_id: str):
        """重置客户端的速率限制
        
        Args:
            client_id: 客户端标识符
        """
        if client_id in self._requests:
            del self._requests[client_id]
            logger.info(f"重置速率限制 | client_id={client_id}")


# 全局速率限制器实例
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """速率限制中间件
    
    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器
        
    Returns:
        HTTP响应对象
    """
    # 跳过健康检查等端点
    if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    client_id = rate_limiter._get_client_id(request)
    path = request.url.path
    current_time = time.time()
    
    # 检查速率限制
    is_allowed, remaining, reset_time = rate_limiter.is_allowed(client_id, path, current_time)
    
    # 添加速率限制响应头
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(rate_limiter._get_limit(path)[0])
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)
    
    if not is_allowed:
        logger.warning(
            f"速率限制触发 | client_id={client_id} | path={path} | "
            f"reset_time={reset_time}"
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "请求过于频繁，请稍后再试",
                "error": "rate_limit_exceeded",
                "retry_after": reset_time - int(current_time),
            },
            headers={
                "X-RateLimit-Limit": str(rate_limiter._get_limit(path)[0]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(reset_time - int(current_time)),
            },
        )
    
    return response


def rate_limit_dependency(max_requests: int = 100, time_window: int = 60) -> Callable:
    """速率限制依赖工厂函数（用于特定端点）
    
    Args:
        max_requests: 最大请求数
        time_window: 时间窗口（秒）
        
    Returns:
        依赖函数
    """
    async def rate_limit_checker(request: Request) -> None:
        """检查速率限制
        
        Args:
            request: FastAPI请求对象
            
        Raises:
            HTTPException: 超过速率限制时抛出429错误
        """
        client_id = rate_limiter._get_client_id(request)
        current_time = time.time()
        
        # 清理过期记录
        rate_limiter._clean_old_requests(client_id, current_time, time_window)
        
        # 统计请求数
        request_count = rate_limiter._count_requests(client_id, current_time, time_window)
        
        if request_count >= max_requests:
            logger.warning(
                f"速率限制触发 | client_id={client_id} | "
                f"max_requests={max_requests} | time_window={time_window}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，每{time_window}秒最多{max_requests}次请求",
                headers={
                    "Retry-After": str(time_window),
                },
            )
        
        # 记录此次请求
        rate_limiter._requests[client_id].append((current_time, 1))
    
    return rate_limit_checker
