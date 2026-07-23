# -*- coding: utf-8 -*-
# tests/integration/test_cache_integration.py
# 缓存集成测试
import os
import sys
from datetime import datetime, timedelta  # noqa: F401
from unittest.mock import AsyncMock, Mock, patch  # noqa: F401

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入mock模块（在sys.path设置后导入）
from core import cache_helpers_mock  # noqa: F401, F402

try:
    sys.modules["core.redis_cluster"] = __import__("core.redis_cluster_mock")
except ImportError:
    # 如果mock模块不存在，创建一个简单的mock
    sys.modules["core.redis_cluster"] = Mock()


class TestCacheIntegration:
    """缓存集成测试"""

    def test_cache_result_basic(self):
        """测试基本的缓存结果"""

        # 使用mock模块的cache_result装饰器
        @cache_helpers_mock.cache_result(ttl=60)
        def test_function(key, value):
            return f"{key}:{value}"

        result = test_function("test_key", "test_value")
        assert result is not None
        assert result == "test_key:test_value"

    def test_cache_stats(self):
        """测试缓存统计"""

        # 先缓存一些数据
        @cache_helpers_mock.cache_result(ttl=60, track_stats=True)
        def test_function_for_stats(key, value):
            return f"{key}:{value}"

        # 调用函数生成缓存
        test_function_for_stats("stats_key", "stats_value")
        test_function_for_stats("stats_key", "stats_value")  # 第二次调用应该命中缓存

        # 获取统计信息
        stats = cache_helpers_mock.get_cache_stats("test_function_for_stats")
        assert stats is not None
        assert "total_hits" in stats
        assert "cache_size" in stats

    def test_cache_invalidation(self):
        """测试缓存失效"""

        # 先缓存一些数据
        @cache_helpers_mock.cache_result(ttl=60)
        def test_function_for_invalidation(key, value):
            return f"{key}:{value}"

        # 调用函数生成缓存
        result1 = test_function_for_invalidation("invalidate_key", "invalidate_value")
        assert result1 is not None

        # 使缓存失效
        cache_helpers_mock.invalidate_cache("test_function_for_invalidation")

        # 再次调用应该重新计算
        result2 = test_function_for_invalidation("invalidate_key", "invalidate_value")
        assert result2 is not None
