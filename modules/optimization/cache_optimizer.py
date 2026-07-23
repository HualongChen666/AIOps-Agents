# -*- coding: utf-8 -*-
"""
cache_optimizer.py
------------------
性能优化 - 缓存优化模块。

功能：
- 缓存策略管理
- 缓存命中率分析
- 缓存预热
- 缓存失效策略
- 分布式缓存管理
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 缓存策略枚举
# ----------------------------------------------------------------------
class CacheStrategy(Enum):
    """缓存策略"""

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最不经常使用
    FIFO = "fifo"  # 先进先出
    TTL = "ttl"  # 生存时间
    WRITE_THROUGH = "write_through"  # 写穿透
    WRITE_BACK = "write_back"  # 写回
    WRITE_AROUND = "write_around"  # 写绕过


# ----------------------------------------------------------------------
# 2️⃣ 缓存条目
# ----------------------------------------------------------------------
@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[int] = None  # 秒
    size: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)

    def touch(self):
        """更新访问时间"""
        self.last_accessed = datetime.now()
        self.access_count += 1


# ----------------------------------------------------------------------
# 3️⃣ 缓存统计
# ----------------------------------------------------------------------
@dataclass
class CacheStatistics:
    """缓存统计"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """未命中率"""
        return 1.0 - self.hit_rate

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
        }


# ----------------------------------------------------------------------
# 4️⃣ 缓存管理器
# ----------------------------------------------------------------------
class CacheManager:
    """缓存管理器"""

    def __init__(
        self,
        max_size: int = 1000,
        strategy: CacheStrategy = CacheStrategy.LRU,
        default_ttl: Optional[int] = None,
    ):
        """
        Parameters
        ----------
        max_size : int
            最大缓存大小
        strategy : CacheStrategy
            缓存策略
        default_ttl : int, optional
            默认 TTL（秒）
        """
        self.max_size = max_size
        self.strategy = strategy
        self.default_ttl = default_ttl

        self.cache: Dict[str, CacheEntry] = {}
        self.statistics = CacheStatistics(max_size=max_size)

        # 加载器函数
        self.loaders: Dict[str, Callable] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Parameters
        ----------
        key : str
            键

        Returns
        -------
        Any or None
            缓存值
        """
        entry = self.cache.get(key)

        if entry is None:
            self.statistics.misses += 1
            return None

        if entry.is_expired():
            self.delete(key)
            self.statistics.misses += 1
            return None

        entry.touch()
        self.statistics.hits += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ):
        """
        设置缓存值

        Parameters
        ----------
        key : str
            键
        value : Any
            值
        ttl : int, optional
            TTL（秒）
        """
        # 检查是否需要淘汰
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict()

        # 计算大小（简化）
        size = len(str(value))

        entry = CacheEntry(
            key=key,
            value=value,
            ttl=ttl or self.default_ttl,
            size=size,
        )

        self.cache[key] = entry
        self.statistics.size = len(self.cache)

    def delete(self, key: str):
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            self.statistics.size = len(self.cache)

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.statistics.size = 0

    def _evict(self):
        """淘汰缓存条目"""
        if not self.cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # 淘汰最近最少使用的
            key_to_evict = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].last_accessed,
            )
        elif self.strategy == CacheStrategy.LFU:
            # 淘汰最不经常使用的
            key_to_evict = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].access_count,
            )
        elif self.strategy == CacheStrategy.FIFO:
            # 淘汰最早创建的
            key_to_evict = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].created_at,
            )
        elif self.strategy == CacheStrategy.TTL:
            # 淘汰已过期的
            for key, entry in self.cache.items():
                if entry.is_expired():
                    key_to_evict = key
                    break
            else:
                # 没有过期的，使用 LRU
                key_to_evict = min(
                    self.cache.keys(),
                    key=lambda k: self.cache[k].last_accessed,
                )
        else:
            # 默认 LRU
            key_to_evict = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].last_accessed,
            )

        self.delete(key_to_evict)
        self.statistics.evictions += 1

    def register_loader(self, key_pattern: str, loader: Callable):
        """
        注册加载器

        Parameters
        ----------
        key_pattern : str
            键模式
        loader : Callable
            加载函数
        """
        self.loaders[key_pattern] = loader

    def get_or_load(self, key: str) -> Any:
        """
        获取或加载缓存值

        Parameters
        ----------
        key : str
            键

        Returns
        -------
        Any
            缓存值
        """
        value = self.get(key)

        if value is not None:
            return value

        # 查找匹配的加载器
        for pattern, loader in self.loaders.items():
            if pattern in key or key in pattern:
                value = loader(key)
                if value is not None:
                    self.set(key, value)
                return value

        return None

    def get_statistics(self) -> CacheStatistics:
        """获取统计信息"""
        return self.statistics

    def warm_up(self, keys: List[str]):
        """
        缓存预热

        Parameters
        ----------
        keys : List[str]
            要预热的键列表
        """
        for key in keys:
            self.get_or_load(key)

        logger.info(f"Cache warm-up completed for {len(keys)} keys")


# ----------------------------------------------------------------------
# 5️⃣ 缓存优化器
# ----------------------------------------------------------------------
class CacheOptimizer:
    """缓存优化器"""

    def __init__(self, cache_manager: CacheManager):
        """
        Parameters
        ----------
        cache_manager : CacheManager
            缓存管理器
        """
        self.cache_manager = cache_manager
        self.access_patterns: Dict[str, List[datetime]] = {}

    def record_access(self, key: str):
        """记录访问"""
        if key not in self.access_patterns:
            self.access_patterns[key] = []
        self.access_patterns[key].append(datetime.now())

    def analyze_access_patterns(self) -> Dict[str, Any]:
        """分析访问模式"""
        analysis = {}

        for key, timestamps in self.access_patterns.items():
            if len(timestamps) < 2:
                continue

            # 计算访问频率
            duration = (timestamps[-1] - timestamps[0]).total_seconds()
            frequency = len(timestamps) / duration if duration > 0 else 0

            analysis[key] = {
                "access_count": len(timestamps),
                "frequency": frequency,
                "first_access": timestamps[0].isoformat(),
                "last_access": timestamps[-1].isoformat(),
            }

        return analysis

    def suggest_ttl(self, key: str) -> Optional[int]:
        """
        建议 TTL

        Parameters
        ----------
        key : str
            键

        Returns
        -------
        int or None
            建议的 TTL（秒）
        """
        if key not in self.access_patterns or len(self.access_patterns[key]) < 2:
            return None

        timestamps = self.access_patterns[key]

        # 计算访问间隔
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds()
            intervals.append(interval)

        if not intervals:
            return None

        # 使用平均间隔的 2 倍作为 TTL
        avg_interval = sum(intervals) / len(intervals)
        suggested_ttl = int(avg_interval * 2)

        return max(60, min(3600, suggested_ttl))  # 限制在 1 分钟到 1 小时之间

    def optimize_cache(self):
        """优化缓存"""
        stats = self.cache_manager.get_statistics()

        if stats.hit_rate < 0.5:
            logger.warning(f"Low cache hit rate: {stats.hit_rate:.2%}")
            logger.info("Consider increasing cache size or adjusting TTL")

        if stats.evictions > stats.size * 0.1:
            logger.warning(f"High eviction rate: {stats.evictions}")
            logger.info("Consider increasing cache size")

        # 为频繁访问的键建议 TTL
        patterns = self.analyze_access_patterns()
        for key, pattern in patterns.items():
            if pattern["frequency"] > 0.1:  # 每秒访问超过 0.1 次
                suggested_ttl = self.suggest_ttl(key)
                if suggested_ttl:
                    logger.info(f"Suggested TTL for {key}: {suggested_ttl}s")


# ----------------------------------------------------------------------
# 6️⃣ 分布式缓存管理器
# ----------------------------------------------------------------------
class DistributedCacheManager:
    """分布式缓存管理器"""

    def __init__(self):
        self.local_caches: Dict[str, CacheManager] = {}
        self.consistency_mode = "eventual"  # "strong", "eventual"

    def add_local_cache(self, node_id: str, cache: CacheManager):
        """添加本地缓存"""
        self.local_caches[node_id] = cache
        logger.info(f"Added local cache for node: {node_id}")

    def get(self, key: str, node_id: Optional[str] = None) -> Optional[Any]:
        """
        获取缓存值

        Parameters
        ----------
        key : str
            键
        node_id : str, optional
            节点 ID

        Returns
        -------
        Any or None
            缓存值
        """
        if node_id and node_id in self.local_caches:
            return self.local_caches[node_id].get(key)

        # 从所有节点获取
        for cache in self.local_caches.values():
            value = cache.get(key)
            if value is not None:
                return value

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置缓存值（所有节点）

        Parameters
        ----------
        key : str
            键
        value : Any
            值
        ttl : int, optional
            TTL
        """
        for cache in self.local_caches.values():
            cache.set(key, value, ttl)

    def invalidate(self, key: str):
        """使缓存失效（所有节点）"""
        for cache in self.local_caches.values():
            cache.delete(key)
        logger.info(f"Invalidated key: {key}")

    def get_global_statistics(self) -> Dict[str, CacheStatistics]:
        """获取全局统计"""
        return {node_id: cache.get_statistics() for node_id, cache in self.local_caches.items()}


# ----------------------------------------------------------------------
# 7️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_cache_manager(
    max_size: int = 1000,
    strategy: CacheStrategy = CacheStrategy.LRU,
) -> CacheManager:
    """创建缓存管理器"""
    return CacheManager(max_size=max_size, strategy=strategy)


def create_cache_optimizer(cache_manager: CacheManager) -> CacheOptimizer:
    """创建缓存优化器"""
    return CacheOptimizer(cache_manager)


def create_distributed_cache_manager() -> DistributedCacheManager:
    """创建分布式缓存管理器"""
    return DistributedCacheManager()


# ----------------------------------------------------------------------
# 8️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试缓存管理器
    logger.info("Testing cache manager")

    cache = create_cache_manager(max_size=100, strategy=CacheStrategy.LRU)

    # 设置缓存
    cache.set("key1", "value1", ttl=60)
    cache.set("key2", "value2")

    # 获取缓存
    value1 = cache.get("key1")
    value3 = cache.get("key3")  # 不存在

    logger.info(f"key1: {value1}")
    logger.info(f"key3: {value3}")

    # 获取统计
    stats = cache.get_statistics()
    logger.info(f"Cache statistics: {stats.to_dict()}")

    # 测试缓存优化器
    logger.info("Testing cache optimizer")

    optimizer = create_cache_optimizer(cache)

    # 记录访问
    for _ in range(10):
        optimizer.record_access("key1")

    # 分析访问模式
    patterns = optimizer.analyze_access_patterns()
    logger.info(f"Access patterns: {patterns}")

    # 建议 TTL
    suggested_ttl = optimizer.suggest_ttl("key1")
    logger.info(f"Suggested TTL for key1: {suggested_ttl}")

    # 优化缓存
    optimizer.optimize_cache()

    logger.info("Test passed!")
