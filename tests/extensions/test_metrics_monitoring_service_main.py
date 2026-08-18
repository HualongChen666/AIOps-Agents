# -*- coding: utf-8 -*-
"""Branch coverage tests for metrics_monitoring_service main.py."""

import os
import time
from collections import defaultdict

import pytest
from fastapi.testclient import TestClient

# Import the main module
from extensions.addons.observability.metrics_monitoring_service import main


@pytest.fixture(autouse=True)
def reset_timeseries_db():
    """Reset the in-memory database before each test."""
    main.timeseries_db = defaultdict(list)
    yield
    main.timeseries_db = defaultdict(list)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(main.app)


def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "metrics_monitoring_service"
    assert data["stored_samples"] == 0


def test_collect_single_sample(client):
    """Test collecting a single metric sample."""
    response = client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 75.5, "labels": {"host": "server1"}}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1


def test_collect_multiple_samples(client):
    """Test collecting multiple metric samples."""
    response = client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 75.5, "labels": {"host": "server1"}},
                {"name": "memory_usage", "value": 50.0, "labels": {"host": "server1"}},
                {"name": "cpu_usage", "value": 80.0, "labels": {"host": "server2"}},
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 3


def test_collect_with_none_labels(client):
    """Test collecting samples with None labels (branch coverage for s.labels or {})."""
    response = client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 75.5, "labels": None}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1


def test_collect_with_none_timestamp(client):
    """Test collecting samples with None timestamp (branch coverage for s.timestamp or time.time())."""
    response = client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 75.5, "timestamp": None}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1


def test_collect_empty_labels(client):
    """Test collecting samples with empty labels dict."""
    response = client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 75.5, "labels": {}}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1


def test_trim_function_triggered(client, monkeypatch):
    """Test the _trim function when samples exceed MAX_SAMPLES (branch coverage for lines 68-69)."""
    # Set MAX_SAMPLES to a small value to trigger trimming
    monkeypatch.setattr(main, "MAX_SAMPLES", 5)
    
    # Add more samples than MAX_SAMPLES
    samples = [{"name": "test_metric", "value": float(i)} for i in range(10)]
    response = client.post("/collect", json={"samples": samples})
    assert response.status_code == 200
    assert response.json()["accepted"] == 10
    
    # Verify that only MAX_SAMPLES are kept
    assert len(main.timeseries_db["test_metric"]) == 5
    # Verify that the last 5 samples are kept
    assert main.timeseries_db["test_metric"][0]["value"] == 5.0
    assert main.timeseries_db["test_metric"][-1]["value"] == 9.0


def test_query_metric_not_found(client):
    """Test querying a metric that doesn't exist (branch coverage for line 104-105)."""
    response = client.get("/query?metric=nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Metric not found"


def test_query_with_no_filters(client):
    """Test querying a metric without any filters."""
    # First add some samples
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 75.5, "timestamp": 1000.0},
                {"name": "cpu_usage", "value": 80.0, "timestamp": 2000.0},
                {"name": "cpu_usage", "value": 70.0, "timestamp": 3000.0},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage")
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "cpu_usage"
    assert data["count"] == 3
    assert data["avg"] == pytest.approx(75.1666666667)
    assert data["min"] == 70.0
    assert data["max"] == 80.0
    assert data["sum"] == pytest.approx(225.5)


def test_query_with_start_filter(client):
    """Test querying with start time filter (branch coverage for line 115-116)."""
    # Add samples with different timestamps
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 10.0, "timestamp": 1000.0},
                {"name": "cpu_usage", "value": 20.0, "timestamp": 2000.0},
                {"name": "cpu_usage", "value": 30.0, "timestamp": 3000.0},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage&start=2500")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["avg"] == 30.0


def test_query_with_end_filter(client):
    """Test querying with end time filter (branch coverage for line 117-118)."""
    # Add samples with different timestamps
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 10.0, "timestamp": 1000.0},
                {"name": "cpu_usage", "value": 20.0, "timestamp": 2000.0},
                {"name": "cpu_usage", "value": 30.0, "timestamp": 3000.0},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage&end=1500")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["avg"] == 10.0


def test_query_with_both_time_filters(client):
    """Test querying with both start and end time filters."""
    # Add samples with different timestamps
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 10.0, "timestamp": 1000.0},
                {"name": "cpu_usage", "value": 20.0, "timestamp": 2000.0},
                {"name": "cpu_usage", "value": 30.0, "timestamp": 3000.0},
                {"name": "cpu_usage", "value": 40.0, "timestamp": 4000.0},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage&start=1500&end=3500")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["avg"] == 25.0


def test_query_with_label_filter(client):
    """Test querying with label filter (branch coverage for line 110-111 and 119-120)."""
    # Add samples with different labels
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 75.5, "labels": {"host": "server1", "region": "us-east"}},
                {"name": "cpu_usage", "value": 80.0, "labels": {"host": "server2", "region": "us-west"}},
                {"name": "cpu_usage", "value": 70.0, "labels": {"host": "server1", "region": "us-west"}},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage&label_filter=host=server1")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    
    response = client.get("/query?metric=cpu_usage&label_filter=region=us-west")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2


def test_query_with_multiple_label_filters(client):
    """Test querying with multiple label filters."""
    # Add samples with different labels
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 75.5, "labels": {"host": "server1", "region": "us-east"}},
                {"name": "cpu_usage", "value": 80.0, "labels": {"host": "server2", "region": "us-west"}},
                {"name": "cpu_usage", "value": 70.0, "labels": {"host": "server1", "region": "us-west"}},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage&label_filter=host=server1,region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["avg"] == 75.5


def test_query_with_label_filter_no_match(client):
    """Test querying with label filter that matches no samples."""
    # Add samples
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 75.5, "labels": {"host": "server1"}},
                {"name": "cpu_usage", "value": 80.0, "labels": {"host": "server2"}},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage&label_filter=host=server3")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["avg"] is None
    assert data["min"] is None
    assert data["max"] is None
    assert data["sum"] is None


def test_query_empty_filtered_results(client):
    """Test querying when all samples are filtered out (branch coverage for line 123-126)."""
    # Add samples
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 75.5, "timestamp": 1000.0},
                {"name": "cpu_usage", "value": 80.0, "timestamp": 2000.0},
            ]
        },
    )
    
    # Query with a time range that excludes all samples
    response = client.get("/query?metric=cpu_usage&start=5000")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["avg"] is None
    assert data["min"] is None
    assert data["max"] is None
    assert data["sum"] is None


def test_query_aggregation_avg(client):
    """Test query with avg aggregation (branch coverage for line 128-134)."""
    client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 10.0}, {"name": "cpu_usage", "value": 20.0}]},
    )
    
    response = client.get("/query?metric=cpu_usage&agg=avg")
    assert response.status_code == 200
    data = response.json()
    assert data["avg"] == 15.0
    assert data["min"] == 10.0
    assert data["max"] == 20.0
    assert data["sum"] == 30.0


def test_query_aggregation_min(client):
    """Test query with min aggregation (branch coverage for line 135-136)."""
    client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 10.0}, {"name": "cpu_usage", "value": 20.0}]},
    )
    
    response = client.get("/query?metric=cpu_usage&agg=min")
    assert response.status_code == 200
    data = response.json()
    assert data["min"] == 10.0
    assert data["avg"] is None
    assert data["max"] is None
    assert data["sum"] is None


def test_query_aggregation_max(client):
    """Test query with max aggregation (branch coverage for line 137-138)."""
    client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 10.0}, {"name": "cpu_usage", "value": 20.0}]},
    )
    
    response = client.get("/query?metric=cpu_usage&agg=max")
    assert response.status_code == 200
    data = response.json()
    assert data["max"] == 20.0
    assert data["avg"] is None
    assert data["min"] is None
    assert data["sum"] is None


def test_query_aggregation_sum(client):
    """Test query with sum aggregation (branch coverage for line 139-140)."""
    client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 10.0}, {"name": "cpu_usage", "value": 20.0}]},
    )
    
    response = client.get("/query?metric=cpu_usage&agg=sum")
    assert response.status_code == 200
    data = response.json()
    assert data["sum"] == 30.0
    assert data["avg"] is None
    assert data["min"] is None
    assert data["max"] is None


def test_query_aggregation_count(client):
    """Test query with count aggregation (branch coverage for line 141-142)."""
    client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 10.0}, {"name": "cpu_usage", "value": 20.0}]},
    )
    
    response = client.get("/query?metric=cpu_usage&agg=count")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["avg"] is None
    assert data["min"] is None
    assert data["max"] is None
    assert data["sum"] is None


def test_query_combined_filters_and_aggregation(client):
    """Test querying with combined filters and different aggregations."""
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 10.0, "labels": {"host": "server1"}, "timestamp": 1000.0},
                {"name": "cpu_usage", "value": 20.0, "labels": {"host": "server2"}, "timestamp": 2000.0},
                {"name": "cpu_usage", "value": 30.0, "labels": {"host": "server1"}, "timestamp": 3000.0},
                {"name": "cpu_usage", "value": 40.0, "labels": {"host": "server2"}, "timestamp": 4000.0},
            ]
        },
    )
    
    # Test with label filter and min aggregation
    response = client.get("/query?metric=cpu_usage&label_filter=host=server1&agg=min")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["min"] == 10.0
    
    # Test with time filter and max aggregation
    response = client.get("/query?metric=cpu_usage&start=2500&agg=max")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["max"] == 40.0


def test_metrics_endpoint(client):
    """Test the Prometheus metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Verify it's a text response
    assert "text/plain" in response.headers["content-type"]


def test_metrics_endpoint_after_api_calls(client):
    """Test that metrics endpoint records API calls."""
    # Make some API calls
    client.post("/collect", json={"samples": [{"name": "test", "value": 1.0}]})
    client.get("/query?metric=test")
    client.get("/health")
    
    # Check metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text
    # Verify that the counter is present
    assert "metrics_api_calls_total" in metrics_text


def test_invalid_aggregation(client):
    """Test that invalid aggregation is rejected by FastAPI validation."""
    # The regex in the Query parameter should reject invalid aggregations
    response = client.get("/query?metric=cpu_usage&agg=invalid")
    # FastAPI should return 422 for invalid query parameter
    assert response.status_code == 422


def test_query_with_missing_label_value(client):
    """Test label filter with missing value (branch coverage for label parsing)."""
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 75.5, "labels": {"host": "server1"}},
            ]
        },
    )
    
    # Label filter without value should be ignored (due to "if '=' in part" check)
    response = client.get("/query?metric=cpu_usage&label_filter=host")
    assert response.status_code == 200
    data = response.json()
    # Should return all samples since the filter is invalid
    assert data["count"] == 1


def test_query_with_malformed_label_filter(client):
    """Test label filter with malformed entries."""
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 75.5, "labels": {"host": "server1"}},
            ]
        },
    )
    
    # Mix of valid and invalid label filters
    response = client.get("/query?metric=cpu_usage&label_filter=host=server1,invalid")
    assert response.status_code == 200
    data = response.json()
    # Should filter by the valid part
    assert data["count"] == 1


def test_collect_with_custom_timestamp(client):
    """Test collecting samples with custom timestamp."""
    custom_time = 1234567890.0
    response = client.post(
        "/collect",
        json={"samples": [{"name": "cpu_usage", "value": 75.5, "timestamp": custom_time}]},
    )
    assert response.status_code == 200
    
    # Verify the timestamp was stored correctly
    assert main.timeseries_db["cpu_usage"][0]["timestamp"] == custom_time


def test_multiple_metrics_same_name(client):
    """Test collecting multiple samples for the same metric name."""
    response = client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 10.0},
                {"name": "cpu_usage", "value": 20.0},
                {"name": "cpu_usage", "value": 30.0},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["accepted"] == 3
    assert len(main.timeseries_db["cpu_usage"]) == 3


def test_multiple_metrics_different_names(client):
    """Test collecting samples for different metric names."""
    response = client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 10.0},
                {"name": "memory_usage", "value": 50.0},
                {"name": "disk_usage", "value": 80.0},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["accepted"] == 3
    assert len(main.timeseries_db["cpu_usage"]) == 1
    assert len(main.timeseries_db["memory_usage"]) == 1
    assert len(main.timeseries_db["disk_usage"]) == 1


def test_query_returns_time_range(client):
    """Test that query returns the requested time range."""
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 10.0, "timestamp": 1000.0},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage&start=500&end=2000")
    assert response.status_code == 200
    data = response.json()
    assert data["start"] == 500.0
    assert data["end"] == 2000.0


def test_query_with_none_time_range(client):
    """Test query with None time range values."""
    client.post(
        "/collect",
        json={
            "samples": [
                {"name": "cpu_usage", "value": 10.0},
            ]
        },
    )
    
    response = client.get("/query?metric=cpu_usage")
    assert response.status_code == 200
    data = response.json()
    assert data["start"] is None
    assert data["end"] is None
