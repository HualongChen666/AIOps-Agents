# -*- coding: utf-8 -*-
# tests/test_caching_strategy.py
# 缓存策略单元测试
import pytest

from core.caching_strategy import (
    cache_decorator,
    clear_cache,
    configure_caching_strategy,
    delete_cache,
    generate_cache_key,
    get_cache,
    get_cache_config,
    get_cache_info,
    get_cache_statistics,
    invalidate_pattern,
    is_caching_enabled,
    reset_cache_statistics,
    set_cache,
)


class TestCachingConfiguration:
    """缓存配置测试"""

    def test_configure_caching_strategy(self):
        """测试配置缓存策略"""
        configure_caching_strategy(
            default_ttl_seconds=600,
            max_size=5000,
            cache_backend="redis",
            cache_key_prefix="test",
        )

        assert is_caching_enabled() is True
        config = get_cache_config()
        assert config["default_ttl_seconds"] == 600
        assert config["max_size"] == 5000
        assert config["cache_backend"] == "redis"

    def test_get_cache_config(self):
        """测试获取缓存配置"""
        configure_caching_strategy()

        config = get_cache_config()
        assert config["enabled"] is True
        assert "default_ttl_seconds" in config
        assert "max_size" in config

    def test_is_caching_enabled(self):
        """测试检查缓存是否启用"""
        # Reset state first
        from core.caching_strategy import _cache_config

        _cache_config["enabled"] = False

        assert is_caching_enabled() is False

        configure_caching_strategy()
        assert is_caching_enabled() is True


class TestCacheOperations:
    """缓存操作测试"""

    def test_generate_cache_key(self):
        """测试生成缓存键"""
        configure_caching_strategy(cache_key_prefix="test")

        key = generate_cache_key("user:123")
        assert key == "test:user:123"

        # Test custom prefix
        key = generate_cache_key("user:123", prefix="custom")
        assert key == "custom:user:123"

    def test_set_cache(self):
        """测试设置缓存"""
        configure_caching_strategy()

        result = set_cache("test_key", "test_value")
        assert result is True

    def test_get_cache(self):
        """测试获取缓存"""
        configure_caching_strategy()

        set_cache("test_key", "test_value")
        value = get_cache("test_key")

        assert value == "test_value"

    def test_get_cache_not_found(self):
        """测试获取不存在的缓存"""
        configure_caching_strategy()

        value = get_cache("nonexistent_key")
        assert value is None

    def test_delete_cache(self):
        """测试删除缓存"""
        configure_caching_strategy()

        set_cache("test_key", "test_value")
        result = delete_cache("test_key")

        assert result is True
        assert get_cache("test_key") is None

    def test_delete_cache_not_found(self):
        """测试删除不存在的缓存"""
        configure_caching_strategy()

        result = delete_cache("nonexistent_key")
        assert result is False

    def test_clear_cache(self):
        """测试清除所有缓存"""
        configure_caching_strategy()

        set_cache("key1", "value1")
        set_cache("key2", "value2")

        count = clear_cache()

        assert count == 2
        assert get_cache("key1") is None


class TestCacheStatistics:
    """缓存统计测试"""

    def test_get_cache_statistics(self):
        """测试获取缓存统计"""
        configure_caching_strategy()
        reset_cache_statistics()

        set_cache("test_key", "test_value")
        get_cache("test_key")
        get_cache("nonexistent_key")

        stats = get_cache_statistics()

        assert stats["enabled"] is True
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] > 0

    def test_reset_cache_statistics(self):
        """测试重置缓存统计"""
        configure_caching_strategy()
        set_cache("test_key", "test_value")
        get_cache("test_key")

        reset_cache_statistics()

        stats = get_cache_statistics()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestCacheDecorator:
    """缓存装饰器测试"""

    def test_cache_decorator(self):
        """测试缓存装饰器"""
        configure_caching_strategy()

        call_count = 0

        @cache_decorator(ttl_seconds=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment


class TestCacheInvalidation:
    """缓存失效测试"""

    def test_invalidate_pattern(self):
        """测试模式失效"""
        configure_caching_strategy()

        set_cache("user:123", "value1")
        set_cache("user:456", "value2")
        set_cache("product:789", "value3")

        count = invalidate_pattern("user:")

        assert count == 2
        assert get_cache("user:123") is None
        assert get_cache("user:456") is None
        assert get_cache("product:789") is not None


class TestCacheInfo:
    """缓存信息测试"""

    def test_get_cache_info(self):
        """测试获取缓存信息"""
        configure_caching_strategy()
        set_cache("test_key", "test_value")

        info = get_cache_info()

        assert info["configuration"]["enabled"] is True
        assert info["statistics"]["size"] > 0
        assert "keys" in info
        assert "memory_usage_bytes" in info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
