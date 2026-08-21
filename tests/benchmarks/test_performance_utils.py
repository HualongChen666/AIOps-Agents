# -*- coding: utf-8 -*-
"""
Tests for Performance Testing Utilities
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from tests.benchmarks.performance_utils import (
    MeasurementResult,
    PerformanceTimer,
    measure_performance,
    ResourceMonitor,
    StatisticalAnalyzer,
    PerformanceComparator,
    ConcurrencyTester,
    WarmupExecutor,
    format_duration,
    format_bytes
)
from tests.benchmarks.benchmark_base import PerformanceMetricType, MetricSample, PerformanceResult


class TestMeasurementResult:
    """Test MeasurementResult dataclass"""
    
    def test_measurement_result_creation(self):
        """Test creating measurement result"""
        timestamp = datetime.now()
        result = MeasurementResult(
            name="cpu_usage",
            value=50.0,
            unit="percent",
            timestamp=timestamp,
            metadata={"core": 0}
        )
        
        assert result.name == "cpu_usage"
        assert result.value == 50.0
        assert result.unit == "percent"
        assert result.timestamp == timestamp
        assert result.metadata == {"core": 0}
    
    def test_measurement_result_defaults(self):
        """Test measurement result with defaults"""
        result = MeasurementResult(
            name="memory_usage",
            value=1024.0,
            unit="MB"
        )
        
        assert result.timestamp is not None
        assert result.metadata == {}
    
    def test_measurement_result_to_dict(self):
        """Test converting measurement result to dictionary"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        result = MeasurementResult(
            name="response_time",
            value=0.5,
            unit="seconds",
            timestamp=timestamp,
            metadata={"iteration": 1}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["name"] == "response_time"
        assert result_dict["value"] == 0.5
        assert result_dict["unit"] == "seconds"
        assert result_dict["timestamp"] == "2024-01-01T12:00:00"
        assert result_dict["metadata"] == {"iteration": 1}


class TestPerformanceTimer:
    """Test PerformanceTimer"""
    
    def test_timer_initialization(self):
        """Test timer initialization"""
        timer = PerformanceTimer("test_operation")
        
        assert timer.name == "test_operation"
        assert timer.start_time is None
        assert timer.end_time is None
        assert timer.elapsed is None
    
    def test_timer_start_stop(self):
        """Test starting and stopping timer"""
        timer = PerformanceTimer("test")
        
        timer.start()
        assert timer.start_time is not None
        
        time.sleep(0.01)
        
        elapsed = timer.stop()
        
        assert timer.end_time is not None
        assert timer.elapsed is not None
        assert elapsed > 0
        assert elapsed == timer.elapsed
    
    def test_timer_stop_without_start(self):
        """Test stopping timer without starting"""
        timer = PerformanceTimer("test")
        
        with pytest.raises(RuntimeError, match="Timer not started"):
            timer.stop()
    
    def test_timer_context_manager(self):
        """Test timer as context manager"""
        with PerformanceTimer("test") as timer:
            assert timer.start_time is not None
            time.sleep(0.01)
        
        assert timer.end_time is not None
        assert timer.elapsed is not None
        assert timer.elapsed > 0


class TestMeasurePerformance:
    """Test measure_performance context manager"""
    
    def test_measure_performance_context(self):
        """Test measure_performance context manager"""
        with measure_performance("test_operation") as timer:
            time.sleep(0.01)
        
        assert timer.elapsed is not None
        assert timer.elapsed > 0


class TestResourceMonitor:
    """Test ResourceMonitor"""
    
    def test_monitor_initialization(self):
        """Test monitor initialization"""
        monitor = ResourceMonitor(sample_interval=0.5)
        
        assert monitor.sample_interval == 0.5
        assert len(monitor.measurements) == 0
        assert monitor._monitoring is False
    
    def test_monitor_start_stop(self):
        """Test starting and stopping monitor"""
        monitor = ResourceMonitor(sample_interval=0.01)
        
        monitor.start()
        assert monitor._monitoring is True
        
        time.sleep(0.05)
        
        monitor.stop()
        assert monitor._monitoring is False
        
        # Should have collected some measurements
        assert len(monitor.measurements) > 0
    
    def test_monitor_start_when_already_monitoring(self):
        """Test starting monitor when already monitoring"""
        monitor = ResourceMonitor(sample_interval=0.01)
        
        monitor.start()
        time.sleep(0.01)
        
        # Should not raise error
        monitor.start()
        
        monitor.stop()
    
    def test_monitor_stop_when_not_monitoring(self):
        """Test stopping monitor when not monitoring"""
        monitor = ResourceMonitor()
        
        # Should not raise error
        monitor.stop()
    
    def test_get_measurements_all(self):
        """Test getting all measurements"""
        monitor = ResourceMonitor()
        
        monitor.measurements.append(MeasurementResult("cpu", 50.0, "percent"))
        monitor.measurements.append(MeasurementResult("memory", 60.0, "percent"))
        
        measurements = monitor.get_measurements()
        
        assert len(measurements) == 2
        assert measurements is not monitor.measurements  # Should be a copy
    
    def test_get_measurements_filtered(self):
        """Test getting measurements filtered by name"""
        monitor = ResourceMonitor()
        
        monitor.measurements.append(MeasurementResult("cpu", 50.0, "percent"))
        monitor.measurements.append(MeasurementResult("memory", 60.0, "percent"))
        monitor.measurements.append(MeasurementResult("cpu", 55.0, "percent"))
        
        cpu_measurements = monitor.get_measurements("cpu")
        
        assert len(cpu_measurements) == 2
        assert all(m.name == "cpu" for m in cpu_measurements)
    
    def test_get_statistics(self):
        """Test getting statistics for measurement type"""
        monitor = ResourceMonitor()
        
        monitor.measurements.append(MeasurementResult("cpu", 50.0, "percent"))
        monitor.measurements.append(MeasurementResult("cpu", 60.0, "percent"))
        monitor.measurements.append(MeasurementResult("cpu", 70.0, "percent"))
        
        stats = monitor.get_statistics("cpu")
        
        assert stats["count"] == 3
        assert stats["mean"] == 60.0
        assert stats["median"] == 60.0
        assert stats["min"] == 50.0
        assert stats["max"] == 70.0
    
    def test_get_statistics_empty(self):
        """Test getting statistics with no measurements"""
        monitor = ResourceMonitor()
        
        stats = monitor.get_statistics("cpu")
        
        assert stats["count"] == 0
        assert stats["mean"] == 0.0
        assert stats["median"] == 0.0
    
    def test_clear_measurements(self):
        """Test clearing measurements"""
        monitor = ResourceMonitor()
        
        monitor.measurements.append(MeasurementResult("cpu", 50.0, "percent"))
        assert len(monitor.measurements) == 1
        
        monitor.clear()
        assert len(monitor.measurements) == 0


class TestStatisticalAnalyzer:
    """Test StatisticalAnalyzer"""
    
    def test_calculate_percentiles(self):
        """Test calculating percentiles"""
        data = [i for i in range(100)]
        
        percentiles = StatisticalAnalyzer.calculate_percentiles(data, [50, 90, 95, 99])
        
        assert percentiles[50] == 50.0
        assert percentiles[90] == 90.0
        assert percentiles[95] == 95.0
        assert percentiles[99] == 99.0
    
    def test_calculate_percentiles_empty(self):
        """Test calculating percentiles with empty data"""
        percentiles = StatisticalAnalyzer.calculate_percentiles([], [50, 90])
        
        assert percentiles[50] == 0.0
        assert percentiles[90] == 0.0
    
    def test_calculate_percentiles_custom(self):
        """Test calculating custom percentiles"""
        data = [i for i in range(100)]
        
        percentiles = StatisticalAnalyzer.calculate_percentiles(data, [25, 75])
        
        assert percentiles[25] == 25.0
        assert percentiles[75] == 75.0
    
    def test_calculate_confidence_interval(self):
        """Test calculating confidence interval"""
        data = [50.0, 51.0, 49.0, 50.5, 50.2]
        
        lower, upper = StatisticalAnalyzer.calculate_confidence_interval(data, 0.95)
        
        assert lower < upper
        assert lower < 50.0 < upper
    
    def test_calculate_confidence_interval_empty(self):
        """Test calculating confidence interval with empty data"""
        lower, upper = StatisticalAnalyzer.calculate_confidence_interval([])
        
        assert lower == 0.0
        assert upper == 0.0
    
    def test_calculate_confidence_interval_single(self):
        """Test calculating confidence interval with single value"""
        lower, upper = StatisticalAnalyzer.calculate_confidence_interval([50.0])
        
        assert lower == 50.0
        assert upper == 50.0
    
    def test_detect_outliers_iqr(self):
        """Test detecting outliers using IQR method"""
        data = [50.0, 51.0, 49.0, 50.5, 100.0]  # 100.0 is an outlier
        
        outliers = StatisticalAnalyzer.detect_outliers(data, method="iqr", multiplier=1.5)
        
        assert len(outliers) > 0
        assert any(v == 100.0 for _, v in outliers)
    
    def test_detect_outliers_zscore(self):
        """Test detecting outliers using z-score method"""
        data = [50.0, 51.0, 49.0, 50.5, 48.0, 52.0, 200.0]  # 200.0 is an extreme outlier
        
        outliers = StatisticalAnalyzer.detect_outliers(data, method="zscore", multiplier=1.5)
        
        assert len(outliers) > 0
    
    def test_detect_outliers_empty(self):
        """Test detecting outliers with empty data"""
        outliers = StatisticalAnalyzer.detect_outliers([])
        
        assert len(outliers) == 0
    
    def test_detect_outliers_no_outliers(self):
        """Test detecting outliers when none exist"""
        data = [50.0, 51.0, 49.0, 50.5, 50.2]
        
        outliers = StatisticalAnalyzer.detect_outliers(data, method="iqr", multiplier=3.0)
        
        assert len(outliers) == 0
    
    def test_calculate_trend_increasing(self):
        """Test calculating increasing trend"""
        data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        
        trend = StatisticalAnalyzer.calculate_trend(data, window_size=5)
        
        assert trend == "increasing"
    
    def test_calculate_trend_decreasing(self):
        """Test calculating decreasing trend"""
        data = [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0, 20.0, 10.0]
        
        trend = StatisticalAnalyzer.calculate_trend(data, window_size=5)
        
        assert trend == "decreasing"
    
    def test_calculate_trend_stable(self):
        """Test calculating stable trend"""
        data = [50.0, 51.0, 49.0, 50.5, 50.2, 50.1, 49.9, 50.3, 50.0, 50.1]
        
        trend = StatisticalAnalyzer.calculate_trend(data, window_size=5)
        
        assert trend == "stable"
    
    def test_calculate_trend_insufficient_data(self):
        """Test calculating trend with insufficient data"""
        data = [50.0, 51.0, 49.0]
        
        trend = StatisticalAnalyzer.calculate_trend(data, window_size=5)
        
        assert trend == "insufficient_data"
    
    def test_compare_datasets(self):
        """Test comparing two datasets"""
        dataset1 = [50.0, 51.0, 49.0, 50.5, 50.2]
        dataset2 = [60.0, 61.0, 59.0, 60.5, 60.2]
        
        comparison = StatisticalAnalyzer.compare_datasets(dataset1, dataset2)
        
        assert "dataset1" in comparison
        assert "dataset2" in comparison
        assert comparison["dataset1"]["mean"] == 50.14
        assert comparison["dataset2"]["mean"] == 60.14
        assert "mean_difference_percent" in comparison
    
    def test_compare_datasets_empty(self):
        """Test comparing empty datasets"""
        comparison = StatisticalAnalyzer.compare_datasets([], [])
        
        assert comparison["dataset1"]["count"] == 0
        assert comparison["dataset2"]["count"] == 0
    
    def test_compare_datasets_single_value(self):
        """Test comparing datasets with single values"""
        comparison = StatisticalAnalyzer.compare_datasets([50.0], [60.0])
        
        assert comparison["dataset1"]["count"] == 1
        assert comparison["dataset2"]["count"] == 1
        assert comparison["dataset1"]["std_dev"] == 0.0
        assert comparison["dataset2"]["std_dev"] == 0.0


class TestPerformanceComparator:
    """Test PerformanceComparator"""
    
    def test_comparator_initialization(self):
        """Test comparator initialization"""
        baseline = PerformanceResult(
            test_name="baseline",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=10.0,
            samples=[
                MetricSample(datetime.now(), PerformanceMetricType.RESPONSE_TIME, 0.5, "seconds")
            ]
        )
        
        comparator = PerformanceComparator(baseline)
        
        assert comparator.baseline == baseline
        assert len(comparator.comparisons) == 0
    
    def test_compare_results(self):
        """Test comparing results"""
        baseline = PerformanceResult(
            test_name="baseline",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=10.0,
            samples=[
                MetricSample(datetime.now(), PerformanceMetricType.RESPONSE_TIME, 0.5, "seconds")
            ]
        )
        
        current = PerformanceResult(
            test_name="current",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=11.0,
            samples=[
                MetricSample(datetime.now(), PerformanceMetricType.RESPONSE_TIME, 0.6, "seconds")
            ]
        )
        
        comparator = PerformanceComparator(baseline)
        comparison = comparator.compare(current)
        
        assert comparison["test_name"] == "current"
        assert comparison["baseline_duration"] == 10.0
        assert comparison["current_duration"] == 11.0
        assert "metrics" in comparison
        assert len(comparator.comparisons) == 1
    
    def test_get_regression_summary(self):
        """Test getting regression summary"""
        baseline = PerformanceResult(
            test_name="baseline",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=10.0,
            samples=[
                MetricSample(datetime.now(), PerformanceMetricType.RESPONSE_TIME, 0.5, "seconds")
            ]
        )
        
        # Create a result with significant regression
        current = PerformanceResult(
            test_name="current",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=15.0,
            samples=[
                MetricSample(datetime.now(), PerformanceMetricType.RESPONSE_TIME, 1.0, "seconds")
            ]
        )
        
        comparator = PerformanceComparator(baseline)
        comparator.compare(current)
        
        summary = comparator.get_regression_summary()
        
        assert summary["total_comparisons"] == 1
        assert "regressions_detected" in summary
        assert "regressions" in summary


class TestConcurrencyTester:
    """Test ConcurrencyTester"""
    
    def test_tester_initialization(self):
        """Test tester initialization"""
        tester = ConcurrencyTester()
        
        assert tester.max_workers > 0
    
    def test_tester_initialization_custom_workers(self):
        """Test tester initialization with custom workers"""
        tester = ConcurrencyTester(max_workers=4)
        
        assert tester.max_workers == 4
    
    @pytest.mark.asyncio
    async def test_async_concurrency_test(self):
        """Test async concurrency testing"""
        async def mock_func():
            await asyncio.sleep(0.001)
            return "result"
        
        tester = ConcurrencyTester()
        result = await tester.test_async_concurrency(mock_func, concurrency=5, total_requests=10)
        
        assert result["concurrency"] == 5
        assert result["total_requests"] == 10
        assert result["successful_requests"] == 10
        assert result["failed_requests"] == 0
        assert result["throughput"] > 0
        assert len(result["response_times"]) == 10
    
    @pytest.mark.asyncio
    async def test_async_concurrency_test_with_errors(self):
        """Test async concurrency testing with errors"""
        async def failing_func():
            if time.time() % 2 < 1:
                raise ValueError("Simulated error")
            await asyncio.sleep(0.001)
            return "result"
        
        tester = ConcurrencyTester()
        result = await tester.test_async_concurrency(failing_func, concurrency=2, total_requests=10)
        
        assert result["total_requests"] == 10
        assert result["successful_requests"] + result["failed_requests"] == 10
    
    def test_thread_concurrency_test(self):
        """Test thread concurrency testing"""
        def mock_func():
            time.sleep(0.001)
            return "result"
        
        tester = ConcurrencyTester()
        result = tester.test_thread_concurrency(mock_func, concurrency=5, total_requests=10)
        
        assert result["concurrency"] == 5
        assert result["total_requests"] == 10
        assert result["successful_requests"] >= 0
        assert result["failed_requests"] >= 0
        assert result["successful_requests"] + result["failed_requests"] == 10
    
    def test_thread_concurrency_test_with_errors(self):
        """Test thread concurrency testing with errors"""
        def failing_func():
            if time.time() % 2 < 1:
                raise ValueError("Simulated error")
            time.sleep(0.001)
            return "result"
        
        tester = ConcurrencyTester()
        result = tester.test_thread_concurrency(failing_func, concurrency=2, total_requests=10)
        
        assert result["total_requests"] == 10
        assert result["successful_requests"] + result["failed_requests"] == 10


class TestWarmupExecutor:
    """Test WarmupExecutor"""
    
    def test_executor_initialization(self):
        """Test executor initialization"""
        executor = WarmupExecutor(warmup_iterations=5)
        
        assert executor.warmup_iterations == 5
    
    def test_executor_default_iterations(self):
        """Test executor with default iterations"""
        executor = WarmupExecutor()
        
        assert executor.warmup_iterations == 3
    
    @pytest.mark.asyncio
    async def test_execute_async_warmup(self):
        """Test executing async warmup"""
        async def mock_func():
            await asyncio.sleep(0.001)
            return "result"
        
        executor = WarmupExecutor(warmup_iterations=2)
        await executor.execute_async(mock_func)
        
        # Should complete without error
    
    @pytest.mark.asyncio
    async def test_execute_async_warmup_with_errors(self):
        """Test executing async warmup with errors"""
        async def failing_func():
            raise ValueError("Simulated error")
        
        executor = WarmupExecutor(warmup_iterations=2)
        
        # Should not raise error, just log warning
        await executor.execute_async(failing_func)
    
    def test_execute_sync_warmup(self):
        """Test executing synchronous warmup"""
        def mock_func():
            time.sleep(0.001)
            return "result"
        
        executor = WarmupExecutor(warmup_iterations=2)
        executor.execute_sync(mock_func)
        
        # Should complete without error
    
    def test_execute_sync_warmup_with_errors(self):
        """Test executing synchronous warmup with errors"""
        def failing_func():
            raise ValueError("Simulated error")
        
        executor = WarmupExecutor(warmup_iterations=2)
        
        # Should not raise error, just log warning
        executor.execute_sync(failing_func)


class TestFormatFunctions:
    """Test formatting utility functions"""
    
    def test_format_duration_microseconds(self):
        """Test formatting microseconds"""
        assert "μs" in format_duration(0.0005)
    
    def test_format_duration_milliseconds(self):
        """Test formatting milliseconds"""
        assert "ms" in format_duration(0.5)
    
    def test_format_duration_seconds(self):
        """Test formatting seconds"""
        assert "s" in format_duration(5.5)
    
    def test_format_duration_minutes(self):
        """Test formatting minutes"""
        result = format_duration(125.0)
        assert "m" in result
        assert "s" in result
    
    def test_format_bytes_bytes(self):
        """Test formatting bytes"""
        assert "B" in format_bytes(500)
    
    def test_format_bytes_kilobytes(self):
        """Test formatting kilobytes"""
        assert "KB" in format_bytes(5000)
    
    def test_format_bytes_megabytes(self):
        """Test formatting megabytes"""
        assert "MB" in format_bytes(5000000)
    
    def test_format_bytes_gigabytes(self):
        """Test formatting gigabytes"""
        assert "GB" in format_bytes(5000000000)
    
    def test_format_bytes_terabytes(self):
        """Test formatting terabytes"""
        assert "TB" in format_bytes(5000000000000)
    
    def test_format_bytes_petabytes(self):
        """Test formatting petabytes"""
        assert "PB" in format_bytes(5000000000000000)
