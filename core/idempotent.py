# -*- coding: utf-8 -*-
"""
Idempotency Framework
幂等性框架，确保重复请求产生相同结果

功能:
- 幂等键生成与验证
- 请求缓存与去重
- 基于Redis/内存的存储
- TTL自动过期
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union  # noqa: F401

from config import REDIS_URL

logger = logging.getLogger(__name__)


class IdempotencyStore:
    """
    幂等性存储基类

    参数:
        ttl: 缓存过期时间（秒）
    """

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取幂等键对应的响应"""
        if key in self._store:
            entry = self._store[key]
            # 检查是否过期
            if datetime.now() < entry["expires_at"]:
                response = entry["response"]
                return Dict[str, Any](response) if isinstance(response, dict) else None
            else:
                # 过期删除
                del self._store[key]
        return None

    def set(self, key: str, response: Dict[str, Any]) -> None:
        """设置幂等键对应的响应"""
        self._store[key] = {
            "response": response,
            "expires_at": datetime.now() + timedelta(seconds=self.ttl),
            "created_at": datetime.now(),
        }

    def delete(self, key: str) -> bool:
        """删除幂等键"""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """检查幂等键是否存在"""
        return self.get(key) is not None

    def clear_expired(self) -> int:
        """清理过期的条目"""
        now = datetime.now()
        expired_keys = [key for key, entry in self._store.items() if now >= entry["expires_at"]]
        for key in expired_keys:
            del self._store[key]
        return len(expired_keys)


class RedisIdempotencyStore(IdempotencyStore):
    """
    基于Redis的幂等性存储

    参数:
        redis_url: Redis连接URL
        ttl: 缓存过期时间（秒）
    """

    def __init__(self, redis_url: str = REDIS_URL, ttl: int = 3600):
        super().__init__(ttl)
        self.redis_url = redis_url
        self._redis_client: Optional[Any] = None  # type: ignore

    def _get_client(self):
        """获取Redis客户端"""
        if self._redis_client is None:
            try:
                import redis

                self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
                logger.info("Redis idempotency store connected")
            except ImportError:
                logger.warning("redis not installed, falling back to in-memory store")
                return None
        return self._redis_client

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """从Redis获取幂等键对应的响应"""
        client = self._get_client()
        if client is None:
            return super().get(key)

        try:
            data = client.get(f"idemp:{key}")
            if data:
                loaded = json.loads(data)
                return Dict[str, Any](loaded) if isinstance(loaded, dict) else None
        except Exception as e:
            logger.error("Failed to get from Redis: %s", e)
        return None

    def set(self, key: str, response: Dict[str, Any]) -> None:
        """设置幂等键对应的响应到Redis"""
        client = self._get_client()
        if client is None:
            return super().set(key, response)

        try:
            client.setex(f"idemp:{key}", self.ttl, json.dumps(response))
        except Exception as e:
            logger.error("Failed to set to Redis: %s", e)

    def delete(self, key: str) -> bool:
        """从Redis删除幂等键"""
        client = self._get_client()
        if client is None:
            return super().delete(key)

        try:
            result = client.delete(f"idemp:{key}")
            return bool(result > 0)
        except Exception as e:
            logger.error("Failed to delete from Redis: %s", e)
            return False

    def exists(self, key: str) -> bool:
        """检查Redis中幂等键是否存在"""
        client = self._get_client()
        if client is None:
            return super().exists(key)

        try:
            return bool(client.exists(f"idemp:{key}") > 0)
        except Exception as e:
            logger.error("Failed to check existence in Redis: %s", e)
            return False


def generate_idempotency_key(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    user_id: Optional[str] = None,
) -> str:
    """
    生成幂等键

    参数:
        method: HTTP方法
        path: 请求路径
        body: 请求体
        headers: 请求头
        user_id: 用户ID

    返回:
        幂等键字符串
    """
    # 构建标准化输入
    key_parts = {
        "method": method.upper(),
        "path": path,
        "body": json.dumps(body, sort_keys=True) if body else "",
        "user_id": user_id or "",
    }

    # 过滤特定头部（如Authorization）
    if headers:
        filtered_headers = {
            k: v for k, v in headers.items() if k.lower() not in ["authorization", "cookie"]
        }
        key_parts["headers"] = json.dumps(filtered_headers, sort_keys=True)

    # 生成哈希
    key_string = json.dumps(key_parts, sort_keys=True)
    hash_obj = hashlib.sha256(key_string.encode())
    return hash_obj.hexdigest()


def idempotent(
    store: Optional[IdempotencyStore] = None,
    key_generator: Optional[Callable] = None,
    ttl: int = 3600,
):
    """
    幂等性装饰器

    参数:
        store: 幂等性存储实例
        key_generator: 自定义键生成函数
        ttl: 缓存过期时间

    使用示例:
        @idempotent()
        async def create_resource(data):
            # 业务逻辑
            return {"id": "123", "status": "created"}
    """
    if store is None:
        store = IdempotencyStore(ttl=ttl)

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 尝试从kwargs中获取幂等键
            idempotency_key = kwargs.pop("idempotency_key", None)

            if idempotency_key is None and key_generator:
                idempotency_key = key_generator(*args, **kwargs)

            if idempotency_key:
                # 检查是否已存在
                cached_response = store.get(idempotency_key)
                if cached_response:
                    logger.info(
                        "Returning cached response for idempotency key: %s", idempotency_key[:16]
                    )
                    return cached_response

            # 执行原函数
            response = await func(*args, **kwargs)

            # 缓存响应
            if idempotency_key:
                store.set(idempotency_key, response)
                logger.debug("Cached response for idempotency key: %s", idempotency_key[:16])

            return response

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步版本
            idempotency_key = kwargs.pop("idempotency_key", None)

            if idempotency_key is None and key_generator:
                idempotency_key = key_generator(*args, **kwargs)

            if idempotency_key:
                cached_response = store.get(idempotency_key)
                if cached_response:
                    logger.info(
                        "Returning cached response for idempotency key: %s", idempotency_key[:16]
                    )
                    return cached_response

            response = func(*args, **kwargs)

            if idempotency_key:
                store.set(idempotency_key, response)
                logger.debug("Cached response for idempotency key: %s", idempotency_key[:16])

            return response

        # 根据函数类型返回对应的wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class IdempotencyMiddleware:
    """
    幂等性中间件（用于FastAPI）

    参数:
        store: 幂等性存储实例
        header_name: 幂等键HTTP头名称
        ttl: 缓存过期时间
    """

    def __init__(
        self,
        store: Optional[IdempotencyStore] = None,
        header_name: str = "Idempotency-Key",
        ttl: int = 3600,
    ):
        self.store = store or IdempotencyStore(ttl=ttl)
        self.header_name = header_name

    async def __call__(self, request, call_next):
        """FastAPI中间件调用"""
        # 只对POST/PUT/PATCH请求启用幂等性
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)

        # 获取幂等键
        idempotency_key = request.headers.get(self.header_name)

        if not idempotency_key:
            # 没有幂等键，直接执行
            return await call_next(request)

        # 检查缓存
        cached_response = self.store.get(idempotency_key)
        if cached_response:
            logger.info("Returning cached response for idempotency key: %s", idempotency_key[:16])
            from fastapi.responses import JSONResponse

            return JSONResponse(content=cached_response)

        # 执行请求
        response = await call_next(request)

        # 缓存响应（仅成功响应）
        if response.status_code < 400:
            try:
                response_body = await response.body()
                response_data = json.loads(response_body.decode())
                self.store.set(idempotency_key, response_data)
                logger.debug("Cached response for idempotency key: %s", idempotency_key[:16])
            except Exception as e:
                logger.warning("Failed to cache response: %s", e)

        return response
