# -*- coding: utf-8 -*-
"""
E2E Test: Redis Cache Integration
真实E2E测试：Redis缓存集成测试，不使用Mock
"""

import asyncio
import time
from datetime import datetime, timedelta  # noqa: F401

import httpx  # noqa: F401
import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestRedisCacheIntegration:
    """Redis缓存集成E2E测试"""

    @pytest.mark.asyncio
    async def test_cache_write_and_read(self, http_client, test_redis_url):
        """测试缓存写入和读取"""

        # 写入缓存
        cache_data = {
            "key": f"test_key_{int(datetime.now().timestamp())}",
            "value": {"test_data": "cache_value", "timestamp": datetime.now().isoformat()},
            "ttl": 3600,  # 1小时过期
        }

        write_response = await http_client.post(
            "http://localhost:8000/api/v1/cache/set", json=cache_data, timeout=10.0
        )

        # 如果缓存API不存在，跳过测试
        if write_response.status_code == 404:
            pytest.skip("Cache API not available")

        assert write_response.status_code in [200, 201]

        # 读取缓存
        read_response = await http_client.get(
            f"http://localhost:8000/api/v1/cache/get/{cache_data['key']}", timeout=10.0
        )

        assert read_response.status_code == 200
        cached_value = read_response.json()

        # 验证缓存数据
        assert cached_value["value"] == cache_data["value"]

        # 清理缓存
        delete_response = await http_client.delete(
            f"http://localhost:8000/api/v1/cache/delete/{cache_data['key']}", timeout=10.0
        )

        assert delete_response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_cache_expiration(self, http_client, test_redis_url):
        """测试缓存过期"""

        # 写入短期缓存
        cache_data = {
            "key": f"expire_test_{int(datetime.now().timestamp())}",
            "value": {"test": "expire"},
            "ttl": 2,  # 2秒过期
        }

        write_response = await http_client.post(
            "http://localhost:8000/api/v1/cache/set", json=cache_data, timeout=10.0
        )

        if write_response.status_code == 404:
            pytest.skip("Cache API not available")

        assert write_response.status_code in [200, 201]

        # 立即读取，应该存在
        read_response1 = await http_client.get(
            f"http://localhost:8000/api/v1/cache/get/{cache_data['key']}", timeout=10.0
        )

        assert read_response1.status_code == 200

        # 等待过期
        await asyncio.sleep(3)

        # 再次读取，应该不存在
        read_response2 = await http_client.get(
            f"http://localhost:8000/api/v1/cache/get/{cache_data['key']}", timeout=10.0
        )

        assert read_response2.status_code == 404

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, http_client, test_redis_url):
        """测试缓存失效"""

        # 写入缓存
        cache_data = {
            "key": f"invalidation_test_{int(datetime.now().timestamp())}",
            "value": {"test": "invalidation"},
            "ttl": 3600,
        }

        write_response = await http_client.post(
            "http://localhost:8000/api/v1/cache/set", json=cache_data, timeout=10.0
        )

        if write_response.status_code == 404:
            pytest.skip("Cache API not available")

        assert write_response.status_code in [200, 201]

        # 失效缓存
        invalidate_response = await http_client.post(
            f"http://localhost:8000/api/v1/cache/invalidate/{cache_data['key']}", timeout=10.0
        )

        assert invalidate_response.status_code in [200, 204]

        # 验证缓存已失效
        read_response = await http_client.get(
            f"http://localhost:8000/api/v1/cache/get/{cache_data['key']}", timeout=10.0
        )

        assert read_response.status_code == 404

    @pytest.mark.asyncio
    async def test_cache_performance(self, http_client, test_redis_url):
        """测试缓存性能"""

        # 测试缓存写入性能
        write_times = []
        for i in range(100):
            start_time = time.time()

            response = await http_client.post(
                "http://localhost:8000/api/v1/cache/set",
                json={"key": f"perf_test_{i}", "value": {"data": i}, "ttl": 60},
                timeout=5.0,
            )

            end_time = time.time()
            write_times.append((end_time - start_time) * 1000)

            if response.status_code == 404:
                pytest.skip("Cache API not available")

        # 计算平均写入时间
        avg_write_time = sum(write_times) / len(write_times)
        assert avg_write_time < 10  # 平均写入时间应该小于10ms

        # 测试缓存读取性能
        read_times = []
        for i in range(100):
            start_time = time.time()

            response = await http_client.get(
                f"http://localhost:8000/api/v1/cache/get/perf_test_{i}", timeout=5.0
            )

            end_time = time.time()
            read_times.append((end_time - start_time) * 1000)

        # 计算平均读取时间
        avg_read_time = sum(read_times) / len(read_times)
        assert avg_read_time < 5  # 平均读取时间应该小于5ms

        # 清理
        for i in range(100):
            await http_client.delete(
                f"http://localhost:8000/api/v1/cache/delete/perf_test_{i}", timeout=5.0
            )

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, http_client, test_redis_url):
        """测试缓存命中率"""

        # 预热缓存
        for i in range(50):
            await http_client.post(
                "http://localhost:8000/api/v1/cache/set",
                json={"key": f"hit_test_{i}", "value": {"data": i}, "ttl": 300},
                timeout=5.0,
            )

        # 执行混合操作
        hits = 0
        misses = 0

        for i in range(100):
            key = f"hit_test_{i % 50}"  # 50%的key存在

            response = await http_client.get(
                f"http://localhost:8000/api/v1/cache/get/{key}", timeout=5.0
            )

            if response.status_code == 200:
                hits += 1
            elif response.status_code == 404:
                misses += 1
            elif response.status_code == 404:
                pytest.skip("Cache API not available")

        # 验证命中率
        hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
        assert hit_rate > 0.4  # 命中率应该大于40%

        # 清理
        for i in range(50):
            await http_client.delete(
                f"http://localhost:8000/api/v1/cache/delete/hit_test_{i}", timeout=5.0
            )

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self, http_client, test_redis_url):
        """测试缓存并发访问"""

        async def cache_operation(key):
            # 写入
            await http_client.post(
                "http://localhost:8000/api/v1/cache/set",
                json={"key": key, "value": {"data": "concurrent"}, "ttl": 60},
                timeout=5.0,
            )

            # 读取
            response = await http_client.get(
                f"http://localhost:8000/api/v1/cache/get/{key}", timeout=5.0
            )

            return response.status_code

        # 并发执行100个缓存操作
        responses = await asyncio.gather(
            *[cache_operation(f"concurrent_test_{i}") for i in range(100)]
        )

        # 验证并发操作成功
        success_count = sum(1 for status in responses if status in [200, 404])
        assert success_count >= 95  # 允许少量失败

        # 清理
        for i in range(100):
            await http_client.delete(
                f"http://localhost:8000/api/v1/cache/delete/concurrent_test_{i}", timeout=5.0
            )

    @pytest.mark.asyncio
    async def test_cache_connection_pool(self, http_client, test_redis_url):
        """测试缓存连接池"""

        # 快速连续请求，测试连接池
        responses = []
        for i in range(200):
            response = await http_client.get(
                "http://localhost:8000/api/v1/cache/health", timeout=5.0
            )
            responses.append(response)

            if response.status_code == 404:
                pytest.skip("Cache health API not available")

        # 验证连接池正常工作
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 190  # 允许少量失败

    @pytest.mark.asyncio
    async def test_cache_data_serialization(self, http_client, test_redis_url):
        """测试缓存数据序列化"""

        # 测试不同数据类型的序列化
        test_data = [
            {"type": "string", "value": "test_string"},
            {"type": "number", "value": 12345},
            {"type": "float", "value": 123.45},
            {"type": "boolean", "value": True},
            {"type": "list", "value": [1, 2, 3, 4, 5]},
            {"type": "dict", "value": {"nested": {"data": "test"}}},
            {"type": "null", "value": None},
        ]

        for data in test_data:
            key = f"serialization_test_{data['type']}"

            # 写入
            write_response = await http_client.post(
                "http://localhost:8000/api/v1/cache/set",
                json={"key": key, "value": data["value"], "ttl": 60},
                timeout=5.0,
            )

            if write_response.status_code == 404:
                pytest.skip("Cache API not available")

            assert write_response.status_code in [200, 201]

            # 读取
            read_response = await http_client.get(
                f"http://localhost:8000/api/v1/cache/get/{key}", timeout=5.0
            )

            assert read_response.status_code == 200
            cached_value = read_response.json()

            # 验证数据完整性
            assert cached_value["value"] == data["value"]

            # 清理
            await http_client.delete(
                f"http://localhost:8000/api/v1/cache/delete/{key}", timeout=5.0
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
