# -*- coding: utf-8 -*-
"""Targeted tests for core.health_check helpers."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.health_check as hc


def _make_db_session_mock(query_time: float = 0.5, size_bytes: int = 0):
    """Return a mock AsyncSession for database health checks."""
    first_result = MagicMock()
    first_result.fetchone = MagicMock(return_value=(1,))
    size_result = MagicMock()
    size_result.scalar = MagicMock(return_value=size_bytes)

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[first_result, size_result])
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


class TestRegisterAlertCallback:
    def test_register_alert_callback(self) -> None:
        cb = AsyncMock()
        hc.register_alert_callback(cb)
        assert cb in hc._alert_callbacks


class TestCheckDatabaseHealth:
    @pytest.mark.asyncio
    async def test_healthy(self, monkeypatch) -> None:
        cm = _make_db_session_mock(query_time=0.5, size_bytes=1024 * 1024)
        with patch("core.db_engine.AsyncSessionLocal", return_value=cm):
            result = await hc.check_database_health()
        assert result["status"] == "healthy"
        assert "query_time_ms" in result["metrics"]

    @pytest.mark.asyncio
    async def test_unhealthy(self, monkeypatch) -> None:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
        cm.__aexit__ = AsyncMock(return_value=None)
        with patch("core.db_engine.AsyncSessionLocal", return_value=cm):
            result = await hc.check_database_health()
        assert result["status"] == "unhealthy"


class TestCheckRedisHealth:
    @pytest.mark.asyncio
    async def test_healthy(self, monkeypatch) -> None:
        mock_redis = MagicMock()
        mock_redis.ping = MagicMock(return_value=True)
        mock_redis.info = MagicMock(return_value={"connected_clients": 5, "used_memory": 1024})
        monkeypatch.setattr("redis.Redis", lambda **_: mock_redis)
        result = await hc.check_redis_health()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_unhealthy(self, monkeypatch) -> None:
        def boom(**_):
            raise RuntimeError("redis down")

        monkeypatch.setattr("redis.Redis", boom)
        result = await hc.check_redis_health()
        assert result["status"] == "unhealthy"


class TestCheckSystemResources:
    @pytest.fixture(autouse=True)
    def _patch_psutil(self, monkeypatch) -> None:
        self.vmem = MagicMock()
        self.vmem.percent = 50.0
        self.vmem.used = 1024 * 1024 * 1024
        self.vmem.total = 2 * 1024 * 1024 * 1024

        self.disk = MagicMock()
        self.disk.percent = 50.0
        self.disk.used = 100 * 1024**3
        self.disk.total = 200 * 1024**3

        monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 50.0)
        monkeypatch.setattr("psutil.virtual_memory", lambda: self.vmem)
        monkeypatch.setattr("psutil.disk_usage", lambda _: self.disk)

    @pytest.mark.asyncio
    async def test_healthy(self) -> None:
        result = await hc.check_system_resources()
        assert result["status"] == "healthy"
        assert result["threshold_exceeded"] is False

    @pytest.mark.asyncio
    async def test_degraded(self, monkeypatch) -> None:
        monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 95.0)
        result = await hc.check_system_resources()
        assert result["status"] == "degraded"
        assert result["threshold_exceeded"] is True

    @pytest.mark.asyncio
    async def test_unhealthy(self, monkeypatch) -> None:
        def boom(interval=None):
            raise RuntimeError("psutil failed")

        monkeypatch.setattr("psutil.cpu_percent", boom)
        result = await hc.check_system_resources()
        assert result["status"] == "unhealthy"


class TestCheckMetricsAndEngines:
    @pytest.mark.asyncio
    async def test_metrics_enabled(self, monkeypatch) -> None:
        monkeypatch.setattr(hc.config, "METRICS_ENABLED", True)
        result = await hc.check_metrics_health()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_metrics_disabled(self, monkeypatch) -> None:
        monkeypatch.setattr(hc.config, "METRICS_ENABLED", False)
        result = await hc.check_metrics_health()
        assert result["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_alert_engine(self) -> None:
        result = await hc.check_alert_engine_health()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_repair_engine(self) -> None:
        result = await hc.check_repair_engine_health()
        assert result["status"] == "healthy"


class TestPerformHealthChecks:
    @pytest.fixture(autouse=True)
    def _reset_state(self, monkeypatch) -> None:
        hc._alert_callbacks.clear()
        monkeypatch.setattr(hc, "_health_history", [])

    @pytest.mark.asyncio
    async def test_all_healthy(self, monkeypatch) -> None:
        monkeypatch.setattr(
            hc, "check_database_health", AsyncMock(return_value={"status": "healthy"})
        )
        monkeypatch.setattr(hc, "check_redis_health", AsyncMock(return_value={"status": "healthy"}))
        monkeypatch.setattr(
            hc, "check_system_resources", AsyncMock(return_value={"status": "healthy"})
        )
        monkeypatch.setattr(
            hc, "check_metrics_health", AsyncMock(return_value={"status": "healthy"})
        )
        monkeypatch.setattr(
            hc, "check_alert_engine_health", AsyncMock(return_value={"status": "healthy"})
        )
        monkeypatch.setattr(
            hc, "check_repair_engine_health", AsyncMock(return_value={"status": "healthy"})
        )
        result = await hc.perform_health_checks()
        assert result["overall_status"] == "healthy"
        assert result["components"]["database"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_degraded_triggers_alert(self, monkeypatch) -> None:
        cb = AsyncMock()
        hc.register_alert_callback(cb)
        monkeypatch.setattr(
            hc,
            "check_database_health",
            AsyncMock(
                return_value={"status": "degraded", "threshold_exceeded": True, "message": "slow"}
            ),
        )
        monkeypatch.setattr(hc, "check_redis_health", AsyncMock(return_value={"status": "healthy"}))
        monkeypatch.setattr(
            hc, "check_system_resources", AsyncMock(return_value={"status": "healthy"})
        )
        monkeypatch.setattr(
            hc, "check_metrics_health", AsyncMock(return_value={"status": "healthy"})
        )
        monkeypatch.setattr(
            hc, "check_alert_engine_health", AsyncMock(return_value={"status": "healthy"})
        )
        monkeypatch.setattr(
            hc, "check_repair_engine_health", AsyncMock(return_value={"status": "healthy"})
        )
        result = await hc.perform_health_checks()
        assert result["overall_status"] == "degraded"
        cb.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unhealthy_and_history(self, monkeypatch) -> None:
        monkeypatch.setattr(
            hc,
            "check_database_health",
            AsyncMock(return_value={"status": "unhealthy", "message": "down"}),
        )
        for func in [
            "check_redis_health",
            "check_system_resources",
            "check_metrics_health",
            "check_alert_engine_health",
            "check_repair_engine_health",
        ]:
            monkeypatch.setattr(hc, func, AsyncMock(return_value={"status": "healthy"}))
        result = await hc.perform_health_checks()
        assert result["overall_status"] == "unhealthy"
        assert len(hc._health_history) == 1


class TestAnalyzeTrend:
    def test_insufficient_data(self) -> None:
        original = hc._health_history
        hc._health_history = []
        trend = hc._analyze_health_trend()
        assert trend["trend"] == "insufficient_data"
        hc._health_history = original

    def test_improving(self) -> None:
        original = hc._health_history
        hc._health_history = [
            {"timestamp": datetime.now(timezone.utc).isoformat(), "overall_status": "healthy"}
            for _ in range(9)
        ]
        trend = hc._analyze_health_trend()
        assert trend["trend"] == "improving"
        hc._health_history = original

    def test_deteriorating(self) -> None:
        original = hc._health_history
        hc._health_history = [
            {"timestamp": datetime.now(timezone.utc).isoformat(), "overall_status": "unhealthy"}
            for _ in range(6)
        ]
        trend = hc._analyze_health_trend()
        assert trend["trend"] == "deteriorating"
        hc._health_history = original

    def test_history_filtering(self) -> None:
        original = hc._health_history
        now = datetime.now(timezone.utc)
        hc._health_history = [
            {"timestamp": now.isoformat(), "overall_status": "healthy"},
            {"timestamp": (now - timedelta(hours=25)).isoformat(), "overall_status": "unhealthy"},
        ]
        result = hc.get_health_history(hours=24)
        assert len(result) == 1
        hc._health_history = original


class TestRecoverySuggestions:
    def test_database_suggestion(self) -> None:
        status = {
            "components": {
                "database": {"status": "unhealthy"},
                "redis": {"status": "healthy"},
                "system_resources": {"status": "healthy", "issues": []},
            }
        }
        suggestions = hc.get_recovery_suggestions(status)
        assert any("database" in s.lower() for s in suggestions)

    def test_system_resources_suggestions(self) -> None:
        status = {
            "components": {
                "system_resources": {"status": "degraded", "issues": ["High CPU usage: 95%"]},
                "redis": {"status": "healthy"},
            }
        }
        suggestions = hc.get_recovery_suggestions(status)
        assert any("CPU" in s for s in suggestions)

    def test_healthy_suggestions(self) -> None:
        status = {"components": {"database": {"status": "healthy"}}}
        suggestions = hc.get_recovery_suggestions(status)
        assert any("healthy" in s.lower() for s in suggestions)


class TestStatusHelpers:
    def test_liveness(self) -> None:
        result = hc.get_liveness_status()
        assert result["status"] == "alive"

    def test_readiness_with_cache(self, monkeypatch) -> None:
        monkeypatch.setattr(
            hc, "_health_cache", {"last_check": "now", "overall_status": "degraded"}
        )
        result = hc.get_readiness_status()
        assert result["status"] == "ready"

    def test_readiness_without_cache(self, monkeypatch) -> None:
        monkeypatch.setattr(hc, "_health_cache", {})
        result = hc.get_readiness_status()
        assert result["status"] == "ready"

    def test_detailed_health(self, monkeypatch) -> None:
        cache = {"overall_status": "healthy"}
        monkeypatch.setattr(hc, "_health_cache", cache)
        assert hc.get_detailed_health() == cache
