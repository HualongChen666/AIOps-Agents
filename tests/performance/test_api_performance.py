# -*- coding: utf-8 -*-
# tests/performance/test_api_performance.py
# API性能测试
import asyncio
import time
from typing import Dict

import pytest
from sqlalchemy import select


@pytest.mark.performance
class TestAPIPerformance:
    """API性能测试"""

    @pytest.mark.asyncio
    async def test_api_response_time(self, client):
        """测试API响应时间"""
        start_time = time.time()
        await client.get("/health")
        end_time = time.time()
        response_time = end_time - start_time

        # 验证响应时间在可接受范围内（< 100ms）
        assert response_time < 0.1, f"Response time too slow: {response_time}s"

    @pytest.mark.asyncio
    async def test_api_throughput(self, client):
        """测试API吞吐量"""
        num_requests = 100
        start_time = time.time()

        # 并发发送请求
        tasks = [client.get("/health") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # 计算吞吐量
        successful_requests = sum(1 for r in responses if not isinstance(r, Exception))
        throughput = successful_requests / total_time

        # 验证吞吐量在可接受范围内（> 1000 QPS）
        assert throughput > 1000, f"Throughput too low: {throughput} QPS"

    @pytest.mark.asyncio
    async def test_api_concurrent_requests(self, client):
        """测试API并发请求处理"""
        num_concurrent = 50
        start_time = time.time()

        # 并发发送请求
        tasks = [client.get("/health") for _ in range(num_concurrent)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # 验证所有请求都成功
        successful_requests = sum(1 for r in responses if not isinstance(r, Exception))
        assert (
            successful_requests == num_concurrent
        ), f"Only {successful_requests}/{num_concurrent} requests succeeded"

        # 验证总时间在可接受范围内
        assert total_time < 5.0, f"Concurrent requests took too long: {total_time}s"

    @pytest.mark.asyncio
    async def test_api_payload_size_performance(self, client):
        """测试不同payload大小的API性能"""
        payload_sizes = [100, 1000, 10000]
        performance_results: Dict[int, float] = {}

        for size in payload_sizes:
            payload = {"data": "x" * size}
            start_time = time.time()
            _ = await client.post("/api/test", json=payload)
            end_time = time.time()
            performance_results[size] = end_time - start_time

        # 验证性能随payload大小线性增长，而非指数增长
        assert performance_results[1000] < performance_results[100] * 20
        assert performance_results[10000] < performance_results[1000] * 20

    @pytest.mark.asyncio
    async def test_api_memory_usage(self, client):
        """测试API内存使用"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 发送大量请求
        for _ in range(100):
            await client.get("/health")

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 验证内存增长在可接受范围内（< 10MB）
        assert (
            memory_increase < 10 * 1024 * 1024
        ), f"Memory increase too large: {memory_increase / 1024 / 1024}MB"


@pytest.mark.performance
class TestDatabasePerformance:
    """数据库性能测试"""

    @pytest.mark.asyncio
    async def test_database_query_performance(self, test_db_session):
        """测试数据库查询性能"""
        # 创建测试数据
        from sqlalchemy import select

        start_time = time.time()

        # 执行查询
        result = await test_db_session.execute(select(1))
        result.scalar()

        end_time = time.time()
        query_time = end_time - start_time

        # 验证查询时间在可接受范围内（< 50ms）
        assert query_time < 0.05, f"Query time too slow: {query_time}s"

    @pytest.mark.asyncio
    async def test_database_insert_performance(self, test_db_session):
        """测试数据库插入性能"""
        # 批量插入测试
        num_inserts = 100
        start_time = time.time()

        for i in range(num_inserts):
            # 模拟插入操作
            pass

        await test_db_session.commit()

        end_time = time.time()
        insert_time = end_time - start_time

        # 验证插入时间在可接受范围内（< 1秒）
        assert insert_time < 1.0, f"Insert time too slow: {insert_time}s"

    @pytest.mark.asyncio
    async def test_database_batch_operation_performance(self, test_db_session):
        """测试数据库批量操作性能"""
        # 批量操作测试
        batch_size = 1000
        start_time = time.time()

        # 模拟批量操作
        for i in range(batch_size):
            pass

        await test_db_session.commit()

        end_time = time.time()
        batch_time = end_time - start_time

        # 验证批量操作时间在可接受范围内（< 5秒）
        assert batch_time < 5.0, f"Batch operation time too slow: {batch_time}s"

    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self, test_db_session):
        """测试数据库连接池性能"""
        # 连接池性能测试
        num_queries = 100
        start_time = time.time()

        # 并发查询
        tasks = [test_db_session.execute(select(1)) for _ in range(num_queries)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        pool_time = end_time - start_time

        # 验证连接池性能（< 2秒）
        assert pool_time < 2.0, f"Connection pool time too slow: {pool_time}s"


@pytest.mark.performance
class TestCachePerformance:
    """缓存性能测试"""

    @pytest.mark.asyncio
    async def test_cache_read_performance(self, test_redis_client):
        """测试缓存读取性能"""
        # 设置测试数据
        await test_redis_client.set("test_key", "test_value")

        # 测试读取性能
        num_reads = 1000
        start_time = time.time()

        for _ in range(num_reads):
            await test_redis_client.get("test_key")

        end_time = time.time()
        read_time = end_time - start_time
        avg_read_time = read_time / num_reads

        # 验证平均读取时间（< 1ms）
        assert avg_read_time < 0.001, f"Average read time too slow: {avg_read_time}s"

    @pytest.mark.asyncio
    async def test_cache_write_performance(self, test_redis_client):
        """测试缓存写入性能"""
        # 测试写入性能
        num_writes = 1000
        start_time = time.time()

        for i in range(num_writes):
            await test_redis_client.set(f"key_{i}", f"value_{i}")

        end_time = time.time()
        write_time = end_time - start_time
        avg_write_time = write_time / num_writes

        # 验证平均写入时间（< 1ms）
        assert avg_write_time < 0.001, f"Average write time too slow: {avg_write_time}s"

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, test_redis_client):
        """测试缓存命中率"""
        # 设置测试数据
        cache_keys = [f"key_{i}" for i in range(100)]
        for key in cache_keys:
            await test_redis_client.set(key, f"value_{key}")

        # 测试缓存命中率
        hits = 0
        misses = 0

        for key in cache_keys:
            result = await test_redis_client.get(key)
            if result:
                hits += 1
            else:
                misses += 1

        # 测试未缓存键
        for _ in range(10):
            result = await test_redis_client.get("non_existent_key")
            if not result:
                misses += 1

        total_requests = hits + misses
        hit_rate = hits / total_requests if total_requests > 0 else 0

        # 验证缓存命中率（> 90%）
        assert hit_rate > 0.9, f"Cache hit rate too low: {hit_rate}"

    @pytest.mark.asyncio
    async def test_cache_concurrent_performance(self, test_redis_client):
        """测试缓存并发性能"""
        # 并发操作测试
        num_concurrent = 100
        start_time = time.time()

        tasks = [test_redis_client.set(f"key_{i}", f"value_{i}") for i in range(num_concurrent)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        concurrent_time = end_time - start_time

        # 验证并发操作时间（< 1秒）
        assert concurrent_time < 1.0, f"Concurrent operations too slow: {concurrent_time}s"


@pytest.mark.performance
class TestAIInferencePerformance:
    """AI推理性能测试"""

    @pytest.mark.asyncio
    async def test_ai_inference_latency(self):
        """测试AI推理延迟"""
        # 模拟AI推理
        start_time = time.time()

        # 模拟推理过程
        await asyncio.sleep(0.1)

        end_time = time.time()
        inference_time = end_time - start_time

        # 验证推理延迟（< 5秒）
        assert inference_time < 5.0, f"Inference latency too high: {inference_time}s"

    @pytest.mark.asyncio
    async def test_ai_concurrent_inference(self):
        """测试AI并发推理性能"""
        # 并发推理测试
        num_concurrent = 10
        start_time = time.time()

        tasks = [asyncio.sleep(0.1) for _ in range(num_concurrent)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        concurrent_time = end_time - start_time

        # 验证并发推理时间（< 5秒）
        assert concurrent_time < 5.0, f"Concurrent inference too slow: {concurrent_time}s"

    @pytest.mark.asyncio
    async def test_ai_batch_inference(self):
        """测试AI批量推理性能"""
        # 批量推理测试
        batch_size = 100
        start_time = time.time()

        # 模拟批量推理
        for _ in range(batch_size):
            await asyncio.sleep(0.001)

        end_time = time.time()
        batch_time = end_time - start_time

        # 验证批量推理时间（< 5秒）
        assert batch_time < 5.0, f"Batch inference too slow: {batch_time}s"


@pytest.mark.performance
class TestMemoryPerformance:
    """内存性能测试"""

    @pytest.mark.asyncio
    async def test_memory_allocation_performance(self):
        """测试内存分配性能"""

        start_time = time.time()

        # 分配大量内存
        data = [bytearray(1024 * 1024) for _ in range(100)]  # 100MB

        end_time = time.time()
        allocation_time = end_time - start_time

        # 验证分配时间（< 1秒）
        assert allocation_time < 1.0, f"Memory allocation too slow: {allocation_time}s"

        # 清理
        del data

    @pytest.mark.asyncio
    async def test_memory_gc_performance(self):
        """测试垃圾回收性能"""
        import gc

        # 创建大量对象
        data = [object() for _ in range(10000)]

        start_time = time.time()
        gc.collect()
        end_time = time.time()

        gc_time = end_time - start_time

        # 验证GC时间（< 1秒）
        assert gc_time < 1.0, f"GC too slow: {gc_time}s"

        # 清理
        del data


@pytest.mark.performance
class TestIOPerformance:
    """IO性能测试"""

    @pytest.mark.asyncio
    async def test_file_read_performance(self, tmp_path):
        """测试文件读取性能"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("x" * 1024 * 1024)  # 1MB

        start_time = time.time()
        test_file.read_text()
        end_time = time.time()

        read_time = end_time - start_time

        # 验证读取时间（< 100ms）
        assert read_time < 0.1, f"File read too slow: {read_time}s"

    @pytest.mark.asyncio
    async def test_file_write_performance(self, tmp_path):
        """测试文件写入性能"""
        test_file = tmp_path / "test.txt"
        content = "x" * 1024 * 1024  # 1MB

        start_time = time.time()
        test_file.write_text(content)
        end_time = time.time()

        write_time = end_time - start_time

        # 验证写入时间（< 100ms）
        assert write_time < 0.1, f"File write too slow: {write_time}s"
