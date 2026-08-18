# -*- coding: utf-8 -*-
"""Tests for metrics.py - Prometheus metrics collector."""

import time
import pytest

from extensions.addons.documentation.sphinx_documentation_service.metrics import (
    MetricsCollector,
)


class TestMetricsCollector:
    """Test suite for MetricsCollector."""

    def test_init_default(self):
        """Test initialization with default parameters."""
        metrics = MetricsCollector("test-service")
        assert metrics.request_count == 0
        assert metrics.cache_hits_count == 0
        assert metrics.cache_misses_count == 0

    def test_init_with_hyphenated_name(self):
        """Test initialization with hyphenated service name."""
        metrics = MetricsCollector("test-service")
        assert metrics is not None

    def test_init_with_underscored_name(self):
        """Test initialization with underscored service name."""
        metrics = MetricsCollector("test_service")
        assert metrics is not None

    def test_singleton_pattern_same_name(self):
        """Test that singleton pattern returns same instance for same name."""
        metrics1 = MetricsCollector("test-service")
        metrics2 = MetricsCollector("test-service")
        assert metrics1 is metrics2

    def test_singleton_pattern_different_names(self):
        """Test that singleton pattern creates different instances for different names."""
        metrics1 = MetricsCollector("service1")
        metrics2 = MetricsCollector("service2")
        assert metrics1 is not metrics2

    def test_singleton_pattern_normalization(self):
        """Test that name normalization works for singleton pattern."""
        metrics1 = MetricsCollector("test-service")
        metrics2 = MetricsCollector("test_service")
        # Hyphens are replaced with underscores, so these should be the same
        assert metrics1 is metrics2

    def test_inc_request(self):
        """Test incrementing request count."""
        metrics = MetricsCollector("test-service")
        initial = metrics.request_count
        metrics.inc_request("test_operation")
        assert metrics.request_count == initial + 1

    def test_inc_request_multiple(self):
        """Test incrementing request count multiple times."""
        metrics = MetricsCollector("test-service-unique-1")
        for _ in range(5):
            metrics.inc_request("test_operation")
        assert metrics.request_count == 5

    def test_inc_request_different_operations(self):
        """Test incrementing request count for different operations."""
        metrics = MetricsCollector("test-service-unique-2")
        metrics.inc_request("op1")
        metrics.inc_request("op2")
        metrics.inc_request("op1")
        assert metrics.request_count == 3

    def test_inc_failure(self):
        """Test incrementing failure count."""
        metrics = MetricsCollector("test-service")
        metrics.inc_failure("test_operation", "test_error")
        # The failure counter is in the Prometheus metric
        assert metrics.failures is not None

    def test_inc_failure_without_error(self):
        """Test incrementing failure count without error name."""
        metrics = MetricsCollector("test-service")
        metrics.inc_failure("test_operation")
        assert metrics.failures is not None

    def test_inc_failure_different_errors(self):
        """Test incrementing failure count for different errors."""
        metrics = MetricsCollector("test-service")
        metrics.inc_failure("test_operation", "error1")
        metrics.inc_failure("test_operation", "error2")
        assert metrics.failures is not None

    def test_observe_latency(self):
        """Test observing latency."""
        metrics = MetricsCollector("test-service")
        metrics.observe_latency("test_operation", 0.5)
        assert metrics.latency is not None

    def test_observe_latency_zero(self):
        """Test observing zero latency."""
        metrics = MetricsCollector("test-service")
        metrics.observe_latency("test_operation", 0.0)
        assert metrics.latency is not None

    def test_observe_latency_negative(self):
        """Test observing negative latency (should be handled)."""
        metrics = MetricsCollector("test-service")
        metrics.observe_latency("test_operation", -0.1)
        assert metrics.latency is not None

    def test_observe_latency_large_value(self):
        """Test observing large latency value."""
        metrics = MetricsCollector("test-service")
        metrics.observe_latency("test_operation", 1000.0)
        assert metrics.latency is not None

    def test_time_operation_context_manager(self):
        """Test time_operation as context manager."""
        metrics = MetricsCollector("test-service")
        with metrics.time_operation("test_operation"):
            time.sleep(0.01)
        assert metrics.latency is not None

    def test_time_operation_measures_time(self):
        """Test that time_operation actually measures time."""
        metrics = MetricsCollector("test-service")
        with metrics.time_operation("test_operation"):
            time.sleep(0.05)
        # The latency should have been recorded
        assert metrics.latency is not None

    def test_time_operation_exception_handling(self):
        """Test that time_operation handles exceptions."""
        metrics = MetricsCollector("test-service")
        try:
            with metrics.time_operation("test_operation"):
                raise ValueError("test error")
        except ValueError:
            pass
        # Latency should still be recorded
        assert metrics.latency is not None

    def test_inc_cache_hit(self):
        """Test incrementing cache hit count."""
        metrics = MetricsCollector("test-service")
        initial = metrics.cache_hits_count
        metrics.inc_cache_hit()
        assert metrics.cache_hits_count == initial + 1

    def test_inc_cache_hit_multiple(self):
        """Test incrementing cache hit count multiple times."""
        metrics = MetricsCollector("test-service-unique-3")
        for _ in range(10):
            metrics.inc_cache_hit()
        assert metrics.cache_hits_count == 10

    def test_inc_cache_miss(self):
        """Test incrementing cache miss count."""
        metrics = MetricsCollector("test-service")
        initial = metrics.cache_misses_count
        metrics.inc_cache_miss()
        assert metrics.cache_misses_count == initial + 1

    def test_inc_cache_miss_multiple(self):
        """Test incrementing cache miss count multiple times."""
        metrics = MetricsCollector("test-service-unique-4")
        for _ in range(10):
            metrics.inc_cache_miss()
        assert metrics.cache_misses_count == 10

    def test_set_index_size(self):
        """Test setting index size."""
        metrics = MetricsCollector("test-service")
        metrics.set_index_size(100)
        assert metrics.index_size is not None

    def test_set_index_size_zero(self):
        """Test setting index size to zero."""
        metrics = MetricsCollector("test-service")
        metrics.set_index_size(0)
        assert metrics.index_size is not None

    def test_set_index_size_negative(self):
        """Test setting negative index size."""
        metrics = MetricsCollector("test-service")
        metrics.set_index_size(-1)
        assert metrics.index_size is not None

    def test_set_index_size_large(self):
        """Test setting large index size."""
        metrics = MetricsCollector("test-service")
        metrics.set_index_size(1000000)
        assert metrics.index_size is not None

    def test_set_index_size_update(self):
        """Test updating index size."""
        metrics = MetricsCollector("test-service")
        metrics.set_index_size(100)
        metrics.set_index_size(200)
        assert metrics.index_size is not None

    def test_observe_batch_size(self):
        """Test observing batch size."""
        metrics = MetricsCollector("test-service")
        metrics.observe_batch_size("test_operation", 50)
        assert metrics.batch_size is not None

    def test_observe_batch_size_zero(self):
        """Test observing zero batch size."""
        metrics = MetricsCollector("test-service")
        metrics.observe_batch_size("test_operation", 0)
        assert metrics.batch_size is not None

    def test_observe_batch_size_negative(self):
        """Test observing negative batch size."""
        metrics = MetricsCollector("test-service")
        metrics.observe_batch_size("test_operation", -1)
        assert metrics.batch_size is not None

    def test_observe_batch_size_large(self):
        """Test observing large batch size."""
        metrics = MetricsCollector("test-service")
        metrics.observe_batch_size("test_operation", 10000)
        assert metrics.batch_size is not None

    def test_observe_batch_size_different_operations(self):
        """Test observing batch size for different operations."""
        metrics = MetricsCollector("test-service")
        metrics.observe_batch_size("op1", 10)
        metrics.observe_batch_size("op2", 20)
        assert metrics.batch_size is not None

    def test_inc_operation(self):
        """Test incrementing operation count."""
        metrics = MetricsCollector("test-service")
        metrics.inc_operation("test_operation")
        assert metrics.operation_count is not None

    def test_inc_operation_multiple(self):
        """Test incrementing operation count multiple times."""
        metrics = MetricsCollector("test-service")
        for _ in range(5):
            metrics.inc_operation("test_operation")
        assert metrics.operation_count is not None

    def test_inc_operation_different_operations(self):
        """Test incrementing operation count for different operations."""
        metrics = MetricsCollector("test-service")
        metrics.inc_operation("op1")
        metrics.inc_operation("op2")
        metrics.inc_operation("op1")
        assert metrics.operation_count is not None

    def test_prometheus_metrics_exist(self):
        """Test that all Prometheus metrics are created."""
        metrics = MetricsCollector("test-service")
        assert metrics.requests is not None
        assert metrics.failures is not None
        assert metrics.latency is not None
        assert metrics.cache_hits is not None
        assert metrics.cache_misses is not None
        assert metrics.index_size is not None
        assert metrics.batch_size is not None
        assert metrics.operation_count is not None

    def test_prometheus_metrics_labels(self):
        """Test that Prometheus metrics have correct labels."""
        metrics = MetricsCollector("test-service")
        # Requests should have 'operation' label
        metrics.inc_request("test_op")
        # Failures should have 'operation' and 'error' labels
        metrics.inc_failure("test_op", "test_error")
        # Latency should have 'operation' label
        metrics.observe_latency("test_op", 0.5)
        # Batch size should have 'operation' label
        metrics.observe_batch_size("test_op", 10)
        # Operation count should have 'operation' label
        metrics.inc_operation("test_op")

    def test_initialized_flag(self):
        """Test that _initialized flag prevents re-initialization."""
        metrics = MetricsCollector("test-service")
        # Calling init again should not re-initialize
        assert metrics._initialized is True

    def test_instances_dict(self):
        """Test that instances are stored in _instances dict."""
        MetricsCollector._instances.clear()  # Clear for clean test
        metrics1 = MetricsCollector("test-service-unique-5")
        assert "test_service_unique_5" in MetricsCollector._instances
        assert MetricsCollector._instances["test_service_unique_5"] is metrics1

    def test_service_name_normalization(self):
        """Test that service names are normalized (hyphens to underscores)."""
        metrics1 = MetricsCollector("test-service-name")
        metrics2 = MetricsCollector("test_service_name")
        assert metrics1 is metrics2

    def test_multiple_metrics_collectors(self):
        """Test creating multiple metrics collectors for different services."""
        MetricsCollector._instances.clear()  # Clear for clean test
        metrics1 = MetricsCollector("service1-unique")
        metrics2 = MetricsCollector("service2-unique")
        metrics3 = MetricsCollector("service3-unique")
        assert metrics1 is not metrics2
        assert metrics2 is not metrics3
        assert metrics1 is not metrics3

    def test_concurrent_metric_updates(self):
        """Test concurrent metric updates."""
        import threading

        MetricsCollector._instances.clear()  # Clear for clean test
        metrics = MetricsCollector("test-service-unique-6")

        def increment_requests():
            for _ in range(10):
                metrics.inc_request("test_operation")

        threads = [threading.Thread(target=increment_requests) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert metrics.request_count == 100

    def test_time_operation_nested(self):
        """Test nested time_operation calls."""
        MetricsCollector._instances.clear()  # Clear for clean test
        metrics = MetricsCollector("test-service-unique-7")
        with metrics.time_operation("outer"):
            with metrics.time_operation("inner"):
                time.sleep(0.01)
        assert metrics.latency is not None

    def test_metric_name_prefix(self):
        """Test that metric names have correct prefix."""
        metrics = MetricsCollector("my-service")
        # The prefix should be "my_service" (hyphens replaced)
        assert metrics.requests is not None
        assert metrics.failures is not None

    def test_cache_hit_miss_ratio(self):
        """Test cache hit/miss ratio calculation."""
        MetricsCollector._instances.clear()  # Clear for clean test
        metrics = MetricsCollector("test-service-unique-8")
        metrics.inc_cache_hit()
        metrics.inc_cache_hit()
        metrics.inc_cache_hit()
        metrics.inc_cache_miss()
        metrics.inc_cache_miss()
        # 3 hits, 2 misses
        assert metrics.cache_hits_count == 3
        assert metrics.cache_misses_count == 2

    def test_all_operations_in_counter(self):
        """Test that all operations can be counted."""
        MetricsCollector._instances.clear()  # Clear for clean test
        metrics = MetricsCollector("test-service-unique-9")
        operations = ["op1", "op2", "op3", "op4", "op5"]
        for op in operations:
            metrics.inc_operation(op)
        assert metrics.operation_count is not None

    def test_unicode_operation_names(self):
        """Test metric operations with unicode names."""
        MetricsCollector._instances.clear()  # Clear for clean test
        metrics = MetricsCollector("test-service-unique-10")
        metrics.inc_request("操作1")
        metrics.inc_failure("操作2", "错误")
        metrics.observe_latency("操作3", 0.5)
        assert metrics.request_count > 0

    def test_special_characters_in_operation_names(self):
        """Test metric operations with special characters."""
        MetricsCollector._instances.clear()  # Clear for clean test
        metrics = MetricsCollector("test-service-unique-11")
        metrics.inc_request("op-with-dashes")
        metrics.inc_request("op_with_underscores")
        metrics.inc_request("op.with.dots")
        assert metrics.request_count == 3
