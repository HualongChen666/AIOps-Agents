# -*- coding: utf-8 -*-
import logging

"""
Transaction Performance Tests
事务处理性能测试
"""

import asyncio
from datetime import datetime

import pytest

from core.db_engine import AsyncSessionLocal
from core.models import Alert, AlertStatus


class TestTransactionPerformance:
    """事务性能测试"""

    @pytest.mark.asyncio
    async def test_single_transaction(self, benchmark):
        """单事务性能"""

        async def single_transaction():
            async with AsyncSessionLocal() as session:
                alert = Alert(
                    id=f"test-single-tx-{datetime.now().timestamp()}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title="Test Single Transaction",
                    description="Test single transaction performance",
                    metric="test_metric",
                    value=50.0,
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                session.add(alert)
                await session.commit()

        benchmark.pedantic(single_transaction)

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, benchmark):
        """事务回滚性能"""

        async def transaction_rollback():
            async with AsyncSessionLocal() as session:
                alert = Alert(
                    id=f"test-rollback-{datetime.now().timestamp()}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title="Test Rollback",
                    description="Test rollback performance",
                    metric="test_metric",
                    value=50.0,
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                session.add(alert)
                await session.rollback()

        benchmark.pedantic(transaction_rollback)

    @pytest.mark.asyncio
    async def test_batch_transaction_10(self, benchmark):
        """批量事务10条记录性能"""

        async def batch_transaction_10():
            async with AsyncSessionLocal() as session:
                alerts = []
                for i in range(10):
                    alert = Alert(
                        id=f"test-batch-tx-10-{datetime.now().timestamp()}-{i}",
                        level="info",
                        category="system",
                        alert_type="test",
                        title=f"Test Batch TX 10 {i}",
                        description="Test batch transaction performance",
                        metric="test_metric",
                        value=50.0,
                        detected_at=datetime.now(),
                        status=AlertStatus.PENDING.value,
                        host="test-host",
                        platform="linux",
                        priority="P3",
                    )
                    alerts.append(alert)

                session.add_all(alerts)
                await session.commit()

        benchmark.pedantic(batch_transaction_10)

    @pytest.mark.asyncio
    async def test_batch_transaction_100(self, benchmark):
        """批量事务100条记录性能"""

        async def batch_transaction_100():
            async with AsyncSessionLocal() as session:
                alerts = []
                for i in range(100):
                    alert = Alert(
                        id=f"test-batch-tx-100-{datetime.now().timestamp()}-{i}",
                        level="info",
                        category="system",
                        alert_type="test",
                        title=f"Test Batch TX 100 {i}",
                        description="Test batch transaction performance",
                        metric="test_metric",
                        value=50.0,
                        detected_at=datetime.now(),
                        status=AlertStatus.PENDING.value,
                        host="test-host",
                        platform="linux",
                        priority="P3",
                    )
                    alerts.append(alert)

                session.add_all(alerts)
                await session.commit()

        benchmark.pedantic(batch_transaction_100)

    @pytest.mark.asyncio
    async def test_batch_transaction_1000(self, benchmark):
        """批量事务1000条记录性能"""

        async def batch_transaction_1000():
            async with AsyncSessionLocal() as session:
                alerts = []
                for i in range(1000):
                    alert = Alert(
                        id=f"test-batch-tx-1000-{datetime.now().timestamp()}-{i}",
                        level="info",
                        category="system",
                        alert_type="test",
                        title=f"Test Batch TX 1000 {i}",
                        description="Test batch transaction performance",
                        metric="test_metric",
                        value=50.0,
                        detected_at=datetime.now(),
                        status=AlertStatus.PENDING.value,
                        host="test-host",
                        platform="linux",
                        priority="P3",
                    )
                    alerts.append(alert)

                session.add_all(alerts)
                await session.commit()

        benchmark.pedantic(batch_transaction_1000)

    @pytest.mark.asyncio
    async def test_transaction_with_read(self, benchmark):
        """读写混合事务性能"""

        async def transaction_with_read():
            async with AsyncSessionLocal() as session:
                # 先读取
                from sqlalchemy import func, select

                stmt = select(func.count(Alert.id))
                result = await session.execute(stmt)
                result.scalar()

                # 再写入
                alert = Alert(
                    id=f"test-read-write-{datetime.now().timestamp()}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title="Test Read Write",
                    description="Test read write transaction",
                    metric="test_metric",
                    value=50.0,
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                session.add(alert)
                await session.commit()

        benchmark.pedantic(transaction_with_read)

    @pytest.mark.asyncio
    async def test_nested_transaction(self, benchmark):
        """嵌套事务性能"""

        async def nested_transaction():
            async with AsyncSessionLocal() as session:
                # 外层事务
                alert1 = Alert(
                    id=f"test-nested-1-{datetime.now().timestamp()}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title="Test Nested 1",
                    description="Test nested transaction",
                    metric="test_metric",
                    value=50.0,
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                session.add(alert1)

                # 内层事务（使用savepoint）
                await session.begin_nested()
                alert2 = Alert(
                    id=f"test-nested-2-{datetime.now().timestamp()}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title="Test Nested 2",
                    description="Test nested transaction",
                    metric="test_metric",
                    value=50.0,
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                session.add(alert2)
                await session.commit()

                await session.commit()

        benchmark.pedantic(nested_transaction)


class TestTransactionIsolation:
    """事务隔离级别测试"""

    @pytest.mark.asyncio
    async def test_read_committed_isolation(self, benchmark):
        """READ COMMITTED隔离级别性能"""

        async def read_committed():
            async with AsyncSessionLocal() as session:
                # READ COMMITTED是默认隔离级别
                from sqlalchemy import func, select

                stmt = select(func.count(Alert.id))
                result = await session.execute(stmt)
                result.scalar()

                alert = Alert(
                    id=f"test-rc-{datetime.now().timestamp()}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title="Test Read Committed",
                    description="Test read committed isolation",
                    metric="test_metric",
                    value=50.0,
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                session.add(alert)
                await session.commit()

        benchmark.pedantic(read_committed)

    @pytest.mark.asyncio
    async def test_serializable_isolation(self, benchmark):
        """SERIALIZABLE隔离级别性能"""

        async def serializable():
            async with AsyncSessionLocal() as session:
                # 设置SERIALIZABLE隔离级别
                await session.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")

                from sqlalchemy import func, select

                stmt = select(func.count(Alert.id))
                result = await session.execute(stmt)
                result.scalar()

                alert = Alert(
                    id=f"test-serializable-{datetime.now().timestamp()}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title="Test Serializable",
                    description="Test serializable isolation",
                    metric="test_metric",
                    value=50.0,
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                session.add(alert)
                await session.commit()

        benchmark.pedantic(serializable)


class TestTransactionConcurrency:
    """事务并发测试"""

    @pytest.mark.asyncio
    async def test_concurrent_transactions_10(self, benchmark):
        """10个并发事务性能"""

        async def concurrent_10():
            async def single_transaction():
                async with AsyncSessionLocal() as session:
                    alert = Alert(
                        id=f"test-concurrent-10-{datetime.now().timestamp()}",
                        level="info",
                        category="system",
                        alert_type="test",
                        title="Test Concurrent 10",
                        description="Test concurrent transactions",
                        metric="test_metric",
                        value=50.0,
                        detected_at=datetime.now(),
                        status=AlertStatus.PENDING.value,
                        host="test-host",
                        platform="linux",
                        priority="P3",
                    )
                    session.add(alert)
                    await session.commit()

            tasks = [single_transaction() for _ in range(10)]
            await asyncio.gather(*tasks)

        benchmark.pedantic(concurrent_10)

    @pytest.mark.asyncio
    async def test_concurrent_transactions_50(self, benchmark):
        """50个并发事务性能"""

        async def concurrent_50():
            async def single_transaction():
                async with AsyncSessionLocal() as session:
                    alert = Alert(
                        id=f"test-concurrent-50-{datetime.now().timestamp()}",
                        level="info",
                        category="system",
                        alert_type="test",
                        title="Test Concurrent 50",
                        description="Test concurrent transactions",
                        metric="test_metric",
                        value=50.0,
                        detected_at=datetime.now(),
                        status=AlertStatus.PENDING.value,
                        host="test-host",
                        platform="linux",
                        priority="P3",
                    )
                    session.add(alert)
                    await session.commit()

            tasks = [single_transaction() for _ in range(50)]
            await asyncio.gather(*tasks)

        benchmark.pedantic(concurrent_50)

    @pytest.mark.asyncio
    async def test_lock_contention(self, benchmark):
        """锁竞争测试"""

        async def lock_contention():
            async def update_same_record():
                async with AsyncSessionLocal() as session:
                    # 所有事务尝试更新同一条记录
                    from sqlalchemy import update

                    stmt = (
                        update(Alert)
                        .where(Alert.id == "test-lock-record")
                        .values(status=AlertStatus.RESOLVED.value)
                    )
                    await session.execute(stmt)
                    await session.commit()

            tasks = [update_same_record() for _ in range(10)]
            await asyncio.gather(*tasks)

        benchmark.pedantic(lock_contention)

    @pytest.mark.asyncio
    async def test_deadlock_detection(self, benchmark):
        """死锁检测测试"""

        async def deadlock_scenario():
            # 模拟死锁场景
            async def transaction1():
                async with AsyncSessionLocal() as session:
                    # 获取记录1的锁
                    from sqlalchemy import update

                    stmt1 = update(Alert).where(Alert.id == "record1").values(status="locked")
                    await session.execute(stmt1)
                    await asyncio.sleep(0.01)  # 延迟以触发死锁
                    # 尝试获取记录2的锁
                    stmt2 = update(Alert).where(Alert.id == "record2").values(status="locked")
                    await session.execute(stmt2)
                    await session.commit()

            async def transaction2():
                async with AsyncSessionLocal() as session:
                    # 获取记录2的锁
                    from sqlalchemy import update

                    stmt1 = update(Alert).where(Alert.id == "record2").values(status="locked")
                    await session.execute(stmt1)
                    await asyncio.sleep(0.01)  # 延迟以触发死锁
                    # 尝试获取记录1的锁
                    stmt2 = update(Alert).where(Alert.id == "record1").values(status="locked")
                    await session.execute(stmt2)
                    await session.commit()

            try:
                await asyncio.gather(transaction1(), transaction2())
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                # 死锁会被检测到
                pass

        benchmark.pedantic(deadlock_scenario)


class TestTransactionVsSingle:
    """单条vs批量事务性能对比"""

    @pytest.mark.asyncio
    async def test_single_vs_batch_100(self, benchmark):
        """单条vs批量100条记录性能对比"""

        # 单条插入
        async def single_inserts():
            for i in range(100):
                async with AsyncSessionLocal() as session:
                    alert = Alert(
                        id=f"test-single-vs-batch-{datetime.now().timestamp()}-{i}",
                        level="info",
                        category="system",
                        alert_type="test",
                        title=f"Test Single vs Batch {i}",
                        description="Test single vs batch",
                        metric="test_metric",
                        value=50.0,
                        detected_at=datetime.now(),
                        status=AlertStatus.PENDING.value,
                        host="test-host",
                        platform="linux",
                        priority="P3",
                    )
                    session.add(alert)
                    await session.commit()

        single_time = benchmark.pedantic(single_inserts)

        # 批量插入
        async def batch_inserts():
            async with AsyncSessionLocal() as session:
                alerts = []
                for i in range(100):
                    alert = Alert(
                        id=f"test-batch-vs-single-{datetime.now().timestamp()}-{i}",
                        level="info",
                        category="system",
                        alert_type="test",
                        title=f"Test Batch vs Single {i}",
                        description="Test batch vs single",
                        metric="test_metric",
                        value=50.0,
                        detected_at=datetime.now(),
                        status=AlertStatus.PENDING.value,
                        host="test-host",
                        platform="linux",
                        priority="P3",
                    )
                    alerts.append(alert)

                session.add_all(alerts)
                await session.commit()

        batch_time = benchmark.pedantic(batch_inserts)

        # 返回性能提升
        improvement = (single_time - batch_time) / single_time * 100
        return improvement
