# -*- coding: utf-8 -*-
"""
Cache Manager
缓存管理器

实现Redis缓存策略，提高查询性能
"""

import json
import time
from typing import Any, Optional, List, Dict
from functools import wraps
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config import REDIS_URL, REDIS_PASSWORD


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.redis_client = None
        self.default_ttl = 3600  # 默认缓存1小时
        self._initialize_redis()

    def _initialize_redis(self):
        """初始化Redis连接"""
        if not REDIS_AVAILABLE:
            print("Redis not available, caching disabled")
            return

        try:
            self.redis_client = redis.from_url(
                REDIS_URL,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # 测试连接
            self.redis_client.ping()
            print("Redis cache initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Redis cache: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.redis_client:
            return None

        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据"""
        if not self.redis_client:
            return False

        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存数据"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有缓存"""
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.redis_client:
            return False

        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.redis_client:
            return {}

        try:
            info = self.redis_client.info()
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {}


# 全局缓存管理器实例
cache_manager = CacheManager()


def cache_key_generator(prefix: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [prefix]
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            # 对于复杂对象，使用hash
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    return ":".join(key_parts)


def cached(ttl: int = 3600, prefix: str = "cache"):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_key_generator(prefix, func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 设置缓存
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """失效匹配模式的所有缓存"""
    return cache_manager.delete_pattern(pattern)


def get_cache_hit_rate() -> float:
    """获取缓存命中率"""
    stats = cache_manager.get_cache_stats()
    hits = stats.get("keyspace_hits", 0)
    misses = stats.get("keyspace_misses", 0)
    total = hits + misses
    
    if total == 0:
        return 0.0
    
    return hits / total