# -*- coding: utf-8 -*-
"""Tests for workflow_service health_check module."""

import time

import pytest
from health_check import _START_TIME, HealthCheckEngine
from schemas import ServiceHealth


class TestHealthCheckEngine:
    """Test cases for HealthCheckEngine."""

    @pytest.mark.asyncio
    async def test_check_basic(self, health_check_engine):
        """Test basic health check functionality."""
        result = await health_check_engine.check("test-service", 10)
        assert isinstance(result, ServiceHealth)
        assert result.status == "ok"
        assert result.service == "test-service"
        assert result.index_size == 10
        assert result.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_check_with_zero_index_size(self, health_check_engine):
        """Test health check with zero index size."""
        result = await health_check_engine.check("test-service", 0)
        assert result.index_size == 0
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_with_large_index_size(self, health_check_engine):
        """Test health check with large index size."""
        result = await health_check_engine.check("test-service", 1000000)
        assert result.index_size == 1000000
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_with_different_service_names(self, health_check_engine):
        """Test health check with various service names."""
        service_names = [
            "workflow-executor",
            "workflow-scheduler",
            "workflow-orchestrator",
            "custom-service",
        ]
        for name in service_names:
            result = await health_check_engine.check(name, 5)
            assert result.service == name

    @pytest.mark.asyncio
    async def test_check_uptime_increases(self, health_check_engine):
        """Test that uptime increases over time."""
        result1 = await health_check_engine.check("test-service", 1)
        time.sleep(0.1)
        result2 = await health_check_engine.check("test-service", 1)
        assert result2.uptime_seconds >= result1.uptime_seconds

    @pytest.mark.asyncio
    async def test_check_with_psutil_normal_usage(self, health_check_engine, mock_psutil):
        """Test health check with normal resource usage."""
        result = await health_check_engine.check("test-service", 5)
        assert result.status == "ok"
        mock_psutil.virtual_memory.assert_called_once()
        mock_psutil.disk_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_with_psutil_high_memory(self, health_check_engine, mock_psutil_high_usage):
        """Test health check with high memory usage triggers degraded status."""
        mock_psutil_high_usage.virtual_memory.return_value.percent = 96
        mock_psutil_high_usage.disk_usage.return_value.percent = 50

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_check_with_psutil_high_disk(self, health_check_engine, mock_psutil_high_usage):
        """Test health check with high disk usage triggers degraded status."""
        mock_psutil_high_usage.virtual_memory.return_value.percent = 50
        mock_psutil_high_usage.disk_usage.return_value.percent = 99

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_check_with_psutil_both_high(self, health_check_engine, mock_psutil_high_usage):
        """Test health check with both memory and disk high."""
        mock_psutil_high_usage.virtual_memory.return_value.percent = 96
        mock_psutil_high_usage.disk_usage.return_value.percent = 99

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_check_with_psutil_boundary_memory(self, health_check_engine, mock_psutil):
        """Test health check at memory boundary (95%)."""
        mock_psutil.virtual_memory.return_value.percent = 95
        mock_psutil.disk_usage.return_value.percent = 50

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_with_psutil_boundary_disk(self, health_check_engine, mock_psutil):
        """Test health check at disk boundary (98%)."""
        mock_psutil.virtual_memory.return_value.percent = 50
        mock_psutil.disk_usage.return_value.percent = 98

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_with_psutil_exception(self, health_check_engine, mock_psutil_exception):
        """Test health check when psutil raises an exception."""
        result = await health_check_engine.check("test-service", 5)
        # Should still return ok status when psutil fails
        assert result.status == "ok"
        assert result.service == "test-service"

    @pytest.mark.asyncio
    async def test_check_without_psutil(self, health_check_engine):
        """Test health check when psutil is not available."""
        # Import and patch psutil to raise ImportError
        import sys

        psutil_module = sys.modules.get("psutil")
        if psutil_module:
            del sys.modules["psutil"]

        try:
            result = await health_check_engine.check("test-service", 5)
            assert result.status == "ok"
        finally:
            # Restore psutil if it was imported
            if psutil_module:
                sys.modules["psutil"] = psutil_module

    @pytest.mark.asyncio
    async def test_check_negative_index_size(self, health_check_engine):
        """Test health check with negative index size (edge case)."""
        result = await health_check_engine.check("test-service", -1)
        # Should handle negative values gracefully
        assert result.index_size == -1

    @pytest.mark.asyncio
    async def test_check_empty_service_name(self, health_check_engine):
        """Test health check with empty service name."""
        result = await health_check_engine.check("", 5)
        assert result.service == ""
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_special_characters_service_name(self, health_check_engine):
        """Test health check with special characters in service name."""
        special_names = ["service-123", "service_test", "service.test", "service:123"]
        for name in special_names:
            result = await health_check_engine.check(name, 5)
            assert result.service == name

    @pytest.mark.asyncio
    async def test_check_unicode_service_name(self, health_check_engine):
        """Test health check with unicode service name."""
        result = await health_check_engine.check("测试服务", 5)
        assert result.service == "测试服务"

    @pytest.mark.asyncio
    async def test_check_very_long_service_name(self, health_check_engine):
        """Test health check with very long service name."""
        long_name = "a" * 1000
        result = await health_check_engine.check(long_name, 5)
        assert result.service == long_name

    @pytest.mark.asyncio
    async def test_check_multiple_calls_consistency(self, health_check_engine):
        """Test that multiple health check calls are consistent."""
        results = []
        for _ in range(5):
            result = await health_check_engine.check("test-service", 5)
            results.append(result)

        # All should have the same service name
        assert all(r.service == "test-service" for r in results)
        # All should have the same index size
        assert all(r.index_size == 5 for r in results)
        # Uptime should be non-decreasing
        for i in range(len(results) - 1):
            assert results[i + 1].uptime_seconds >= results[i].uptime_seconds

    @pytest.mark.asyncio
    async def test_check_service_health_model_validation(self, health_check_engine):
        """Test that the returned ServiceHealth model is valid."""
        result = await health_check_engine.check("test-service", 5)
        # Verify all required fields are present
        assert hasattr(result, "status")
        assert hasattr(result, "service")
        assert hasattr(result, "index_size")
        assert hasattr(result, "uptime_seconds")
        # Verify types
        assert isinstance(result.status, str)
        assert isinstance(result.service, str)
        assert isinstance(result.index_size, int)
        assert isinstance(result.uptime_seconds, int)

    @pytest.mark.asyncio
    async def test_check_status_values(self, health_check_engine):
        """Test that status field only contains expected values."""
        result = await health_check_engine.check("test-service", 5)
        assert result.status in ["ok", "degraded"]

    @pytest.mark.asyncio
    async def test_check_with_psutil_memory_96(self, health_check_engine, mock_psutil):
        """Test health check with memory at exactly 96%."""
        mock_psutil.virtual_memory.return_value.percent = 96
        mock_psutil.disk_usage.return_value.percent = 50

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_check_with_psutil_disk_99(self, health_check_engine, mock_psutil):
        """Test health check with disk at exactly 99%."""
        mock_psutil.virtual_memory.return_value.percent = 50
        mock_psutil.disk_usage.return_value.percent = 99

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_check_with_psutil_memory_94(self, health_check_engine, mock_psutil):
        """Test health check with memory at 94% (below threshold)."""
        mock_psutil.virtual_memory.return_value.percent = 94
        mock_psutil.disk_usage.return_value.percent = 50

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_with_psutil_disk_97(self, health_check_engine, mock_psutil):
        """Test health check with disk at 97% (below threshold)."""
        mock_psutil.virtual_memory.return_value.percent = 50
        mock_psutil.disk_usage.return_value.percent = 97

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_with_psutil_zero_usage(self, health_check_engine, mock_psutil):
        """Test health check with zero resource usage."""
        mock_psutil.virtual_memory.return_value.percent = 0
        mock_psutil.disk_usage.return_value.percent = 0

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_with_psutil_max_usage(self, health_check_engine, mock_psutil):
        """Test health check with maximum resource usage."""
        mock_psutil.virtual_memory.return_value.percent = 100
        mock_psutil.disk_usage.return_value.percent = 100

        result = await health_check_engine.check("test-service", 5)
        assert result.status == "degraded"


class TestStartTime:
    """Test cases for _START_TIME constant."""

    def test_start_time_is_set(self):
        """Test that _START_TIME is initialized."""
        assert _START_TIME is not None
        assert isinstance(_START_TIME, float)

    def test_start_time_is_in_past(self):
        """Test that _START_TIME represents a time in the past."""
        current_time = time.time()
        assert _START_TIME <= current_time

    def test_start_time_reasonable_value(self):
        """Test that _START_TIME has a reasonable value."""
        current_time = time.time()
        # Start time should be within the last hour (for testing purposes)
        assert current_time - _START_TIME < 3600
        # Start time should not be in the future
        assert _START_TIME <= current_time
