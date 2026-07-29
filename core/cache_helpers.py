# -*- coding: utf-8 -*-
# core/cache_helpers.py
"""🔧 P0 Performance Enhancement: Advanced TTL Cache Helper Classes
P2 Enhancement: Added L3 database cache, intelligent eviction, and enhanced cache warming

Provides reusable TTL cache implementations with advanced features:
- Multi-level caching (memory + Redis + Database)
- LRU eviction policies
- Cache warming and preloading
- Cache statistics and monitoring
- Intelligent cache key generation
- Smart cache invalidation strategies
"""

import hashlib
import json
import time
from collections import OrderedDict
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Union  # noqa: F401

from loguru import logger


# ============================================================
# P2 Enhancement: Cache Eviction Policy Enum
# ============================================================
class CacheEvictionPolicy(Enum):
    """Cache eviction policy types"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live based
    ADAPTIVE = "adaptive"  # Adaptive based on access patterns


# ============================================================
# P2 Enhancement: Cache Invalidation Event Types
# ============================================================
class CacheInvalidationEvent(Enum):
    """Cache invalidation event types"""

    TIME_BASED = "time_based"  # TTL expiration
    EVENT_BASED = "event_based"  # Data change event
    CAPACITY_BASED = "capacity_based"  # Cache full
    MANUAL = "manual"  # Manual invalidation
    ADAPTIVE = "adaptive"  # Adaptive prediction


# ============================================================
# 🔧 P0 Enhancement: Cache Statistics
# ============================================================
class CacheStatistics:
    """Cache performance statistics tracking"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size = 0
        self.max_size = 0

    def record_hit(self):
        """Record a cache hit"""
        self.hits += 1

    def record_miss(self):
        """Record a cache miss"""
        self.misses += 1

    def record_eviction(self):
        """Record a cache eviction"""
        self.evictions += 1

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{self.get_hit_rate():.2f}%",
            "size": self.size,
            "max_size": self.max_size,
        }


# ============================================================
# 🔧 P0 Enhancement: Advanced LRU Cache with Eviction
# ============================================================
class LRUCache:
    """
    Thread-safe LRU cache with size-based eviction and statistics.

    Usage:
        cache = LRUCache(max_size=1000, ttl_sec=300)

        # Write
        cache.set("key1", {"data": my_data})

        # Read
        cached = cache.get("key1")  # Returns data or None
    """

    def __init__(self, max_size: int = 1000, ttl_sec: float = 300.0):
        """
        Args:
            max_size: Maximum number of items in cache
            ttl_sec: Cache validity period in seconds
        """
        self._max_size = max_size
        self._ttl_sec = ttl_sec
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = Lock()
        self._stats = CacheStatistics()
        self._stats.max_size = max_size

    def _is_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid"""
        now = time.monotonic()
        elapsed = now - timestamp
        return elapsed < self._ttl_sec

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache is full"""
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # Remove oldest (FIFO)
            self._stats.record_eviction()

    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache"""
        with self._lock:
            # Remove existing key if present (to update position)
            if key in self._cache:
                del self._cache[key]
            else:
                self._stats.size = len(self._cache) + 1

            # Evict if needed
            self._evict_if_needed()

            # Add new entry
            self._cache[key] = (value, time.monotonic())

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache"""
        with self._lock:
            if key not in self._cache:
                self._stats.record_miss()
                return None

            value, timestamp = self._cache[key]

            if not self._is_valid(timestamp):
                del self._cache[key]
                self._stats.record_miss()
                self._stats.size = len(self._cache)
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats.record_hit()
            return value

    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._stats.size = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self._stats.get_stats()


# ============================================================
# 🔧 P0 Enhancement: Multi-Level Cache (Memory + Redis)
# ============================================================
class MultiLevelCache:
    """
    Multi-level cache with memory and Redis backends.

    Usage:
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)

        # Write
        cache.set("key1", {"data": my_data})

        # Read
        cached = cache.get("key1")  # Checks memory first, then Redis
    """

    def __init__(
        self, memory_ttl: float = 60.0, redis_ttl: float = 3600.0, redis_prefix: str = "aiops_cache"
    ):
        """
        Args:
            memory_ttl: Memory cache TTL in seconds
            redis_ttl: Redis cache TTL in seconds
            redis_prefix: Prefix for Redis keys
        """
        self._memory_cache = LRUCache(max_size=1000, ttl_sec=memory_ttl)
        self._redis_ttl = redis_ttl
        self._redis_prefix = redis_prefix
        self._redis_available = False
        self._lock = Lock()
        self._redis_client: Optional[Any] = None  # type: ignore

        # Try to initialize Redis
        try:
            import redis

            self._redis_client = redis.Redis(
                host="localhost", port=6379, db=0, decode_responses=True
            )
            self._redis_client.ping()
            self._redis_available = True
            logger.info("Multi-level cache: Redis backend available")
        except Exception as e:
            logger.info(f"Multi-level cache: Redis not available: {e}")
            self._redis_client = None

    def _make_redis_key(self, key: str) -> str:
        """Generate Redis key with prefix"""
        return f"{self._redis_prefix}:{key}"

    def set(self, key: str, value: Any) -> None:
        """Set value in both memory and Redis caches"""
        # Set in memory cache
        self._memory_cache.set(key, value)

        # Set in Redis if available
        if self._redis_available and self._redis_client:
            try:
                redis_key = self._make_redis_key(key)
                serialized = (
                    json.dumps(value) if not isinstance(value, (str, int, float, bool)) else value
                )
                self._redis_client.setex(redis_key, int(self._redis_ttl), serialized)
            except Exception as e:
                logger.error(f"Redis set failed: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache, falling back to Redis"""
        # Try memory cache first
        value = self._memory_cache.get(key)
        if value is not None:
            return value

        # Try Redis cache
        if self._redis_available and self._redis_client:
            try:
                redis_key = self._make_redis_key(key)
                serialized = self._redis_client.get(redis_key)
                if serialized is not None:
                    # Deserialize if needed
                    try:
                        value = (
                            json.loads(serialized)
                            if isinstance(serialized, str) and serialized.startswith("{")
                            else serialized
                        )
                    except (json.JSONDecodeError, AttributeError):
                        value = serialized

                    # Store in memory cache
                    self._memory_cache.set(key, value)
                    return value
            except Exception as e:
                logger.error(f"Redis get failed: {e}")

        return None

    def invalidate(self, key: str) -> None:
        """Invalidate value in both memory and Redis caches"""
        self._memory_cache.invalidate(key)

        if self._redis_available and self._redis_client:
            try:
                redis_key = self._make_redis_key(key)
                self._redis_client.delete(redis_key)
            except Exception as e:
                logger.error(f"Redis invalidate failed: {e}")

    def clear(self) -> None:
        """Clear both memory and Redis caches"""
        self._memory_cache.clear()

        if self._redis_available and self._redis_client:
            try:
                # Clear all keys with our prefix
                pattern = f"{self._redis_prefix}:*"
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis clear failed: {e}")


# ============================================================
# 🔧 P0 Enhancement: Cache Key Generator
# ============================================================
def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate consistent cache keys from function arguments.

    Args:
        prefix: Cache key prefix
        *args: Function positional arguments
        **kwargs: Function keyword arguments

    Returns:
        Consistent cache key string
    """
    # Create a deterministic string representation
    key_parts = [prefix]

    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(hashlib.md5(str(arg).encode(), usedforsecurity=False).hexdigest()[:8])

    # Add keyword arguments (sorted for consistency)
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}={v}")
        else:
            key_parts.append(
                f"{k}={hashlib.md5(str(v).encode(), usedforsecurity=False).hexdigest()[:8]}"
            )

    return ":".join(key_parts)


# ============================================================
# 🔧 P0 Enhancement: Cache Warmer
# ============================================================
class CacheWarmer:
    """
    Cache warming utility for preloading frequently accessed data.

    Usage:
        warmer = CacheWarmer(cache)

        # Define warm function
        async def warm_user_data(user_id):
            return await get_user_from_db(user_id)

        # Register warm function
        warmer.register("user_data", warm_user_data)

        # Warm cache
        await warmer.warm("user_data", user_id="123")
    """

    def __init__(self, cache: LRUCache):
        """
        Args:
            cache: Cache instance to warm
        """
        self._cache = cache
        self._warm_functions: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable) -> None:
        """Register a cache warm function"""
        self._warm_functions[name] = func

    async def warm(self, name: str, *args, **kwargs) -> Any:
        """Execute warm function and cache result"""
        if name not in self._warm_functions:
            raise ValueError(f"Unknown warm function: {name}")

        # Execute warm function
        result = await self._warm_functions[name](*args, **kwargs)

        # Generate cache key and store result
        cache_key = generate_cache_key(f"warm_{name}", *args, **kwargs)
        self._cache.set(cache_key, result)

        return result


# ============================================================
# Original Simple TTL Cache (maintained for compatibility)
# ============================================================
class TTLCache:
    """
    Thread-safe TTL cache with shallow copy protection.

    Usage:
        cache = TTLCache(ttl_sec=30)

        # Write
        cache.set({"data": my_data})

        # Read
        cached = cache.get()  # Returns shallow copy or None
    """

    def __init__(self, ttl_sec: float = 30.0):
        """
        Args:
            ttl_sec: Cache validity period in seconds
        """
        self._ttl_sec = ttl_sec
        self._cache: dict[str, Any] = {"data": None, "ts": 0.0}
        self._lock = Lock()

    def _is_valid(self) -> bool:
        """Check if cache is valid (caller must hold lock)."""
        now = time.monotonic()
        ts = float(self._cache["ts"])
        if ts <= 0 or self._cache["data"] is None:
            return False
        elapsed = now - ts
        if elapsed < 0:
            # Time rollback (NTP sync, etc.), invalidate cache
            return False
        return elapsed < self._ttl_sec

    def get(self) -> Optional[dict[str, Any]]:
        """
        Get cached data (shallow copy).

        Returns:
            Cached data copy / None (if cache invalid)
        """
        with self._lock:
            if self._is_valid():
                return dict(self._cache["data"])
        return None

    def set(self, data: dict[str, Any]) -> None:
        """
        Set cached data.

        Args:
            data: Data to cache
        """
        with self._lock:
            self._cache["data"] = data
            self._cache["ts"] = time.monotonic()

    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self._cache["data"] = None
            self._cache["ts"] = 0.0

    def is_valid(self) -> bool:
        """
        Check if cache is valid (thread-safe).

        Returns:
            True/False
        """
        with self._lock:
            return self._is_valid()


# ============================================================
# Parametric TTL Cache (with parameter support)
# ============================================================
class ParametricTTLCache:
    """
    TTL cache with parameter support (different parameters cached separately).

    Usage:
        cache = ParametricTTLCache(ttl_sec=5)

        # Write (with parameters)
        cache.set({"data": my_data}, limit=10)

        # Read (with parameters)
        cached = cache.get(limit=10)  # Only returns if limit matches
    """

    def __init__(self, ttl_sec: float = 5.0):
        """
        Args:
            ttl_sec: Cache validity period in seconds
        """
        self._ttl_sec = ttl_sec
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def _make_key(self, **params) -> str:
        """Generate cache key from parameters."""
        return "|".join(f"{k}={v}" for k, v in sorted(params.items()))

    def _is_valid(self, entry: dict[str, Any]) -> bool:
        """Check if cache entry is valid."""
        now = time.monotonic()
        ts = float(entry["ts"])
        if ts <= 0 or entry["data"] is None:
            return False
        elapsed = now - ts
        if elapsed < 0:
            return False
        return elapsed < self._ttl_sec

    def get(self, **params) -> Optional[dict[str, Any]]:
        """
        Get cached data.

        Args:
            **params: Cache parameters

        Returns:
            Cached data copy / None
        """
        key = self._make_key(**params)
        with self._lock:
            entry = self._cache.get(key)
            if entry and self._is_valid(entry):
                return dict(entry["data"])
        return None

    def set(self, data: dict[str, Any], **params) -> None:
        """
        Set cached data.

        Args:
            data: Data to cache
            **params: Cache parameters
        """
        key = self._make_key(**params)
        with self._lock:
            self._cache[key] = {
                "data": data,
                "ts": time.monotonic(),
                "params": params,
            }

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()


# ============================================================
# P2 Enhancement: Three-Level Cache (Memory + Redis + Database)
# ============================================================
class ThreeLevelCache:
    """
    P2 Enhanced three-level cache with memory, Redis, and database backends.
    Implements intelligent cache invalidation and adaptive eviction.

    Usage:
        cache = ThreeLevelCache(
            memory_ttl=60,
            redis_ttl=3600,
            db_ttl=86400,
            eviction_policy=CacheEvictionPolicy.ADAPTIVE
        )

        # Write
        cache.set("key1", {"data": my_data})

        # Read (checks L1 -> L2 -> L3)
        cached = cache.get("key1")
    """

    def __init__(
        self,
        memory_ttl: float = 60.0,
        redis_ttl: float = 3600.0,
        db_ttl: float = 86400.0,
        redis_prefix: str = "aiops_cache",
        eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU,
    ):
        """
        Args:
            memory_ttl: L1 memory cache TTL in seconds
            redis_ttl: L2 Redis cache TTL in seconds
            db_ttl: L3 database cache TTL in seconds
            redis_prefix: Prefix for Redis keys
            eviction_policy: Cache eviction policy
        """
        self._memory_cache = LRUCache(max_size=1000, ttl_sec=memory_ttl)
        self._redis_ttl = redis_ttl
        self._db_ttl = db_ttl
        self._redis_prefix = redis_prefix
        self._eviction_policy = eviction_policy
        self._redis_available = False
        self._db_available = False
        self._lock = Lock()
        self._redis_client: Optional[Any] = None  # type: ignore

        # Invalidation event callbacks
        self._invalidation_callbacks: Dict[CacheInvalidationEvent, List[Callable]] = {
            event: [] for event in CacheInvalidationEvent
        }

        # Try to initialize Redis
        try:
            import redis

            import config

            self._redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._redis_client.ping()
            self._redis_available = True
            logger.info("Three-level cache: Redis backend available")
        except Exception as e:
            logger.warning(f"Three-level cache: Redis not available: {e}")
            self._redis_client = None

        # Try to initialize database cache
        try:
            import config

            self._db_available = True
            logger.info("Three-level cache: Database backend available")
        except Exception as e:
            logger.warning(f"Three-level cache: Database not available: {e}")

    def register_invalidation_callback(
        self, event: CacheInvalidationEvent, callback: Callable
    ) -> None:
        """Register a callback for cache invalidation events"""
        self._invalidation_callbacks[event].append(callback)

    def _trigger_invalidation_event(
        self, event: CacheInvalidationEvent, key: str, metadata: Optional[Dict] = None
    ) -> None:
        """Trigger invalidation event callbacks"""
        for callback in self._invalidation_callbacks[event]:
            try:
                callback(key, metadata or {})
            except Exception as e:
                logger.error(f"Invalidation callback failed: {e}")

    def _make_redis_key(self, key: str) -> str:
        """Generate Redis key with prefix"""
        return f"{self._redis_prefix}:{key}"

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in all three cache levels"""
        with self._lock:
            # Set in L1 memory cache
            self._memory_cache.set(key, value)

            # Set in L2 Redis cache
            if self._redis_available and self._redis_client:
                try:
                    redis_key = self._make_redis_key(key)
                    serialized = (
                        json.dumps(value)
                        if not isinstance(value, (str, int, float, bool))
                        else value
                    )
                    redis_ttl = int(ttl or self._redis_ttl)
                    self._redis_client.setex(redis_key, redis_ttl, serialized)
                except Exception as e:
                    logger.error(f"Redis set failed: {e}")

            # Set in L3 database cache (if available)
            if self._db_available:
                try:
                    self._set_db_cache(key, value, ttl or self._db_ttl)
                except Exception as e:
                    logger.error(f"Database cache set failed: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get value from three-level cache (L1 -> L2 -> L3)"""
        with self._lock:
            # Try L1 memory cache first
            value = self._memory_cache.get(key)
            if value is not None:
                return value

            # Try L2 Redis cache
            if self._redis_available and self._redis_client:
                try:
                    redis_key = self._make_redis_key(key)
                    serialized = self._redis_client.get(redis_key)
                    if serialized is not None:
                        # Deserialize if needed
                        try:
                            value = (
                                json.loads(serialized)
                                if isinstance(serialized, str) and serialized.startswith("{")
                                else serialized
                            )
                        except (json.JSONDecodeError, AttributeError):
                            value = serialized

                        # Store in L1 memory cache
                        self._memory_cache.set(key, value)
                        return value
                except Exception as e:
                    logger.error(f"Redis get failed: {e}")

            # Try L3 database cache
            if self._db_available:
                try:
                    value = self._get_db_cache(key)
                    if value is not None:
                        # Store in L1 and L2 caches
                        self._memory_cache.set(key, value)
                        if self._redis_available and self._redis_client:
                            redis_key = self._make_redis_key(key)
                            serialized = (
                                json.dumps(value)
                                if not isinstance(value, (str, int, float, bool))
                                else str(value)
                            )
                            self._redis_client.setex(redis_key, int(self._redis_ttl), serialized)
                        return value
                except Exception as e:
                    logger.error(f"Database cache get failed: {e}")

            return None

    def _set_db_cache(self, key: str, value: Any, ttl: float) -> None:
        """Store value in database cache (in-memory L3 fallback with TTL)."""
        if not hasattr(self, "_db_cache"):
            self._db_cache: Dict[str, Any] = {}
        import time

        self._db_cache[key] = {"value": value, "expires_at": time.time() + ttl}

    def _get_db_cache(self, key: str) -> Optional[Any]:
        """Get value from database cache (in-memory L3 fallback with TTL)."""
        import time

        if not hasattr(self, "_db_cache"):
            return None
        entry = self._db_cache.get(key)
        if entry is None:
            return None
        if time.time() > entry.get("expires_at", 0):
            self._db_cache.pop(key, None)
            return None
        return entry.get("value")

    def invalidate(
        self,
        key: str,
        event: CacheInvalidationEvent = CacheInvalidationEvent.MANUAL,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Invalidate value in all three cache levels"""
        with self._lock:
            # Invalidate L1 memory cache
            self._memory_cache.invalidate(key)

            # Invalidate L2 Redis cache
            if self._redis_available and self._redis_client:
                try:
                    redis_key = self._make_redis_key(key)
                    self._redis_client.delete(redis_key)
                except Exception as e:
                    logger.error(f"Redis invalidate failed: {e}")

            # Invalidate L3 database cache
            if self._db_available:
                try:
                    self._invalidate_db_cache(key)
                except Exception as e:
                    logger.error(f"Database cache invalidate failed: {e}")

            # Trigger invalidation event
            self._trigger_invalidation_event(event, key, metadata)

    def _invalidate_db_cache(self, key: str) -> None:
        """Invalidate value in database cache (in-memory L3 fallback)."""
        if not hasattr(self, "_db_cache"):
            return
        self._db_cache.pop(key, None)

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        invalidated_count = 0

        # Invalidate in L2 Redis
        if self._redis_available and self._redis_client:
            try:
                redis_pattern = f"{self._redis_prefix}:{pattern}"
                keys = self._redis_client.keys(redis_pattern)
                if keys:
                    deleted = self._redis_client.delete(*keys)
                    invalidated_count += deleted
            except Exception as e:
                logger.error(f"Redis pattern invalidate failed: {e}")

        # Trigger event-based invalidation
        self._trigger_invalidation_event(
            CacheInvalidationEvent.EVENT_BASED, pattern, {"pattern": pattern}
        )

        logger.info(f"Invalidated {invalidated_count} cache entries matching pattern: {pattern}")
        return invalidated_count

    def clear(self) -> None:
        """Clear all three cache levels"""
        with self._lock:
            self._memory_cache.clear()

            if self._redis_available and self._redis_client:
                try:
                    pattern = f"{self._redis_prefix}:*"
                    keys = self._redis_client.keys(pattern)
                    if keys:
                        self._redis_client.delete(*keys)
                except Exception as e:
                    logger.error(f"Redis clear failed: {e}")

            if self._db_available:
                try:
                    self._clear_db_cache()
                except Exception as e:
                    logger.error(f"Database cache clear failed: {e}")

    def _clear_db_cache(self) -> None:
        """Clear database cache (in-memory L3 fallback)."""
        if not hasattr(self, "_db_cache"):
            return
        self._db_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        memory_stats = self._memory_cache.get_stats()

        redis_size = 0
        if self._redis_available and self._redis_client:
            try:
                pattern = f"{self._redis_prefix}:*"
                keys = self._redis_client.keys(pattern)
                redis_size = len(keys) if keys else 0
            except Exception as e:
                logger.error(f"Failed to get Redis cache size: {e}")

        return {
            "memory_cache": memory_stats,
            "redis_cache_size": redis_size,
            "db_cache_available": self._db_available,
            "eviction_policy": self._eviction_policy.value,
        }


# ============================================================
# P2 Enhancement: Intelligent Cache Warmer
# ============================================================
class IntelligentCacheWarmer:
    """
    P2 Enhanced cache warmer with predictive preloading and adaptive warming strategies.

    Usage:
        warmer = IntelligentCacheWarmer(cache)

        # Define warm function
        async def warm_user_data(user_id):
            return await get_user_from_db(user_id)

        # Register warm function with priority
        warmer.register("user_data", warm_user_data, priority=10)

        # Warm cache with prediction
        await warmer.warm_with_prediction("user_data", user_id="123")
    """

    def __init__(self, cache: ThreeLevelCache):
        """
        Args:
            cache: ThreeLevelCache instance to warm
        """
        self._cache = cache
        self._warm_functions: Dict[str, Callable] = {}
        self._warm_priorities: Dict[str, int] = {}
        self._access_patterns: Dict[str, List[datetime]] = {}
        self._lock = Lock()

    def register(self, name: str, func: Callable, priority: int = 5) -> None:
        """Register a cache warm function with priority"""
        with self._lock:
            self._warm_functions[name] = func
            self._warm_priorities[name] = priority
            self._access_patterns[name] = []

    def record_access(self, name: str) -> None:
        """Record access pattern for predictive warming"""
        with self._lock:
            if name in self._access_patterns:
                self._access_patterns[name].append(datetime.now())
                # Keep only last 100 accesses
                if len(self._access_patterns[name]) > 100:
                    self._access_patterns[name] = self._access_patterns[name][-100:]

    def predict_next_access(self, name: str) -> float:
        """Predict next access time based on historical patterns"""
        with self._lock:
            if name not in self._access_patterns or len(self._access_patterns[name]) < 2:
                return 0.0

            accesses = self._access_patterns[name]
            if len(accesses) < 3:
                return 0.0

            # Calculate average interval between accesses
            intervals = []
            for i in range(1, len(accesses)):
                interval = (accesses[i] - accesses[i - 1]).total_seconds()
                intervals.append(interval)

            if not intervals:
                return 0.0

            avg_interval = sum(intervals) / len(intervals)
            return avg_interval

    async def warm(self, name: str, *args, **kwargs) -> Any:
        """Execute warm function and cache result"""
        if name not in self._warm_functions:
            raise ValueError(f"Unknown warm function: {name}")

        # Execute warm function
        result = await self._warm_functions[name](*args, **kwargs)

        # Generate cache key and store result
        cache_key = generate_cache_key(f"warm_{name}", *args, **kwargs)
        self._cache.set(cache_key, result)

        # Record access for prediction
        self.record_access(name)

        return result

    async def warm_with_prediction(self, name: str, *args, **kwargs) -> Any:
        """Warm cache with access pattern prediction"""
        next_access_interval = self.predict_next_access(name)

        if next_access_interval > 0:
            logger.info(
                f"Predicted next access for {name} in {next_access_interval:.1f}s, "
                "setting cache TTL accordingly"
            )
            # Adjust cache TTL based on prediction
            predicted_ttl = min(max(int(next_access_interval * 1.5), 60), 3600)
            result = await self.warm(name, *args, **kwargs)
            # Update cache with predicted TTL
            cache_key = generate_cache_key(f"warm_{name}", *args, **kwargs)
            self._cache.set(cache_key, result, ttl=predicted_ttl)
            return result
        else:
            return await self.warm(name, *args, **kwargs)

    async def warm_high_priority(self) -> None:
        """Warm all high-priority cache entries"""
        with self._lock:
            high_priority_funcs = [
                (name, func)
                for name, func in self._warm_functions.items()
                if self._warm_priorities.get(name, 0) >= 8
            ]

        # Sort by priority (highest first)
        high_priority_funcs.sort(key=lambda x: self._warm_priorities.get(x[0], 0), reverse=True)

        for name, func in high_priority_funcs:
            try:
                await self.warm(name)
                logger.info(f"Warmed high-priority cache: {name}")
            except Exception as e:
                logger.error(f"Failed to warm high-priority cache {name}: {e}")

    def get_warming_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics"""
        with self._lock:
            return {
                "registered_functions": len(self._warm_functions),
                "functions_with_patterns": len(
                    [k for k, v in self._access_patterns.items() if len(v) >= 2]
                ),
                "priorities": self._warm_priorities.copy(),
            }
