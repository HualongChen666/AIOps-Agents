# -*- coding: utf-8 -*-
"""
性能优化组件
Performance Optimization Components

提供分片管理、延迟计算、缓存验证等性能优化组件。
"""

import threading
import time
from collections import defaultdict
from typing import Dict, Any
from loguru import logger
from .stats import WelfordStats


class ShardedStatsManager:
    """
    分片统计管理器

    使用分片技术减少锁竞争，提高并发性能。
    """

    def __init__(self, num_shards: int = 4):
        """
        初始化分片管理器

        Args:
            num_shards: 分片数量
        """
        self.num_shards = num_shards
        self._shards = [threading.RLock() for _ in range(num_shards)]
        self._baselines = [defaultdict(dict) for _ in range(num_shards)]

    def _get_shard(self, agent_id: str) -> int:
        """
        基于agent_id哈希选择分片

        Args:
            agent_id: agent ID

        Returns:
            分片索引
        """
        return hash(agent_id) % self.num_shards

    def get_or_create(self, agent_id: str, metric_name: str) -> WelfordStats:
        """
        获取或创建统计基线

        Args:
            agent_id: agent ID
            metric_name: 指标名称

        Returns:
            WelfordStats对象
        """
        shard_idx = self._get_shard(agent_id)
        with self._shards[shard_idx]:  # 只锁住一个分片
            shard_data = self._baselines[shard_idx]

            if agent_id not in shard_data:
                shard_data[agent_id] = {}

            if metric_name not in shard_data[agent_id]:
                shard_data[agent_id][metric_name] = WelfordStats()

            return shard_data[agent_id][metric_name]


class LazyWelfordStats:
    """
    延迟计算的Welford统计

    按需计算统计量，避免不必要的计算开销。
    """

    def __init__(self):
        """初始化延迟统计"""
        self._welford = WelfordStats()
        self._dirty = True  # 脏标记
        self._cached_mean = None
        self._cached_std = None

    def update(self, value: float) -> None:
        """
        更新统计量（标记为脏）

        Args:
            value: 新的观测值
        """
        self._welford.update(value)
        self._dirty = True

    def _ensure_calculated(self) -> None:
        """按需计算统计量"""
        if self._dirty:
            self._cached_mean = self._welford.get_mean()
            self._cached_std = self._welford.get_std()
            self._dirty = False

    def get_mean(self) -> float:
        """获取均值"""
        self._ensure_calculated()
        return self._cached_mean if self._cached_mean is not None else 0.0

    def get_std(self) -> float:
        """获取标准差"""
        self._ensure_calculated()
        return self._cached_std if self._cached_std is not None else 0.0

    def z_score(self, value: float) -> float:
        """计算z-score"""
        self._ensure_calculated()
        std = self._cached_std if self._cached_std is not None else 0.0
        mean = self._cached_mean if self._cached_mean is not None else 0.0
        return (value - mean) / std if std > 0 else 0.0


class CachedConfigValidator:
    """
    缓存验证结果

    缓存配置验证结果，避免重复验证。
    """

    def __init__(self, cache_ttl: int = 300):
        """
        初始化缓存验证器

        Args:
            cache_ttl: 缓存生存时间（秒）
        """
        self._validation_cache: Dict[str, Any] = {}
        self._last_validation_time = 0
        self._cache_ttl = cache_ttl

    def validate_with_cache(self, config, validator_func) -> tuple:
        """
        带缓存的验证

        Args:
            config: 配置对象
            validator_func: 验证函数

        Returns:
            验证结果
        """
        now = time.time()
        cache_key = self._make_cache_key(config)

        # 缓存命中
        if cache_key in self._validation_cache:
            if now - self._last_validation_time < self._cache_ttl:
                logger.debug("配置验证缓存命中")
                return self._validation_cache[cache_key]

        # 执行验证
        result = validator_func(config)
        self._validation_cache[cache_key] = result
        self._last_validation_time = now
        logger.debug("配置验证缓存未命中，执行验证")
        return result

    def _make_cache_key(self, config) -> str:
        """
        生成缓存键

        Args:
            config: 配置对象

        Returns:
            缓存键字符串
        """
        # 简化：使用配置的关键属性生成键
        return f"{config.max_agents}_{config.ttl_days}_{config.min_samples_for_z_score}"

    def clear_cache(self) -> None:
        """清除缓存"""
        self._validation_cache.clear()
        logger.debug("配置验证缓存已清除")
