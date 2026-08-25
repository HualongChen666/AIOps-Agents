# -*- coding: utf-8 -*-
"""
Simple unit tests for anomaly_router.py - Testing without async complexity
"""

import asyncio
import datetime
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

# Import the actual module for coverage
from api import anomaly_router


def run_async(coro):
    """Helper to run async functions in sync tests"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestGetRecords:
    """Test cases for GET /api/v1/anomaly/records endpoint"""

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_get_records_success(self, mock_detect, mock_history):
        """Test successful retrieval of anomaly records"""
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.return_value = [{"metric": "cpu", "value": 30, "is_anomaly": True}]

        result = run_async(anomaly_router.get_records())

        assert result == [{"metric": "cpu", "value": 30, "is_anomaly": True}]
        mock_history.to_dict.assert_called_once()
        mock_detect.assert_called_once_with({"cpu": [10, 20, 30]})

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_get_records_empty_history(self, mock_detect, mock_history):
        """Test with empty metrics history"""
        mock_history.to_dict.return_value = {}
        mock_detect.return_value = []

        result = run_async(anomaly_router.get_records())

        assert result == []
        mock_detect.assert_called_once_with({})

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_get_records_no_anomalies(self, mock_detect, mock_history):
        """Test when no anomalies are detected"""
        mock_history.to_dict.return_value = {"cpu": [10, 15, 12]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.get_records())

        assert result == []

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_get_records_multiple_anomalies(self, mock_detect, mock_history):
        """Test with multiple anomaly records"""
        mock_history.to_dict.return_value = {"cpu": [10, 100, 15], "memory": [20, 80, 25]}
        mock_detect.return_value = [
            {"metric": "cpu", "value": 100, "is_anomaly": True},
            {"metric": "memory", "value": 80, "is_anomaly": True},
        ]

        result = run_async(anomaly_router.get_records())

        assert len(result) == 2
        assert result[0]["metric"] == "cpu"
        assert result[1]["metric"] == "memory"


class TestGetStatistics:
    """Test cases for GET /api/v1/anomaly/statistics endpoint"""

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_anomalies")
    def test_get_statistics_success(self, mock_detect, mock_history):
        """Test successful retrieval of anomaly statistics"""
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.side_effect = [
            [{"metric": "cpu", "value": 30}],  # cpu anomalies
            [],  # memory anomalies
            [{"metric": "net_in", "value": 100}],  # net_in anomalies
        ]

        result = run_async(anomaly_router.get_statistics())

        assert result["cpu"] == 1
        assert result["memory"] == 0
        assert result["net_in"] == 1
        assert result["total"] == 2

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_anomalies")
    def test_get_statistics_empty_history(self, mock_detect, mock_history):
        """Test with empty metrics history"""
        mock_history.to_dict.return_value = {}
        mock_detect.return_value = []

        result = run_async(anomaly_router.get_statistics())

        assert result["cpu"] == 0
        assert result["memory"] == 0
        assert result["net_in"] == 0
        assert result["total"] == 0

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_anomalies")
    def test_get_statistics_all_metrics_zero(self, mock_detect, mock_history):
        """Test when all metrics have zero anomalies"""
        mock_history.to_dict.return_value = {"cpu": [10, 15, 12]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.get_statistics())

        assert result["total"] == 0
        assert all(result[m] == 0 for m in ["cpu", "memory", "net_in"])

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_anomalies")
    def test_get_statistics_high_anomaly_count(self, mock_detect, mock_history):
        """Test with high anomaly counts"""
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.side_effect = [
            [{"i": i} for i in range(10)],  # 10 cpu anomalies
            [{"i": i} for i in range(5)],  # 5 memory anomalies
            [{"i": i} for i in range(3)],  # 3 net_in anomalies
        ]

        result = run_async(anomaly_router.get_statistics())

        assert result["cpu"] == 10
        assert result["memory"] == 5
        assert result["net_in"] == 3
        assert result["total"] == 18


class TestDetectEndpoint:
    """Test cases for POST /api/v1/anomaly/detect endpoint"""

    @patch("api.anomaly_router.detect_anomalies")
    def test_detect_with_payload(self, mock_detect):
        """Test detection with custom payload"""
        payload = {
            "metric": "cpu",
            "values": [10, 20, 100, 15],
            "timestamps": [
                "2024-01-01T00:00:00",
                "2024-01-01T00:01:00",
                "2024-01-01T00:02:00",
                "2024-01-01T00:03:00",
            ],
        }
        mock_detect.return_value = [{"metric": "cpu", "value": 100, "is_anomaly": True}]

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == [{"metric": "cpu", "value": 100, "is_anomaly": True}]
        assert result["count"] == 1
        mock_detect.assert_called_once()

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_detect_without_payload(self, mock_detect, mock_history):
        """Test detection without payload (uses system history)"""
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.return_value = [{"metric": "cpu", "value": 30, "is_anomaly": True}]

        result = run_async(anomaly_router.detect_endpoint(None))

        assert result["anomalies"] == [{"metric": "cpu", "value": 30, "is_anomaly": True}]
        assert result["count"] == 1
        mock_history.to_dict.assert_called_once()
        mock_detect.assert_called_once_with({"cpu": [10, 20, 30]})

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_detect_with_empty_payload(self, mock_detect, mock_history):
        """Test detection with empty payload dict"""
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint({}))

        assert result["anomalies"] == []
        assert result["count"] == 0

    def test_detect_values_not_list_raises_422(self):
        """Test that non-list values raises HTTP 422"""
        payload = {"metric": "cpu", "values": "not a list"}

        with pytest.raises(HTTPException) as exc_info:
            run_async(anomaly_router.detect_endpoint(payload))

        assert exc_info.value.status_code == 422
        assert "values must be a list" in str(exc_info.value.detail)

    def test_detect_values_is_dict_raises_422(self):
        """Test that dict values raises HTTP 422"""
        payload = {"metric": "cpu", "values": {"a": 1, "b": 2}}

        with pytest.raises(HTTPException) as exc_info:
            run_async(anomaly_router.detect_endpoint(payload))

        assert exc_info.value.status_code == 422

    def test_detect_values_is_int_raises_422(self):
        """Test that int values raises HTTP 422"""
        payload = {"metric": "cpu", "values": 123}

        with pytest.raises(HTTPException) as exc_info:
            run_async(anomaly_router.detect_endpoint(payload))

        assert exc_info.value.status_code == 422

    @patch("api.anomaly_router.detect_anomalies")
    @patch("api.anomaly_router.datetime")
    def test_detect_without_timestamps_generates_default(self, mock_datetime, mock_detect):
        """Test that missing timestamps are auto-generated"""
        payload = {"metric": "cpu", "values": [10, 20, 30]}
        mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T00:00:00"
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == []
        assert result["count"] == 0
        # Verify timestamps were generated
        call_args = mock_detect.call_args[0][0]
        assert "timestamps" in call_args
        assert len(call_args["timestamps"]) == 3

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_detect_with_metric_only(self, mock_detect, mock_history):
        """Test with metric but no values (uses system history)"""
        payload = {"metric": "cpu"}
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == []
        assert result["count"] == 0

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_detect_with_values_only(self, mock_detect, mock_history):
        """Test with values but no metric (uses system history)"""
        payload = {"values": [10, 20, 30]}
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == []
        assert result["count"] == 0

    @patch("api.anomaly_router.detect_anomalies")
    def test_detect_empty_values_list(self, mock_detect):
        """Test with empty values list"""
        payload = {"metric": "cpu", "values": []}
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == []
        assert result["count"] == 0

    @patch("api.anomaly_router.detect_anomalies")
    def test_detect_single_value(self, mock_detect):
        """Test with single value"""
        payload = {"metric": "cpu", "values": [50]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == []
        assert result["count"] == 0

    @patch("api.anomaly_router.detect_anomalies")
    def test_detect_large_dataset(self, mock_detect):
        """Test with large dataset"""
        payload = {"metric": "cpu", "values": list(range(1000))}
        mock_detect.return_value = [{"metric": "cpu", "value": 999, "is_anomaly": True}]

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["count"] == 1
        assert len(result["anomalies"]) == 1

    @patch("api.anomaly_router.detect_anomalies")
    def test_detect_no_anomalies_found(self, mock_detect):
        """Test when no anomalies are found in custom payload"""
        payload = {"metric": "cpu", "values": [10, 12, 11, 13, 10]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == []
        assert result["count"] == 0

    @patch("api.anomaly_router.detect_anomalies")
    def test_detect_multiple_anomalies_found(self, mock_detect):
        """Test when multiple anomalies are found"""
        payload = {"metric": "cpu", "values": [10, 100, 15, 95, 12]}
        mock_detect.return_value = [
            {"metric": "cpu", "value": 100, "is_anomaly": True},
            {"metric": "cpu", "value": 95, "is_anomaly": True},
        ]

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["count"] == 2
        assert len(result["anomalies"]) == 2


class TestIntegration:
    """Integration tests for anomaly router"""

    def test_router_prefix_and_tags(self):
        """Test router configuration"""
        assert anomaly_router.router.prefix == "/api/v1/anomaly"
        assert anomaly_router.router.tags == ["异常检测"]

    def test_all_endpoints_registered(self):
        """Test that all endpoints are properly registered"""
        routes = [route.path for route in anomaly_router.router.routes]
        assert "/api/v1/anomaly/records" in routes
        assert "/api/v1/anomaly/statistics" in routes
        assert "/api/v1/anomaly/detect" in routes


class TestEdgeCases:
    """Edge case tests"""

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_detect_with_none_values(self, mock_detect, mock_history):
        """Test with None values"""
        payload = {"metric": "cpu", "values": None}
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == []

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_all_anomalies")
    def test_detect_with_none_metric(self, mock_detect, mock_history):
        """Test with None metric"""
        payload = {"metric": None, "values": [10, 20, 30]}
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}
        mock_detect.return_value = []

        result = run_async(anomaly_router.detect_endpoint(payload))

        assert result["anomalies"] == []

    @patch("api.anomaly_router.metrics_history")
    @patch("api.anomaly_router.detect_anomalies")
    def test_get_statistics_with_missing_metrics(self, mock_detect, mock_history):
        """Test statistics when some metrics are missing from history"""
        mock_history.to_dict.return_value = {"cpu": [10, 20, 30]}  # Only cpu
        mock_detect.return_value = []

        result = run_async(anomaly_router.get_statistics())

        # Should still check all three metrics
        assert "cpu" in result
        assert "memory" in result
        assert "net_in" in result
        assert "total" in result
        assert mock_detect.call_count == 3  # Called for each metric


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
