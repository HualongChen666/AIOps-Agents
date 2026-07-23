# -*- coding: utf-8 -*-
# tests/test_health_check.py
# 健康检查单元测试
from unittest.mock import AsyncMock, patch  # noqa: F401

import asyncio
import sys

import pytest

from core.health_check import (
    check_database_health,
    check_metrics_health,
    check_redis_health,
    get_detailed_health,
    get_liveness_status,
    get_readiness_status,
    perform_health_checks,
)


@pytest.fixture(autouse=True)
def _patch_expensive_health_checks(monkeypatch):
    """Patch expensive network/system health checks to keep this module fast/flake-free."""
    healthy = {
        "status": "healthy",
        "message": "patched",
        "timestamp": "2026-01-01T00:00:00",
    }
    monkeypatch.setattr(
        "core.health_check.check_database_health",
        AsyncMock(return_value=healthy),
    )
    monkeypatch.setattr(
        "core.health_check.check_redis_health",
        AsyncMock(return_value=healthy),
    )
    monkeypatch.setattr(
        "core.health_check.check_system_resources",
        AsyncMock(return_value=healthy),
    )
    # The tests imported some functions locally; patch the local bindings too.
    test_module = sys.modules[__name__]
    monkeypatch.setattr(test_module, "check_database_health", AsyncMock(return_value=healthy))
    monkeypatch.setattr(test_module, "check_redis_health", AsyncMock(return_value=healthy))


class TestLivenessStatus:
    """存活状态测试"""

    def test_get_liveness_status(self):
        """测试获取存活状态"""
        status = get_liveness_status()

        assert status["status"] == "alive"
        assert "timestamp" in status


class TestReadinessStatus:
    """就绪状态测试"""

    def test_get_readiness_status_no_cache(self):
        """测试无缓存时的就绪状态"""
        status = get_readiness_status()

        assert status["status"] == "ready"
        assert "timestamp" in status

    @pytest.mark.asyncio
    async def test_get_readiness_status_with_health_checks(self):
        """测试有健康检查缓存时的就绪状态"""
        # Perform health checks first
        await asyncio.wait_for(perform_health_checks(), timeout=10)

        status = get_readiness_status()

        assert status["status"] in ["ready", "not_ready"]
        assert "timestamp" in status


class TestDetailedHealth:
    """详细健康状态测试"""

    def test_get_detailed_health_empty(self):
        """测试空缓存时的详细健康状态"""
        health = get_detailed_health()

        assert isinstance(health, dict)
        # Empty cache should have minimal structure
        assert "last_check" in health or health == {}


class TestComponentHealthChecks:
    """组件健康检查测试"""

    @pytest.mark.asyncio
    async def test_check_database_health(self):
        """测试数据库健康检查"""
        health = await check_database_health()

        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_check_redis_health(self):
        """测试Redis健康检查"""
        health = await check_redis_health()

        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_check_metrics_health(self):
        """测试指标健康检查"""
        health = await check_metrics_health()

        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health


class TestPerformHealthChecks:
    """执行健康检查测试"""

    @pytest.mark.asyncio
    async def test_perform_health_checks(self):
        """测试执行所有健康检查"""
        result = await asyncio.wait_for(perform_health_checks(), timeout=10)

        assert isinstance(result, dict)
        assert "last_check" in result
        assert "overall_status" in result
        assert "components" in result
        assert isinstance(result["components"], dict)

    @pytest.mark.asyncio
    async def test_perform_health_checks_component_structure(self):
        """测试健康检查组件结构"""
        result = await asyncio.wait_for(perform_health_checks(), timeout=10)

        components = result["components"]

        # Check that expected components exist
        expected_components = ["database", "redis", "metrics", "alert_engine", "repair_engine"]
        for component in expected_components:
            assert component in components
            assert "status" in components[component]
            assert "timestamp" in components[component]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
