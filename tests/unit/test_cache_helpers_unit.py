# -*- coding: utf-8 -*-
# tests/unit/test_cache_helpers_unit.py
# Cache Helpers模块单元测试
import time  # noqa: F401

import pytest  # noqa: F401


class TestCacheStatistics:
    """测试缓存统计"""

    def test_cache_statistics_initialization(self):
        """测试缓存统计初始化"""
        from core.cache_helpers import CacheStatistics

        stats = CacheStatistics()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 0
        assert stats.max_size == 0

    def test_cache_statistics_record_hit(self):
        """测试记录缓存命中"""
        from core.cache_helpers import CacheStatistics

        stats = CacheStatistics()
        stats.record_hit()

        assert stats.hits == 1
        assert stats.misses == 0

    def test_cache_statistics_record_miss(self):
        """测试记录缓存未命中"""
        from core.cache_helpers import CacheStatistics

        stats = CacheStatistics()
        stats.record_miss()

        assert stats.hits == 0
        assert stats.misses == 1

    def test_cache_statistics_record_eviction(self):
        """测试记录缓存驱逐"""
        from core.cache_helpers import CacheStatistics

        stats = CacheStatistics()
        stats.record_eviction()

        assert stats.evictions == 1

    def test_cache_statistics_get_hit_rate(self):
        """测试获取缓存命中率"""
        from core.cache_helpers import CacheStatistics

        stats = CacheStatistics()

        # 没有任何请求时
        assert stats.get_hit_rate() == 0.0

        # 有请求但都是未命中
        stats.record_miss()
        assert stats.get_hit_rate() == 0.0

        # 有命中
        stats.record_hit()
        assert stats.get_hit_rate() == 50.0  # 返回百分比

        # 更多命中
        stats.record_hit()
        assert stats.get_hit_rate() == 66.66666666666666  # 返回百分比
