# -*- coding: utf-8 -*-
"""Tests for HealthCheckEngine module."""

import pytest
import time
from unittest.mock import patch, MagicMock

from extensions.addons.ai_plus.knowledge_graph_service.health_check import (
    HealthCheckEngine,
)


class TestHealthCheckEngine:
    """Test cases for HealthCheckEngine class."""

    @pytest.mark.asyncio
    async def test_check_basic(self):
        """Test basic health check."""
        engine = HealthCheckEngine()
        result = await engine.check()

        assert isinstance(result, dict)
        assert result["status"] in ["ok", "degraded"]
        assert "service" in result
        assert "uptime_seconds" in result
        assert "timestamp" in result
        assert result["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_check_without_psutil(self):
        """Test health check when psutil is not available."""
        engine = HealthCheckEngine()

        # Mock the import to fail
        with patch.dict("sys.modules", {"psutil": None}):
            result = await engine.check()
            # Should still return ok status without psutil
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_exception_handling(self):
        """Test that exception in psutil usage is caught (covers line 52)."""
        engine = HealthCheckEngine()

        # Mock psutil to raise exception when accessed
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.side_effect = Exception("psutil error")
        mock_psutil.disk_usage.side_effect = Exception("psutil error")

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            # Should fall back to ok status on exception
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_psutil_disk_usage_exception(self):
        """Test that exception in disk_usage is caught (covers line 52)."""
        engine = HealthCheckEngine()

        # Mock psutil to raise exception only on disk_usage
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.side_effect = Exception("disk error")

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            # Should fall back to ok status on exception
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_with_psutil_memory_high(self):
        """Test health check with high memory usage."""
        engine = HealthCheckEngine()

        # Mock psutil to return high memory usage
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.percent = 96.0  # Above 95% threshold
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_check_with_psutil_disk_high(self):
        """Test health check with high disk usage."""
        engine = HealthCheckEngine()

        # Mock psutil to return high disk usage
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 99.0  # Above 98% threshold
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_check_exception_in_try_block(self):
        """Test that exception in try block is caught (covers line 52)."""
        engine = HealthCheckEngine()

        # Mock psutil to raise exception during import or access
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.side_effect = RuntimeError("access error")
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 50.0
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            # Should fall back to ok status on exception
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_with_psutil_both_high(self):
        """Test health check with both memory and disk high."""
        engine = HealthCheckEngine()

        # Mock psutil to return high memory and disk usage
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.percent = 96.0
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 99.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_check_with_psutil_normal(self):
        """Test health check with normal psutil readings."""
        engine = HealthCheckEngine()

        # Mock psutil to return normal readings
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.percent = 50.0  # Normal
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 50.0  # Normal
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_virtual_memory_exception(self):
        """Test that exception in virtual_memory is caught (covers line 52)."""
        engine = HealthCheckEngine()

        # Mock psutil to raise exception only on virtual_memory
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.side_effect = Exception("memory error")
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 50.0
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            # Should fall back to ok status on exception
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_uptime_increases(self):
        """Test that uptime increases over time."""
        engine = HealthCheckEngine()

        result1 = await engine.check()
        uptime1 = result1["uptime_seconds"]

        time.sleep(1)

        result2 = await engine.check()
        uptime2 = result2["uptime_seconds"]

        assert uptime2 > uptime1

    @pytest.mark.asyncio
    async def test_check_timestamp_format(self):
        """Test that timestamp is in correct format."""
        engine = HealthCheckEngine()

        result = await engine.check()
        timestamp = result["timestamp"]

        # Check ISO 8601 format
        assert "T" in timestamp
        assert "Z" in timestamp
        assert len(timestamp) == 20  # YYYY-MM-DDTHH:MM:SSZ

    @pytest.mark.asyncio
    async def test_check_service_name(self):
        """Test that service name is included."""
        engine = HealthCheckEngine()

        result = await engine.check()

        assert "service" in result
        assert isinstance(result["service"], str)

    @pytest.mark.asyncio
    async def test_check_environment(self):
        """Test that environment is included."""
        engine = HealthCheckEngine()

        result = await engine.check()

        assert "environment" in result
        assert isinstance(result["environment"], str)

    @pytest.mark.asyncio
    async def test_check_memory_threshold_boundary(self):
        """Test health check at memory threshold boundary."""
        engine = HealthCheckEngine()

        # Test exactly at threshold (95%)
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.percent = 95.0
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            # At exactly 95%, should still be ok (not degraded)
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_disk_threshold_boundary(self):
        """Test health check at disk threshold boundary."""
        engine = HealthCheckEngine()

        # Test exactly at threshold (98%)
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 98.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            # At exactly 98%, should still be ok (not degraded)
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_with_psutil_disk_usage_path(self):
        """Test health check with disk usage path parameter."""
        engine = HealthCheckEngine()

        # Mock psutil with disk_usage
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_disk_usage = MagicMock()
        mock_disk_usage.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk_usage

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            result = await engine.check()
            assert result["status"] == "ok"
            # Verify disk_usage was called
            mock_psutil.disk_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_multiple_calls_consistency(self):
        """Test that multiple health check calls are consistent."""
        engine = HealthCheckEngine()

        results = []
        for _ in range(3):
            result = await engine.check()
            results.append(result["service"])

        # Service name should be consistent
        assert all(r == results[0] for r in results)
