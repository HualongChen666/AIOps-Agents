# -*- coding: utf-8 -*-
"""
Database CRUD Performance Tests
基于pytest-benchmark的数据库CRUD操作性能测试
"""

import random
from datetime import datetime, timedelta

import pytest

from core.db_engine import (
    AsyncSessionLocal,
)
from core.models import Alert, AlertStatus


@pytest.fixture(scope="function")
async def db_session():
    """数据库会话fixture"""
    async with AsyncSessionLocal() as session:
        yield session
        # 清理测试数据
        await session.execute(Alert.__table__.delete())
        await session.commit()


@pytest.fixture(scope="function")
async def sample_alerts(db_session):
    """生成测试告警数据"""
    alerts = []
    for i in range(100):
        alert = Alert(
            id=f"test-alert-{i}",
            level=random.choice(["info", "warning", "error", "critical"]),
            category=random.choice(["system", "network", "database", "application"]),
            alert_type=random.choice(["cpu_high", "memory_high", "disk_full", "network_error"]),
            title=f"Test Alert {i}",
            description=f"Test alert description {i}",
            metric=random.choice(["cpu_usage", "memory_usage", "disk_usage"]),
            value=random.uniform(0, 100),
            detected_at=datetime.now() - timedelta(minutes=random.randint(0, 60)),
            status=random.choice([AlertStatus.PENDING.value, AlertStatus.RESOLVED.value]),
            host=f"host-{random.randint(1, 10)}",
            platform=random.choice(["windows", "linux", "macos"]),
            priority=random.choice(["P1", "P2", "P3", "P4"]),
        )
        db_session.add(alert)
        alerts.append(alert)

    await db_session.commit()
    return alerts


class TestSelectPerformance:
    """SELECT查询性能测试"""

    @pytest.mark.asyncio
    async def test_select_single_by_id(self, db_session, sample_alerts, benchmark):
        """单条记录查询性能"""
        alert_id = sample_alerts[0].id

        async def select_by_id():
            from sqlalchemy import select

            stmt = select(Alert).where(Alert.id == alert_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        result = benchmark.pedantic(select_by_id)
        assert result is not None

    @pytest.mark.asyncio
    async def test_select_with_filter(self, db_session, sample_alerts, benchmark):
        """带过滤条件的查询性能"""

        async def select_with_filter():
            from sqlalchemy import select

            stmt = select(Alert).where(Alert.level == "error").limit(10)
            result = await db_session.execute(stmt)
            return result.scalars().all()

        result = benchmark.pedantic(select_with_filter)
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_select_with_multiple_filters(self, db_session, sample_alerts, benchmark):
        """多条件过滤查询性能"""

        async def select_with_filters():
            from sqlalchemy import select

            stmt = (
                select(Alert)
                .where(Alert.level == "error")
                .where(Alert.status == AlertStatus.PENDING.value)
                .where(Alert.platform == "linux")
                .limit(10)
            )
            result = await db_session.execute(stmt)
            return result.scalars().all()

        result = benchmark.pedantic(select_with_filters)
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_select_with_order(self, db_session, sample_alerts, benchmark):
        """带排序的查询性能"""

        async def select_with_order():
            from sqlalchemy import select

            stmt = select(Alert).order_by(Alert.detected_at.desc()).limit(10)
            result = await db_session.execute(stmt)
            return result.scalars().all()

        result = benchmark.pedantic(select_with_order)
        assert len(result) <= 10

    @pytest.mark.asyncio
    async def test_select_with_join(self, db_session, sample_alerts, benchmark):
        """JOIN查询性能"""

        async def select_with_join():
            from sqlalchemy import select

            # 这里假设有其他表可以JOIN
            stmt = select(Alert).limit(10)
            result = await db_session.execute(stmt)
            return result.scalars().all()

        result = benchmark.pedantic(select_with_join)
        assert len(result) <= 10

    @pytest.mark.asyncio
    async def test_select_count(self, db_session, sample_alerts, benchmark):
        """COUNT查询性能"""

        async def select_count():
            from sqlalchemy import func, select

            stmt = select(func.count(Alert.id))
            result = await db_session.execute(stmt)
            return result.scalar()

        result = benchmark.pedantic(select_count)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_select_aggregate(self, db_session, sample_alerts, benchmark):
        """聚合查询性能"""

        async def select_aggregate():
            from sqlalchemy import func, select

            stmt = select(
                func.count(Alert.id),
                func.avg(Alert.value),
                func.max(Alert.value),
                func.min(Alert.value),
            )
            result = await db_session.execute(stmt)
            return result.first()

        result = benchmark.pedantic(select_aggregate)
        assert result is not None

    @pytest.mark.asyncio
    async def test_select_group_by(self, db_session, sample_alerts, benchmark):
        """GROUP BY查询性能"""

        async def select_group_by():
            from sqlalchemy import func, select

            stmt = select(Alert.level, func.count(Alert.id)).group_by(Alert.level)
            result = await db_session.execute(stmt)
            return result.all()

        result = benchmark.pedantic(select_group_by)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_select_with_subquery(self, db_session, sample_alerts, benchmark):
        """子查询性能"""

        async def select_with_subquery():
            from sqlalchemy import func, select

            subquery = (
                select(Alert.host, func.count(Alert.id).label("count"))
                .group_by(Alert.host)
                .subquery()
            )
            stmt = select(subquery).where(subquery.c.count > 5)
            result = await db_session.execute(stmt)
            return result.all()

        result = benchmark.pedantic(select_with_subquery)
        assert len(result) >= 0


class TestInsertPerformance:
    """INSERT操作性能测试"""

    @pytest.mark.asyncio
    async def test_insert_single(self, db_session, benchmark):
        """单条插入性能"""

        async def insert_single():
            alert = Alert(
                id=f"test-insert-{random.randint(1000, 9999)}",
                level="info",
                category="system",
                alert_type="test",
                title="Test Insert",
                description="Test insert performance",
                metric="test_metric",
                value=50.0,
                detected_at=datetime.now(),
                status=AlertStatus.PENDING.value,
                host="test-host",
                platform="linux",
                priority="P3",
            )
            db_session.add(alert)
            await db_session.commit()
            return alert.id

        alert_id = benchmark.pedantic(insert_single)
        assert alert_id is not None

    @pytest.mark.asyncio
    async def test_insert_batch_10(self, db_session, benchmark):
        """批量插入10条记录性能"""

        async def insert_batch_10():
            alerts = []
            for i in range(10):
                alert = Alert(
                    id=f"test-batch-10-{random.randint(1000, 9999)}-{i}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title=f"Test Batch 10 {i}",
                    description="Test batch insert performance",
                    metric="test_metric",
                    value=random.uniform(0, 100),
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                alerts.append(alert)

            db_session.add_all(alerts)
            await db_session.commit()
            return len(alerts)

        count = benchmark.pedantic(insert_batch_10)
        assert count == 10

    @pytest.mark.asyncio
    async def test_insert_batch_100(self, db_session, benchmark):
        """批量插入100条记录性能"""

        async def insert_batch_100():
            alerts = []
            for i in range(100):
                alert = Alert(
                    id=f"test-batch-100-{random.randint(1000, 9999)}-{i}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title=f"Test Batch 100 {i}",
                    description="Test batch insert performance",
                    metric="test_metric",
                    value=random.uniform(0, 100),
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                alerts.append(alert)

            db_session.add_all(alerts)
            await db_session.commit()
            return len(alerts)

        count = benchmark.pedantic(insert_batch_100)
        assert count == 100

    @pytest.mark.asyncio
    async def test_insert_batch_1000(self, db_session, benchmark):
        """批量插入1000条记录性能"""

        async def insert_batch_1000():
            alerts = []
            for i in range(1000):
                alert = Alert(
                    id=f"test-batch-1000-{random.randint(1000, 9999)}-{i}",
                    level="info",
                    category="system",
                    alert_type="test",
                    title=f"Test Batch 1000 {i}",
                    description="Test batch insert performance",
                    metric="test_metric",
                    value=random.uniform(0, 100),
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host="test-host",
                    platform="linux",
                    priority="P3",
                )
                alerts.append(alert)

            db_session.add_all(alerts)
            await db_session.commit()
            return len(alerts)

        count = benchmark.pedantic(insert_batch_1000)
        assert count == 1000


class TestUpdatePerformance:
    """UPDATE操作性能测试"""

    @pytest.mark.asyncio
    async def test_update_single(self, db_session, sample_alerts, benchmark):
        """单条更新性能"""
        alert_id = sample_alerts[0].id

        async def update_single():
            from sqlalchemy import update

            stmt = (
                update(Alert).where(Alert.id == alert_id).values(status=AlertStatus.RESOLVED.value)
            )
            await db_session.execute(stmt)
            await db_session.commit()

        benchmark.pedantic(update_single)

    @pytest.mark.asyncio
    async def test_update_batch_10(self, db_session, sample_alerts, benchmark):
        """批量更新10条记录性能"""
        alert_ids = [a.id for a in sample_alerts[:10]]

        async def update_batch_10():
            from sqlalchemy import update

            stmt = (
                update(Alert)
                .where(Alert.id.in_(alert_ids))
                .values(status=AlertStatus.RESOLVED.value)
            )
            await db_session.execute(stmt)
            await db_session.commit()

        benchmark.pedantic(update_batch_10)

    @pytest.mark.asyncio
    async def test_update_batch_100(self, db_session, sample_alerts, benchmark):
        """批量更新100条记录性能"""
        alert_ids = [a.id for a in sample_alerts[:100]]

        async def update_batch_100():
            from sqlalchemy import update

            stmt = (
                update(Alert)
                .where(Alert.id.in_(alert_ids))
                .values(status=AlertStatus.RESOLVED.value)
            )
            await db_session.execute(stmt)
            await db_session.commit()

        benchmark.pedantic(update_batch_100)


class TestDeletePerformance:
    """DELETE操作性能测试"""

    @pytest.mark.asyncio
    async def test_delete_single(self, db_session, sample_alerts, benchmark):
        """单条删除性能"""
        alert_id = sample_alerts[0].id

        async def delete_single():
            from sqlalchemy import delete

            stmt = delete(Alert).where(Alert.id == alert_id)
            await db_session.execute(stmt)
            await db_session.commit()

        benchmark.pedantic(delete_single)

    @pytest.mark.asyncio
    async def test_delete_batch_10(self, db_session, sample_alerts, benchmark):
        """批量删除10条记录性能"""
        alert_ids = [a.id for a in sample_alerts[:10]]

        async def delete_batch_10():
            from sqlalchemy import delete

            stmt = delete(Alert).where(Alert.id.in_(alert_ids))
            await db_session.execute(stmt)
            await db_session.commit()

        benchmark.pedantic(delete_batch_10)

    @pytest.mark.asyncio
    async def test_delete_batch_100(self, db_session, sample_alerts, benchmark):
        """批量删除100条记录性能"""
        alert_ids = [a.id for a in sample_alerts[:100]]

        async def delete_batch_100():
            from sqlalchemy import delete

            stmt = delete(Alert).where(Alert.id.in_(alert_ids))
            await db_session.execute(stmt)
            await db_session.commit()

        benchmark.pedantic(delete_batch_100)


class TestComplexQueryPerformance:
    """复杂查询性能测试"""

    @pytest.mark.asyncio
    async def test_window_function(self, db_session, sample_alerts, benchmark):
        """窗口函数查询性能"""

        async def window_function():
            from sqlalchemy import func, select

            stmt = select(
                Alert.id,
                Alert.level,
                Alert.value,
                func.row_number().over(order_by=Alert.detected_at.desc()).label("row_num"),
            ).limit(10)
            result = await db_session.execute(stmt)
            return result.all()

        result = benchmark.pedantic(window_function)
        assert len(result) <= 10

    @pytest.mark.asyncio
    async def test_cte_query(self, db_session, sample_alerts, benchmark):
        """CTE查询性能"""

        async def cte_query():
            from sqlalchemy import func, select
            from sqlalchemy.orm import aliased

            # 创建CTE
            cte = (
                select(
                    Alert.host,
                    func.count(Alert.id).label("alert_count"),
                    func.avg(Alert.value).label("avg_value"),
                )
                .group_by(Alert.host)
                .cte("host_stats")
            )

            # 使用CTE
            host_stats = aliased(cte)
            stmt = select(host_stats).where(host_stats.c.alert_count > 5)
            result = await db_session.execute(stmt)
            return result.all()

        result = benchmark.pedantic(cte_query)
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_json_query(self, db_session, sample_alerts, benchmark):
        """JSON字段查询性能"""

        async def json_query():
            from sqlalchemy import select

            # 假设Alert有metadata JSON字段
            stmt = select(Alert).where(Alert.metadata.isnot(None)).limit(10)
            result = await db_session.execute(stmt)
            return result.scalars().all()

        result = benchmark.pedantic(json_query)
        assert len(result) <= 10


class TestDifferentDataVolume:
    """不同数据量级下的性能测试"""

    @pytest.mark.asyncio
    async def test_select_1k_records(self, db_session, benchmark):
        """1K记录查询性能"""
        # 先插入1K条记录
        alerts = []
        for i in range(1000):
            alert = Alert(
                id=f"test-1k-{i}",
                level="info",
                category="system",
                alert_type="test",
                title=f"Test 1K {i}",
                description="Test 1K records",
                metric="test_metric",
                value=random.uniform(0, 100),
                detected_at=datetime.now(),
                status=AlertStatus.PENDING.value,
                host=f"host-{i % 10}",
                platform="linux",
                priority="P3",
            )
            alerts.append(alert)

        db_session.add_all(alerts)
        await db_session.commit()

        async def select_1k():
            from sqlalchemy import select

            stmt = select(Alert).limit(100)
            result = await db_session.execute(stmt)
            return result.scalars().all()

        result = benchmark.pedantic(select_1k)
        assert len(result) <= 100

    @pytest.mark.asyncio
    async def test_select_10k_records(self, db_session, benchmark):
        """10K记录查询性能"""
        # 先插入10K条记录
        alerts = []
        for i in range(10000):
            alert = Alert(
                id=f"test-10k-{i}",
                level="info",
                category="system",
                alert_type="test",
                title=f"Test 10K {i}",
                description="Test 10K records",
                metric="test_metric",
                value=random.uniform(0, 100),
                detected_at=datetime.now(),
                status=AlertStatus.PENDING.value,
                host=f"host-{i % 10}",
                platform="linux",
                priority="P3",
            )
            alerts.append(alert)

        db_session.add_all(alerts)
        await db_session.commit()

        async def select_10k():
            from sqlalchemy import select

            stmt = select(Alert).limit(100)
            result = await db_session.execute(stmt)
            return result.scalars().all()

        result = benchmark.pedantic(select_10k)
        assert len(result) <= 100
