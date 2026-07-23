# -*- coding: utf-8 -*-
"""
Index Performance Tests
索引优化效果测试
"""

import random
from datetime import datetime

import pytest

from core.db_engine import AsyncSessionLocal
from core.models import Alert, AlertStatus


class TestIndexPerformance:
    """索引性能测试"""

    @pytest.mark.asyncio
    async def test_query_with_index(self, benchmark):
        """有索引查询性能"""

        # 假设id字段有主键索引
        async def query_with_index():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                stmt = select(Alert).where(Alert.id == "test-index-1")
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        benchmark.pedantic(query_with_index)

    @pytest.mark.asyncio
    async def test_query_without_index(self, benchmark):
        """无索引查询性能"""

        # 假设description字段没有索引
        async def query_without_index():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                stmt = select(Alert).where(Alert.description == "test description")
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(query_without_index)

    @pytest.mark.asyncio
    async def test_index_vs_no_index_comparison(self, benchmark):
        """有索引vs无索引性能对比"""

        # 有索引查询（id字段）
        async def indexed_query():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                stmt = select(Alert).where(Alert.id == "test-comparison-1")
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        indexed_time = benchmark.pedantic(indexed_query)

        # 无索引查询（description字段）
        async def non_indexed_query():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                stmt = select(Alert).where(Alert.description == "test description for comparison")
                result = await session.execute(stmt)
                return result.scalars().all()

        non_indexed_time = benchmark.pedantic(non_indexed_query)

        # 计算性能提升
        if non_indexed_time > 0:
            improvement = (non_indexed_time - indexed_time) / non_indexed_time * 100
            return improvement
        return 0

    @pytest.mark.asyncio
    async def test_composite_index(self, benchmark):
        """复合索引查询性能"""

        async def composite_index_query():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                # 假设有(level, status)的复合索引
                stmt = (
                    select(Alert)
                    .where(Alert.level == "error")
                    .where(Alert.status == AlertStatus.PENDING.value)
                    .limit(10)
                )
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(composite_index_query)

    @pytest.mark.asyncio
    async def test_range_query_with_index(self, benchmark):
        """范围查询索引性能"""

        async def range_query():
            async with AsyncSessionLocal() as session:
                # 假设detected_at字段有索引
                from datetime import datetime, timedelta

                from sqlalchemy import select

                start_time = datetime.now() - timedelta(hours=1)
                stmt = select(Alert).where(Alert.detected_at >= start_time).limit(10)
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(range_query)

    @pytest.mark.asyncio
    async def test_sort_with_index(self, benchmark):
        """排序索引性能"""

        async def sort_with_index():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                # 假设detected_at字段有索引
                stmt = select(Alert).order_by(Alert.detected_at.desc()).limit(10)
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(sort_with_index)

    @pytest.mark.asyncio
    async def test_sort_without_index(self, benchmark):
        """无索引排序性能"""

        async def sort_without_index():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                # 假设description字段没有索引
                stmt = select(Alert).order_by(Alert.description).limit(10)
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(sort_without_index)

    @pytest.mark.asyncio
    async def test_index_creation_performance(self, benchmark):
        """索引创建性能"""

        async def create_index():
            async with AsyncSessionLocal() as session:
                # 创建索引
                await session.execute("CREATE INDEX IF NOT EXISTS idx_alert_level ON alerts(level)")
                await session.commit()

        benchmark.pedantic(create_index)

    @pytest.mark.asyncio
    async def test_index_drop_performance(self, benchmark):
        """索引删除性能"""

        async def drop_index():
            async with AsyncSessionLocal() as session:
                # 删除索引
                await session.execute("DROP INDEX IF EXISTS idx_alert_level")
                await session.commit()

        benchmark.pedantic(drop_index)

    @pytest.mark.asyncio
    async def test_index_rebuild_performance(self, benchmark):
        """索引重建性能"""

        async def rebuild_index():
            async with AsyncSessionLocal() as session:
                # 重建索引
                await session.execute("REINDEX INDEX idx_alert_level")
                await session.commit()

        benchmark.pedantic(rebuild_index)

    @pytest.mark.asyncio
    async def test_partial_index(self, benchmark):
        """部分索引查询性能"""

        async def partial_index_query():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                # 部分索引只包含特定条件的记录
                stmt = (
                    select(Alert)
                    .where(Alert.level == "critical")
                    .where(Alert.status == AlertStatus.PENDING.value)
                    .limit(10)
                )
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(partial_index_query)

    @pytest.mark.asyncio
    async def test_covering_index(self, benchmark):
        """覆盖索引查询性能"""

        async def covering_index_query():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                # 覆盖索引包含查询所需的所有字段
                stmt = select(Alert.id, Alert.level, Alert.status).limit(10)
                result = await session.execute(stmt)
                return result.all()

        benchmark.pedantic(covering_index_query)


class TestIndexEffectiveness:
    """索引有效性测试"""

    @pytest.mark.asyncio
    async def test_index_selectivity(self):
        """索引选择性测试"""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import func, select

            # 计算字段的选择性
            stmt = select(func.count(func.distinct(Alert.level)), func.count(Alert.id))
            result = await session.execute(stmt)
            distinct_count, total_count = result.first()

            selectivity = distinct_count / total_count if total_count > 0 else 0
            return selectivity

    @pytest.mark.asyncio
    async def test_index_usage_statistics(self):
        """索引使用统计"""
        async with AsyncSessionLocal() as session:
            # 查询索引使用统计
            result = await session.execute(
                "SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch "
                "FROM pg_stat_user_indexes WHERE tablename = 'alerts'"
            )
            stats = result.fetchall()

            return [
                {
                    "schemaname": row[0],
                    "tablename": row[1],
                    "indexname": row[2],
                    "idx_scan": row[3],
                    "idx_tup_read": row[4],
                    "idx_tup_fetch": row[5],
                }
                for row in stats
            ]

    @pytest.mark.asyncio
    async def test_unused_indexes(self):
        """未使用索引检测"""
        async with AsyncSessionLocal() as session:
            # 查询未使用的索引
            result = await session.execute(
                "SELECT schemaname, tablename, indexname "
                "FROM pg_stat_user_indexes "
                "WHERE idx_scan = 0 AND indexname NOT LIKE '%_pkey'"
            )
            unused = result.fetchall()

            return [
                {
                    "schemaname": row[0],
                    "tablename": row[1],
                    "indexname": row[2],
                }
                for row in unused
            ]

    @pytest.mark.asyncio
    async def test_index_size(self):
        """索引大小分析"""
        async with AsyncSessionLocal() as session:
            # 查询索引大小
            result = await session.execute(
                "SELECT indexname, pg_size_pretty(pg_relation_size(indexrelid)) as size "
                "FROM pg_stat_user_indexes WHERE tablename = 'alerts'"
            )
            sizes = result.fetchall()

            return [
                {
                    "indexname": row[0],
                    "size": row[1],
                }
                for row in sizes
            ]


class TestDifferentDataVolumeWithIndex:
    """不同数据量下的索引性能测试"""

    @pytest.mark.asyncio
    async def test_index_performance_1k(self, benchmark):
        """1K数据量索引性能"""
        # 先插入1K条数据
        async with AsyncSessionLocal() as session:
            alerts = []
            for i in range(1000):
                alert = Alert(
                    id=f"test-index-1k-{i}",
                    level=random.choice(["info", "warning", "error", "critical"]),
                    category="system",
                    alert_type="test",
                    title=f"Test Index 1K {i}",
                    description="Test index performance",
                    metric="test_metric",
                    value=random.uniform(0, 100),
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host=f"host-{i % 10}",
                    platform="linux",
                    priority="P3",
                )
                alerts.append(alert)

            session.add_all(alerts)
            await session.commit()

        async def query_1k():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                stmt = select(Alert).where(Alert.level == "error").limit(10)
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(query_1k)

    @pytest.mark.asyncio
    async def test_index_performance_10k(self, benchmark):
        """10K数据量索引性能"""
        # 先插入10K条数据
        async with AsyncSessionLocal() as session:
            alerts = []
            for i in range(10000):
                alert = Alert(
                    id=f"test-index-10k-{i}",
                    level=random.choice(["info", "warning", "error", "critical"]),
                    category="system",
                    alert_type="test",
                    title=f"Test Index 10K {i}",
                    description="Test index performance",
                    metric="test_metric",
                    value=random.uniform(0, 100),
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host=f"host-{i % 10}",
                    platform="linux",
                    priority="P3",
                )
                alerts.append(alert)

            session.add_all(alerts)
            await session.commit()

        async def query_10k():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                stmt = select(Alert).where(Alert.level == "error").limit(10)
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(query_10k)

    @pytest.mark.asyncio
    async def test_index_performance_100k(self, benchmark):
        """100K数据量索引性能"""
        # 先插入100K条数据
        async with AsyncSessionLocal() as session:
            alerts = []
            for i in range(100000):
                alert = Alert(
                    id=f"test-index-100k-{i}",
                    level=random.choice(["info", "warning", "error", "critical"]),
                    category="system",
                    alert_type="test",
                    title=f"Test Index 100K {i}",
                    description="Test index performance",
                    metric="test_metric",
                    value=random.uniform(0, 100),
                    detected_at=datetime.now(),
                    status=AlertStatus.PENDING.value,
                    host=f"host-{i % 10}",
                    platform="linux",
                    priority="P3",
                )
                alerts.append(alert)

            session.add_all(alerts)
            await session.commit()

        async def query_100k():
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                stmt = select(Alert).where(Alert.level == "error").limit(10)
                result = await session.execute(stmt)
                return result.scalars().all()

        benchmark.pedantic(query_100k)


# 导入random
