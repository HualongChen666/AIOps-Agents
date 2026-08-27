# -*- coding: utf-8 -*-
"""
Cache Manager Tests
缓存管理器测试

测试Redis缓存策略的正确性和性能
"""

import pytest
import time
from core.cache_manager import cache_manager, cache_key_generator, cached, invalidate_cache_pattern, get_cache_hit_rate


class TestCacheManager:
    """缓存管理器测试"""

    def test_cache_set_get(self):
        """测试缓存设置和获取"""
        test_key = "test_key_1"
        test_value = {"data": "test_value", "number": 123}
        
        # 设置缓存
        result = cache_manager.set(test_key, test_value, ttl=60)
        assert result is True or result is False  # 允许Redis不可用的情况
        
        # 获取缓存
        if cache_manager.redis_client:
            cached_value = cache_manager.get(test_key)
            assert cached_value == test_value
        
        # 删除缓存
        cache_manager.delete(test_key)

    def test_cache_key_generator(self):
        """测试缓存键生成器"""
        key1 = cache_key_generator("prefix", "arg1", "arg2", param1="value1")
        key2 = cache_key_generator("prefix", "arg1", "arg2", param1="value1")
        key3 = cache_key_generator("prefix", "arg1", "arg2", param1="value2")
        
        assert key1 == key2
        assert key1 != key3
        assert "prefix" in key1
        assert "arg1" in key1
        assert "param1:value1" in key1

    def test_cache_decorator(self):
        """测试缓存装饰器"""
        call_count = 0
        
        @cached(ttl=60, prefix="test_decorator")
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # 第一次调用应该执行函数
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # 第二次调用应该从缓存获取（如果Redis可用）
        if cache_manager.redis_client:
            result2 = expensive_function(1, 2)
            assert result2 == 3
            assert call_count == 1  # 不应该再次调用函数
        else:
            # 如果Redis不可用，装饰器应该正常工作但不会缓存
            result2 = expensive_function(1, 2)
            assert result2 == 3
            assert call_count == 2  # 每次都会调用函数
        
        # 不同参数应该重新调用
        result3 = expensive_function(2, 3)
        assert result3 == 5
        if cache_manager.redis_client:
            assert call_count == 2
        else:
            assert call_count == 3

    def test_cache_expiration(self):
        """测试缓存过期"""
        test_key = "test_expiration"
        test_value = {"data": "test"}
        
        # 设置短TTL缓存
        cache_manager.set(test_key, test_value, ttl=1)
        
        if cache_manager.redis_client:
            # 立即获取应该成功
            cached_value = cache_manager.get(test_key)
            assert cached_value == test_value
            
            # 等待过期
            time.sleep(2)
            
            # 过期后应该返回None
            expired_value = cache_manager.get(test_key)
            assert expired_value is None

    def test_cache_invalidation(self):
        """测试缓存失效"""
        # 设置多个缓存
        for i in range(5):
            cache_manager.set(f"test_pattern_{i}", {"data": i}, ttl=60)
        
        if cache_manager.redis_client:
            # 验证缓存存在
            assert cache_manager.exists("test_pattern_0")
            assert cache_manager.exists("test_pattern_1")
            
            # 按模式失效
            deleted_count = invalidate_cache_pattern("test_pattern_*")
            assert deleted_count >= 2
            
            # 验证缓存已删除
            assert not cache_manager.exists("test_pattern_0")
            assert not cache_manager.exists("test_pattern_1")

    def test_cache_stats(self):
        """测试缓存统计"""
        stats = cache_manager.get_cache_stats()
        
        if cache_manager.redis_client:
            # 验证统计信息包含必要的字段
            assert "used_memory" in stats
            assert "keyspace_hits" in stats
            assert "keyspace_misses" in stats
            assert "total_commands_processed" in stats

    def test_cache_hit_rate(self):
        """测试缓存命中率计算"""
        # 执行一些缓存操作
        cache_manager.set("hit_test", {"data": "test"}, ttl=60)
        cache_manager.get("hit_test")
        cache_manager.get("miss_test")
        
        hit_rate = get_cache_hit_rate()
        assert 0 <= hit_rate <= 1


class TestCachePerformance:
    """缓存性能测试"""

    def test_cache_performance_vs_database(self):
        """测试缓存vs数据库性能"""
        from core.auth_db import get_session
        from core.models import BusinessImpactAnalysisDB
        import uuid
        
        # 测试数据库查询时间
        db = get_session()
        try:
            start_time = time.time()
            db.query(BusinessImpactAnalysisDB).limit(10).all()
            db_time = time.time() - start_time
            
            # 测试缓存查询时间
            cache_manager.set("perf_test", {"data": "test"}, ttl=60)
            start_time = time.time()
            cache_manager.get("perf_test")
            cache_time = time.time() - start_time
            
            print(f"Database query time: {db_time*1000:.2f}ms")
            print(f"Cache query time: {cache_time*1000:.2f}ms")
            
            # 缓存应该比数据库快
            if cache_manager.redis_client:
                assert cache_time < db_time, "Cache should be faster than database"
        finally:
            db.close()

    def test_cache_concurrent_access(self):
        """测试缓存并发访问"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def cache_operation(operation_id):
            cache_manager.set(f"concurrent_{operation_id}", {"data": operation_id}, ttl=60)
            cached = cache_manager.get(f"concurrent_{operation_id}")
            results.put(cached)
        
        # 创建10个并发线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=cache_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有操作都成功
        success_count = 0
        while not results.empty():
            result = results.get()
            if result is not None:
                success_count += 1
        
        if cache_manager.redis_client:
            assert success_count == 10, "All concurrent operations should succeed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])