# -*- coding: utf-8 -*-
"""测试 core/connection_pool_optimization 的池监控与推荐逻辑"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core import connection_pool_optimization as cpo


class FakeConnection:
    def __init__(self):
        self.execute = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class BrokenConnection:
    async def __aenter__(self):
        raise RuntimeError("connect failed")

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.fixture
def fake_engine():
    engine = MagicMock()
    pool = MagicMock()
    pool.size.return_value = 10
    pool.checkedin.return_value = 3
    pool.checkedout.return_value = 5
    pool.overflow.return_value = 2
    pool._max_overflow = 20
    engine.pool = pool

    def _connect():
        return FakeConnection()

    engine.connect = _connect
    return engine


@pytest.mark.asyncio
class TestConnectionPoolMonitor:
    async def test_get_pool_status(self, fake_engine):
        monitor = cpo.ConnectionPoolMonitor(fake_engine)
        result = await monitor.get_pool_status()
        assert result["size"] == 10
        assert result["checked_out"] == 5

    async def test_get_pool_status_error(self, fake_engine, monkeypatch):
        monkeypatch.setattr(
            fake_engine.pool, "size", MagicMock(side_effect=RuntimeError("bad pool"))
        )
        monitor = cpo.ConnectionPoolMonitor(fake_engine)
        result = await monitor.get_pool_status()
        assert "error" in result

    async def test_analyze_high_utilization(self, fake_engine):
        fake_engine.pool.checkedout.return_value = 9
        monitor = cpo.ConnectionPoolMonitor(fake_engine)
        result = await monitor.analyze_pool_performance()
        assert any("High pool utilization" in r for r in result["recommendations"])

    async def test_analyze_low_utilization(self, fake_engine):
        fake_engine.pool.checkedout.return_value = 1
        monitor = cpo.ConnectionPoolMonitor(fake_engine)
        result = await monitor.analyze_pool_performance()
        assert any("Low pool utilization" in r for r in result["recommendations"])

    async def test_analyze_overflow(self, fake_engine):
        fake_engine.pool.overflow.return_value = 18
        monitor = cpo.ConnectionPoolMonitor(fake_engine)
        result = await monitor.analyze_pool_performance()
        assert any("overflow" in r.lower() for r in result["recommendations"])

    async def test_analyze_history_trim(self, fake_engine):
        monitor = cpo.ConnectionPoolMonitor(fake_engine)
        for _ in range(105):
            await monitor.analyze_pool_performance()
        assert len(monitor._metrics_history) == 100

    async def test_connection_health_healthy(self, fake_engine):
        monitor = cpo.ConnectionPoolMonitor(fake_engine)
        result = await monitor.test_connection_health()
        assert result["status"] == "healthy"

    async def test_connection_health_unhealthy(self, fake_engine, monkeypatch):
        monkeypatch.setattr(fake_engine, "connect", lambda: BrokenConnection())
        monitor = cpo.ConnectionPoolMonitor(fake_engine)
        result = await monitor.test_connection_health()
        assert result["status"] == "unhealthy"


@pytest.mark.asyncio
class TestCreateOptimizedEngine:
    async def test_create_engine(self, monkeypatch):
        fake_engine = MagicMock()
        monkeypatch.setattr(
            "core.connection_pool_optimization.create_async_engine",
            lambda url, **kw: fake_engine,
        )
        result = await cpo.create_optimized_engine("postgresql+asyncpg://x")
        assert result is fake_engine


@pytest.mark.asyncio
class TestOptimizeExistingEngine:
    async def test_optimize_existing(self, fake_engine):
        result = await cpo.optimize_existing_engine(fake_engine)
        assert result["status"] == "analysis_completed"
        assert "recommended_config" in result


class TestGetRecommendations:
    def test_read_heavy(self):
        result = cpo.get_connection_pool_recommendations("read_heavy")
        assert result["pool_size"] == 30

    def test_write_heavy(self):
        result = cpo.get_connection_pool_recommendations("write_heavy")
        assert result["pool_size"] == 15

    def test_mixed(self):
        result = cpo.get_connection_pool_recommendations("mixed")
        assert result["pool_size"] == 20

    def test_analytics(self):
        result = cpo.get_connection_pool_recommendations("analytics")
        assert result["pool_timeout"] == 120

    def test_unknown_defaults_to_mixed(self):
        result = cpo.get_connection_pool_recommendations("unknown")
        assert result["pool_size"] == 20
