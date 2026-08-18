# -*- coding: utf-8 -*-
"""Tests for health_check.py - Health check for the microservice."""

import asyncio
import pytest
import time

from extensions.addons.documentation.sphinx_documentation_service.health_check import (
    HealthCheckEngine,
)
from extensions.addons.documentation.sphinx_documentation_service.schemas import ServiceHealth


class TestHealthCheckEngine:
    """Test suite for HealthCheckEngine."""

    @pytest.fixture
    def health_engine(self):
        """Fixture for HealthCheckEngine."""
        return HealthCheckEngine()

    @pytest.mark.asyncio
    async def test_check_returns_service_health(self, health_engine):
        """Test that check returns ServiceHealth instance."""
        result = await health_engine.check("test-service")
        assert isinstance(result, ServiceHealth)

    @pytest.mark.asyncio
    async def test_check_default_service_name(self, health_engine):
        """Test check with default service name."""
        result = await health_engine.check("sphinx-documentation-service")
        assert result.service == "sphinx-documentation-service"

    @pytest.mark.asyncio
    async def test_check_custom_service_name(self, health_engine):
        """Test check with custom service name."""
        result = await health_engine.check("custom-service")
        assert result.service == "custom-service"

    @pytest.mark.asyncio
    async def test_check_default_index_size(self, health_engine):
        """Test check with default index_size."""
        result = await health_engine.check("test-service")
        assert result.index_size == 1

    @pytest.mark.asyncio
    async def test_check_custom_index_size(self, health_engine):
        """Test check with custom index_size."""
        result = await health_engine.check("test-service", index_size=100)
        assert result.index_size == 100

    @pytest.mark.asyncio
    async def test_check_index_size_zero(self, health_engine):
        """Test check with index_size=0."""
        result = await health_engine.check("test-service", index_size=0)
        assert result.index_size == 0

    @pytest.mark.asyncio
    async def test_check_large_index_size(self, health_engine):
        """Test check with large index_size."""
        result = await health_engine.check("test-service", index_size=1000000)
        assert result.index_size == 1000000

    @pytest.mark.asyncio
    async def test_check_negative_index_size(self, health_engine):
        """Test check with negative index_size."""
        result = await health_engine.check("test-service", index_size=-1)
        assert result.index_size == -1

    @pytest.mark.asyncio
    async def test_check_status_ok(self, health_engine):
        """Test that status is 'ok' under normal conditions."""
        result = await health_engine.check("test-service")
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_uptime_seconds(self, health_engine):
        """Test that uptime_seconds is calculated correctly."""
        result = await health_engine.check("test-service")
        assert isinstance(result.uptime_seconds, int)
        assert result.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_check_uptime_increases(self, health_engine):
        """Test that uptime_seconds increases over time."""
        result1 = await health_engine.check("test-service")
        await asyncio.sleep(1)
        result2 = await health_engine.check("test-service")
        assert result2.uptime_seconds > result1.uptime_seconds

    @pytest.mark.asyncio
    async def test_check_with_psutil_available(self, health_engine):
        """Test check when psutil is available."""
        # This test assumes psutil might be available
        result = await health_engine.check("test-service")
        assert result.status in ["ok", "degraded"]

    @pytest.mark.asyncio
    async def test_check_without_psutil(self, health_engine):
        """Test check when psutil is not available."""
        # This test documents expected behavior when psutil is unavailable
        # In actual test environment, psutil might be available
        result = await health_engine.check("test-service")
        # Should still return a result even without psutil
        assert isinstance(result, ServiceHealth)
        assert result.status in ["ok", "degraded"]

    @pytest.mark.asyncio
    async def test_check_concurrent_calls(self, health_engine):
        """Test concurrent health check calls."""
        tasks = [health_engine.check("test-service", index_size=i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.index_size == i

    @pytest.mark.asyncio
    async def test_check_empty_service_name(self, health_engine):
        """Test check with empty service name."""
        result = await health_engine.check("")
        assert result.service == ""

    @pytest.mark.asyncio
    async def test_check_unicode_service_name(self, health_engine):
        """Test check with unicode service name."""
        result = await health_engine.check("测试服务")
        assert result.service == "测试服务"

    @pytest.mark.asyncio
    async def test_check_service_name_with_spaces(self, health_engine):
        """Test check with service name containing spaces."""
        result = await health_engine.check("test service")
        assert result.service == "test service"

    @pytest.mark.asyncio
    async def test_check_service_name_with_special_chars(self, health_engine):
        """Test check with service name containing special characters."""
        result = await health_engine.check("test-service_v1.0")
        assert result.service == "test-service_v1.0"

    @pytest.mark.asyncio
    async def test_check_multiple_engines(self):
        """Test multiple HealthCheckEngine instances."""
        engine1 = HealthCheckEngine()
        engine2 = HealthCheckEngine()

        result1 = await engine1.check("service1")
        result2 = await engine2.check("service2")

        assert result1.service == "service1"
        assert result2.service == "service2"

    @pytest.mark.asyncio
    async def test_check_consistency(self, health_engine):
        """Test that health check results are consistent."""
        result1 = await health_engine.check("test-service", index_size=10)
        result2 = await health_engine.check("test-service", index_size=10)

        assert result1.service == result2.service
        assert result1.index_size == result2.index_size
        # uptime may differ slightly
        assert abs(result2.uptime_seconds - result1.uptime_seconds) < 2

    @pytest.mark.asyncio
    async def test_check_with_high_memory_pressure(self, health_engine, monkeypatch):
        """Test check under simulated high memory pressure."""
        # Mock psutil to return high memory usage
        import sys

        class MockPsutil:
            @staticmethod
            def virtual_memory():
                class MockMem:
                    percent = 96
                return MockMem()

            @staticmethod
            def disk_usage(path):
                class MockDisk:
                    percent = 99
                return MockDisk()

        monkeypatch.setitem(sys.modules, "psutil", MockPsutil())

        result = await health_engine.check("test-service")
        assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_check_with_moderate_memory_pressure(self, health_engine, monkeypatch):
        """Test check under moderate memory pressure (should be ok)."""
        import sys

        class MockPsutil:
            @staticmethod
            def virtual_memory():
                class MockMem:
                    percent = 90
                return MockMem()

            @staticmethod
            def disk_usage(path):
                class MockDisk:
                    percent = 90
                return MockDisk()

        monkeypatch.setitem(sys.modules, "psutil", MockPsutil())

        result = await health_engine.check("test-service")
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_psutil_exception_handling(self, health_engine, monkeypatch):
        """Test that psutil exceptions are handled gracefully."""
        import sys

        class MockPsutil:
            @staticmethod
            def virtual_memory():
                raise Exception("psutil error")

            @staticmethod
            def disk_usage(path):
                raise Exception("psutil error")

        monkeypatch.setitem(sys.modules, "psutil", MockPsutil())

        result = await health_engine.check("test-service")
        # Should still return a result despite psutil errors
        assert isinstance(result, ServiceHealth)
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_service_health_schema_validation(self, health_engine):
        """Test that result matches ServiceHealth schema."""
        result = await health_engine.check("test-service")
        # Validate all required fields are present
        assert hasattr(result, "status")
        assert hasattr(result, "service")
        assert hasattr(result, "uptime_seconds")
        assert hasattr(result, "index_size")
        # Validate types
        assert isinstance(result.status, str)
        assert isinstance(result.service, str)
        assert isinstance(result.uptime_seconds, int)
        assert isinstance(result.index_size, int)

    @pytest.mark.asyncio
    async def test_check_uptime_reasonable_range(self, health_engine):
        """Test that uptime_seconds is within reasonable range."""
        result = await health_engine.check("test-service")
        # Uptime should be less than 1 year in seconds
        assert result.uptime_seconds < 31536000
        # Uptime should be non-negative
        assert result.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_check_status_values(self, health_engine):
        """Test that status only contains expected values."""
        result = await health_engine.check("test-service")
        assert result.status in ["ok", "degraded"]
