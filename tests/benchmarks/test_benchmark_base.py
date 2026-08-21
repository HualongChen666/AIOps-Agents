# -*- coding: utf-8 -*-
"""
Tests for Performance Benchmark Base Framework
"""

import asyncio
import json
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.benchmarks.benchmark_base import (
    PerformanceMetricType,
    PerformanceSeverity,
    PerformanceThreshold,
    MetricSample,
    PerformanceResult,
    PerformanceMetricsCollector,
    PerformanceResultAnalyzer,
    PerformanceReportGenerator,
    BenchmarkBase
)


class TestPerformanceMetricType:
    """Test PerformanceMetricType enum"""
    
    def test_metric_type_values(self):
        """Test that all metric types have correct values"""
        assert PerformanceMetricType.RESPONSE_TIME.value == "response_time"
        assert PerformanceMetricType.THROUGHPUT.value == "throughput"
        assert PerformanceMetricType.CPU_USAGE.value == "cpu_usage"
        assert PerformanceMetricType.MEMORY_USAGE.value == "memory_usage"
        assert PerformanceMetricType.DISK_IO.value == "disk_io"
        assert PerformanceMetricType.NETWORK_IO.value == "network_io"
        assert PerformanceMetricType.ERROR_RATE.value == "error_rate"
        assert PerformanceMetricType.CONCURRENCY.value == "concurrency"
        assert PerformanceMetricType.LATENCY_PERCENTILES.value == "latency_percentiles"


class TestPerformanceSeverity:
    """Test PerformanceSeverity enum"""
    
    def test_severity_values(self):
        """Test that all severity levels have correct values"""
        assert PerformanceSeverity.EXCELLENT.value == "excellent"
        assert PerformanceSeverity.GOOD.value == "good"
        assert PerformanceSeverity.ACCEPTABLE.value == "acceptable"
        assert PerformanceSeverity.WARNING.value == "warning"
        assert PerformanceSeverity.CRITICAL.value == "critical"


class TestPerformanceThreshold:
    """Test PerformanceThreshold dataclass"""
    
    def test_threshold_creation(self):
        """Test creating a performance threshold"""
        threshold = PerformanceThreshold(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
            unit="ms"
        )
        
        assert threshold.metric_type == PerformanceMetricType.RESPONSE_TIME
        assert threshold.excellent == 0.1
        assert threshold.good == 0.5
        assert threshold.acceptable == 1.0
        assert threshold.warning == 2.0
        assert threshold.critical == 5.0
        assert threshold.unit == "ms"
    
    def test_get_severity_excellent(self):
        """Test severity determination for excellent value"""
        threshold = PerformanceThreshold(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0
        )
        
        assert threshold.get_severity(0.05) == PerformanceSeverity.EXCELLENT
        assert threshold.get_severity(0.1) == PerformanceSeverity.EXCELLENT
    
    def test_get_severity_good(self):
        """Test severity determination for good value"""
        threshold = PerformanceThreshold(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0
        )
        
        assert threshold.get_severity(0.3) == PerformanceSeverity.GOOD
        assert threshold.get_severity(0.5) == PerformanceSeverity.GOOD
    
    def test_get_severity_acceptable(self):
        """Test severity determination for acceptable value"""
        threshold = PerformanceThreshold(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0
        )
        
        assert threshold.get_severity(0.7) == PerformanceSeverity.ACCEPTABLE
        assert threshold.get_severity(1.0) == PerformanceSeverity.ACCEPTABLE
    
    def test_get_severity_warning(self):
        """Test severity determination for warning value"""
        threshold = PerformanceThreshold(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0
        )
        
        assert threshold.get_severity(1.5) == PerformanceSeverity.WARNING
        assert threshold.get_severity(2.0) == PerformanceSeverity.WARNING
    
    def test_get_severity_critical(self):
        """Test severity determination for critical value"""
        threshold = PerformanceThreshold(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0
        )
        
        assert threshold.get_severity(3.0) == PerformanceSeverity.CRITICAL
        assert threshold.get_severity(10.0) == PerformanceSeverity.CRITICAL


class TestMetricSample:
    """Test MetricSample dataclass"""
    
    def test_sample_creation(self):
        """Test creating a metric sample"""
        timestamp = datetime.now()
        sample = MetricSample(
            timestamp=timestamp,
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            value=0.5,
            unit="seconds",
            metadata={"iteration": 1}
        )
        
        assert sample.timestamp == timestamp
        assert sample.metric_type == PerformanceMetricType.RESPONSE_TIME
        assert sample.value == 0.5
        assert sample.unit == "seconds"
        assert sample.metadata == {"iteration": 1}
    
    def test_sample_creation_without_metadata(self):
        """Test creating a sample without metadata"""
        sample = MetricSample(
            timestamp=datetime.now(),
            metric_type=PerformanceMetricType.CPU_USAGE,
            value=50.0,
            unit="percent"
        )
        
        assert sample.metadata == {}
    
    def test_sample_to_dict(self):
        """Test converting sample to dictionary"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        sample = MetricSample(
            timestamp=timestamp,
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            value=0.5,
            unit="seconds",
            metadata={"iteration": 1}
        )
        
        result = sample.to_dict()
        
        assert result["timestamp"] == "2024-01-01T12:00:00"
        assert result["metric_type"] == "response_time"
        assert result["value"] == 0.5
        assert result["unit"] == "seconds"
        assert result["metadata"] == {"iteration": 1}


class TestPerformanceResult:
    """Test PerformanceResult dataclass"""
    
    def test_result_creation(self):
        """Test creating a performance result"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 10)
        samples = [
            MetricSample(
                timestamp=start_time,
                metric_type=PerformanceMetricType.RESPONSE_TIME,
                value=0.5,
                unit="seconds"
            )
        ]
        
        result = PerformanceResult(
            test_name="test_benchmark",
            start_time=start_time,
            end_time=end_time,
            duration=10.0,
            samples=samples
        )
        
        assert result.test_name == "test_benchmark"
        assert result.start_time == start_time
        assert result.end_time == end_time
        assert result.duration == 10.0
        assert result.sample_count == 1
    
    def test_sample_count_property(self):
        """Test sample count property"""
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=[
                MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent"),
                MetricSample(datetime.now(), PerformanceMetricType.MEMORY_USAGE, 60.0, "percent")
            ]
        )
        
        assert result.sample_count == 2
    
    def test_get_samples_by_type(self):
        """Test filtering samples by type"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.MEMORY_USAGE, 60.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 55.0, "percent")
        ]
        
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        
        cpu_samples = result.get_samples_by_type(PerformanceMetricType.CPU_USAGE)
        assert len(cpu_samples) == 2
        
        memory_samples = result.get_samples_by_type(PerformanceMetricType.MEMORY_USAGE)
        assert len(memory_samples) == 1
    
    def test_get_metric_values(self):
        """Test getting metric values"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 55.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.MEMORY_USAGE, 60.0, "percent")
        ]
        
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        
        cpu_values = result.get_metric_values(PerformanceMetricType.CPU_USAGE)
        assert cpu_values == [50.0, 55.0]
        
        memory_values = result.get_metric_values(PerformanceMetricType.MEMORY_USAGE)
        assert memory_values == [60.0]
    
    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 10)
        samples = [
            MetricSample(
                timestamp=start_time,
                metric_type=PerformanceMetricType.RESPONSE_TIME,
                value=0.5,
                unit="seconds"
            )
        ]
        thresholds = {
            PerformanceMetricType.RESPONSE_TIME: PerformanceThreshold(
                metric_type=PerformanceMetricType.RESPONSE_TIME,
                excellent=0.1,
                good=0.5,
                acceptable=1.0,
                warning=2.0,
                critical=5.0
            )
        }
        
        result = PerformanceResult(
            test_name="test_benchmark",
            start_time=start_time,
            end_time=end_time,
            duration=10.0,
            samples=samples,
            thresholds=thresholds,
            metadata={"iterations": 10}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["test_name"] == "test_benchmark"
        assert result_dict["start_time"] == "2024-01-01T12:00:00"
        assert result_dict["end_time"] == "2024-01-01T12:00:10"
        assert result_dict["duration"] == 10.0
        assert result_dict["sample_count"] == 1
        assert len(result_dict["samples"]) == 1
        assert "response_time" in result_dict["thresholds"]
        assert result_dict["metadata"]["iterations"] == 10


class TestPerformanceMetricsCollector:
    """Test PerformanceMetricsCollector"""
    
    def test_collector_initialization(self):
        """Test collector initialization"""
        collector = PerformanceMetricsCollector(sample_interval=0.5)
        
        assert collector.sample_interval == 0.5
        assert len(collector.samples) == 0
        assert collector._collecting is False
    
    def test_add_custom_sample(self):
        """Test adding custom sample"""
        collector = PerformanceMetricsCollector()
        
        collector.add_custom_sample(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            value=0.5,
            unit="seconds",
            metadata={"iteration": 1}
        )
        
        assert len(collector.samples) == 1
        assert collector.samples[0].metric_type == PerformanceMetricType.RESPONSE_TIME
        assert collector.samples[0].value == 0.5
        assert collector.samples[0].unit == "seconds"
    
    def test_add_custom_sample_without_metadata(self):
        """Test adding custom sample without metadata"""
        collector = PerformanceMetricsCollector()
        
        collector.add_custom_sample(
            metric_type=PerformanceMetricType.CPU_USAGE,
            value=50.0,
            unit="percent"
        )
        
        assert len(collector.samples) == 1
        assert collector.samples[0].metadata == {}
    
    def test_get_samples(self):
        """Test getting samples"""
        collector = PerformanceMetricsCollector()
        
        collector.add_custom_sample(PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        collector.add_custom_sample(PerformanceMetricType.MEMORY_USAGE, 60.0, "percent")
        
        samples = collector.get_samples()
        
        assert len(samples) == 2
        assert samples is not collector.samples  # Should be a copy
    
    def test_clear_samples(self):
        """Test clearing samples"""
        collector = PerformanceMetricsCollector()
        
        collector.add_custom_sample(PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        assert len(collector.samples) == 1
        
        collector.clear_samples()
        assert len(collector.samples) == 0
    
    def test_start_stop_collection(self):
        """Test starting and stopping collection"""
        collector = PerformanceMetricsCollector(sample_interval=0.01)
        
        collector.start_collection()
        assert collector._collecting is True
        
        time.sleep(0.05)  # Let it collect some samples
        
        collector.stop_collection()
        assert collector._collecting is False
    
    def test_start_when_already_collecting(self):
        """Test starting collection when already collecting"""
        collector = PerformanceMetricsCollector(sample_interval=0.01)
        
        collector.start_collection()
        time.sleep(0.01)
        
        # Should not raise error
        collector.start_collection()
        
        collector.stop_collection()


class TestPerformanceResultAnalyzer:
    """Test PerformanceResultAnalyzer"""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        
        analyzer = PerformanceResultAnalyzer(result)
        
        assert analyzer.result == result
    
    def test_calculate_statistics_empty(self):
        """Test calculating statistics with no data"""
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=[]
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        stats = analyzer.calculate_statistics(PerformanceMetricType.CPU_USAGE)
        
        assert stats["count"] == 0
        assert stats["mean"] == 0.0
        assert stats["median"] == 0.0
        assert stats["std_dev"] == 0.0
    
    def test_calculate_statistics_with_data(self):
        """Test calculating statistics with data"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 60.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 70.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        stats = analyzer.calculate_statistics(PerformanceMetricType.CPU_USAGE)
        
        assert stats["count"] == 3
        assert stats["mean"] == 60.0
        assert stats["median"] == 60.0
        assert stats["min"] == 50.0
        assert stats["max"] == 70.0
    
    def test_calculate_statistics_single_value(self):
        """Test calculating statistics with single value"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        stats = analyzer.calculate_statistics(PerformanceMetricType.CPU_USAGE)
        
        assert stats["count"] == 1
        assert stats["mean"] == 50.0
        assert stats["std_dev"] == 0.0
    
    def test_percentile_calculation(self):
        """Test percentile calculation"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, float(i), "percent")
            for i in range(100)
        ]
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        stats = analyzer.calculate_statistics(PerformanceMetricType.CPU_USAGE)
        
        assert stats["p50"] == 50.0
        assert stats["p90"] == 90.0
        assert stats["p95"] == 95.0
        assert stats["p99"] == 99.0
    
    def test_evaluate_against_thresholds_no_threshold(self):
        """Test evaluation when no threshold configured"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        evaluation = analyzer.evaluate_against_thresholds(PerformanceMetricType.CPU_USAGE)
        
        assert evaluation["status"] == "no_threshold"
    
    def test_evaluate_against_thresholds_with_threshold(self):
        """Test evaluation with threshold configured"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        ]
        threshold = PerformanceThreshold(
            metric_type=PerformanceMetricType.CPU_USAGE,
            excellent=20.0,
            good=50.0,
            acceptable=70.0,
            warning=85.0,
            critical=95.0
        )
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples,
            thresholds={PerformanceMetricType.CPU_USAGE: threshold}
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        evaluation = analyzer.evaluate_against_thresholds(PerformanceMetricType.CPU_USAGE)
        
        assert evaluation["metric_type"] == "cpu_usage"
        assert "threshold" in evaluation
        assert "statistics" in evaluation
        assert "evaluation" in evaluation
        assert evaluation["evaluation"]["mean_severity"] == "good"
    
    def test_detect_anomalies_empty(self):
        """Test anomaly detection with no data"""
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=[]
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        anomalies = analyzer.detect_anomalies(PerformanceMetricType.CPU_USAGE)
        
        assert len(anomalies) == 0
    
    def test_detect_anomalies_insufficient_data(self):
        """Test anomaly detection with insufficient data"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        anomalies = analyzer.detect_anomalies(PerformanceMetricType.CPU_USAGE)
        
        assert len(anomalies) == 0
    
    def test_detect_anomalies_with_outliers(self):
        """Test anomaly detection with outliers"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 51.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 49.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 52.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 48.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 200.0, "percent")  # Extreme outlier
        ]
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=samples
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        anomalies = analyzer.detect_anomalies(PerformanceMetricType.CPU_USAGE, std_dev_threshold=1.0)
        
        assert len(anomalies) > 0
    
    def test_generate_summary(self):
        """Test generating comprehensive summary"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.MEMORY_USAGE, 60.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test_benchmark",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=10.0,
            samples=samples
        )
        analyzer = PerformanceResultAnalyzer(result)
        
        summary = analyzer.generate_summary()
        
        assert summary["test_name"] == "test_benchmark"
        assert summary["duration"] == 10.0
        assert summary["sample_count"] == 2
        assert "cpu_usage" in summary["metrics"]
        assert "memory_usage" in summary["metrics"]


class TestPerformanceReportGenerator:
    """Test PerformanceReportGenerator"""
    
    def test_generator_initialization(self):
        """Test generator initialization"""
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=[]
        )
        
        generator = PerformanceReportGenerator(result)
        
        assert generator.result == result
        assert generator.analyzer.result == result
    
    def test_generate_text_report(self):
        """Test generating text report"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent"),
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 60.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test_benchmark",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=10.0,
            samples=samples
        )
        generator = PerformanceReportGenerator(result)
        
        report = generator.generate_text_report()
        
        assert "PERFORMANCE TEST REPORT" in report
        assert "test_benchmark" in report
        assert "Duration:" in report
        assert "METRICS SUMMARY" in report
        assert "CPU_USAGE" in report
    
    def test_generate_json_report(self):
        """Test generating JSON report"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test_benchmark",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=10.0,
            samples=samples
        )
        generator = PerformanceReportGenerator(result)
        
        report = generator.generate_json_report()
        
        # Should be valid JSON
        parsed = json.loads(report)
        assert parsed["test_name"] == "test_benchmark"
        assert parsed["duration"] == 10.0
    
    def test_save_report_json(self):
        """Test saving JSON report to file"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test_benchmark",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=10.0,
            samples=samples
        )
        generator = PerformanceReportGenerator(result)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            saved_path = generator.save_report(temp_path, format="json")
            
            assert Path(saved_path).exists()
            
            with open(saved_path, 'r') as f:
                content = f.read()
                parsed = json.loads(content)
                assert parsed["test_name"] == "test_benchmark"
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_save_report_text(self):
        """Test saving text report to file"""
        samples = [
            MetricSample(datetime.now(), PerformanceMetricType.CPU_USAGE, 50.0, "percent")
        ]
        result = PerformanceResult(
            test_name="test_benchmark",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=10.0,
            samples=samples
        )
        generator = PerformanceReportGenerator(result)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            saved_path = generator.save_report(temp_path, format="text")
            
            assert Path(saved_path).exists()
            
            with open(saved_path, 'r') as f:
                content = f.read()
                assert "PERFORMANCE TEST REPORT" in content
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_save_report_unsupported_format(self):
        """Test saving report with unsupported format"""
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=[]
        )
        generator = PerformanceReportGenerator(result)
        
        with pytest.raises(ValueError, match="Unsupported format"):
            generator.save_report("test.xml", format="xml")


class TestBenchmarkBase:
    """Test BenchmarkBase abstract class"""
    
    def test_benchmark_base_is_abstract(self):
        """Test that BenchmarkBase cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BenchmarkBase(name="test")
    
    def test_concrete_benchmark_implementation(self):
        """Test concrete implementation of BenchmarkBase"""
        
        class ConcreteBenchmark(BenchmarkBase):
            def _setup_thresholds(self):
                self.add_threshold(
                    PerformanceMetricType.RESPONSE_TIME,
                    excellent=0.1,
                    good=0.5,
                    acceptable=1.0,
                    warning=2.0,
                    critical=5.0
                )
            
            async def run_workload(self):
                await asyncio.sleep(0.01)
                return "result"
        
        benchmark = ConcreteBenchmark(name="concrete_test")
        
        assert benchmark.name == "concrete_test"
        assert PerformanceMetricType.RESPONSE_TIME in benchmark.thresholds
    
    def test_add_threshold(self):
        """Test adding threshold to benchmark"""
        
        class ConcreteBenchmark(BenchmarkBase):
            def _setup_thresholds(self):
                pass
            
            async def run_workload(self):
                return "result"
        
        benchmark = ConcreteBenchmark(name="test")
        
        benchmark.add_threshold(
            PerformanceMetricType.CPU_USAGE,
            excellent=20.0,
            good=50.0,
            acceptable=70.0,
            warning=85.0,
            critical=95.0,
            unit="percent"
        )
        
        assert PerformanceMetricType.CPU_USAGE in benchmark.thresholds
        assert benchmark.thresholds[PerformanceMetricType.CPU_USAGE].excellent == 20.0
    
    @pytest.mark.asyncio
    async def test_execute_single_iteration(self):
        """Test executing benchmark with single iteration"""
        
        class ConcreteBenchmark(BenchmarkBase):
            def _setup_thresholds(self):
                pass
            
            async def run_workload(self):
                await asyncio.sleep(0.01)
                return "result"
        
        benchmark = ConcreteBenchmark(name="test")
        result = await benchmark.execute(iterations=1)
        
        assert result.test_name == "test"
        assert result.sample_count > 0
        assert result.duration > 0
    
    @pytest.mark.asyncio
    async def test_execute_multiple_iterations(self):
        """Test executing benchmark with multiple iterations"""
        
        class ConcreteBenchmark(BenchmarkBase):
            def _setup_thresholds(self):
                pass
            
            async def run_workload(self):
                await asyncio.sleep(0.001)
                return "result"
        
        benchmark = ConcreteBenchmark(name="test")
        result = await benchmark.execute(iterations=5)
        
        assert result.test_name == "test"
        assert result.metadata["iterations"] == 5
    
    @pytest.mark.asyncio
    async def test_execute_concurrent(self):
        """Test executing benchmark with concurrency"""
        
        class ConcreteBenchmark(BenchmarkBase):
            def _setup_thresholds(self):
                pass
            
            async def run_workload(self):
                await asyncio.sleep(0.001)
                return "result"
        
        benchmark = ConcreteBenchmark(name="test")
        result = await benchmark.execute_concurrent(concurrency=5, total_requests=10)
        
        assert result.test_name == "test_concurrent"
        assert result.metadata["concurrency"] == 5
        assert result.metadata["total_requests"] == 10
    
    @pytest.mark.asyncio
    async def test_execute_concurrent_with_errors(self):
        """Test executing concurrent benchmark with errors"""
        
        class FailingBenchmark(BenchmarkBase):
            def _setup_thresholds(self):
                pass
            
            async def run_workload(self):
                if time.time() % 2 < 1:  # Randomly fail
                    raise ValueError("Simulated error")
                await asyncio.sleep(0.001)
                return "result"
        
        benchmark = FailingBenchmark(name="failing_test")
        result = await benchmark.execute_concurrent(concurrency=2, total_requests=10)
        
        assert result.metadata["failed_requests"] >= 0
        assert result.metadata["successful_requests"] + result.metadata["failed_requests"] == 10
    
    def test_generate_report_without_file(self):
        """Test generating report without saving to file"""
        
        class ConcreteBenchmark(BenchmarkBase):
            def _setup_thresholds(self):
                pass
            
            async def run_workload(self):
                return "result"
        
        benchmark = ConcreteBenchmark(name="test")
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=[]
        )
        
        json_report = benchmark.generate_report(result, format="json")
        assert "test_name" in json_report
        
        text_report = benchmark.generate_report(result, format="text")
        assert "PERFORMANCE TEST REPORT" in text_report
    
    def test_generate_report_with_file(self):
        """Test generating report and saving to file"""
        
        class ConcreteBenchmark(BenchmarkBase):
            def _setup_thresholds(self):
                pass
            
            async def run_workload(self):
                return "result"
        
        benchmark = ConcreteBenchmark(name="test")
        result = PerformanceResult(
            test_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            samples=[]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            saved_path = benchmark.generate_report(result, output_path=temp_path, format="json")
            assert Path(saved_path).exists()
        finally:
            Path(temp_path).unlink(missing_ok=True)
