# -*- coding: utf-8 -*-
"""
Performance Metrics Collector
Collects and aggregates performance metrics from various sources
"""

import statistics
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

from loguru import logger


class MetricType(Enum):
    """Types of metrics"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """Represents a metric data point"""

    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "unit": self.unit,
        }


@dataclass
class HistogramBucket:
    """Histogram bucket for distribution tracking"""

    upper_bound: float
    count: int = 0


@dataclass
class Histogram:
    """Histogram for tracking value distributions"""

    name: str
    buckets: List[HistogramBucket] = field(default_factory=list)
    sum: float = 0.0
    count: int = 0
    unit: str = ""

    def observe(self, value: float) -> None:
        """Record a value in the histogram"""
        self.sum += value
        self.count += 1
        for bucket in self.buckets:
            if value <= bucket.upper_bound:
                bucket.count += 1

    def get_percentile(self, percentile: float) -> float:
        """Calculate approximate percentile"""
        if self.count == 0:
            return 0.0

        target_count = int(self.count * percentile / 100)
        cumulative = 0
        for bucket in self.buckets:
            cumulative += bucket.count
            if cumulative >= target_count:
                return bucket.upper_bound
        return self.buckets[-1].upper_bound if self.buckets else 0.0


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time"""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response_time_ms: float = 0.0
    throughput_rps: float = 0.0
    error_rate: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_percent: float = 0.0
    network_io_bytes: float = 0.0
    active_connections: int = 0
    queue_length: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "throughput_rps": self.throughput_rps,
            "error_rate": self.error_rate,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_mb": self.memory_usage_mb,
            "disk_usage_percent": self.disk_usage_percent,
            "network_io_bytes": self.network_io_bytes,
            "active_connections": self.active_connections,
            "queue_length": self.queue_length,
        }


class PerformanceMetricsCollector:
    """
    Collector for performance metrics from various sources
    """

    def __init__(self, max_history_size: int = 1000):
        """
        Initialize the metrics collector

        Args:
            max_history_size: Maximum number of data points to keep in history
        """
        self.max_history_size = max_history_size
        self.metrics: Dict[str, Deque[Metric]] = defaultdict(lambda: deque(maxlen=max_history_size))
        self.histograms: Dict[str, Histogram] = {}
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.performance_history: Deque[PerformanceSnapshot] = deque(maxlen=max_history_size)

        # Response time histogram buckets (in milliseconds)
        self.response_time_histogram = Histogram(
            name="response_time",
            buckets=[
                HistogramBucket(10),
                HistogramBucket(50),
                HistogramBucket(100),
                HistogramBucket(500),
                HistogramBucket(1000),
                HistogramBucket(5000),
                HistogramBucket(10000),
                HistogramBucket(float("inf")),
            ],
            unit="ms",
        )

        self.lock = threading.Lock()
        logger.info("Performance metrics collector initialized")

    def record_metric(self, metric: Metric) -> None:
        """
        Record a metric data point

        Args:
            metric: Metric to record
        """
        with self.lock:
            self.metrics[metric.name].append(metric)

            # Update histogram if it's a response time metric
            if metric.name == "response_time_ms":
                self.response_time_histogram.observe(metric.value)

            # Update counter or gauge
            if metric.metric_type == MetricType.COUNTER:
                self.counters[metric.name] += metric.value
            elif metric.metric_type == MetricType.GAUGE:
                self.gauges[metric.name] = metric.value

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Increment a counter metric

        Args:
            name: Counter name
            value: Value to increment by
            labels: Optional labels
        """
        metric = Metric(name=name, value=value, metric_type=MetricType.COUNTER, labels=labels or {})
        self.record_metric(metric)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric

        Args:
            name: Gauge name
            value: Gauge value
            labels: Optional labels
        """
        metric = Metric(name=name, value=value, metric_type=MetricType.GAUGE, labels=labels or {})
        self.record_metric(metric)

    def record_response_time(self, response_time_ms: float, endpoint: str = "") -> None:
        """
        Record response time metric

        Args:
            response_time_ms: Response time in milliseconds
            endpoint: Optional endpoint identifier
        """
        labels = {"endpoint": endpoint} if endpoint else {}
        metric = Metric(
            name="response_time_ms",
            value=response_time_ms,
            metric_type=MetricType.HISTOGRAM,
            labels=labels,
            unit="ms",
        )
        self.record_metric(metric)

    def record_error(self, error_type: str = "", endpoint: str = "") -> None:
        """
        Record an error metric

        Args:
            error_type: Type of error
            endpoint: Optional endpoint where error occurred
        """
        labels = {"error_type": error_type, "endpoint": endpoint} if error_type or endpoint else {}
        self.increment_counter("error_count", 1.0, labels)

    def record_request(self, endpoint: str = "") -> None:
        """
        Record a request metric

        Args:
            endpoint: Optional endpoint identifier
        """
        labels = {"endpoint": endpoint} if endpoint else {}
        self.increment_counter("request_count", 1.0, labels)

    def capture_performance_snapshot(self) -> PerformanceSnapshot:
        """
        Capture a snapshot of current performance metrics

        Returns:
            PerformanceSnapshot with current metrics
        """
        snapshot = PerformanceSnapshot()

        # Response time metrics
        if "response_time_ms" in self.metrics and self.metrics["response_time_ms"]:
            recent_times = [m.value for m in list(self.metrics["response_time_ms"])[-100:]]
            if recent_times:
                snapshot.response_time_ms = statistics.mean(recent_times)

        # Throughput calculation (requests per second)
        if "request_count" in self.counters:
            # Calculate throughput over last minute
            recent_requests = [
                m
                for m in self.metrics["request_count"]
                if m.timestamp > datetime.now(timezone.utc) - timedelta(minutes=1)
            ]
            if recent_requests:
                total_requests = sum(m.value for m in recent_requests)
                snapshot.throughput_rps = total_requests / 60.0

        # Error rate calculation
        if "error_count" in self.counters and "request_count" in self.counters:
            total_errors = self.counters["error_count"]
            total_requests = self.counters["request_count"]
            snapshot.error_rate = total_errors / total_requests if total_requests > 0 else 0.0

        # Resource metrics (would be populated by system monitoring)
        snapshot.cpu_usage_percent = self.gauges.get("cpu_usage_percent", 0.0)
        snapshot.memory_usage_mb = self.gauges.get("memory_usage_mb", 0.0)
        snapshot.disk_usage_percent = self.gauges.get("disk_usage_percent", 0.0)
        snapshot.network_io_bytes = self.gauges.get("network_io_bytes", 0.0)
        snapshot.active_connections = int(self.gauges.get("active_connections", 0.0))
        snapshot.queue_length = int(self.gauges.get("queue_length", 0.0))

        # Store snapshot in history
        with self.lock:
            self.performance_history.append(snapshot)

        return snapshot

    def get_response_time_distribution(self) -> Dict[str, Any]:
        """
        Get response time distribution statistics

        Returns:
            Dictionary with distribution statistics
        """
        if not self.response_time_histogram.count:
            return {
                "count": 0,
                "average_ms": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "max_ms": 0.0,
            }

        return {
            "count": self.response_time_histogram.count,
            "average_ms": self.response_time_histogram.sum / self.response_time_histogram.count,
            "p50_ms": self.response_time_histogram.get_percentile(50),
            "p95_ms": self.response_time_histogram.get_percentile(95),
            "p99_ms": self.response_time_histogram.get_percentile(99),
            "max_ms": (
                self.response_time_histogram.buckets[-2].upper_bound
            ),  # Exclude infinity bucket
        }

    def get_metrics_summary(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get summary of all metrics within time window

        Args:
            time_window: Optional time window to filter metrics

        Returns:
            Dictionary with metrics summary
        """
        summary: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "response_time_distribution": self.get_response_time_distribution(),
        }

        # Add time-filtered metrics if window specified
        if time_window:
            cutoff_time = datetime.now(timezone.utc) - time_window
            for metric_name, metric_list in self.metrics.items():
                recent_metrics = [m for m in metric_list if m.timestamp >= cutoff_time]
                if recent_metrics:
                    summary[f"{metric_name}_recent_count"] = len(recent_metrics)
                    summary[f"{metric_name}_recent_sum"] = sum(m.value for m in recent_metrics)
                    summary[f"{metric_name}_recent_avg"] = statistics.mean(
                        m.value for m in recent_metrics
                    )

        return summary

    def get_performance_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get performance history snapshots

        Args:
            limit: Maximum number of snapshots to return

        Returns:
            List of performance snapshots as dictionaries
        """
        with self.lock:
            snapshots = list(self.performance_history)[-limit:]
        return [snapshot.to_dict() for snapshot in snapshots]

    def reset_metrics(self) -> None:
        """Reset all metrics"""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.response_time_histogram = Histogram(
                name="response_time",
                buckets=[
                    HistogramBucket(10),
                    HistogramBucket(50),
                    HistogramBucket(100),
                    HistogramBucket(500),
                    HistogramBucket(1000),
                    HistogramBucket(5000),
                    HistogramBucket(10000),
                    HistogramBucket(float("inf")),
                ],
                unit="ms",
            )
        logger.info("Performance metrics reset")


# Global instance
_metrics_collector: Optional[PerformanceMetricsCollector] = None


def get_performance_metrics_collector() -> PerformanceMetricsCollector:
    """
    Get the global performance metrics collector instance

    Returns:
        PerformanceMetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = PerformanceMetricsCollector()
    return _metrics_collector
