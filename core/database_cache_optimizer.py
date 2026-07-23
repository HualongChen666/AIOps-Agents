# -*- coding: utf-8 -*-
"""
Database Cache Optimization
Enterprise-grade database caching with intelligent cache management
"""

import hashlib
import json
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from loguru import logger

__all__ = [
    "CacheStrategy",
    "CacheInvalidationPolicy",
    "CacheEntry",
    "CacheMetrics",
    "DatabaseCacheOptimizer",
    "get_database_cache_optimizer",
]


class CacheStrategy(Enum):
    """Cache strategy"""

    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"


class CacheInvalidationPolicy(Enum):
    """Cache invalidation policy"""

    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    MANUAL = "manual"
    HYBRID = "hybrid"


@dataclass
class CacheEntry:
    """Cache entry"""

    cache_key: str
    data: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        return (datetime.now(timezone.utc) - self.created_at).total_seconds() > self.ttl_seconds

    def touch(self) -> None:
        """Update last accessed time"""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1


@dataclass
class CacheMetrics:
    """Cache metrics"""

    cache_name: str = "default"
    total_entries: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    total_size_bytes: int = 0
    avg_entry_size_bytes: float = 0.0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def hits(self) -> int:
        """Alias for hit_count used by tests."""
        return self.hit_count

    @property
    def misses(self) -> int:
        """Alias for miss_count used by tests."""
        return self.miss_count


class _Cache:
    """Simple per-name cache used by DatabaseCacheOptimizer.get_cache."""

    def __init__(self, name: str, strategy: CacheStrategy = CacheStrategy.LRU, size: int = 1000):
        self.name = name
        self.strategy = strategy
        self.size = size
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._frequency: Dict[str, int] = {}

    def _evict_if_needed(self) -> None:
        if len(self.cache) < self.size:
            return
        if self.strategy == CacheStrategy.LRU:
            oldest = next(iter(self.cache))
            self.cache.pop(oldest)
            self._frequency.pop(oldest, None)
        elif self.strategy == CacheStrategy.LFU:
            min_freq = min(self._frequency.values()) if self._frequency else 0
            for key in list(self.cache.keys()):
                if self._frequency.get(key, 0) == min_freq:
                    self.cache.pop(key)
                    self._frequency.pop(key, None)
                    break
        else:
            oldest = next(iter(self.cache))
            self.cache.pop(oldest)
            self._frequency.pop(oldest, None)

    def set(self, key: str, value: Any) -> None:
        if key not in self.cache:
            self._evict_if_needed()
        self.cache[key] = value
        self._frequency[key] = self._frequency.get(key, 0) + 1
        if self.strategy == CacheStrategy.LRU:
            self.cache.move_to_end(key)

    def get(self, key: str) -> Any:
        if key in self.cache:
            value = self.cache[key]
            self.hits += 1
            self._frequency[key] = self._frequency.get(key, 0) + 1
            if self.strategy == CacheStrategy.LRU:
                self.cache.move_to_end(key)
            return value
        self.misses += 1
        return None

    def invalidate(self, key: str) -> None:
        self.cache.pop(key, None)
        self._frequency.pop(key, None)

    def clear(self) -> None:
        self.cache.clear()
        self._frequency.clear()

    def get_stats(self) -> Dict[str, int]:
        return {"hits": self.hits, "misses": self.misses}


class DatabaseCacheOptimizer:
    """Enterprise-grade database cache optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize database cache optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Cache storage
        self.caches: Dict[str, OrderedDict] = {}

        # Cache configurations
        self.cache_configs: Dict[str, Dict[str, Any]] = {}

        # Cache metrics
        self.cache_metrics: Dict[str, CacheMetrics] = {}

        # Default configuration
        self.default_cache_size = self.config.get("default_cache_size", 1000)
        self.default_ttl_seconds = self.config.get("default_ttl_seconds", 3600)
        self.default_strategy = CacheStrategy.LRU

        # Preload configurations
        self.preload_queries: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Statistics
        self.total_cache_hits = 0
        self.total_cache_misses = 0

        # Per-name caches returned by get_cache()
        self._cache_objects: Dict[str, _Cache] = {}

        logger.info("Database cache optimizer initialized")

    def get_cache(
        self,
        cache_name: str,
        strategy: Optional[CacheStrategy] = None,
        size: Optional[int] = None,
    ) -> _Cache:
        """Get or create a simple cache by name."""
        if cache_name in self._cache_objects:
            return self._cache_objects[cache_name]

        strat = strategy or self.default_strategy
        cache_size = size or self.default_cache_size
        cache = _Cache(cache_name, strategy=strat, size=cache_size)
        self._cache_objects[cache_name] = cache
        return cache

    def get_stats(self) -> Dict[str, Any]:
        """Get overall cache statistics."""
        return self.get_statistics()

    def create_cache(
        self,
        cache_name: str,
        cache_size: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.LRU,
        ttl_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create cache

        Args:
            cache_name: Cache name
            cache_size: Maximum cache size
            strategy: Cache strategy
            ttl_seconds: Default TTL in seconds
            metadata: Additional metadata
        """
        if cache_name in self.caches:
            logger.warning(f"Cache {cache_name} already exists")
            return

        cache_size = cache_size or self.default_cache_size

        self.caches[cache_name] = OrderedDict()
        self.cache_configs[cache_name] = {
            "name": cache_name,
            "size": cache_size,
            "strategy": strategy,
            "ttl_seconds": ttl_seconds or self.default_ttl_seconds,
            "created_at": datetime.now(timezone.utc),
            "metadata": metadata or {},
        }
        self.cache_metrics[cache_name] = CacheMetrics(cache_name=cache_name)

        logger.info(f"Created cache: {cache_name} (size: {cache_size}, strategy: {strategy})")

    def _generate_cache_key(
        self, cache_name: str, query: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate cache key

        Args:
            cache_name: Cache name
            query: SQL query
            params: Query parameters

        Returns:
            Cache key
        """
        key_string = f"{cache_name}:{query}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()

    def get(
        self, cache_name: str, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get data from cache

        Args:
            cache_name: Cache name
            query: SQL query
            params: Query parameters

        Returns:
            Cached data or None
        """
        if cache_name not in self.caches:
            return None

        cache = self.caches[cache_name]
        cache_key = self._generate_cache_key(cache_name, query, params)

        if cache_key in cache:
            entry = cache[cache_key]

            # Check expiration
            if entry.is_expired():
                self._evict(cache_name, cache_key, reason="expired")
                self.total_cache_misses += 1
                self._update_metrics(cache_name, hit=False)
                return None

            # Update access time for LRU/LFU
            entry.touch()

            # Move to end for LRU
            if self.cache_configs[cache_name]["strategy"] == CacheStrategy.LRU:
                cache.move_to_end(cache_key)

            self.total_cache_hits += 1
            self._update_metrics(cache_name, hit=True)
            logger.debug(f"Cache hit: {cache_name}")
            return entry.data

        self.total_cache_misses += 1
        self._update_metrics(cache_name, hit=False)
        logger.debug(f"Cache miss: {cache_name}")
        return None

    def set(
        self,
        cache_name: str,
        query: str,
        data: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """
        Set data in cache

        Args:
            cache_name: Cache name
            query: SQL query
            data: Data to cache
            params: Query parameters
            ttl_seconds: TTL in seconds
        """
        if cache_name not in self.caches:
            logger.warning(f"Cache {cache_name} not found")
            return

        cache = self.caches[cache_name]
        config = self.cache_configs[cache_name]
        cache_key = self._generate_cache_key(cache_name, query, params)
        ttl = ttl_seconds or config["ttl_seconds"]

        # Calculate data size
        data_size = len(json.dumps(data, default=str).encode())

        # Check cache size and evict if necessary
        if len(cache) >= config["size"] and cache_key not in cache:
            self._evict_oldest(cache_name)

        # Create cache entry
        entry = CacheEntry(
            cache_key=cache_key, data=data, ttl_seconds=ttl, metadata={"size_bytes": data_size}
        )

        cache[cache_key] = entry
        self._update_metrics(cache_name)

        logger.debug(f"Cached data: {cache_name} (key: {cache_key})")

    def invalidate(
        self, cache_name: str, query: Optional[str] = None, params: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Invalidate cache entries

        Args:
            cache_name: Cache name
            query: SQL query (None to invalidate all)
            params: Query parameters

        Returns:
            Number of entries invalidated
        """
        if cache_name not in self.caches:
            return 0

        cache = self.caches[cache_name]

        if query is None:
            # Invalidate all
            count = len(cache)
            cache.clear()
            logger.info(f"Invalidated all entries in cache: {cache_name}")
            return count

        cache_key = self._generate_cache_key(cache_name, query, params)

        if cache_key in cache:
            self._evict(cache_name, cache_key, reason="manual_invalidation")
            logger.info(f"Invalidated entry: {cache_name} (key: {cache_key})")
            return 1

        return 0

    def _evict(self, cache_name: str, cache_key: str, reason: str = "eviction") -> None:
        """
        Evict cache entry

        Args:
            cache_name: Cache name
            cache_key: Cache key
            reason: Eviction reason
        """
        if cache_name not in self.caches:
            return

        cache = self.caches[cache_name]

        if cache_key in cache:
            del cache[cache_key]
            self.cache_metrics[cache_name].eviction_count += 1
            logger.debug(f"Evicted entry: {cache_name} (key: {cache_key}, reason: {reason})")

    def _evict_oldest(self, cache_name: str) -> None:
        """
        Evict oldest cache entry based on strategy

        Args:
            cache_name: Cache name
        """
        if cache_name not in self.caches:
            return

        cache = self.caches[cache_name]
        strategy = self.cache_configs[cache_name]["strategy"]

        if not cache:
            return

        if strategy == CacheStrategy.LRU:
            # Evict least recently used (first item in OrderedDict)
            oldest_key = next(iter(cache))
            self._evict(cache_name, oldest_key, reason="lru_eviction")

        elif strategy == CacheStrategy.LFU:
            # Evict least frequently used
            min_access = min(entry.access_count for entry in cache.values())
            for cache_key, entry in list(cache.items()):
                if entry.access_count == min_access:
                    self._evict(cache_name, cache_key, reason="lfu_eviction")
                    break

        elif strategy == CacheStrategy.TTL:
            # Evict expired entries
            expired_keys = [cache_key for cache_key, entry in cache.items() if entry.is_expired()]
            for cache_key in expired_keys:
                self._evict(cache_name, cache_key, reason="ttl_eviction")

            # If no expired entries, evict oldest
            if not expired_keys:
                oldest_key = next(iter(cache))
                self._evict(cache_name, oldest_key, reason="ttl_oldest_eviction")

    def _update_metrics(self, cache_name: str, hit: Optional[bool] = None) -> None:
        """
        Update cache metrics

        Args:
            cache_name: Cache name
            hit: Cache hit or miss
        """
        if cache_name not in self.cache_metrics:
            return

        metrics = self.cache_metrics[cache_name]
        cache = self.caches[cache_name]

        metrics.total_entries = len(cache)

        if hit is not None:
            if hit:
                metrics.hit_count += 1
            else:
                metrics.miss_count += 1

        total_requests = metrics.hit_count + metrics.miss_count
        metrics.hit_rate = metrics.hit_count / total_requests if total_requests > 0 else 0
        metrics.miss_rate = metrics.miss_count / total_requests if total_requests > 0 else 0

        # Calculate total size
        total_size = sum(entry.metadata.get("size_bytes", 0) for entry in cache.values())
        metrics.total_size_bytes = total_size
        metrics.avg_entry_size_bytes = total_size / len(cache) if cache else 0

        metrics.last_updated = datetime.now(timezone.utc)

    def add_preload_query(
        self,
        cache_name: str,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> None:
        """
        Add query to preload list

        Args:
            cache_name: Cache name
            query: SQL query
            params: Query parameters
            priority: Priority (higher = loaded first)
        """
        self.preload_queries[cache_name].append(
            {
                "query": query,
                "params": params,
                "priority": priority,
                "added_at": datetime.now(timezone.utc),
            }
        )

        logger.info(f"Added preload query to cache: {cache_name}")

    def preload_cache(
        self,
        cache_name: str,
        data_loader: Union[Callable[[str, Dict[str, Any]], Any], Dict[str, Any]],
    ) -> int:
        """
        Preload cache with data.

        Args:
            cache_name: Cache name
            data_loader: Function to load data, or a dict of preloaded key/value pairs

        Returns:
            Number of entries preloaded
        """
        cache = self.get_cache(cache_name)

        if isinstance(data_loader, dict):
            for key, value in data_loader.items():
                cache.set(str(key), value)
            return len(data_loader)

        if cache_name not in self.caches:
            return 0

        queries = self.preload_queries[cache_name]

        # Sort by priority
        queries.sort(key=lambda x: x["priority"], reverse=True)

        loaded_count = 0
        for query_info in queries:
            try:
                data = data_loader(query_info["query"], query_info["params"] or {})
                self.set(cache_name, query_info["query"], data, query_info["params"])
                loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to preload query: {e}")

        logger.info(f"Preloaded {loaded_count} entries in cache: {cache_name}")

        return loaded_count

    def cleanup_expired_entries(self, cache_name: str) -> int:
        """
        Clean up expired cache entries

        Args:
            cache_name: Cache name

        Returns:
            Number of entries cleaned up
        """
        if cache_name not in self.caches:
            return 0

        cache = self.caches[cache_name]

        expired_keys = [cache_key for cache_key, entry in cache.items() if entry.is_expired()]

        for cache_key in expired_keys:
            self._evict(cache_name, cache_key, reason="expired_cleanup")

        logger.info(f"Cleaned up {len(expired_keys)} expired entries in cache: {cache_name}")

        return len(expired_keys)

    def get_cache_metrics(self, cache_name: str) -> Optional[CacheMetrics]:
        """
        Get cache metrics

        Args:
            cache_name: Cache name

        Returns:
            Cache metrics or None
        """
        if cache_name not in self.cache_metrics:
            return None

        self._update_metrics(cache_name)
        return self.cache_metrics[cache_name]

    def get_all_cache_metrics(self) -> Dict[str, CacheMetrics]:
        """Get all cache metrics"""
        for cache_name in self.caches:
            self._update_metrics(cache_name)
        return self.cache_metrics.copy()

    def optimize_cache_size(self, cache_name: str, target_hit_rate: float = 0.8) -> Dict[str, Any]:
        """
        Analyze cache usage and recommend optimal size

        Args:
            cache_name: Cache name
            target_hit_rate: Target hit rate

        Returns:
            Optimization recommendations
        """
        if cache_name not in self.cache_metrics:
            return {"error": "Cache not found"}

        metrics = self.get_cache_metrics(cache_name)
        config = self.cache_configs[cache_name]

        current_size = config["size"]
        if metrics is None:
            return {"error": "Unable to retrieve cache metrics"}
        current_hit_rate = metrics.hit_rate

        recommendations = []

        if current_hit_rate < target_hit_rate:
            # Hit rate too low, increase cache size
            recommended_size = int(current_size * 1.5)
            recommendations.append(
                {
                    "type": "increase_size",
                    "reason": f"Hit rate ({  # noqa: E501
                        current_hit_rate:.2%}) below target ({target_hit_rate:.2%})",
                    "current_size": current_size,
                    "recommended_size": recommended_size,
                    "expected_hit_rate": min(target_hit_rate, current_hit_rate + 0.15),
                }
            )
        elif current_hit_rate > target_hit_rate + 0.1:
            # Hit rate very high, could reduce cache size
            recommended_size = int(current_size * 0.8)
            recommendations.append(
                {
                    "type": "decrease_size",
                    "reason": (
                        f"Hit rate ({current_hit_rate:.2%}) significantly above target "
                        f"({target_hit_rate:.2%})"
                    ),
                    "current_size": current_size,
                    "recommended_size": max(recommended_size, 100),
                    "expected_hit_rate": max(target_hit_rate, current_hit_rate - 0.05),
                }
            )
        else:
            recommendations.append(
                {
                    "type": "no_change",
                    "reason": f"Hit rate ({current_hit_rate:.2%}) is optimal",
                    "current_size": current_size,
                    "recommended_size": current_size,
                    "expected_hit_rate": current_hit_rate,
                }
            )

        return {
            "cache_name": cache_name,
            "current_metrics": {
                "hit_rate": current_hit_rate,
                "miss_rate": metrics.miss_rate,
                "total_entries": metrics.total_entries,
                "total_size_bytes": metrics.total_size_bytes,
            },
            "recommendations": recommendations,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache optimizer statistics"""
        return {
            "total_caches": len(self.caches),
            "total_cache_hits": self.total_cache_hits,
            "total_cache_misses": self.total_cache_misses,
            "global_hit_rate": (
                self.total_cache_hits / (self.total_cache_hits + self.total_cache_misses)
                if (self.total_cache_hits + self.total_cache_misses) > 0
                else 0
            ),
            "total_preload_queries": sum(len(queries) for queries in self.preload_queries.values()),
        }


def get_database_cache_optimizer(config: Optional[Dict[str, Any]] = None) -> DatabaseCacheOptimizer:
    """
    Factory function to get database cache optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        DatabaseCacheOptimizer: Cache optimizer instance
    """
    return DatabaseCacheOptimizer(config)
