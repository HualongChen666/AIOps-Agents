# -*- coding: utf-8 -*-
"""
Simple comprehensive coverage tests for batch_router.py
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from api.batch_router import batch_get_alerts, batch_get_metrics, router


def run_async(coro):
    """Helper to run async functions in sync tests"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestBatchGetAlerts:
    """Test cases for POST /api/v1/batch/alerts endpoint"""

    @patch(
        "core.alert_engine.alert_history",
        new=[
            {"id": "alert-1", "title": "CPU告警", "level": "critical"},
            {"id": "alert-2", "title": "内存告警", "level": "warning"},
            {"id": "alert-3", "title": "磁盘告警", "level": "info"},
        ],
    )
    def test_batch_get_alerts_success(self):
        """Test successful batch retrieval of alerts"""
        alert_ids = ["alert-1", "alert-2"]
        result = run_async(batch_get_alerts(alert_ids))

        assert result["results"] == [
            {"id": "alert-1", "title": "CPU告警", "level": "critical"},
            {"id": "alert-2", "title": "内存告警", "level": "warning"},
        ]

    @patch("core.alert_engine.alert_history", new=[])
    def test_batch_get_alerts_empty_list(self):
        """Test with empty alert_ids list"""
        alert_ids = []
        result = run_async(batch_get_alerts(alert_ids))

        assert result["results"] == []

    @patch(
        "core.alert_engine.alert_history",
        new=[{"id": "alert-1", "title": "CPU告警", "level": "critical"}],
    )
    def test_batch_get_alerts_nonexistent_ids(self):
        """Test with non-existent alert IDs"""
        alert_ids = ["alert-999", "alert-1000"]
        result = run_async(batch_get_alerts(alert_ids))

        assert result["results"] == [None, None]

    @patch(
        "core.alert_engine.alert_history",
        new=[
            {"id": "alert-1", "title": "CPU告警", "level": "critical"},
            {"id": "alert-3", "title": "磁盘告警", "level": "info"},
        ],
    )
    def test_batch_get_alerts_mixed_results(self):
        """Test with mix of existing and non-existing IDs"""
        alert_ids = ["alert-1", "alert-2", "alert-3"]
        result = run_async(batch_get_alerts(alert_ids))

        assert result["results"] == [
            {"id": "alert-1", "title": "CPU告警", "level": "critical"},
            None,
            {"id": "alert-3", "title": "磁盘告警", "level": "info"},
        ]

    @patch(
        "core.alert_engine.alert_history",
        new=[{"id": f"alert-{i}", "title": f"告警{i}", "level": "critical"} for i in range(100)],
    )
    def test_batch_get_alerts_large_batch(self):
        """Test with large batch of alert IDs"""
        alert_ids = [f"alert-{i}" for i in range(50)]
        result = run_async(batch_get_alerts(alert_ids))

        assert len(result["results"]) == 50
        assert all(r is not None for r in result["results"])

    @patch(
        "core.alert_engine.alert_history",
        new=[{"id": "alert-1", "title": "CPU告警", "level": "critical"}],
    )
    def test_batch_get_alerts_duplicate_ids(self):
        """Test with duplicate alert IDs"""
        alert_ids = ["alert-1", "alert-1", "alert-1"]
        result = run_async(batch_get_alerts(alert_ids))

        assert result["results"] == [
            {"id": "alert-1", "title": "CPU告警", "level": "critical"},
            {"id": "alert-1", "title": "CPU告警", "level": "critical"},
            {"id": "alert-1", "title": "CPU告警", "level": "critical"},
        ]

    @patch("core.alert_engine.alert_history", new=[])
    def test_batch_get_alerts_empty_alert_history(self):
        """Test when alert_history is empty"""
        alert_ids = ["alert-1", "alert-2"]
        result = run_async(batch_get_alerts(alert_ids))

        assert result["results"] == [None, None]

    @patch(
        "core.alert_engine.alert_history",
        new=[
            {"title": "CPU告警", "level": "critical"},  # Missing id
            {"id": "alert-2", "title": "内存告警", "level": "warning"},
        ],
    )
    def test_batch_get_alerts_alert_without_id(self):
        """Test when alert_history contains alerts without id field"""
        alert_ids = ["alert-1", "alert-2"]
        result = run_async(batch_get_alerts(alert_ids))

        assert result["results"] == [
            None,
            {"id": "alert-2", "title": "内存告警", "level": "warning"},
        ]


class TestBatchGetMetrics:
    """Test cases for POST /api/v1/batch/metrics endpoint"""

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_success(self, mock_collect_all):
        """Test successful batch retrieval of metrics"""
        mock_collect_all.return_value = {
            "cpu_usage": {"value": 45.2, "unit": "%"},
            "memory_usage": {"value": 68.3, "unit": "%"},
            "disk_usage": {"value": 80.5, "unit": "%"},
        }

        metric_ids = ["cpu_usage", "memory_usage"]
        result = run_async(batch_get_metrics(metric_ids))

        assert result["results"] == {
            "cpu_usage": {"value": 45.2, "unit": "%"},
            "memory_usage": {"value": 68.3, "unit": "%"},
        }

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_empty_list(self, mock_collect_all):
        """Test with empty metric_ids list"""
        mock_collect_all.return_value = {"cpu_usage": {"value": 45.2, "unit": "%"}}

        metric_ids = []
        result = run_async(batch_get_metrics(metric_ids))

        assert result["results"] == {}

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_nonexistent_ids(self, mock_collect_all):
        """Test with non-existent metric IDs"""
        mock_collect_all.return_value = {"cpu_usage": {"value": 45.2, "unit": "%"}}

        metric_ids = ["nonexistent_metric", "another_fake"]
        result = run_async(batch_get_metrics(metric_ids))

        assert result["results"] == {}

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_all_available(self, mock_collect_all):
        """Test requesting all available metrics"""
        mock_collect_all.return_value = {
            "cpu_usage": {"value": 45.2, "unit": "%"},
            "memory_usage": {"value": 68.3, "unit": "%"},
            "disk_usage": {"value": 80.5, "unit": "%"},
        }

        metric_ids = ["cpu_usage", "memory_usage", "disk_usage"]
        result = run_async(batch_get_metrics(metric_ids))

        assert len(result["results"]) == 3
        assert "cpu_usage" in result["results"]
        assert "memory_usage" in result["results"]
        assert "disk_usage" in result["results"]

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_empty_collect_all(self, mock_collect_all):
        """Test when collect_all returns empty dict"""
        mock_collect_all.return_value = {}

        metric_ids = ["cpu_usage", "memory_usage"]
        result = run_async(batch_get_metrics(metric_ids))

        assert result["results"] == {}

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_large_batch(self, mock_collect_all):
        """Test with large batch of metric IDs"""
        mock_collect_all.return_value = {
            f"metric_{i}": {"value": i * 10, "unit": "%"} for i in range(100)
        }

        metric_ids = [f"metric_{i}" for i in range(50)]
        result = run_async(batch_get_metrics(metric_ids))

        assert len(result["results"]) == 50

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_duplicate_ids(self, mock_collect_all):
        """Test with duplicate metric IDs"""
        mock_collect_all.return_value = {"cpu_usage": {"value": 45.2, "unit": "%"}}

        metric_ids = ["cpu_usage", "cpu_usage", "cpu_usage"]
        result = run_async(batch_get_metrics(metric_ids))

        # Should return single entry since it's a dict
        assert result["results"] == {"cpu_usage": {"value": 45.2, "unit": "%"}}

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_complex_values(self, mock_collect_all):
        """Test with complex metric values"""
        mock_collect_all.return_value = {
            "cpu_usage": {"value": 45.2, "unit": "%", "timestamp": "2024-01-01T00:00:00"},
            "memory_usage": {"value": 68.3, "unit": "%", "tags": ["server1", "production"]},
        }

        metric_ids = ["cpu_usage", "memory_usage"]
        result = run_async(batch_get_metrics(metric_ids))

        assert result["results"]["cpu_usage"]["timestamp"] == "2024-01-01T00:00:00"
        assert result["results"]["memory_usage"]["tags"] == ["server1", "production"]


class TestIntegration:
    """Integration tests for batch router"""

    def test_router_prefix_and_tags(self):
        """Test router configuration"""
        assert router.prefix == "/api/v1/batch"
        assert router.tags == ["Batch"]

    def test_all_endpoints_registered(self):
        """Test that all endpoints are properly registered"""
        routes = [route.path for route in router.routes]
        assert "/api/v1/batch/alerts" in routes
        assert "/api/v1/batch/metrics" in routes

    def test_endpoint_responses(self):
        """Test endpoint response configurations"""
        routes = {route.path: route for route in router.routes}

        # Check alerts endpoint
        alerts_route = routes["/api/v1/batch/alerts"]
        assert 200 in alerts_route.responses
        assert 500 in alerts_route.responses

        # Check metrics endpoint
        metrics_route = routes["/api/v1/batch/metrics"]
        assert 200 in metrics_route.responses
        assert 500 in metrics_route.responses


class TestEdgeCases:
    """Edge case tests"""

    @patch(
        "core.alert_engine.alert_history",
        new=[{"id": "alert-1", "title": "CPU告警", "level": "critical"}],
    )
    def test_batch_get_alerts_single_id(self):
        """Test with single alert ID"""
        alert_ids = ["alert-1"]
        result = run_async(batch_get_alerts(alert_ids))

        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "alert-1"

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_single_id(self, mock_collect_all):
        """Test with single metric ID"""
        mock_collect_all.return_value = {"cpu_usage": {"value": 45.2, "unit": "%"}}

        metric_ids = ["cpu_usage"]
        result = run_async(batch_get_metrics(metric_ids))

        assert len(result["results"]) == 1
        assert "cpu_usage" in result["results"]

    @patch(
        "core.alert_engine.alert_history",
        new=[{"id": "Alert-1", "title": "CPU告警", "level": "critical"}],
    )
    def test_batch_get_alerts_case_sensitive(self):
        """Test case sensitivity of alert IDs"""
        alert_ids = ["alert-1"]  # Different case
        result = run_async(batch_get_alerts(alert_ids))

        assert result["results"] == [None]  # Should not match due to case sensitivity

    @patch("core.collector.collect_all")
    def test_batch_get_metrics_case_sensitive(self, mock_collect_all):
        """Test case sensitivity of metric IDs"""
        mock_collect_all.return_value = {"CPU_Usage": {"value": 45.2, "unit": "%"}}

        metric_ids = ["cpu_usage"]  # Different case
        result = run_async(batch_get_metrics(metric_ids))

        assert result["results"] == {}  # Should not match due to case sensitivity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
