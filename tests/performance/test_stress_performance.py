# -*- coding: utf-8 -*-
# tests/performance/test_stress_performance.py
# 压力测试
import logging
import asyncio
import time

import pytest


@pytest.mark.performance
@pytest.mark.slow
class TestStressAPI:
    """API压力测试"""

    @pytest.mark.asyncio
    async def test_sustained_load(self, client):
        """测试持续负载"""
        duration = 30  # 30秒
        interval = 0.1  # 每100ms发送一个请求
        num_requests = int(duration / interval)

        start_time = time.time()
        request_times = []

        for i in range(num_requests):
            req_start = time.time()
            try:
                await client.get("/health")
                req_time = time.time() - req_start
                request_times.append(req_time)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
            await asyncio.sleep(interval)

        time.time() - start_time

        # 验证所有请求都完成
        assert len(request_times) > num_requests * 0.9  # 允许10%失败

        # 验证平均响应时间
        avg_response_time = sum(request_times) / len(request_times)
        assert (
            avg_response_time < 1.0
        ), f"Average response time too high under load: {avg_response_time}s"

    @pytest.mark.asyncio
    async def test_spike_load(self, client):
        """测试突发负载"""
        # 正常负载
        for _ in range(10):
            await client.get("/health")
            await asyncio.sleep(0.1)

        # 突发负载
        spike_tasks = [client.get("/health") for _ in range(100)]
        await asyncio.gather(*spike_tasks, return_exceptions=True)

        # 恢复到正常负载
        for _ in range(10):
            await client.get("/health")
            await asyncio.sleep(0.1)

        # 验证系统仍然响应
        response = await client.get("/health")
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_memory_leak_under_load(self, client):
        """测试负载下的内存泄漏"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 执行大量请求
        for _ in range(1000):
            await client.get("/health")

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 验证内存增长合理（< 50MB）
        assert (
            memory_increase < 50 * 1024 * 1024
        ), f"Memory leak detected: {memory_increase / 1024 / 1024}MB"


@pytest.mark.performance
@pytest.mark.slow
class TestStressDatabase:
    """数据库压力测试"""

    @pytest.mark.asyncio
    async def test_sustained_database_load(self, test_db_engine):
        """测试持续数据库负载"""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker

        async_session = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)

        duration = 20  # 20秒
        interval = 0.05  # 每50ms执行一次查询
        num_queries = int(duration / interval)

        start_time = time.time()
        query_times = []

        for _ in range(num_queries):
            query_start = time.time()
            try:
                async with async_session() as session:
                    await session.execute(select(1))
                query_time = time.time() - query_start
                query_times.append(query_time)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
            await asyncio.sleep(interval)

        time.time() - start_time

        # 验证所有查询都完成
        assert len(query_times) > num_queries * 0.9

        # 验证平均查询时间
        avg_query_time = sum(query_times) / len(query_times)
        assert avg_query_time < 0.1, f"Average query time too high under load: {avg_query_time}s"

    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion(self, test_db_engine):
        """测试数据库连接池耗尽"""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker

        async_session = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)

        async def query_one():
            async with async_session() as session:
                await session.execute(select(1))

        # 尝试大量并发查询
        num_queries = 200
        start_time = time.time()

        tasks = [query_one() for _ in range(num_queries)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # 验证大部分查询成功
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert (
            successful > num_queries * 0.8
        ), f"Too many failed queries: {successful}/{num_queries}"

        # 验证总时间合理
        assert total_time < 10.0, f"Connection pool exhaustion test too slow: {total_time}s"


@pytest.mark.performance
@pytest.mark.slow
class TestStressCache:
    """缓存压力测试"""

    @pytest.mark.asyncio
    async def test_sustained_cache_load(self, test_redis_client):
        """测试持续缓存负载"""
        duration = 20  # 20秒
        interval = 0.01  # 每10ms执行一次操作
        num_ops = int(duration / interval)

        start_time = time.time()
        op_times = []

        for i in range(num_ops):
            op_start = time.time()
            try:
                if i % 2 == 0:
                    await test_redis_client.set(f"key_{i}", f"value_{i}")
                else:
                    await test_redis_client.get(f"key_{i % 100}")
                op_time = time.time() - op_start
                op_times.append(op_time)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
            await asyncio.sleep(interval)

        time.time() - start_time

        # 验证所有操作都完成
        assert len(op_times) > num_ops * 0.9

        # 验证平均操作时间
        avg_op_time = sum(op_times) / len(op_times)
        assert avg_op_time < 0.05, f"Average operation time too high under load: {avg_op_time}s"

    @pytest.mark.asyncio
    async def test_cache_memory_exhaustion(self, test_redis_client):
        """测试缓存内存耗尽"""
        # 尝试写入大量数据
        num_keys = 10000
        key_size = 1024  # 1KB per key

        start_time = time.time()

        for i in range(num_keys):
            try:
                await test_redis_client.set(f"key_{i}", "x" * key_size)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                # 内存不足，停止
                break

        end_time = time.time()
        total_time = end_time - start_time

        # 验证写入性能
        assert total_time < 30.0, f"Cache memory exhaustion test too slow: {total_time}s"

        # 清理
        await test_redis_client.flushall()


@pytest.mark.performance
@pytest.mark.slow
class TestStressConcurrency:
    """并发压力测试"""

    @pytest.mark.asyncio
    async def test_extreme_concurrency(self, client):
        """测试极端并发"""
        num_concurrent = 500
        start_time = time.time()

        tasks = [client.get("/health") for _ in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # 验证大部分请求成功
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert (
            successful > num_concurrent * 0.7
        ), f"Too many failed requests: {successful}/{num_concurrent}"

        # 验证总时间
        assert total_time < 30.0, f"Extreme concurrency test too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_rapid_concurrency_changes(self, client):
        """测试快速并发变化"""
        # 从低并发到高并发
        concurrency_levels = [10, 50, 100, 200, 50, 10]

        for concurrency in concurrency_levels:
            tasks = [client.get("/health") for _ in range(concurrency)]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.5)  # 短暂暂停

        # 验证系统仍然响应
        response = await client.get("/health")
        assert response.status_code in [200, 404]


@pytest.mark.performance
@pytest.mark.slow
class TestLongRunningPerformance:
    """长时间运行性能测试"""

    @pytest.mark.asyncio
    async def test_long_running_api_performance(self, client):
        """测试长时间运行的API性能"""
        duration = 60  # 60秒
        sample_interval = 10  # 每10秒采样一次
        num_samples = int(duration / sample_interval)

        response_times = []

        for i in range(num_samples):
            start_time = time.time()

            # 发送10个请求
            for _ in range(10):
                await client.get("/health")

            end_time = time.time()
            response_times.append((end_time - start_time) / 10)

            if i < num_samples - 1:
                await asyncio.sleep(sample_interval)

        # 验证性能没有显著下降
        first_avg = sum(response_times[:3]) / 3
        last_avg = sum(response_times[-3:]) / 3

        # 允许性能下降不超过50%
        assert (
            last_avg < first_avg * 1.5
        ), f"Performance degradation detected: {first_avg}s -> {last_avg}s"

    @pytest.mark.asyncio
    async def test_long_running_cache_performance(self, test_redis_client):
        """测试长时间运行的缓存性能"""
        duration = 60  # 60秒
        sample_interval = 10  # 每10秒采样一次
        num_samples = int(duration / sample_interval)

        op_times = []

        for i in range(num_samples):
            start_time = time.time()

            # 执行100次操作
            for j in range(100):
                if j % 2 == 0:
                    await test_redis_client.set(f"key_{i}_{j}", f"value_{j}")
                else:
                    await test_redis_client.get(f"key_{i}_{j}")

            end_time = time.time()
            op_times.append((end_time - start_time) / 100)

            if i < num_samples - 1:
                await asyncio.sleep(sample_interval)

        # 验证性能没有显著下降
        first_avg = sum(op_times[:3]) / 3
        last_avg = sum(op_times[-3:]) / 3

        # 允许性能下降不超过50%
        assert (
            last_avg < first_avg * 1.5
        ), f"Cache performance degradation detected: {first_avg}s -> {last_avg}s"

        # 清理
        await test_redis_client.flushall()


@pytest.mark.performance
@pytest.mark.slow
class TestResourceExhaustion:
    """资源耗尽测试"""

    @pytest.mark.asyncio
    async def test_file_descriptor_exhaustion(self, tmp_path):
        """测试文件描述符耗尽"""

        # 尝试打开大量文件
        max_files = 1000
        files = []

        try:
            for i in range(max_files):
                file_path = tmp_path / f"test_{i}.txt"
                f = open(file_path, "w")
                f.write("test")
                files.append(f)

                if i % 100 == 0:
                    await asyncio.sleep(0.01)

        except OSError:
            # 文件描述符耗尽
            pass
        finally:
            # 清理
            for f in files:
                f.close()

        # 验证至少能打开一定数量的文件
        assert len(files) > 100, f"Too few files opened: {len(files)}"

    @pytest.mark.asyncio
    async def test_thread_exhaustion(self):
        """测试线程耗尽"""
        from concurrent.futures import ThreadPoolExecutor

        max_threads = 100
        results = []

        def blocking_task(n):
            time.sleep(0.01)
            return n

        try:
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [executor.submit(blocking_task, i) for i in range(max_threads)]
                results = [f.result() for f in futures]
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            # 线程耗尽
            pass

        # 验证至少能执行一定数量的任务
        assert len(results) > 50, f"Too few tasks completed: {len(results)}"
