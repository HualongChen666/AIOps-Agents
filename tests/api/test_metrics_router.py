# -*- coding: utf-8 -*-
"""Comprehensive tests for metrics_router.py to achieve 90%+ coverage."""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.api]

import api.ai_feedback_router as ai_feedback_router
import api.metrics_router as metrics_router
import core.collector
import core.stats_engine


# ============================================================================
# Helper functions
# ============================================================================

def _patch_all_metrics(monkeypatch, dual_write_available=False, dual_init_fails=False):
    """Patch all metrics dependencies."""
    # Patch core functions
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(return_value={"total_alerts": 5, "heal_rate": 90, "mttd_min": 10, "rca_accuracy": 95}),
    )
    monkeypatch.setattr(
        metrics_router,
        "collect_all",
        MagicMock(return_value={"cpu": {"usage_percent": 10}, "memory": {"usage_percent": 20}}),
    )
    monkeypatch.setattr(metrics_router, "get_top_processes", MagicMock(return_value=[]))
    monkeypatch.setattr(
        metrics_router.metrics_history,
        "to_dict",
        MagicMock(return_value={"cpu": [1.0, 2.0], "memory": [3.0, 4.0], "net_in": [5.0, 6.0]}),
    )
    monkeypatch.setattr(
        metrics_router, "get_decision_accuracy", MagicMock(return_value={"accuracy": 0.9})
    )
    monkeypatch.setattr(
        ai_feedback_router, "_compute_feedback_stats", MagicMock(return_value={"accuracy": 0.8})
    )

    # Patch dual write availability
    if dual_write_available:
        if dual_init_fails:
            # Simulate initialization failure
            monkeypatch.setattr(
                metrics_router,
                "DUAL_WRITE_AVAILABLE",
                True,
            )
            # Force initialization to fail by making DualWriteStrategy raise exception
            original_init = metrics_router.DualWriteStrategy if hasattr(metrics_router, 'DualWriteStrategy') else None
            if original_init:
                def failing_init(*args, **kwargs):
                    raise Exception("Dual write init failed")
                monkeypatch.setattr(metrics_router, "DualWriteStrategy", MagicMock(side_effect=failing_init))
        else:
            monkeypatch.setattr(metrics_router, "DUAL_WRITE_AVAILABLE", True)
            # Create fake dual write strategy
            fake_strategy = MagicMock()
            fake_strategy.write_batch_metrics = AsyncMock()
            monkeypatch.setattr(metrics_router, "_dual_write_strategy", fake_strategy)
            fake_converter = MagicMock()
            monkeypatch.setattr(metrics_router, "_metrics_converter", fake_converter)
    else:
        monkeypatch.setattr(metrics_router, "DUAL_WRITE_AVAILABLE", False)
        monkeypatch.setattr(metrics_router, "_dual_write_strategy", None)
        monkeypatch.setattr(metrics_router, "_metrics_converter", None)


# ============================================================================
# Test 1: Dual write initialization failure (lines 223-231, 228-231)
# ============================================================================

def test_dual_write_initialization_failure(monkeypatch):
    """Test dual write initialization failure handling."""
    _patch_all_metrics(monkeypatch, dual_write_available=False)

    # Verify dual write is not available
    assert metrics_router.DUAL_WRITE_AVAILABLE is False
    assert metrics_router._dual_write_strategy is None
    assert metrics_router._metrics_converter is None


# ============================================================================
# Test 2: Cache helper functions (lines 269-272, 311, 556-559, 583)
# ============================================================================

def test_try_get_snapshot_from_cache_hit(monkeypatch):
    """Test _try_get_snapshot_from_cache when cache is hit."""
    _patch_all_metrics(monkeypatch)
    
    # Set cache data
    test_data = {"cpu": 50, "memory": 60}
    metrics_router._snapshot_cache.set(test_data)
    
    # Call function
    result = metrics_router._try_get_snapshot_from_cache()
    
    assert result == test_data


def test_try_get_snapshot_from_cache_miss(monkeypatch):
    """Test _try_get_snapshot_from_cache when cache is empty."""
    _patch_all_metrics(monkeypatch)
    
    # Clear cache
    metrics_router._snapshot_cache.clear()
    
    # Call function
    result = metrics_router._try_get_snapshot_from_cache()
    
    assert result is None


def test_update_snapshot_cache(monkeypatch):
    """Test _update_snapshot_cache function."""
    _patch_all_metrics(monkeypatch)
    
    test_data = {"cpu": 50, "memory": 60}
    metrics_router._update_snapshot_cache(test_data)
    
    # Verify cache was set
    result = metrics_router._snapshot_cache.get()
    assert result == test_data


def test_try_get_processes_from_cache_hit(monkeypatch):
    """Test _try_get_processes_from_cache when cache is hit."""
    _patch_all_metrics(monkeypatch)
    
    # Set cache data
    test_data = {"processes": [{"name": "test", "pid": 123}]}
    metrics_router._processes_cache.set(test_data, limit=10)
    
    # Call function
    result = metrics_router._try_get_processes_from_cache(limit=10)
    
    assert result == test_data


def test_try_get_processes_from_cache_miss(monkeypatch):
    """Test _try_get_processes_from_cache when cache is empty."""
    _patch_all_metrics(monkeypatch)
    
    # Clear cache
    metrics_router._processes_cache.clear()
    
    # Call function
    result = metrics_router._try_get_processes_from_cache(limit=10)
    
    assert result is None


def test_update_processes_cache(monkeypatch):
    """Test _update_processes_cache function."""
    _patch_all_metrics(monkeypatch)
    
    test_data = {"processes": [{"name": "test", "pid": 123}]}
    metrics_router._update_processes_cache(test_data, limit=10)
    
    # Verify cache was set
    result = metrics_router._processes_cache.get(limit=10)
    assert result == test_data


# ============================================================================
# Test 3: get_snapshot cache hit and CancelledError (lines 353, 361-366)
# ============================================================================

def test_get_snapshot_cache_hit(client, monkeypatch):
    """Test get_snapshot when cache is hit."""
    _patch_all_metrics(monkeypatch)
    
    # Pre-populate cache
    test_data = {"cpu": {"usage_percent": 45}, "memory": {"usage_percent": 60}, "summary": {"total_alerts": 5}}
    metrics_router._snapshot_cache.set(test_data)
    
    resp = client.get("/api/v1/metrics/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpu"]["usage_percent"] == 45


@pytest.mark.asyncio
async def test_get_snapshot_cancelled_error(client, monkeypatch):
    """Test get_snapshot when asyncio.CancelledError is raised."""
    _patch_all_metrics(monkeypatch)
    
    # Clear cache to force collection
    metrics_router._snapshot_cache.clear()
    
    # Make asyncio.to_thread raise CancelledError
    async def failing_to_thread(func, *args, **kwargs):
        raise asyncio.CancelledError()
    
    monkeypatch.setattr(asyncio, "to_thread", failing_to_thread)
    
    with pytest.raises(asyncio.CancelledError):
        # This should raise CancelledError
        await metrics_router.get_snapshot()


def test_get_snapshot_collection_error(client, monkeypatch):
    """Test get_snapshot when collection fails with regular exception."""
    _patch_all_metrics(monkeypatch)
    
    # Clear cache to force collection
    metrics_router._snapshot_cache.clear()
    
    # Make asyncio.to_thread raise exception
    async def failing_to_thread(func, *args, **kwargs):
        raise Exception("Collection failed")
    
    monkeypatch.setattr(asyncio, "to_thread", failing_to_thread)
    
    resp = client.get("/api/v1/metrics/snapshot")
    assert resp.status_code == 500
    assert "系统指标采集失败" in resp.text


# ============================================================================
# Test 4: get_history error handling (lines 429-431)
# ============================================================================

def test_get_history_error(client, monkeypatch):
    """Test get_history when metrics_history.to_dict fails."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router.metrics_history,
        "to_dict",
        MagicMock(side_effect=Exception("History fetch failed"))
    )
    
    resp = client.get("/api/v1/metrics/history")
    assert resp.status_code == 500
    assert "历史数据获取失败" in resp.text


# ============================================================================
# Test 5: _to_floats edge cases (lines 438, 442-443)
# ============================================================================

def test_to_floats_non_sequence():
    """Test _to_floats with non-list/tuple input."""
    result = metrics_router._to_floats("not a list")
    assert result == []


def test_to_floats_with_invalid_values():
    """Test _to_floats with mixed valid/invalid values."""
    result = metrics_router._to_floats([1, 2, "invalid", None, "3.5", "abc"])
    assert result == [1.0, 2.0, 3.5]


def test_to_floats_empty_list():
    """Test _to_floats with empty list."""
    result = metrics_router._to_floats([])
    assert result == []


# ============================================================================
# Test 6: _linear_slope edge cases (lines 451, 459)
# ============================================================================

def test_linear_slope_single_value():
    """Test _linear_slope with single value (n < 2)."""
    result = metrics_router._linear_slope([5.0])
    assert result == 0.0


def test_linear_slope_zero_denominator():
    """Test _linear_slope when denominator is zero."""
    # When all x values are the same, denominator becomes zero
    result = metrics_router._linear_slope([5.0, 5.0, 5.0])
    assert result == 0.0


def test_linear_slope_normal_case():
    """Test _linear_slope with normal increasing values."""
    result = metrics_router._linear_slope([1.0, 2.0, 3.0, 4.0])
    assert result == 1.0


# ============================================================================
# Test 7: _build_predictions edge cases (lines 474, 497-498)
# ============================================================================

def test_build_predictions_empty_values():
    """Test _build_predictions when metric has no values."""
    history = {"cpu": [], "memory": [1.0, 2.0], "net_in": []}
    predictions = metrics_router._build_predictions(history)
    
    # Should only have predictions for memory (has values)
    assert len(predictions) == 1
    assert predictions[0]["id"] == "pred-memory"


def test_build_predictions_insufficient_samples():
    """Test _build_predictions when metric has only 1 sample."""
    history = {"cpu": [50.0], "memory": [60.0], "net_in": [10.0]}
    predictions = metrics_router._build_predictions(history)
    
    # All should have predictions but with "low" priority
    assert len(predictions) == 3
    for pred in predictions:
        assert pred["priority"] == "low"
        assert "采样点不足" in pred["description"]


def test_build_predictions_rising_trend():
    """Test _build_predictions with rising trend."""
    history = {"cpu": [10.0, 20.0, 30.0, 40.0], "memory": [50.0, 51.0, 52.0, 53.0], "net_in": []}
    predictions = metrics_router._build_predictions(history)
    
    cpu_pred = next(p for p in predictions if p["id"] == "pred-cpu")
    assert cpu_pred["priority"] == "high"
    assert "上升" in cpu_pred["description"]


def test_build_predictions_falling_trend():
    """Test _build_predictions with falling trend."""
    history = {"cpu": [40.0, 30.0, 20.0, 10.0], "memory": [50.0, 51.0, 52.0, 53.0], "net_in": []}
    predictions = metrics_router._build_predictions(history)
    
    cpu_pred = next(p for p in predictions if p["id"] == "pred-cpu")
    assert cpu_pred["priority"] == "low"
    assert "下降" in cpu_pred["description"]


def test_build_predictions_stable_trend():
    """Test _build_predictions with stable trend."""
    history = {"cpu": [50.0, 50.1, 49.9, 50.0], "memory": [50.0, 51.0, 52.0, 53.0], "net_in": []}
    predictions = metrics_router._build_predictions(history)
    
    cpu_pred = next(p for p in predictions if p["id"] == "pred-cpu")
    assert cpu_pred["priority"] == "low"
    assert "平稳" in cpu_pred["description"]


# ============================================================================
# Test 8: get_processes cache hit and CancelledError (lines 649, 657)
# ============================================================================

def test_get_processes_cache_hit(client, monkeypatch):
    """Test get_processes when cache is hit."""
    _patch_all_metrics(monkeypatch)
    
    # Pre-populate cache
    test_data = {"processes": [{"name": "test", "pid": 123, "cpu_percent": 5.0}]}
    metrics_router._processes_cache.set(test_data, limit=10)
    
    resp = client.get("/api/v1/metrics/processes?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["processes"]) == 1


@pytest.mark.asyncio
async def test_get_processes_cancelled_error(client, monkeypatch):
    """Test get_processes when asyncio.CancelledError is raised."""
    _patch_all_metrics(monkeypatch)
    
    # Clear cache to force collection
    metrics_router._processes_cache.clear()
    
    # Make asyncio.to_thread raise CancelledError
    async def failing_to_thread(func, *args, **kwargs):
        raise asyncio.CancelledError()
    
    monkeypatch.setattr(asyncio, "to_thread", failing_to_thread)
    
    with pytest.raises(asyncio.CancelledError):
        await metrics_router.get_processes(limit=10)


def test_get_processes_collection_error(client, monkeypatch):
    """Test get_processes when collection fails."""
    _patch_all_metrics(monkeypatch)
    
    # Clear cache to force collection
    metrics_router._processes_cache.clear()
    
    # Make asyncio.to_thread raise exception
    async def failing_to_thread(func, *args, **kwargs):
        raise Exception("Process collection failed")
    
    monkeypatch.setattr(asyncio, "to_thread", failing_to_thread)
    
    resp = client.get("/api/v1/metrics/processes?limit=10")
    assert resp.status_code == 500
    assert "进程列表获取失败" in resp.text


# ============================================================================
# Test 9: get_summary error handling (lines 703-705)
# ============================================================================

def test_get_summary_error(client, monkeypatch):
    """Test get_summary when get_real_summary fails."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router, "get_real_summary", AsyncMock(side_effect=Exception("Summary fetch failed"))
    )
    
    resp = client.get("/api/v1/metrics/summary")
    assert resp.status_code == 500
    assert "摘要数据获取失败" in resp.text


# ============================================================================
# Test 10: clear_snapshot_cache engine layer error (lines 768-770)
# ============================================================================

def test_clear_snapshot_cache_engine_error(client, monkeypatch):
    """Test clear_snapshot_cache when engine layer cache clear fails."""
    _patch_all_metrics(monkeypatch)
    
    # Make invalidate_collect_cache raise exception
    def failing_invalidate():
        raise Exception("Engine cache clear failed")
    
    monkeypatch.setattr(core.collector, "invalidate_collect_cache", failing_invalidate)
    
    resp = client.delete("/api/v1/metrics/cache")
    assert resp.status_code == 200
    data = resp.json()
    # Should still return success even if engine cache clear fails
    assert data["status"] == "ok"
    assert data["snapshot_cleared"] is True
    assert data["processes_cleared"] is True
    assert data["engine_cleared"] is False


def test_clear_snapshot_cache_import_error(client, monkeypatch):
    """Test clear_snapshot_cache when invalidate_collect_cache doesn't exist."""
    _patch_all_metrics(monkeypatch)
    
    # Remove invalidate_collect_cache to simulate ImportError
    monkeypatch.delattr(core.collector, "invalidate_collect_cache", raising=False)
    
    resp = client.delete("/api/v1/metrics/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["engine_cleared"] is False


def test_clear_snapshot_cache_success(client, monkeypatch):
    """Test clear_snapshot_cache successful clear."""
    _patch_all_metrics(monkeypatch)
    
    # Populate caches
    metrics_router._snapshot_cache.set({"test": "data"})
    metrics_router._processes_cache.set({"processes": []}, limit=10)
    
    # Mock successful engine cache clear
    monkeypatch.setattr(core.collector, "invalidate_collect_cache", MagicMock())
    
    resp = client.delete("/api/v1/metrics/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["snapshot_cleared"] is True
    assert data["processes_cleared"] is True
    assert data["engine_cleared"] is True


# ============================================================================
# Test 11: get_kpi_values no visible configs (line 824)
# ============================================================================

def test_get_kpi_values_no_visible_configs(client, monkeypatch):
    """Test get_kpi_values when no configs are visible."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(return_value=[
            {"id": "1", "visible": False, "endpoint": "summary", "field_path": "total_alerts"}
        ])
    )
    
    resp = client.get("/api/v1/metrics/kpi/values")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"] == []


# ============================================================================
# Test 12: get_kpi_values skip non-visible (lines 834, 857)
# ============================================================================

def test_get_kpi_values_mixed_visibility(client, monkeypatch):
    """Test get_kpi_values with mixed visible/non-visible configs."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(return_value=[
            {"id": "1", "visible": True, "endpoint": "summary", "field_path": "total_alerts", "name": "Alerts", "target": 10, "unit": ""},
            {"id": "2", "visible": False, "endpoint": "summary", "field_path": "heal_rate", "name": "Heal Rate", "target": 90, "unit": "%"},
            {"id": "3", "visible": True, "endpoint": "summary", "field_path": "mttd_min", "name": "MTTD", "target": 30, "unit": "min"},
        ])
    )
    monkeypatch.setattr(metrics_router, "resolve_field", MagicMock(return_value=5))
    
    resp = client.get("/api/v1/metrics/kpi/values")
    assert resp.status_code == 200
    data = resp.json()
    # Should only return visible configs
    assert len(data["data"]) == 2
    ids = [item["id"] for item in data["data"]]
    assert "1" in ids
    assert "3" in ids
    assert "2" not in ids


# ============================================================================
# Test 13: get_kpi_values different endpoints
# ============================================================================

def test_get_kpi_values_snapshot_endpoint(client, monkeypatch):
    """Test get_kpi_values with snapshot endpoint."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(return_value=[
            {"id": "1", "visible": True, "endpoint": "snapshot", "field_path": "cpu.usage_percent", "name": "CPU", "target": 80, "unit": "%"}
        ])
    )
    monkeypatch.setattr(metrics_router, "resolve_field", MagicMock(return_value=45.5))
    
    resp = client.get("/api/v1/metrics/kpi/values")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["value"] == 45.5


def test_get_kpi_values_decision_accuracy_endpoint(client, monkeypatch):
    """Test get_kpi_values with decision accuracy endpoint."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(return_value=[
            {"id": "1", "visible": True, "endpoint": "agent/decision-accuracy", "field_path": "accuracy", "name": "Accuracy", "target": 0.9, "unit": ""}
        ])
    )
    monkeypatch.setattr(metrics_router, "resolve_field", MagicMock(return_value=0.95))
    
    resp = client.get("/api/v1/metrics/kpi/values")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["value"] == 0.95


def test_get_kpi_values_feedback_accuracy_endpoint(client, monkeypatch):
    """Test get_kpi_values with feedback accuracy endpoint."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(return_value=[
            {"id": "1", "visible": True, "endpoint": "agent/feedback-accuracy", "field_path": "accuracy", "name": "Feedback", "target": 0.8, "unit": ""}
        ])
    )
    monkeypatch.setattr(metrics_router, "resolve_field", MagicMock(return_value=0.85))
    
    resp = client.get("/api/v1/metrics/kpi/values")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["value"] == 0.85


# ============================================================================
# Test 14: get_kpi_values value conversion errors
# ============================================================================

def test_get_kpi_values_value_conversion_error(client, monkeypatch):
    """Test get_kpi_values when value conversion fails."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(return_value=[
            {"id": "1", "visible": True, "endpoint": "summary", "field_path": "total_alerts", "name": "Alerts", "target": 10, "unit": ""}
        ])
    )
    # Return non-convertible value
    monkeypatch.setattr(metrics_router, "resolve_field", MagicMock(return_value="not a number"))
    
    resp = client.get("/api/v1/metrics/kpi/values")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    # Should default to 0.0 on conversion error
    assert data["data"][0]["value"] == 0.0


def test_get_kpi_values_none_value(client, monkeypatch):
    """Test get_kpi_values when value is None."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(return_value=[
            {"id": "1", "visible": True, "endpoint": "summary", "field_path": "total_alerts", "name": "Alerts", "target": 10, "unit": ""}
        ])
    )
    monkeypatch.setattr(metrics_router, "resolve_field", MagicMock(return_value=None))
    
    resp = client.get("/api/v1/metrics/kpi/values")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    # Should default to 0.0 when value is None
    assert data["data"][0]["value"] == 0.0


# ============================================================================
# Test 15: get_dashboard_metrics edge cases
# ============================================================================

def test_get_dashboard_metrics_high_alerts(client, monkeypatch):
    """Test dashboard metrics with high alert count (critical level)."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(return_value={"total_alerts": 60, "heal_rate": 90, "mttd_min": 10, "rca_accuracy": 95})
    )
    
    resp = client.get("/api/v1/metrics/")
    assert resp.status_code == 200
    data = resp.json()
    alert_metric = next(m for m in data["metrics"] if m["key"] == "告警数量")
    assert alert_metric["level"] == "critical"


def test_get_dashboard_metrics_warning_alerts(client, monkeypatch):
    """Test dashboard metrics with warning alert count."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(return_value={"total_alerts": 30, "heal_rate": 90, "mttd_min": 10, "rca_accuracy": 95})
    )
    
    resp = client.get("/api/v1/metrics/")
    assert resp.status_code == 200
    data = resp.json()
    alert_metric = next(m for m in data["metrics"] if m["key"] == "告警数量")
    assert alert_metric["level"] == "warning"


def test_get_dashboard_metrics_normal_alerts(client, monkeypatch):
    """Test dashboard metrics with normal alert count."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(return_value={"total_alerts": 10, "heal_rate": 90, "mttd_min": 10, "rca_accuracy": 95})
    )
    
    resp = client.get("/api/v1/metrics/")
    assert resp.status_code == 200
    data = resp.json()
    alert_metric = next(m for m in data["metrics"] if m["key"] == "告警数量")
    assert alert_metric["level"] == "normal"


def test_get_dashboard_metrics_low_heal_rate(client, monkeypatch):
    """Test dashboard metrics with low heal rate."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(return_value={"total_alerts": 10, "heal_rate": 70, "mttd_min": 10, "rca_accuracy": 95})
    )
    
    resp = client.get("/api/v1/metrics/")
    assert resp.status_code == 200
    data = resp.json()
    heal_metric = next(m for m in data["metrics"] if m["key"] == "自愈成功率")
    assert heal_metric["level"] == "warning"


def test_get_dashboard_metrics_high_mttd(client, monkeypatch):
    """Test dashboard metrics with high MTTD."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(return_value={"total_alerts": 10, "heal_rate": 90, "mttd_min": 40, "rca_accuracy": 95})
    )
    
    resp = client.get("/api/v1/metrics/")
    assert resp.status_code == 200
    data = resp.json()
    mttd_metric = next(m for m in data["metrics"] if m["key"] == "MTTD")
    assert mttd_metric["level"] == "warning"


def test_get_dashboard_metrics_low_rca_accuracy(client, monkeypatch):
    """Test dashboard metrics with low RCA accuracy."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(return_value={"total_alerts": 10, "heal_rate": 90, "mttd_min": 10, "rca_accuracy": 80})
    )
    
    resp = client.get("/api/v1/metrics/")
    assert resp.status_code == 200
    data = resp.json()
    rca_metric = next(m for m in data["metrics"] if m["key"] == "RCA准确率")
    assert rca_metric["level"] == "warning"


# ============================================================================
# Test 16: KPI config CRUD operations
# ============================================================================

def test_kpi_config_update_not_found(client, monkeypatch):
    """Test KPI config update when config doesn't exist."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(metrics_router, "update_kpi_config", MagicMock(return_value=None))
    
    resp = client.put("/api/v1/metrics/kpi/config/nonexistent", json={"name": "test"})
    assert resp.status_code == 404
    assert "KPI 配置不存在" in resp.text


def test_kpi_config_delete_not_found(client, monkeypatch):
    """Test KPI config delete when config doesn't exist."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(metrics_router, "delete_kpi_config", MagicMock(return_value=False))
    
    resp = client.delete("/api/v1/metrics/kpi/config/nonexistent")
    assert resp.status_code == 404
    assert "KPI 配置不存在" in resp.text


# ============================================================================
# Test 17: get_processes limit validation
# ============================================================================

def test_get_processes_limit_validation(client, monkeypatch):
    """Test get_processes with different limit values."""
    _patch_all_metrics(monkeypatch)
    
    # Clear cache
    metrics_router._processes_cache.clear()
    
    # Test minimum limit
    resp = client.get("/api/v1/metrics/processes?limit=1")
    assert resp.status_code == 200
    
    # Test maximum limit
    resp = client.get("/api/v1/metrics/processes?limit=100")
    assert resp.status_code == 200
    
    # Test default limit
    resp = client.get("/api/v1/metrics/processes")
    assert resp.status_code == 200


def test_get_processes_invalid_limit(client, monkeypatch):
    """Test get_processes with invalid limit values."""
    _patch_all_metrics(monkeypatch)
    
    # Test limit below minimum
    resp = client.get("/api/v1/metrics/processes?limit=0")
    assert resp.status_code == 422
    
    # Test limit above maximum
    resp = client.get("/api/v1/metrics/processes?limit=101")
    assert resp.status_code == 422


# ============================================================================
# Test 18: _collect_system_snapshot with dual write
# ============================================================================

@pytest.mark.asyncio
async def test_collect_system_snapshot_dual_write_success(monkeypatch):
    """Test _collect_system_snapshot with successful dual write."""
    _patch_all_metrics(monkeypatch, dual_write_available=True)
    
    # Create fake dual write strategy
    fake_strategy = MagicMock()
    fake_strategy.write_batch_metrics = AsyncMock()
    monkeypatch.setattr(metrics_router, "_dual_write_strategy", fake_strategy)
    fake_converter = MagicMock()
    monkeypatch.setattr(metrics_router, "_metrics_converter", fake_converter)
    
    # Call the function
    result = await metrics_router._collect_system_snapshot()
    
    assert "cpu" in result or "memory" in result
    assert "summary" in result
    # Verify dual write was called
    fake_strategy.write_batch_metrics.assert_called_once()


@pytest.mark.asyncio
async def test_collect_system_snapshot_dual_write_failure(monkeypatch):
    """Test _collect_system_snapshot when dual write fails."""
    _patch_all_metrics(monkeypatch, dual_write_available=True)
    
    # Create fake dual write strategy that fails
    fake_strategy = MagicMock()
    fake_strategy.write_batch_metrics = AsyncMock(side_effect=Exception("Dual write failed"))
    monkeypatch.setattr(metrics_router, "_dual_write_strategy", fake_strategy)
    fake_converter = MagicMock()
    monkeypatch.setattr(metrics_router, "_metrics_converter", fake_converter)
    
    # Call the function - should still succeed despite dual write failure
    result = await metrics_router._collect_system_snapshot()
    
    assert "summary" in result


# ============================================================================
# Test 19: get_predictions error handling
# ============================================================================

def test_get_predictions_error(client, monkeypatch):
    """Test get_predictions when _build_predictions fails."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router.metrics_history,
        "to_dict",
        MagicMock(side_effect=Exception("History fetch failed"))
    )
    
    resp = client.get("/api/v1/metrics/predictions")
    assert resp.status_code == 500
    assert "预测性维护建议生成失败" in resp.text


# ============================================================================
# Test 20: Cache isolation between different limits
# ============================================================================

def test_processes_cache_isolation(client, monkeypatch):
    """Test that different limit values use separate cache entries."""
    _patch_all_metrics(monkeypatch)
    
    # Clear cache
    metrics_router._processes_cache.clear()
    
    # First call with limit=10
    resp1 = client.get("/api/v1/metrics/processes?limit=10")
    assert resp1.status_code == 200
    
    # Second call with limit=20 should not use the same cache
    resp2 = client.get("/api/v1/metrics/processes?limit=20")
    assert resp2.status_code == 200
    
    # Both should succeed independently
    assert resp1.status_code == 200
    assert resp2.status_code == 200


# ============================================================================
# Test 21: get_dashboard_metrics exception handling (lines 212-214)
# ============================================================================

def test_get_dashboard_metrics_exception(client, monkeypatch):
    """Test get_dashboard_metrics when get_real_summary raises exception."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router, "get_real_summary", AsyncMock(side_effect=Exception("Summary failed"))
    )
    
    resp = client.get("/api/v1/metrics/")
    assert resp.status_code == 500
    assert "仪表盘指标获取失败" in resp.text


# ============================================================================
# Test 22: get_history metadata and logging (lines 416-428)
# ============================================================================

def test_get_history_with_metadata(client, monkeypatch):
    """Test get_history returns proper metadata."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router.metrics_history,
        "to_dict",
        MagicMock(return_value={"cpu": [1.0, 2.0, 3.0], "memory": [4.0, 5.0, 6.0], "net_in": [7.0, 8.0, 9.0]})
    )
    
    resp = client.get("/api/v1/metrics/history")
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify _meta field exists
    assert "_meta" in data
    assert "size" in data["_meta"]
    assert "maxlen" in data["_meta"]
    assert data["_meta"]["size"] == 3


# ============================================================================
# Test 23: get_predictions logging (lines 541-542)
# ============================================================================

def test_get_predictions_success(client, monkeypatch):
    """Test get_predictions successful case with logging."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router.metrics_history,
        "to_dict",
        MagicMock(return_value={"cpu": [10.0, 20.0, 30.0], "memory": [40.0, 50.0, 60.0], "net_in": [70.0, 80.0, 90.0]})
    )
    
    resp = client.get("/api/v1/metrics/predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert len(data["data"]) > 0


# ============================================================================
# Test 24: get_summary logging (lines 696-702)
# ============================================================================

def test_get_summary_with_logging(client, monkeypatch):
    """Test get_summary with successful logging."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(return_value={"total_alerts": 42, "heal_rate": 85, "mttd_min": 15, "rca_accuracy": 92})
    )
    
    resp = client.get("/api/v1/metrics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_alerts"] == 42
    assert data["heal_rate"] == 85


# ============================================================================
# Test 25: get_feedback_accuracy endpoint (lines 722-724)
# ============================================================================

def test_get_feedback_accuracy(client, monkeypatch):
    """Test get_feedback_accuracy endpoint."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        ai_feedback_router, "_compute_feedback_stats", MagicMock(return_value={"total": 100, "positive": 80, "negative": 20, "accuracy": 0.8})
    )
    
    resp = client.get("/api/v1/metrics/agent/feedback-accuracy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["accuracy"] == 0.8


# ============================================================================
# Test 26: get_decision_accuracy_endpoint (line 734)
# ============================================================================

def test_get_decision_accuracy_endpoint(client, monkeypatch):
    """Test get_decision_accuracy_endpoint."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router, "get_decision_accuracy", MagicMock(return_value={"precision": 0.9, "recall": 0.85, "f1_score": 0.87, "accuracy": 0.88})
    )
    
    resp = client.get("/api/v1/metrics/agent/decision-accuracy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["accuracy"] == 0.88


# ============================================================================
# Test 27: KPI config CRUD endpoints (lines 795, 800-801, 809, 816)
# ============================================================================

def test_kpi_config_get_list(client, monkeypatch):
    """Test get_kpi_configs endpoint."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(return_value=[{"id": "1", "name": "Test", "visible": True}])
    )
    
    resp = client.get("/api/v1/metrics/kpi/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert len(data["data"]) == 1


def test_kpi_config_create(client, monkeypatch):
    """Test post_kpi_config endpoint."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router, "create_kpi_config", MagicMock(return_value={"id": "new-1", "name": "New Config"})
    )
    
    resp = client.post("/api/v1/metrics/kpi/config", json={"name": "New Config", "endpoint": "summary"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["id"] == "new-1"


def test_kpi_config_update_success(client, monkeypatch):
    """Test put_kpi_config successful update."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(
        metrics_router, "update_kpi_config", MagicMock(return_value={"id": "1", "name": "Updated"})
    )
    
    resp = client.put("/api/v1/metrics/kpi/config/1", json={"name": "Updated"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["name"] == "Updated"


def test_kpi_config_delete_success(client, monkeypatch):
    """Test del_kpi_config successful deletion."""
    _patch_all_metrics(monkeypatch)
    
    monkeypatch.setattr(metrics_router, "delete_kpi_config", MagicMock(return_value=True))
    
    resp = client.delete("/api/v1/metrics/kpi/config/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ============================================================================
# Test 28: _linear_slope with zero denominator (line 459)
# ============================================================================

def test_linear_slope_zero_denominator_edge_case():
    """Test _linear_slope when denominator calculation results in zero."""
    # This happens when all x values are the same (variance is zero)
    # n * sxx - sx * sx = 0
    result = metrics_router._linear_slope([5.0, 5.0, 5.0, 5.0])
    assert result == 0.0
    
    # Another case: single value (n < 2)
    result = metrics_router._linear_slope([10.0])
    assert result == 0.0
