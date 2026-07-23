# -*- coding: utf-8 -*-
# tests/unit/test_caching_strategy_unit.py
# Caching Strategy模块单元测试
import pytest  # noqa: F401


class TestConfigureCachingStrategy:
    """测试缓存策略配置"""

    def test_configure_caching_strategy_defaults(self):
        """测试缓存策略配置默认值"""
        from core.caching_strategy import _cache_config, configure_caching_strategy

        configure_caching_strategy()

        assert _cache_config["default_ttl_seconds"] == 300
        assert _cache_config["max_size"] == 10000
        assert _cache_config["cache_backend"] == "memory"
        assert _cache_config["cache_key_prefix"] == "aiops"

    def test_configure_caching_strategy_custom(self):
        """测试缓存策略配置自定义值"""
        from core.caching_strategy import _cache_config, configure_caching_strategy

        configure_caching_strategy(
            default_ttl_seconds=600,
            max_size=20000,
            cache_backend="redis",
            cache_key_prefix="custom",
        )

        assert _cache_config["default_ttl_seconds"] == 600
        assert _cache_config["max_size"] == 20000
        assert _cache_config["cache_backend"] == "redis"
        assert _cache_config["cache_key_prefix"] == "custom"


class TestCacheKeyGeneration:
    """测试缓存键生成"""

    def test_generate_cache_key_string(self):
        """测试生成缓存键字符串"""
        from core.caching_strategy import generate_cache_key

        key = generate_cache_key("test_key", {"param1": "value1"})

        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_cache_key_consistency(self):
        """测试缓存键生成一致性"""
        from core.caching_strategy import generate_cache_key

        key1 = generate_cache_key("test_key", {"param1": "value1"})
        key2 = generate_cache_key("test_key", {"param1": "value1"})

        assert key1 == key2

    def test_generate_cache_key_uniqueness(self):
        """测试缓存键生成唯一性"""
        from core.caching_strategy import generate_cache_key

        key1 = generate_cache_key("test_key", {"param1": "value1"})
        key2 = generate_cache_key("test_key", {"param1": "value2"})

        assert key1 != key2
