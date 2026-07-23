# -*- coding: utf-8 -*-
"""
Connection Pool Performance Tests
连接池性能测试
"""

import asyncio
import time

import pytest

from core.db_engine import AsyncSessionLocal, engine


class TestConnectionPoolPerformance:
    """连接池性能测试"""

    @pytest.mark.asyncio
    async def test_connection_acquire(self, benchmark):
        """连接获取性能"""

        async def acquire_connection():
            async with AsyncSessionLocal() as session:
                # 执行简单查询
                from sqlalchemy import func, select

                stmt = select(func.count())
                await session.execute(stmt)

        benchmark.pedantic(acquire_connection)

    @pytest.mark.asyncio
    async def test_connection_release(self, benchmark):
        """连接释放性能"""

        async def release_connection():
            async with AsyncSessionLocal() as _:
                pass  # 立即释放连接

        benchmark.pedantic(release_connection)

    @pytest.mark.asyncio
    async def test_concurrent_connections_10(self, benchmark):
        """10个并发连接性能"""

        async def concurrent_10():
            async def get_connection():
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import func, select

                    stmt = select(func.count())
                    await session.execute(stmt)

            tasks = [get_connection() for _ in range(10)]
            await asyncio.gather(*tasks)

        benchmark.pedantic(concurrent_10)

    @pytest.mark.asyncio
    async def test_concurrent_connections_50(self, benchmark):
        """50个并发连接性能"""

        async def concurrent_50():
            async def get_connection():
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import func, select

                    stmt = select(func.count())
                    await session.execute(stmt)

            tasks = [get_connection() for _ in range(50)]
            await asyncio.gather(*tasks)

        benchmark.pedantic(concurrent_50)

    @pytest.mark.asyncio
    async def test_concurrent_connections_100(self, benchmark):
        """100个并发连接性能"""

        async def concurrent_100():
            async def get_connection():
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import func, select

                    stmt = select(func.count())
                    await session.execute(stmt)

            tasks = [get_connection() for _ in range(100)]
            await asyncio.gather(*tasks)

        benchmark.pedantic(concurrent_100)

    @pytest.mark.asyncio
    async def test_connection_pool_size_optimization(self, benchmark):
        """连接池大小优化测试"""
        pool_sizes = [5, 10, 20, 30, 40, 50]
        results = {}

        for pool_size in pool_sizes:
            start_time = time.time()

            async def test_pool_size():
                async def get_connection():
                    async with AsyncSessionLocal() as session:
                        from sqlalchemy import func, select

                        stmt = select(func.count())
                        await session.execute(stmt)

                tasks = [get_connection() for _ in range(pool_size * 2)]
                await asyncio.gather(*tasks)

            await test_pool_size()
            duration = time.time() - start_time
            results[pool_size] = duration

        # 返回最优池大小
        optimal_size = min(results, key=results.get)
        return optimal_size, results

    @pytest.mark.asyncio
    async def test_connection_wait_time(self, benchmark):
        """连接等待时间测试"""

        async def connection_wait():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import func, select

                stmt = select(func.count())
                await session.execute(stmt)

        # 测试在高并发下的等待时间
        start_time = time.time()
        tasks = [connection_wait() for _ in range(100)]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        avg_wait_time = total_time / 100
        return avg_wait_time

    @pytest.mark.asyncio
    async def test_connection_reuse(self, benchmark):
        """连接复用性能"""

        async def connection_reuse():
            # 复用同一个连接执行多次查询
            async with AsyncSessionLocal() as session:
                from sqlalchemy import func, select

                for _ in range(10):
                    stmt = select(func.count())
                    await session.execute(stmt)

        benchmark.pedantic(connection_reuse)

    @pytest.mark.asyncio
    async def test_connection_leak_detection(self, benchmark):
        """连接泄漏检测"""
        initial_pool_size = engine.pool.size()

        async def potential_leak():
            # 故意不关闭连接（模拟泄漏）
            session = AsyncSessionLocal()
            from sqlalchemy import func, select

            stmt = select(func.count())
            await session.execute(stmt)
            # 不关闭连接
            await session.close()

        # 执行多次
        for _ in range(10):
            await potential_leak()

        # 检查连接池状态
        final_pool_size = engine.pool.size()
        pool_growth = final_pool_size - initial_pool_size

        return pool_growth


class TestConnectionPoolStress:
    """连接池压力测试"""

    @pytest.mark.asyncio
    async def test_stress_test_1000_requests(self, benchmark):
        """1000请求压力测试"""

        async def stress_1000():
            async def single_request():
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import func, select

                    stmt = select(func.count())
                    await session.execute(stmt)

            tasks = [single_request() for _ in range(1000)]
            await asyncio.gather(*tasks)

        benchmark.pedantic(stress_1000)

    @pytest.mark.asyncio
    async def test_stress_test_sustained_load(self, benchmark):
        """持续负载压力测试"""

        async def sustained_load():
            async def single_request():
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import func, select

                    stmt = select(func.count())
                    await session.execute(stmt)

            # 持续执行100个请求
            for _ in range(100):
                await single_request()

        benchmark.pedantic(sustained_load)

    @pytest.mark.asyncio
    async def test_pool_exhaustion_recovery(self, benchmark):
        """连接池耗尽恢复测试"""

        async def exhaustion_recovery():
            # 耗尽连接池
            sessions = []
            try:
                for _ in range(100):  # 超过连接池大小
                    session = AsyncSessionLocal()
                    sessions.append(session)
                    from sqlalchemy import func, select

                    stmt = select(func.count())
                    await session.execute(stmt)
            finally:
                # 释放所有连接
                for session in sessions:
                    await session.close()

        benchmark.pedantic(exhaustion_recovery)


class TestConnectionPoolMetrics:
    """连接池指标测试"""

    @pytest.mark.asyncio
    async def test_pool_status(self):
        """连接池状态测试"""
        pool = engine.pool

        metrics = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": pool.max_overflow,
        }

        return metrics

    @pytest.mark.asyncio
    async def test_pool_health_check(self, benchmark):
        """连接池健康检查"""

        async def health_check():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import func, select

                stmt = select(func.count())
                result = await session.execute(stmt)
                return result.scalar()

        result = benchmark.pedantic(health_check)
        assert result is not None
