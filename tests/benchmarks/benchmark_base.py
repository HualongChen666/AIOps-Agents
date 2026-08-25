# -*- coding: utf-8 -*-
"""
Performance Benchmark Base Framework
====================================

Enterprise-level performance benchmark testing framework providing:
- Base class for performance tests
- Performance metrics collection
- Result analysis and reporting
- Support for multiple performance metrics
"""

import asyncio
import json
import os
import statistics
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import psutil
from loguru import logger


class PerformanceMetricType(Enum):
    """Types of performance metrics that can be collected"""

    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    ERROR_RATE = "error_rate"
    CONCURRENCY = "concurrency"
    LATENCY_PERCENTILES = "latency_percentiles"


class PerformanceSeverity(Enum):
    """Severity levels for performance issues"""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""

    metric_type: PerformanceMetricType
    excellent: float
    good: float
    acceptable: float
    warning: float
    critical: float
    unit: str = "ms"

    def get_severity(self, value: float) -> PerformanceSeverity:
        """Determine severity based on value"""
        if value <= self.excellent:
            return PerformanceSeverity.EXCELLENT
        elif value <= self.good:
            return PerformanceSeverity.GOOD
        elif value <= self.acceptable:
            return PerformanceSeverity.ACCEPTABLE
        elif value <= self.warning:
            return PerformanceSeverity.WARNING
        else:
            return PerformanceSeverity.CRITICAL


@dataclass
class MetricSample:
    """Single metric measurement sample"""

    timestamp: datetime
    metric_type: PerformanceMetricType
    value: float
    unit: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "metadata": self.metadata,
        }


@dataclass
class PerformanceResult:
    """Complete performance test result"""

    test_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    samples: List[MetricSample] = field(default_factory=list)
    thresholds: Dict[PerformanceMetricType, PerformanceThreshold] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def sample_count(self) -> int:
        """Get total number of samples"""
        return len(self.samples)

    def get_samples_by_type(self, metric_type: PerformanceMetricType) -> List[MetricSample]:
        """Get samples filtered by metric type"""
        return [s for s in self.samples if s.metric_type == metric_type]

    def get_metric_values(self, metric_type: PerformanceMetricType) -> List[float]:
        """Get values for a specific metric type"""
        return [s.value for s in self.get_samples_by_type(metric_type)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_name": self.test_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "sample_count": self.sample_count,
            "samples": [s.to_dict() for s in self.samples],
            "thresholds": {
                k.value: {
                    "excellent": v.excellent,
                    "good": v.good,
                    "acceptable": v.acceptable,
                    "warning": v.warning,
                    "critical": v.critical,
                    "unit": v.unit,
                }
                for k, v in self.thresholds.items()
            },
            "metadata": self.metadata,
        }


class PerformanceMetricsCollector:
    """Collects performance metrics during test execution"""

    def __init__(self, sample_interval: float = 0.1):
        """
        Initialize metrics collector

        Args:
            sample_interval: Interval between samples in seconds
        """
        self.sample_interval = sample_interval
        self.samples: List[MetricSample] = []
        self._collecting = False
        self._collect_thread: Optional[threading.Thread] = None
        self._process = psutil.Process()
        self._initial_cpu_times = self._process.cpu_times()
        self._initial_io_counters = (
            self._process.io_counters() if hasattr(self._process, "io_counters") else None
        )
        self._initial_net_io = psutil.net_io_counters()

    def start_collection(self):
        """Start background metrics collection"""
        if self._collecting:
            logger.warning("Metrics collection already in progress")
            return

        self._collecting = True
        self._collect_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._collect_thread.start()
        logger.info("Started metrics collection")

    def stop_collection(self):
        """Stop background metrics collection"""
        if not self._collecting:
            return

        self._collecting = False
        if self._collect_thread:
            self._collect_thread.join(timeout=5.0)
        logger.info("Stopped metrics collection")

    def _collect_loop(self):
        """Background collection loop"""
        while self._collecting:
            try:
                self._collect_sample()
                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                break

    def _collect_sample(self):
        """Collect a single metric sample"""
        timestamp = datetime.now()

        # CPU usage
        try:
            cpu_percent = self._process.cpu_percent(interval=0.01)
            self.samples.append(
                MetricSample(
                    timestamp=timestamp,
                    metric_type=PerformanceMetricType.CPU_USAGE,
                    value=cpu_percent,
                    unit="percent",
                )
            )
        except Exception as e:
            logger.debug(f"Error collecting CPU metric: {e}")

        # Memory usage
        try:
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            self.samples.append(
                MetricSample(
                    timestamp=timestamp,
                    metric_type=PerformanceMetricType.MEMORY_USAGE,
                    value=memory_percent,
                    unit="percent",
                    metadata={"rss_mb": memory_info.rss / 1024 / 1024},
                )
            )
        except Exception as e:
            logger.debug(f"Error collecting memory metric: {e}")

        # Disk I/O
        if self._initial_io_counters:
            try:
                current_io = self._process.io_counters()
                read_bytes = current_io.read_bytes - self._initial_io_counters.read_bytes
                write_bytes = current_io.write_bytes - self._initial_io_counters.write_bytes
                self.samples.append(
                    MetricSample(
                        timestamp=timestamp,
                        metric_type=PerformanceMetricType.DISK_IO,
                        value=read_bytes + write_bytes,
                        unit="bytes",
                        metadata={"read_bytes": read_bytes, "write_bytes": write_bytes},
                    )
                )
            except Exception as e:
                logger.debug(f"Error collecting disk I/O metric: {e}")

        # Network I/O
        try:
            current_net = psutil.net_io_counters()
            net_bytes = (current_net.bytes_sent + current_net.bytes_recv) - (
                self._initial_net_io.bytes_sent + self._initial_net_io.bytes_recv
            )
            self.samples.append(
                MetricSample(
                    timestamp=timestamp,
                    metric_type=PerformanceMetricType.NETWORK_IO,
                    value=net_bytes,
                    unit="bytes",
                )
            )
        except Exception as e:
            logger.debug(f"Error collecting network I/O metric: {e}")

    def add_custom_sample(
        self,
        metric_type: PerformanceMetricType,
        value: float,
        unit: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Add a custom metric sample

        Args:
            metric_type: Type of metric
            value: Metric value
            unit: Unit of measurement
            metadata: Additional metadata
        """
        self.samples.append(
            MetricSample(
                timestamp=datetime.now(),
                metric_type=metric_type,
                value=value,
                unit=unit,
                metadata=metadata or {},
            )
        )

    def get_samples(self) -> List[MetricSample]:
        """Get all collected samples"""
        return self.samples.copy()

    def clear_samples(self):
        """Clear all collected samples"""
        self.samples.clear()


class PerformanceResultAnalyzer:
    """Analyzes performance test results"""

    def __init__(self, result: PerformanceResult):
        """
        Initialize analyzer

        Args:
            result: Performance result to analyze
        """
        self.result = result

    def calculate_statistics(self, metric_type: PerformanceMetricType) -> Dict[str, float]:
        """
        Calculate statistical metrics for a given metric type

        Args:
            metric_type: Type of metric to analyze

        Returns:
            Dictionary with statistical metrics
        """
        values = self.result.get_metric_values(metric_type)

        if not values:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "mean": statistics.mean(sorted_values),
            "median": statistics.median(sorted_values),
            "std_dev": statistics.stdev(sorted_values) if count > 1 else 0.0,
            "min": min(sorted_values),
            "max": max(sorted_values),
            "p50": self._percentile(sorted_values, 50),
            "p90": self._percentile(sorted_values, 90),
            "p95": self._percentile(sorted_values, 95),
            "p99": self._percentile(sorted_values, 99),
        }

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not sorted_values:
            return 0.0

        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def evaluate_against_thresholds(self, metric_type: PerformanceMetricType) -> Dict[str, Any]:
        """
        Evaluate metrics against configured thresholds

        Args:
            metric_type: Type of metric to evaluate

        Returns:
            Dictionary with evaluation results
        """
        if metric_type not in self.result.thresholds:
            return {"status": "no_threshold", "message": "No threshold configured"}

        threshold = self.result.thresholds[metric_type]
        stats = self.calculate_statistics(metric_type)

        # Evaluate mean value
        mean_severity = threshold.get_severity(stats["mean"])

        # Evaluate p95 value
        p95_severity = threshold.get_severity(stats["p95"])

        # Determine overall severity (worst case)
        severity_order = [
            PerformanceSeverity.EXCELLENT,
            PerformanceSeverity.GOOD,
            PerformanceSeverity.ACCEPTABLE,
            PerformanceSeverity.WARNING,
            PerformanceSeverity.CRITICAL,
        ]
        overall_severity = max([mean_severity, p95_severity], key=lambda x: severity_order.index(x))

        return {
            "metric_type": metric_type.value,
            "threshold": {
                "excellent": threshold.excellent,
                "good": threshold.good,
                "acceptable": threshold.acceptable,
                "warning": threshold.warning,
                "critical": threshold.critical,
                "unit": threshold.unit,
            },
            "statistics": stats,
            "evaluation": {
                "mean_severity": mean_severity.value,
                "p95_severity": p95_severity.value,
                "overall_severity": overall_severity.value,
                "passed": overall_severity
                in [
                    PerformanceSeverity.EXCELLENT,
                    PerformanceSeverity.GOOD,
                    PerformanceSeverity.ACCEPTABLE,
                ],
            },
        }

    def detect_anomalies(
        self, metric_type: PerformanceMetricType, std_dev_threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in metric data using standard deviation

        Args:
            metric_type: Type of metric to analyze
            std_dev_threshold: Number of standard deviations to consider as anomaly

        Returns:
            List of detected anomalies
        """
        values = self.result.get_metric_values(metric_type)
        samples = self.result.get_samples_by_type(metric_type)

        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        std_dev = statistics.stdev(values)

        anomalies = []
        for sample, value in zip(samples, values):
            z_score = abs((value - mean) / std_dev) if std_dev > 0 else 0
            if z_score > std_dev_threshold:
                anomalies.append(
                    {
                        "timestamp": sample.timestamp.isoformat(),
                        "value": value,
                        "unit": sample.unit,
                        "z_score": z_score,
                        "deviation_from_mean": value - mean,
                    }
                )

        return anomalies

    def generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive performance summary"""
        summary = {
            "test_name": self.result.test_name,
            "duration": self.result.duration,
            "sample_count": self.result.sample_count,
            "metrics": {},
        }

        # Collect all metric types present in samples
        metric_types = set(s.metric_type for s in self.result.samples)

        for metric_type in metric_types:
            stats = self.calculate_statistics(metric_type)
            evaluation = self.evaluate_against_thresholds(metric_type)
            anomalies = self.detect_anomalies(metric_type)

            summary["metrics"][metric_type.value] = {
                "statistics": stats,
                "evaluation": evaluation,
                "anomalies": anomalies,
            }

        return summary


class PerformanceReportGenerator:
    """Generates performance test reports in various formats"""

    def __init__(self, result: PerformanceResult):
        """
        Initialize report generator

        Args:
            result: Performance result to report on
        """
        self.result = result
        self.analyzer = PerformanceResultAnalyzer(result)

    def generate_text_report(self) -> str:
        """Generate human-readable text report"""
        summary = self.analyzer.generate_summary()

        lines = [
            "=" * 80,
            f"PERFORMANCE TEST REPORT: {self.result.test_name}",
            "=" * 80,
            f"Duration: {self.result.duration:.2f} seconds",
            f"Sample Count: {self.result.sample_count}",
            f"Start Time: {self.result.start_time.isoformat()}",
            f"End Time: {self.result.end_time.isoformat()}",
            "",
            "-" * 80,
            "METRICS SUMMARY",
            "-" * 80,
        ]

        for metric_name, metric_data in summary["metrics"].items():
            lines.append(f"\n{metric_name.upper()}:")
            lines.append("-" * 40)

            stats = metric_data["statistics"]
            lines.append(f"  Count: {stats['count']}")
            lines.append(f"  Mean: {stats['mean']:.4f}")
            lines.append(f"  Median: {stats['median']:.4f}")
            lines.append(f"  Std Dev: {stats['std_dev']:.4f}")
            lines.append(f"  Min: {stats['min']:.4f}")
            lines.append(f"  Max: {stats['max']:.4f}")
            lines.append(f"  P50: {stats['p50']:.4f}")
            lines.append(f"  P90: {stats['p90']:.4f}")
            lines.append(f"  P95: {stats['p95']:.4f}")
            lines.append(f"  P99: {stats['p99']:.4f}")

            evaluation = metric_data["evaluation"]
            if evaluation.get("status") != "no_threshold":
                lines.append(f"\n  Threshold Evaluation:")
                lines.append(
                    f"    Overall Severity: {evaluation['evaluation']['overall_severity']}"
                )
                lines.append(f"    Passed: {evaluation['evaluation']['passed']}")

            anomalies = metric_data["anomalies"]
            if anomalies:
                lines.append(f"\n  Anomalies Detected: {len(anomalies)}")
                for anomaly in anomalies[:5]:  # Show first 5 anomalies
                    lines.append(
                        f"    - {anomaly['timestamp']}: {anomaly['value']:.4f} (z-score: {anomaly['z_score']:.2f})"
                    )
                if len(anomalies) > 5:
                    lines.append(f"    ... and {len(anomalies) - 5} more")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def generate_json_report(self) -> str:
        """Generate JSON report"""
        summary = self.analyzer.generate_summary()
        return json.dumps(summary, indent=2, default=str)

    def save_report(self, output_path: Union[str, Path], format: str = "json") -> str:
        """
        Save report to file

        Args:
            output_path: Path to save report
            format: Report format ('json' or 'text')

        Returns:
            Path to saved report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            content = self.generate_json_report()
        elif format == "text":
            content = self.generate_text_report()
        else:
            raise ValueError(f"Unsupported format: {format}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Report saved to {output_path}")
        return str(output_path)


class BenchmarkBase(ABC):
    """Base class for performance benchmark tests"""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize benchmark

        Args:
            name: Benchmark name
            config: Optional configuration
        """
        self.name = name
        self.config = config or {}
        self.collector = PerformanceMetricsCollector(
            sample_interval=self.config.get("sample_interval", 0.1)
        )
        self.thresholds: Dict[PerformanceMetricType, PerformanceThreshold] = {}
        self._setup_thresholds()

    @abstractmethod
    def _setup_thresholds(self):
        """Setup performance thresholds for this benchmark"""
        pass

    @abstractmethod
    async def run_workload(self) -> Any:
        """
        Execute the workload to be benchmarked

        Returns:
            Workload result
        """
        pass

    def add_threshold(
        self,
        metric_type: PerformanceMetricType,
        excellent: float,
        good: float,
        acceptable: float,
        warning: float,
        critical: float,
        unit: str = "ms",
    ):
        """
        Add a performance threshold

        Args:
            metric_type: Type of metric
            excellent: Excellent threshold value
            good: Good threshold value
            acceptable: Acceptable threshold value
            warning: Warning threshold value
            critical: Critical threshold value
            unit: Unit of measurement
        """
        self.thresholds[metric_type] = PerformanceThreshold(
            metric_type=metric_type,
            excellent=excellent,
            good=good,
            acceptable=acceptable,
            warning=warning,
            critical=critical,
            unit=unit,
        )

    async def execute(self, iterations: int = 1) -> PerformanceResult:
        """
        Execute the benchmark

        Args:
            iterations: Number of iterations to run

        Returns:
            Performance result
        """
        logger.info(f"Starting benchmark: {self.name}")
        start_time = datetime.now()

        self.collector.start_collection()

        try:
            results = []
            for i in range(iterations):
                logger.debug(f"Running iteration {i + 1}/{iterations}")
                iteration_start = time.time()

                result = await self.run_workload()
                iteration_duration = time.time() - iteration_start

                # Record response time
                self.collector.add_custom_sample(
                    metric_type=PerformanceMetricType.RESPONSE_TIME,
                    value=iteration_duration,
                    unit="seconds",
                    metadata={"iteration": i + 1},
                )

                results.append(result)

                # Calculate throughput
                if iteration_duration > 0:
                    throughput = 1.0 / iteration_duration
                    self.collector.add_custom_sample(
                        metric_type=PerformanceMetricType.THROUGHPUT,
                        value=throughput,
                        unit="ops_per_second",
                        metadata={"iteration": i + 1},
                    )
        finally:
            self.collector.stop_collection()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Create performance result
        performance_result = PerformanceResult(
            test_name=self.name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            samples=self.collector.get_samples(),
            thresholds=self.thresholds.copy(),
            metadata={"iterations": iterations, "config": self.config},
        )

        logger.info(f"Completed benchmark: {self.name} in {duration:.2f}s")
        return performance_result

    async def execute_concurrent(
        self, concurrency: int = 10, total_requests: int = 100
    ) -> PerformanceResult:
        """
        Execute benchmark with concurrent requests

        Args:
            concurrency: Number of concurrent operations
            total_requests: Total number of requests to make

        Returns:
            Performance result
        """
        logger.info(
            f"Starting concurrent benchmark: {self.name} (concurrency={concurrency}, total={total_requests})"
        )
        start_time = datetime.now()

        self.collector.start_collection()

        try:
            semaphore = asyncio.Semaphore(concurrency)
            response_times = []
            errors = 0

            async def limited_run():
                async with semaphore:
                    try:
                        iteration_start = time.time()
                        await self.run_workload()
                        iteration_duration = time.time() - iteration_start
                        response_times.append(iteration_duration)
                        return True
                    except Exception as e:
                        logger.error(f"Error in concurrent execution: {e}")
                        return False

            # Execute concurrent requests
            tasks = [limited_run() for _ in range(total_requests)]
            results = await asyncio.gather(*tasks)
            errors = sum(1 for r in results if not r)

            # Record metrics
            for i, rt in enumerate(response_times):
                self.collector.add_custom_sample(
                    metric_type=PerformanceMetricType.RESPONSE_TIME,
                    value=rt,
                    unit="seconds",
                    metadata={"request": i + 1},
                )

            # Calculate throughput
            duration = (datetime.now() - start_time).total_seconds()
            if duration > 0:
                throughput = len(response_times) / duration
                self.collector.add_custom_sample(
                    metric_type=PerformanceMetricType.THROUGHPUT,
                    value=throughput,
                    unit="ops_per_second",
                )

            # Record error rate
            error_rate = errors / total_requests if total_requests > 0 else 0
            self.collector.add_custom_sample(
                metric_type=PerformanceMetricType.ERROR_RATE, value=error_rate, unit="percent"
            )

            # Record concurrency
            self.collector.add_custom_sample(
                metric_type=PerformanceMetricType.CONCURRENCY, value=concurrency, unit="count"
            )

        finally:
            self.collector.stop_collection()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Create performance result
        performance_result = PerformanceResult(
            test_name=f"{self.name}_concurrent",
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            samples=self.collector.get_samples(),
            thresholds=self.thresholds.copy(),
            metadata={
                "concurrency": concurrency,
                "total_requests": total_requests,
                "successful_requests": len(response_times),
                "failed_requests": errors,
                "config": self.config,
            },
        )

        logger.info(f"Completed concurrent benchmark: {self.name} in {duration:.2f}s")
        return performance_result

    def generate_report(
        self,
        result: PerformanceResult,
        output_path: Optional[Union[str, Path]] = None,
        format: str = "json",
    ) -> str:
        """
        Generate performance report

        Args:
            result: Performance result
            output_path: Optional path to save report
            format: Report format ('json' or 'text')

        Returns:
            Report content
        """
        generator = PerformanceReportGenerator(result)

        if output_path:
            return generator.save_report(output_path, format)
        elif format == "json":
            return generator.generate_json_report()
        else:
            return generator.generate_text_report()
