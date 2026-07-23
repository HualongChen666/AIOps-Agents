# -*- coding: utf-8 -*-
"""
Enhanced Caching Strategy
增强缓存策略

Advanced caching utilities including Redis backend, cache warming,
and intelligent cache invalidation for the AIOps Agent system.
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import redis
from loguru import logger


class RedisCacheBackend:
    """Redis-based cache backend for distributed caching"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 300,
    ):
        """
        Initialize Redis cache backend

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            default_ttl: Default time-to-live in seconds
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            self.client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in Redis

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from Redis

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            return False

    def flush_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis flush pattern failed: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics

        Returns:
            Dictionary with Redis stats
        """
        if not self.client:
            return {"error": "Not connected"}

        try:
            info = self.client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_keys": info.get("db0", {}).get("keys", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {"error": str(e)}


class CacheWarmer:
    """Cache warming utility for pre-loading frequently accessed data"""

    def __init__(self, cache_backend):
        """
        Initialize cache warmer

        Args:
            cache_backend: Cache backend instance
        """
        self.cache_backend = cache_backend
        self.warmup_tasks: List[Callable] = []

    def register_warmup_task(self, task: Callable):
        """
        Register a cache warmup task

        Args:
            task: Async function that returns dict of key-value pairs to cache
        """
        self.warmup_tasks.append(task)

    async def warmup_cache(self):
        """Execute all registered warmup tasks"""
        logger.info(f"Starting cache warmup with {len(self.warmup_tasks)} tasks")

        for task in self.warmup_tasks:
            try:
                logger.info(f"Running warmup task: {task.__name__}")
                cache_data = await task()

                for key, value in cache_data.items():
                    self.cache_backend.set(key, value)

                logger.info(
                    f"Warmup task {task.__name__} completed: {len(cache_data)} items cached"
                )

            except Exception as e:
                logger.error(f"Warmup task {task.__name__} failed: {e}")

        logger.info("Cache warmup completed")


class CacheInvalidationStrategy:
    """Intelligent cache invalidation strategies"""

    @staticmethod
    def invalidate_by_prefix(cache_backend, prefix: str):
        """
        Invalidate all cache entries with a given prefix

        Args:
            cache_backend: Cache backend instance
            prefix: Key prefix to invalidate
        """
        if isinstance(cache_backend, RedisCacheBackend):
            pattern = f"{prefix}:*"
            count = cache_backend.flush_pattern(pattern)
            logger.info(f"Invalidated {count} cache entries with prefix: {prefix}")
        else:
            logger.warning("Prefix invalidation only supported for Redis backend")

    @staticmethod
    def invalidate_by_tags(cache_backend, tags: List[str]):
        """
        Invalidate cache entries by tags (requires tag-based caching)

        Args:
            cache_backend: Cache backend instance
            tags: List of tags to invalidate
        """
        if isinstance(cache_backend, RedisCacheBackend):
            for tag in tags:
                pattern = f"tag:{tag}:*"
                count = cache_backend.flush_pattern(pattern)
                logger.info(f"Invalidated {count} cache entries with tag: {tag}")
        else:
            logger.warning("Tag-based invalidation only supported for Redis backend")

    @staticmethod
    def invalidate_by_time(cache_backend, older_than_seconds: int):
        """
        Invalidate cache entries older than specified time

        Args:
            cache_backend: Cache backend instance
            older_than_seconds: Age threshold in seconds
        """
        logger.warning("Time-based invalidation not yet implemented")


def smart_cache(
    ttl: int = 300, key_prefix: str = "", cache_backend=None, condition: Optional[Callable] = None
):
    """
    Advanced caching decorator with conditional caching

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache_backend: Cache backend instance
        condition: Optional function to determine if caching should be applied
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check condition if provided
            if condition and not condition(*args, **kwargs):
                return await func(*args, **kwargs)

            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5("|".join(key_parts).encode(), usedforsecurity=False).hexdigest()

            # Try to get from cache
            if cache_backend:
                cached = cache_backend.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            if cache_backend:
                cache_backend.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {func.__name__}")

            return result

        return wrapper

    return decorator


async def setup_enhanced_caching():
    """
    Setup enhanced caching with Redis backend
    """
    try:
        # Initialize Redis cache backend
        redis_cache = RedisCacheBackend(host="localhost", port=6379, db=0, default_ttl=300)

        # Setup cache warmer
        cache_warmer = CacheWarmer(redis_cache)

        # Register warmup tasks (example)
        async def warmup_system_config():
            # Example warmup task - load system configuration
            return {
                "system:config": {"version": "1.0.0", "features": []},
                "system:metrics": {"cpu": 0, "memory": 0},
            }

        cache_warmer.register_warmup_task(warmup_system_config)

        # Perform cache warmup
        await cache_warmer.warmup_cache()

        logger.info("Enhanced caching setup completed")
        return {"status": "success", "backend": "redis", "cache_stats": redis_cache.get_stats()}

    except Exception as e:
        logger.error(f"Enhanced caching setup failed: {e}")
        return {"status": "error", "error": str(e)}
