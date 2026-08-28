# -*- coding: utf-8 -*-
"""
Cache Manager
缓存管理器

实现Redis缓存策略，提高查询性能
支持TTL、主动失效、缓存预热、缓存统计
"""

import json
import time
from typing import Any, Optional, List, Dict, Callable
from functools import wraps
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config import REDIS_URL, REDIS_PASSWORD


class CacheManager:
    """增强的缓存管理器"""

    def __init__(self):
        self.redis_client = None
        self.default_ttl = 3600  # 默认缓存1小时
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        self.cache_policies = {}
        self._initialize_redis()
        self._load_cache_policies()

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
                max_connections=20,
                retry_on_timeout=True
            )
            # 测试连接
            self.redis_client.ping()
            print("Redis cache initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Redis cache: {e}")
            self.redis_client = None

    def _load_cache_policies(self):
        """加载缓存策略配置"""
        # 定义缓存策略
        self.cache_policies = {
            "alerts": {"ttl": 60, "description": "Alerts list - frequently accessed"},
            "metrics": {"ttl": 30, "description": "Metrics data - high access rate"},
            "configurations": {"ttl": 3600, "description": "Configuration - rarely changes"},
            "ai_analysis": {"ttl": 300, "description": "AI analysis - computationally expensive"},
            "dashboard": {"ttl": 120, "description": "Dashboard - aggregated data"},
            "health": {"ttl": 10, "description": "Health status - very frequent access"},
            "topology": {"ttl": 300, "description": "System topology - changes infrequently"},
            "workflows": {"ttl": 180, "description": "Workflow list - moderate change rate"},
            "users": {"ttl": 600, "description": "User data - changes infrequently"},
            "services": {"ttl": 300, "description": "Service list - changes infrequently"},
            "auto_heal": {"ttl": 60, "description": "Auto-heal status - frequently accessed"},
            "statistics": {"ttl": 300, "description": "Statistics - expensive to compute"},
            "performance": {"ttl": 60, "description": "Performance metrics - frequently accessed"},
            "recommendations": {"ttl": 300, "description": "AI recommendations - cacheable results"},
            "slos": {"ttl": 300, "description": "SLO data - changes infrequently"},
        }

    def get(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.redis_client:
            self.cache_stats["misses"] += 1
            return None

        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                self.cache_stats["hits"] += 1
                return json.loads(cached_data)
            self.cache_stats["misses"] += 1
            return None
        except Exception as e:
            self.cache_stats["errors"] += 1
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
            self.cache_stats["sets"] += 1
            return True
        except Exception as e:
            self.cache_stats["errors"] += 1
            print(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存数据"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            self.cache_stats["deletes"] += 1
            return True
        except Exception as e:
            self.cache_stats["errors"] += 1
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
            return self.cache_stats

        try:
            info = self.redis_client.info()
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "application_stats": self.cache_stats
            }
        except Exception as e:
            print(f"Cache stats error: {e}")
            return self.cache_stats

    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        if total == 0:
            return 0.0
        return self.cache_stats["hits"] / total

    def invalidate_by_pattern(self, pattern: str) -> int:
        """按模式失效缓存"""
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                self.cache_stats["deletes"] += deleted
                return deleted
            return 0
        except Exception as e:
            self.cache_stats["errors"] += 1
            print(f"Cache invalidate pattern error: {e}")
            return 0

    def warm_cache(self, data_loader: Callable[[str], Any], patterns: List[str]) -> int:
        """缓存预热"""
        warmed_count = 0
        for pattern in patterns:
            try:
                data = data_loader(pattern)
                if data:
                    key = f"warm:{pattern}"
                    self.set(key, data, ttl=self.default_ttl)
                    warmed_count += 1
            except Exception as e:
                print(f"Cache warm error for {pattern}: {e}")
        return warmed_count

    def get_policy_ttl(self, policy_name: str) -> int:
        """获取策略的TTL"""
        policy = self.cache_policies.get(policy_name)
        return policy["ttl"] if policy else self.default_ttl


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


def cached(ttl: int = 3600, prefix: str = "cache", policy: Optional[str] = None):
    """增强的缓存装饰器，支持策略和TTL"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取TTL
            cache_ttl = ttl
            if policy and cache_manager.cache_policies.get(policy):
                cache_ttl = cache_manager.cache_policies[policy]["ttl"]
            
            # 生成缓存键
            cache_key = cache_key_generator(prefix, func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 设置缓存
            cache_manager.set(cache_key, result, ttl=cache_ttl)
            
            return result
        return wrapper
    return decorator


def cache_with_invalidation(ttl: int = 3600, prefix: str = "cache", invalidate_patterns: Optional[List[str]] = None):
    """支持主动失效的缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 执行函数
            result = func(*args, **kwargs)
            
            # 如果有失效模式，失效相关缓存
            if invalidate_patterns:
                for pattern in invalidate_patterns:
                    cache_manager.invalidate_by_pattern(pattern)
            
            return result
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str) -> int:
    """失效匹配模式的所有缓存"""
    return cache_manager.invalidate_by_pattern(pattern)


def get_cache_policies() -> Dict[str, Dict[str, Any]]:
    """获取缓存策略配置"""
    return cache_manager.cache_policies


def set_cache_policy(policy_name: str, ttl: int, description: str) -> bool:
    """设置缓存策略"""
    cache_manager.cache_policies[policy_name] = {
        "ttl": ttl,
        "description": description
    }
    return True


def get_cache_hit_rate() -> float:
    """获取缓存命中率"""
    return cache_manager.get_cache_hit_rate()


def cache_aware(ttl: int = 3600, prefix: str = "cache", policy: Optional[str] = None):
    """缓存感知装饰器，自动处理缓存失效"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取TTL
            cache_ttl = ttl
            if policy and cache_manager.cache_policies.get(policy):
                cache_ttl = cache_manager.cache_policies[policy]["ttl"]
            
            # 生成缓存键
            cache_key = cache_key_generator(prefix, func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 检查是否应该缓存结果
            should_cache = True
            if isinstance(result, (list, dict)):
                should_cache = len(result) > 0  # 只缓存非空结果
            
            if should_cache:
                cache_manager.set(cache_key, result, ttl=cache_ttl)
            
            return result
        return wrapper
    return decorator


# 导出便捷函数
__all__ = [
    "CacheManager",
    "cache_manager",
    "cache_key_generator",
    "cached",
    "cache_with_invalidation",
    "cache_aware",
    "invalidate_cache_pattern",
    "get_cache_hit_rate",
    "get_cache_policies",
    "set_cache_policy",
]