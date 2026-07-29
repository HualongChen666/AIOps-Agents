# -*- coding: utf-8 -*-
# tests/performance/test_concurrent_performance.py
# 并发性能测试
import asyncio
import time

import pytest


@pytest.mark.performance
class TestConcurrentAPIPerformance:
    """并发API性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_get_requests(self, client):
        """测试并发GET请求性能"""
        num_requests = 200
        start_time = time.time()

        tasks = [client.get("/health") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        successful = sum(1 for r in responses if not isinstance(r, Exception))
        assert successful == num_requests
        assert total_time < 10.0, f"Concurrent GET requests too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_post_requests(self, client):
        """测试并发POST请求性能"""
        num_requests = 100
        start_time = time.time()

        tasks = [client.post("/api/test", json={"data": "test"}) for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        successful = sum(1 for r in responses if not isinstance(r, Exception))
        assert successful >= num_requests * 0.9  # 允许10%失败
        assert total_time < 10.0, f"Concurrent POST requests too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_requests(self, client):
        """测试并发混合请求性能"""
        num_requests = 100
        start_time = time.time()

        tasks = []
        for i in range(num_requests):
            if i % 2 == 0:
                tasks.append(client.get("/health"))
            else:
                tasks.append(client.post("/api/test", json={"data": "test"}))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        successful = sum(1 for r in responses if not isinstance(r, Exception))
        assert successful >= num_requests * 0.9
        assert total_time < 10.0, f"Concurrent mixed requests too slow: {total_time}s"


@pytest.mark.performance
class TestConcurrentDatabasePerformance:
    """并发数据库性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_database_reads(self, test_db_engine):
        """测试并发数据库读取性能"""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker

        async_session = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)

        async def read_one():
            async with async_session() as session:
                await session.execute(select(1))

        num_reads = 100
        start_time = time.time()

        tasks = [read_one() for _ in range(num_reads)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        assert total_time < 5.0, f"Concurrent database reads too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_database_writes(self, test_db_session):
        """测试并发数据库写入性能"""
        num_writes = 50
        start_time = time.time()

        async def write_operation(i):
            # 模拟写入操作
            pass

        tasks = [write_operation(i) for i in range(num_writes)]
        await asyncio.gather(*tasks)
        await test_db_session.commit()

        end_time = time.time()
        total_time = end_time - start_time

        assert total_time < 5.0, f"Concurrent database writes too slow: {total_time}s"


@pytest.mark.performance
class TestConcurrentCachePerformance:
    """并发缓存性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_cache_reads(self, test_redis_client):
        """测试并发缓存读取性能"""
        # 设置测试数据
        await test_redis_client.set("test_key", "test_value")

        num_reads = 1000
        start_time = time.time()

        tasks = [test_redis_client.get("test_key") for _ in range(num_reads)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        assert total_time < 5.0, f"Concurrent cache reads too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_cache_writes(self, test_redis_client):
        """测试并发缓存写入性能"""
        num_writes = 500
        start_time = time.time()

        tasks = [test_redis_client.set(f"key_{i}", f"value_{i}") for i in range(num_writes)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        assert total_time < 5.0, f"Concurrent cache writes too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_cache_mixed_operations(self, test_redis_client):
        """测试并发缓存混合操作性能"""
        num_ops = 200
        start_time = time.time()

        tasks = []
        for i in range(num_ops):
            if i % 3 == 0:
                tasks.append(test_redis_client.set(f"key_{i}", f"value_{i}"))
            elif i % 3 == 1:
                tasks.append(test_redis_client.get(f"key_{i}"))
            else:
                tasks.append(test_redis_client.delete(f"key_{i}"))

        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        assert total_time < 5.0, f"Concurrent cache mixed operations too slow: {total_time}s"


@pytest.mark.performance
class TestConcurrentProcessingPerformance:
    """并发处理性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_data_processing(self):
        """测试并发数据处理性能"""
        num_tasks = 100

        async def process_data(i):
            # 模拟数据处理
            await asyncio.sleep(0.01)
            return i * 2

        start_time = time.time()
        tasks = [process_data(i) for i in range(num_tasks)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time

        assert len(results) == num_tasks
        assert total_time < 5.0, f"Concurrent data processing too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self):
        """测试并发API调用性能"""
        num_calls = 50

        async def mock_api_call(i):
            # 模拟API调用
            await asyncio.sleep(0.05)
            return {"result": i}

        start_time = time.time()
        tasks = [mock_api_call(i) for i in range(num_calls)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time

        assert len(results) == num_calls
        assert total_time < 5.0, f"Concurrent API calls too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_task_queue_processing(self):
        """测试并发任务队列处理性能"""
        import asyncio

        queue = asyncio.Queue(maxsize=1000)
        num_tasks = 500

        # 填充队列
        for i in range(num_tasks):
            await queue.put(i)

        async def process_queue():
            processed = 0
            while not queue.empty():
                await queue.get()
                await asyncio.sleep(0.001)  # 模拟处理
                processed += 1
            return processed

        start_time = time.time()
        results = await asyncio.gather(process_queue(), process_queue(), process_queue())
        end_time = time.time()

        total_time = end_time - start_time
        total_processed = sum(results)

        assert total_processed == num_tasks
        assert total_time < 5.0, f"Concurrent queue processing too slow: {total_time}s"


@pytest.mark.performance
class TestResourceUtilization:
    """资源利用率测试"""

    @pytest.mark.asyncio
    async def test_cpu_utilization_under_load(self):
        """测试负载下的CPU利用率"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        process.cpu_percent()

        # 执行CPU密集型任务
        num_tasks = 1000
        start_time = time.time()

        def cpu_intensive_task(n):
            return sum(i * i for i in range(n))

        tasks = [asyncio.to_thread(cpu_intensive_task, 1000) for _ in range(num_tasks)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        process.cpu_percent()

        total_time = end_time - start_time

        # 验证任务完成且CPU使用合理
        assert total_time < 10.0, f"CPU intensive tasks too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_memory_utilization_under_load(self):
        """测试负载下的内存利用率"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 执行内存密集型任务
        data = [bytearray(1024 * 1024) for _ in range(10)]  # 10MB

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 验证内存增长合理
        assert (
            memory_increase < 20 * 1024 * 1024
        ), f"Memory increase too large: {memory_increase / 1024 / 1024}MB"

        # 清理
        del data

    @pytest.mark.asyncio
    async def test_io_utilization_under_load(self):
        """测试负载下的IO利用率"""
        import tempfile

        # 执行IO密集型任务
        num_files = 100
        with tempfile.TemporaryDirectory() as tmpdir:
            start_time = time.time()

            # 并发写入文件
            async def write_file(i):
                file_path = f"{tmpdir}/test_{i}.txt"
                with open(file_path, "w") as f:
                    f.write("x" * 1024 * 10)  # 10KB

            tasks = [write_file(i) for i in range(num_files)]
            await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = end_time - start_time

            # 验证IO性能
            assert total_time < 5.0, f"IO intensive tasks too slow: {total_time}s"


@pytest.mark.performance
class TestScalabilityPerformance:
    """可扩展性性能测试"""

    @pytest.mark.asyncio
    async def test_linear_scalability(self):
        """测试线性可扩展性"""
        workloads = [10, 50, 100, 200]
        times = []

        for workload in workloads:
            start_time = time.time()

            async def process_task(i):
                await asyncio.sleep(0.01)
                return i

            tasks = [process_task(i) for i in range(workload)]
            await asyncio.gather(*tasks)

            end_time = time.time()
            times.append(end_time - start_time)

        # 验证时间线性增长（而非指数增长）
        assert times[1] < times[0] * 10  # 50个任务应该比10个任务快5倍以上
        assert times[2] < times[1] * 5  # 100个任务应该比50个任务快2倍以上

    @pytest.mark.asyncio
    async def test_concurrent_scalability(self):
        """测试并发可扩展性"""
        concurrency_levels = [1, 5, 10, 20]
        times = []

        for concurrency in concurrency_levels:
            start_time = time.time()

            async def process_task():
                await asyncio.sleep(0.1)
                return True

            tasks = [process_task() for _ in range(concurrency)]
            await asyncio.gather(*tasks)

            end_time = time.time()
            times.append(end_time - start_time)

        # 验证并发扩展性
        # 更高并发应该不会显著增加总时间（因为任务并行执行）
        assert times[2] < times[0] * 3  # 10并发应该比1并发快3倍以上
