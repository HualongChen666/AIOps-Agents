# -*- coding: utf-8 -*-
"""Coverage tests for capacity_router.py to reach 90%+ coverage.

This file uses direct imports and mocking to test the capacity_router module
without requiring full database setup.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [pytest.mark.api]


def _raise(exc):
    """Helper to raise an exception."""

    def _inner(*args, **kwargs):
        raise exc

    return _inner


@pytest.fixture
def mock_dependencies():
    """Mock all core dependencies for capacity_router."""
    with (
        patch("api.capacity_router.forecast_capacity") as mock_forecast,
        patch("api.capacity_router.generate_scaling_recommendations") as mock_recommendations,
        patch("api.capacity_router.metrics_history") as mock_history,
    ):

        # Setup default mock returns
        mock_forecast.return_value = {
            "CPU使用率": {
                "metric": "CPU使用率",
                "currentValue": 65.0,
                "forecast7d": 72.0,
                "forecast30d": 85.0,
                "threshold": 80.0,
                "unit": "%",
                "dataAvailable": True,
            }
        }

        mock_recommendations.return_value = [
            {
                "id": "SR-CPU",
                "service": "compute-service",
                "action": "scale-up",
                "reason": "CPU forecast exceeds threshold",
                "priority": "high",
                "estimatedCost": 300,
            }
        ]

        mock_history.to_dict.return_value = {
            "cpu": [45.0, 46.5, 48.0],
            "memory": [55.0, 57.0, 59.0],
            "net_in": [30.0, 32.0, 34.0],
        }
        # 真实磁盘历史由采样循环写入，经 get_disk_series() 读取
        mock_history.get_disk_series.return_value = [45.0, 50.0]

        yield {
            "forecast": mock_forecast,
            "recommendations": mock_recommendations,
            "history": mock_history,
        }


def test_build_metric_history_success(mock_dependencies):
    """Test _build_metric_history uses every real history source (no synthesis)."""
    from api.capacity_router import _build_metric_history

    result = asyncio.run(_build_metric_history())

    assert "cpu" in result
    assert "memory" in result
    assert "disk" in result
    assert "network" in result
    # 磁盘序列直接取自真实历史，不再合成
    assert result["disk"] == [45.0, 50.0]
    assert result["cpu"] == [45.0, 46.5, 48.0]


def test_build_metric_history_disk_read_exception(mock_dependencies):
    """Test _build_metric_history when disk history read fails."""
    from api.capacity_router import _build_metric_history

    mock_dependencies["history"].get_disk_series.side_effect = RuntimeError("disk read failed")

    result = asyncio.run(_build_metric_history())

    # 读取失败按“无历史”处理，不伪造
    assert "disk" in result
    assert result["disk"] == []


def test_build_metric_history_empty_disk_history(mock_dependencies):
    """Test _build_metric_history when no genuine disk history exists yet."""
    from api.capacity_router import _build_metric_history

    mock_dependencies["history"].get_disk_series.return_value = []

    result = asyncio.run(_build_metric_history())

    assert "disk" in result
    assert result["disk"] == []


def test_build_metric_history_network_normalization(mock_dependencies):
    """Test network normalization logic in _build_metric_history (line 41)."""
    from api.capacity_router import _build_metric_history

    # Set net_in values that need normalization (values > _NETWORK_CAP_MB)
    mock_dependencies["history"].to_dict.return_value = {
        "cpu": [45.0],
        "memory": [55.0],
        "net_in": [150.0, 200.0, 50.0],  # Values above and below 100 MB/s
    }

    result = asyncio.run(_build_metric_history())

    assert "network" in result
    # Values should be normalized to percentage (0-100)
    # 150.0 / 100.0 * 100 = 150, but min(100.0, 150) = 100
    # 200.0 / 100.0 * 100 = 200, but min(100.0, 200) = 100
    # 50.0 / 100.0 * 100 = 50
    assert result["network"][0] == 100.0
    assert result["network"][1] == 100.0
    assert result["network"][2] == 50.0


def test_build_metric_history_empty_metrics(mock_dependencies):
    """Test _build_metric_history with empty metric history."""
    from api.capacity_router import _build_metric_history

    mock_dependencies["history"].to_dict.return_value = {
        "cpu": [],
        "memory": [],
        "net_in": [],
    }

    result = asyncio.run(_build_metric_history())

    assert "cpu" in result
    assert "memory" in result
    assert "network" in result
    assert result["cpu"] == []
    assert result["memory"] == []
    assert result["network"] == []


def test_build_metric_history_missing_metric_keys(mock_dependencies):
    """Test _build_metric_history when metric history is missing keys."""
    from api.capacity_router import _build_metric_history

    mock_dependencies["history"].to_dict.return_value = {}

    result = asyncio.run(_build_metric_history())

    assert "cpu" in result
    assert "memory" in result
    assert "network" in result
    assert result["cpu"] == []
    assert result["memory"] == []
    assert result["network"] == []


def test_get_forecast_success(mock_dependencies):
    """Test successful get_forecast endpoint."""
    from api.capacity_router import get_forecast

    result = asyncio.run(get_forecast())

    assert "data" in result
    assert isinstance(result["data"], list)
    mock_dependencies["forecast"].assert_called_once()


def test_get_forecast_exception_handling(mock_dependencies):
    """Test forecast endpoint exception handling (lines 97-99)."""
    from fastapi import HTTPException

    from api.capacity_router import get_forecast

    # Make forecast_capacity raise an exception
    mock_dependencies["forecast"].side_effect = Exception("Forecast failed")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_forecast())

    assert exc_info.value.status_code == 500
    assert "容量预测失败" in str(exc_info.value.detail)


def test_get_recommendations_success(mock_dependencies):
    """Test successful get_recommendations endpoint."""
    from api.capacity_router import get_recommendations

    result = asyncio.run(get_recommendations())

    assert "data" in result
    assert isinstance(result["data"], list)
    mock_dependencies["recommendations"].assert_called_once()


def test_get_recommendations_exception_handling(mock_dependencies):
    """Test recommendations endpoint exception handling (lines 137-139)."""
    from fastapi import HTTPException

    from api.capacity_router import get_recommendations

    # Make generate_scaling_recommendations raise an exception
    mock_dependencies["recommendations"].side_effect = Exception("Recommendations failed")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_recommendations())

    assert exc_info.value.status_code == 500
    assert "扩容建议生成失败" in str(exc_info.value.detail)


def test_get_recommendations_build_metric_history_exception(mock_dependencies):
    """Test recommendations when disk history read fails."""
    from api.capacity_router import get_recommendations

    # Make disk history read fail during recommendations call
    mock_dependencies["history"].get_disk_series.side_effect = RuntimeError("Disk metrics failed")

    # Should still succeed because the exception is caught in _build_metric_history
    result = asyncio.run(get_recommendations())

    assert "data" in result
    assert isinstance(result["data"], list)


def test_get_forecast_build_metric_history_exception(mock_dependencies):
    """Test forecast when disk history read fails."""
    from api.capacity_router import get_forecast

    # Make disk history read fail — should be handled gracefully
    mock_dependencies["history"].get_disk_series.side_effect = RuntimeError(
        "Permission denied accessing disk"
    )

    # Should succeed because exception is caught and disk treated as unavailable
    result = asyncio.run(get_forecast())

    assert "data" in result
    assert isinstance(result["data"], list)
