# -*- coding: utf-8 -*-
"""Unit tests for health_check.py - Health check for LLM router service."""

import pytest
import time
from unittest.mock import patch, MagicMock
from extensions.addons.ai_plus.llm_router_service.health_check import (
    HealthCheckEngine,
    _START_TIME,
)
from extensions.addons.ai_plus.llm_router_service.schemas import ServiceHealth


class TestHealthCheckEngine:
    """Test HealthCheckEngine class."""

    @pytest.mark.asyncio
    async def test_health_check_basic(self):
        """Test basic health check."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="llm-router", index_size=5)

        assert isinstance(health, ServiceHealth)
        assert health.status in ["ok", "degraded"]
        assert health.service == "llm-router"
        # index_size is a parameter, not a field in ServiceHealth
        assert health.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_health_check_different_service_names(self):
        """Test health check with different service names."""
        engine = HealthCheckEngine()
        services = ["llm-router", "api-gateway", "auth-service", "data-processor"]

        for service in services:
            health = await engine.check(service_name=service)
            assert health.service == service

    @pytest.mark.asyncio
    async def test_health_check_different_index_sizes(self):
        """Test health check with different index sizes."""
        engine = HealthCheckEngine()
        sizes = [0, 1, 10, 100, 1000]

        for size in sizes:
            health = await engine.check(service_name="test", index_size=size)
            # index_size is a parameter, not a field in ServiceHealth
            assert health.service == "test"

    @pytest.mark.asyncio
    async def test_health_check_uptime(self):
        """Test health check uptime calculation."""
        engine = HealthCheckEngine()
        health1 = await engine.check(service_name="test")

        # Wait a bit
        time.sleep(0.1)

        health2 = await engine.check(service_name="test")

        assert health2.uptime_seconds >= health1.uptime_seconds
        assert health2.uptime_seconds - health1.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_health_check_with_psutil_available(self):
        """Test health check when psutil is available."""
        import sys
        mock_psutil = MagicMock()
        mock_vm = MagicMock()
        mock_vm.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_vm

        mock_disk = MagicMock()
        mock_disk.percent = 80.0
        mock_psutil.disk_usage.return_value = mock_disk

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            # Re-import the module to use the mocked psutil
            import importlib
            import extensions.addons.ai_plus.llm_router_service.health_check as hc_module
            importlib.reload(hc_module)

            engine = hc_module.HealthCheckEngine()
            health = await engine.check(service_name="test")

            assert health.status == "ok"
            assert health.service == "test"

    @pytest.mark.asyncio
    async def test_health_check_default_index_size(self):
        """Test health check with default index size."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="test")

        # ServiceHealth doesn't have index_size field
        assert health.service == "test"

    @pytest.mark.asyncio
    async def test_health_check_zero_index_size(self):
        """Test health check with zero index size."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="test", index_size=0)

        # ServiceHealth doesn't have index_size field
        assert health.service == "test"

    @pytest.mark.asyncio
    async def test_health_check_large_index_size(self):
        """Test health check with large index size."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="test", index_size=1000000)

        # ServiceHealth doesn't have index_size field, it's only used as parameter
        assert health.service == "test"

    @pytest.mark.asyncio
    async def test_health_check_negative_index_size(self):
        """Test health check with negative index size."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="test", index_size=-1)

        # ServiceHealth doesn't have index_size field
        assert health.service == "test"

    @pytest.mark.asyncio
    async def test_health_check_multiple_calls(self):
        """Test multiple health check calls."""
        engine = HealthCheckEngine()

        health1 = await engine.check(service_name="test")
        health2 = await engine.check(service_name="test")
        health3 = await engine.check(service_name="test")

        assert health1.service == health2.service == health3.service
        assert health2.uptime_seconds >= health1.uptime_seconds
        assert health3.uptime_seconds >= health2.uptime_seconds

    @pytest.mark.asyncio
    async def test_health_check_service_name_with_special_chars(self):
        """Test health check with special characters in service name."""
        engine = HealthCheckEngine()
        special_names = [
            "service-with-dashes",
            "service_with_underscores",
            "service.with.dots",
            "service/with/slashes",
        ]

        for name in special_names:
            health = await engine.check(service_name=name)
            assert health.service == name

    @pytest.mark.asyncio
    async def test_health_check_service_name_unicode(self):
        """Test health check with unicode service name."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="测试服务")

        assert health.service == "测试服务"

    @pytest.mark.asyncio
    async def test_health_check_empty_service_name(self):
        """Test health check with empty service name."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="")

        assert health.service == ""

    @pytest.mark.asyncio
    async def test_start_time_constant(self):
        """Test that _START_TIME is set at module import."""
        assert isinstance(_START_TIME, float)
        assert _START_TIME > 0

    @pytest.mark.asyncio
    async def test_uptime_reasonable(self):
        """Test that uptime is reasonable (not negative or extremely large)."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="test")

        assert health.uptime_seconds >= 0
        # Uptime should be less than 1 hour for a fresh process
        assert health.uptime_seconds < 3600

    @pytest.mark.asyncio
    async def test_health_check_status_values(self):
        """Test that health check returns valid status values."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="test")

        assert health.status in ["ok", "degraded", "error"]

    @pytest.mark.asyncio
    async def test_health_check_return_type(self):
        """Test that health check returns correct type."""
        engine = HealthCheckEngine()
        health = await engine.check(service_name="test")

        assert isinstance(health, ServiceHealth)
        assert hasattr(health, "status")
        assert hasattr(health, "service")
        assert hasattr(health, "uptime_seconds")
        # index_size is not a field in ServiceHealth

    @pytest.mark.asyncio
    async def test_health_check_disk_usage_path(self):
        """Test that disk usage checks root path."""
        import sys
        mock_psutil = MagicMock()
        mock_vm = MagicMock()
        mock_vm.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_vm

        mock_disk = MagicMock()
        mock_disk.percent = 80.0
        mock_psutil.disk_usage.return_value = mock_disk

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            # Re-import the module to use the mocked psutil
            import importlib
            import extensions.addons.ai_plus.llm_router_service.health_check as hc_module
            importlib.reload(hc_module)

            engine = hc_module.HealthCheckEngine()
            await engine.check(service_name="test")

            mock_psutil.disk_usage.assert_called_once_with("/")

    @pytest.mark.asyncio
    async def test_health_check_concurrent_calls(self):
        """Test concurrent health check calls."""
        import asyncio

        engine = HealthCheckEngine()
        tasks = [engine.check(service_name=f"service-{i}") for i in range(10)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for i, health in enumerate(results):
            assert health.service == f"service-{i}"
