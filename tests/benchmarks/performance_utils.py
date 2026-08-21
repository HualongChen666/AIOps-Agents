# -*- coding: utf-8 -*-
"""
Performance Testing Utilities
==============================

Enterprise-level performance testing utilities including:
- Performance measurement tools
- Statistical analysis tools
- Resource monitoring tools
- Performance comparison tools
"""

import asyncio
import statistics
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing as mp

import psutil
from loguru import logger

from tests.benchmarks.benchmark_base import PerformanceMetricType, MetricSample, PerformanceResult


@dataclass
class MeasurementResult:
    """Result of a performance measurement"""
    
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class PerformanceTimer:
    """High-precision performance timer"""
    
    def __init__(self, name: str = "operation"):
        """
        Initialize timer
        
        Args:
            name: Name of the operation being timed
        """
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: Optional[float] = None
    
    def start(self):
        """Start the timer"""
        self.start_time = time.perf_counter()
        self.end_time = None
        self.elapsed = None
    
    def stop(self) -> float:
        """
        Stop the timer and return elapsed time
        
        Returns:
            Elapsed time in seconds
        """
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        return self.elapsed
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.start_time is not None:
            self.stop()
            logger.debug(f"{self.name} took {self.elapsed:.6f}s")
        return False


@contextmanager
def measure_performance(operation_name: str = "operation"):
    """
    Context manager to measure performance of a code block
    
    Args:
        operation_name: Name of the operation
        
    Yields:
        MeasurementResult with timing information
    """
    timer = PerformanceTimer(operation_name)
    timer.start()
    try:
        yield timer
    finally:
        elapsed = timer.stop()
        logger.debug(f"{operation_name} completed in {elapsed:.6f}s")


class ResourceMonitor:
    """Monitor system resources during execution"""
    
    def __init__(self, sample_interval: float = 0.1):
        """
        Initialize resource monitor
        
        Args:
            sample_interval: Interval between samples in seconds
        """
        self.sample_interval = sample_interval
        self.process = psutil.Process()
        self.measurements: List[MeasurementResult] = []
        self._monitoring = False
        self._initial_cpu_times = self.process.cpu_times()
        self._initial_io_counters = self.process.io_counters() if hasattr(self.process, 'io_counters') else None
        self._initial_net_io = psutil.net_io_counters()
    
    def start(self):
        """Start resource monitoring"""
        if self._monitoring:
            logger.warning("Resource monitoring already in progress")
            return
        
        self._monitoring = True
        self._take_sample()
        logger.info("Started resource monitoring")
    
    def stop(self):
        """Stop resource monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._take_sample()  # Final sample
        logger.info("Stopped resource monitoring")
    
    def _take_sample(self):
        """Take a resource measurement sample"""
        timestamp = datetime.now()
        
        # CPU usage
        try:
            cpu_percent = self.process.cpu_percent(interval=0.01)
            self.measurements.append(MeasurementResult(
                name="cpu_usage",
                value=cpu_percent,
                unit="percent",
                timestamp=timestamp
            ))
        except Exception as e:
            logger.debug(f"Error measuring CPU: {e}")
        
        # Memory usage
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            self.measurements.append(MeasurementResult(
                name="memory_usage",
                value=memory_percent,
                unit="percent",
                timestamp=timestamp,
                metadata={"rss_mb": memory_info.rss / 1024 / 1024, "vms_mb": memory_info.vms / 1024 / 1024}
            ))
        except Exception as e:
            logger.debug(f"Error measuring memory: {e}")
        
        # Disk I/O
        if self._initial_io_counters:
            try:
                current_io = self.process.io_counters()
                read_bytes = current_io.read_bytes - self._initial_io_counters.read_bytes
                write_bytes = current_io.write_bytes - self._initial_io_counters.write_bytes
                self.measurements.append(MeasurementResult(
                    name="disk_io",
                    value=read_bytes + write_bytes,
                    unit="bytes",
                    timestamp=timestamp,
                    metadata={"read_bytes": read_bytes, "write_bytes": write_bytes}
                ))
            except Exception as e:
                logger.debug(f"Error measuring disk I/O: {e}")
        
        # Network I/O
        try:
            current_net = psutil.net_io_counters()
            net_bytes = (current_net.bytes_sent + current_net.bytes_recv) - (self._initial_net_io.bytes_sent + self._initial_net_io.bytes_recv)
            self.measurements.append(MeasurementResult(
                name="network_io",
                value=net_bytes,
                unit="bytes",
                timestamp=timestamp,
                metadata={"sent_bytes": current_net.bytes_sent - self._initial_net_io.bytes_sent, 
                         "recv_bytes": current_net.bytes_recv - self._initial_net_io.bytes_recv}
            ))
        except Exception as e:
            logger.debug(f"Error measuring network I/O: {e}")
        
        # Thread count
        try:
            thread_count = self.process.num_threads()
            self.measurements.append(MeasurementResult(
                name="thread_count",
                value=thread_count,
                unit="count",
                timestamp=timestamp
            ))
        except Exception as e:
            logger.debug(f"Error measuring thread count: {e}")
        
        # File descriptors
        try:
            fd_count = self.process.num_fds() if hasattr(self.process, 'num_fds') else 0
            self.measurements.append(MeasurementResult(
                name="file_descriptor_count",
                value=fd_count,
                unit="count",
                timestamp=timestamp
            ))
        except Exception as e:
            logger.debug(f"Error measuring file descriptors: {e}")
    
    def get_measurements(self, name: Optional[str] = None) -> List[MeasurementResult]:
        """
        Get measurements, optionally filtered by name
        
        Args:
            name: Optional name to filter by
            
        Returns:
            List of measurements
        """
        if name is None:
            return self.measurements.copy()
        return [m for m in self.measurements if m.name == name]
    
    def get_statistics(self, name: str) -> Dict[str, float]:
        """
        Get statistical summary for a specific measurement type
        
        Args:
            name: Name of measurement type
            
        Returns:
            Dictionary with statistics
        """
        measurements = self.get_measurements(name)
        values = [m.value for m in measurements]
        
        if not values:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0
            }
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values)
        }
    
    def clear(self):
        """Clear all measurements"""
        self.measurements.clear()


class StatisticalAnalyzer:
    """Statistical analysis tools for performance data"""
    
    @staticmethod
    def calculate_percentiles(data: List[float], percentiles: List[int] = [50, 90, 95, 99]) -> Dict[int, float]:
        """
        Calculate percentiles for data
        
        Args:
            data: List of values
            percentiles: List of percentiles to calculate
            
        Returns:
            Dictionary mapping percentile to value
        """
        if not data:
            return {p: 0.0 for p in percentiles}
        
        sorted_data = sorted(data)
        result = {}
        
        for p in percentiles:
            index = int(len(sorted_data) * p / 100)
            result[p] = sorted_data[min(index, len(sorted_data) - 1)]
        
        return result
    
    @staticmethod
    def calculate_confidence_interval(data: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate confidence interval for data
        
        Args:
            data: List of values
            confidence: Confidence level (0.0 to 1.0)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if len(data) < 2:
            return (data[0] if data else 0.0, data[0] if data else 0.0)
        
        mean = statistics.mean(data)
        std_err = statistics.stdev(data) / (len(data) ** 0.5)
        
        # Approximate using normal distribution
        from math import sqrt
        z_score = 1.96  # For 95% confidence
        
        margin = z_score * std_err
        return (mean - margin, mean + margin)
    
    @staticmethod
    def detect_outliers(data: List[float], method: str = "iqr", multiplier: float = 1.5) -> List[Tuple[int, float]]:
        """
        Detect outliers in data
        
        Args:
            data: List of values
            method: Method to use ('iqr' or 'zscore')
            multiplier: Multiplier for threshold
            
        Returns:
            List of (index, value) tuples for outliers
        """
        if not data:
            return []
        
        outliers = []
        
        if method == "iqr":
            # Interquartile range method
            sorted_data = sorted(data)
            q1 = sorted_data[len(sorted_data) // 4]
            q3 = sorted_data[3 * len(sorted_data) // 4]
            iqr = q3 - q1
            
            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr
            
            for i, value in enumerate(data):
                if value < lower_bound or value > upper_bound:
                    outliers.append((i, value))
        
        elif method == "zscore":
            # Z-score method
            mean = statistics.mean(data)
            std_dev = statistics.stdev(data) if len(data) > 1 else 0
            
            if std_dev == 0:
                return []
            
            for i, value in enumerate(data):
                z_score = abs((value - mean) / std_dev)
                if z_score > multiplier:
                    outliers.append((i, value))
        
        return outliers
    
    @staticmethod
    def calculate_trend(data: List[float], window_size: int = 5) -> str:
        """
        Calculate trend direction from data
        
        Args:
            data: List of values
            window_size: Size of window for trend calculation
            
        Returns:
            Trend direction ('increasing', 'decreasing', 'stable', 'insufficient_data')
        """
        if len(data) < window_size:
            return "insufficient_data"
        
        # Calculate moving average
        recent = data[-window_size:]
        earlier = data[-2*window_size:-window_size] if len(data) >= 2*window_size else data[:window_size]
        
        recent_avg = statistics.mean(recent)
        earlier_avg = statistics.mean(earlier)
        
        change_percent = ((recent_avg - earlier_avg) / earlier_avg) * 100 if earlier_avg != 0 else 0
        
        if change_percent > 5:
            return "increasing"
        elif change_percent < -5:
            return "decreasing"
        else:
            return "stable"
    
    @staticmethod
    def compare_datasets(dataset1: List[float], dataset2: List[float]) -> Dict[str, Any]:
        """
        Compare two datasets statistically
        
        Args:
            dataset1: First dataset
            dataset2: Second dataset
            
        Returns:
            Dictionary with comparison results
        """
        result = {
            "dataset1": {
                "count": len(dataset1),
                "mean": statistics.mean(dataset1) if dataset1 else 0.0,
                "median": statistics.median(dataset1) if dataset1 else 0.0,
                "std_dev": statistics.stdev(dataset1) if len(dataset1) > 1 else 0.0
            },
            "dataset2": {
                "count": len(dataset2),
                "mean": statistics.mean(dataset2) if dataset2 else 0.0,
                "median": statistics.median(dataset2) if dataset2 else 0.0,
                "std_dev": statistics.stdev(dataset2) if len(dataset2) > 1 else 0.0
            }
        }
        
        # Calculate relative difference
        if result["dataset1"]["mean"] != 0:
            result["mean_difference_percent"] = ((result["dataset2"]["mean"] - result["dataset1"]["mean"]) / result["dataset1"]["mean"]) * 100
        else:
            result["mean_difference_percent"] = 0.0
        
        # Determine if datasets are significantly different
        if len(dataset1) > 1 and len(dataset2) > 1:
            # Simple t-test approximation
            pooled_std = ((result["dataset1"]["std_dev"]**2 / len(dataset1)) + 
                         (result["dataset2"]["std_dev"]**2 / len(dataset2))) ** 0.5
            if pooled_std > 0:
                t_stat = (result["dataset2"]["mean"] - result["dataset1"]["mean"]) / pooled_std
                result["t_statistic"] = t_stat
                result["significantly_different"] = abs(t_stat) > 1.96  # Approximate for 95% confidence
            else:
                result["t_statistic"] = 0.0
                result["significantly_different"] = False
        else:
            result["t_statistic"] = 0.0
            result["significantly_different"] = False
        
        return result


class PerformanceComparator:
    """Compare performance results across different runs"""
    
    def __init__(self, baseline_result: PerformanceResult):
        """
        Initialize comparator with baseline result
        
        Args:
            baseline_result: Baseline performance result
        """
        self.baseline = baseline_result
        self.comparisons: List[Tuple[PerformanceResult, Dict[str, Any]]] = []
    
    def compare(self, current_result: PerformanceResult) -> Dict[str, Any]:
        """
        Compare current result against baseline
        
        Args:
            current_result: Current performance result to compare
            
        Returns:
            Dictionary with comparison results
        """
        comparison = {
            "test_name": current_result.test_name,
            "baseline_duration": self.baseline.duration,
            "current_duration": current_result.duration,
            "duration_change_percent": ((current_result.duration - self.baseline.duration) / self.baseline.duration * 100) if self.baseline.duration > 0 else 0.0,
            "metrics": {}
        }
        
        # Get all metric types from both results
        baseline_types = set(s.metric_type for s in self.baseline.samples)
        current_types = set(s.metric_type for s in current_result.samples)
        all_types = baseline_types.union(current_types)
        
        for metric_type in all_types:
            baseline_values = self.baseline.get_metric_values(metric_type)
            current_values = current_result.get_metric_values(metric_type)
            
            if not baseline_values and not current_values:
                continue
            
            stats_comparison = StatisticalAnalyzer.compare_datasets(baseline_values, current_values)
            
            comparison["metrics"][metric_type.value] = {
                "baseline_count": len(baseline_values),
                "current_count": len(current_values),
                "statistics": stats_comparison,
                "regression_detected": stats_comparison.get("significantly_different", False) and 
                                      stats_comparison.get("mean_difference_percent", 0) > 10
            }
        
        self.comparisons.append((current_result, comparison))
        return comparison
    
    def get_regression_summary(self) -> Dict[str, Any]:
        """
        Get summary of regressions detected across all comparisons
        
        Returns:
            Dictionary with regression summary
        """
        regressions = []
        
        for result, comparison in self.comparisons:
            for metric_name, metric_data in comparison["metrics"].items():
                if metric_data.get("regression_detected", False):
                    regressions.append({
                        "test_name": comparison["test_name"],
                        "metric": metric_name,
                        "baseline_mean": metric_data["statistics"]["dataset1"]["mean"],
                        "current_mean": metric_data["statistics"]["dataset2"]["mean"],
                        "change_percent": metric_data["statistics"]["mean_difference_percent"]
                    })
        
        return {
            "total_comparisons": len(self.comparisons),
            "regressions_detected": len(regressions),
            "regressions": regressions
        }


class ConcurrencyTester:
    """Test performance under concurrent load"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize concurrency tester
        
        Args:
            max_workers: Maximum number of worker threads (defaults to CPU count)
        """
        self.max_workers = max_workers or mp.cpu_count()
    
    async def test_async_concurrency(self, func: Callable, concurrency: int, total_requests: int) -> Dict[str, Any]:
        """
        Test async function under concurrent load
        
        Args:
            func: Async function to test
            concurrency: Number of concurrent operations
            total_requests: Total number of requests
            
        Returns:
            Dictionary with test results
        """
        semaphore = asyncio.Semaphore(concurrency)
        response_times = []
        errors = 0
        start_time = time.time()
        
        async def limited_call():
            async with semaphore:
                try:
                    call_start = time.time()
                    await func()
                    call_duration = time.time() - call_start
                    response_times.append(call_duration)
                    return True
                except Exception as e:
                    logger.error(f"Error in concurrent call: {e}")
                    return False
        
        tasks = [limited_call() for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)
        errors = sum(1 for r in results if not r)
        
        total_duration = time.time() - start_time
        
        return {
            "concurrency": concurrency,
            "total_requests": total_requests,
            "successful_requests": len(response_times),
            "failed_requests": errors,
            "total_duration": total_duration,
            "throughput": len(response_times) / total_duration if total_duration > 0 else 0,
            "response_times": response_times,
            "statistics": StatisticalAnalyzer.compare_datasets([], response_times) if response_times else {}
        }
    
    def test_thread_concurrency(self, func: Callable, concurrency: int, total_requests: int) -> Dict[str, Any]:
        """
        Test synchronous function under thread concurrency
        
        Args:
            func: Synchronous function to test
            concurrency: Number of concurrent operations
            total_requests: Total number of requests
            
        Returns:
            Dictionary with test results
        """
        response_times = []
        errors = 0
        start_time = time.time()
        
        def call_func():
            try:
                call_start = time.time()
                result = func()
                call_duration = time.time() - call_start
                return call_duration, True
            except Exception as e:
                logger.error(f"Error in thread call: {e}")
                return 0.0, False
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(call_func) for _ in range(total_requests)]
            for future in as_completed(futures):
                duration, success = future.result()
                if success:
                    response_times.append(duration)
                else:
                    errors += 1
        
        total_duration = time.time() - start_time
        
        return {
            "concurrency": concurrency,
            "total_requests": total_requests,
            "successful_requests": len(response_times),
            "failed_requests": errors,
            "total_duration": total_duration,
            "throughput": len(response_times) / total_duration if total_duration > 0 else 0,
            "response_times": response_times,
            "statistics": StatisticalAnalyzer.compare_datasets([], response_times) if response_times else {}
        }


class WarmupExecutor:
    """Execute warmup iterations before benchmark"""
    
    def __init__(self, warmup_iterations: int = 3):
        """
        Initialize warmup executor
        
        Args:
            warmup_iterations: Number of warmup iterations
        """
        self.warmup_iterations = warmup_iterations
    
    async def execute_async(self, func: Callable) -> None:
        """
        Execute async warmup iterations
        
        Args:
            func: Async function to warm up
        """
        logger.info(f"Executing {self.warmup_iterations} warmup iterations")
        for i in range(self.warmup_iterations):
            try:
                await func()
                logger.debug(f"Warmup iteration {i + 1}/{self.warmup_iterations} completed")
            except Exception as e:
                logger.warning(f"Warmup iteration {i + 1} failed: {e}")
    
    def execute_sync(self, func: Callable) -> None:
        """
        Execute synchronous warmup iterations
        
        Args:
            func: Synchronous function to warm up
        """
        logger.info(f"Executing {self.warmup_iterations} warmup iterations")
        for i in range(self.warmup_iterations):
            try:
                func()
                logger.debug(f"Warmup iteration {i + 1}/{self.warmup_iterations} completed")
            except Exception as e:
                logger.warning(f"Warmup iteration {i + 1} failed: {e}")


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string
    """
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"


def format_bytes(bytes_value: float) -> str:
    """
    Format bytes in human-readable format
    
    Args:
        bytes_value: Value in bytes
        
    Returns:
        Formatted string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f}{unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f}PB"
