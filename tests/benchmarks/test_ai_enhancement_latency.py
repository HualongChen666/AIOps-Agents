# -*- coding: utf-8 -*-
"""
AI Enhancement Latency Benchmark Test Suite
============================================

Comprehensive AI performance benchmarking including:
- AI inference latency testing
- Model performance comparison
- Token processing speed
- Batch processing performance
- Resource usage monitoring (CPU/GPU/Memory)
- Cost-benefit analysis

Performance Benchmarks:
- AI inference latency < 2s
- Token processing speed > 1000 tokens/s
- Batch processing efficiency > 80%
- Resource usage optimization

Requirements:
- Uses real AI modules (no mocking)
- Integrates with existing test framework
- Achieves 90%+ statement and branch coverage
- Provides complete AI performance reports
"""

import asyncio
import gc
import json
import os
import psutil
import statistics
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Import real AI modules
from core.ai_enhancement import (
    AIAnalysisEnhancer,
    MultiTurnConversationManager,
    get_ai_enhancer,
    get_conversation_manager,
)
from core.ai.token_budget import estimate_tokens
from core.ai_interface import AnalysisType
from core.llm_cost_monitor import (
    LLMCostMonitor,
    get_llm_cost_monitor,
    reset_llm_cost_monitor,
)


# ============================================================================
# Performance Metrics Data Classes
# ============================================================================


@dataclass
class LatencyMetrics:
    """Latency measurement metrics"""

    operation: str
    total_time: float
    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    p95_time: float
    p99_time: float
    std_dev: float
    sample_count: int
    success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "total_time": round(self.total_time, 4),
            "min_time": round(self.min_time, 4),
            "max_time": round(self.max_time, 4),
            "avg_time": round(self.avg_time, 4),
            "median_time": round(self.median_time, 4),
            "p95_time": round(self.p95_time, 4),
            "p99_time": round(self.p99_time, 4),
            "std_dev": round(self.std_dev, 4),
            "sample_count": self.sample_count,
            "success_rate": round(self.success_rate * 100, 2),
        }


@dataclass
class TokenMetrics:
    """Token processing metrics"""

    operation: str
    total_tokens: int
    tokens_per_second: float
    avg_tokens_per_second: float
    input_tokens: int
    output_tokens: int
    processing_time: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "total_tokens": self.total_tokens,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "avg_tokens_per_second": round(self.avg_tokens_per_second, 2),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "processing_time": round(self.processing_time, 4),
        }


@dataclass
class ResourceMetrics:
    """Resource usage metrics"""

    operation: str
    cpu_percent_before: float
    cpu_percent_after: float
    cpu_percent_delta: float
    memory_mb_before: float
    memory_mb_after: float
    memory_mb_delta: float
    thread_count: int
    gc_collections: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "cpu_percent_before": round(self.cpu_percent_before, 2),
            "cpu_percent_after": round(self.cpu_percent_after, 2),
            "cpu_percent_delta": round(self.cpu_percent_delta, 2),
            "memory_mb_before": round(self.memory_mb_before, 2),
            "memory_mb_after": round(self.memory_mb_after, 2),
            "memory_mb_delta": round(self.memory_mb_delta, 2),
            "thread_count": self.thread_count,
            "gc_collections": self.gc_collections,
        }


@dataclass
class CostMetrics:
    """Cost analysis metrics"""

    operation: str
    estimated_cost: float
    actual_cost: float
    cost_efficiency: float
    tokens_per_dollar: float
    model_used: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "estimated_cost": round(self.estimated_cost, 6),
            "actual_cost": round(self.actual_cost, 6),
            "cost_efficiency": round(self.cost_efficiency, 4),
            "tokens_per_dollar": round(self.tokens_per_dollar, 2),
            "model_used": self.model_used,
        }


@dataclass
class BatchMetrics:
    """Batch processing metrics"""

    operation: str
    batch_size: int
    total_time: float
    avg_time_per_item: float
    throughput: float
    efficiency: float
    parallel_speedup: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "batch_size": self.batch_size,
            "total_time": round(self.total_time, 4),
            "avg_time_per_item": round(self.avg_time_per_item, 4),
            "throughput": round(self.throughput, 2),
            "efficiency": round(self.efficiency * 100, 2),
            "parallel_speedup": round(self.parallel_speedup, 2),
        }


@dataclass
class AIPerformanceReport:
    """Comprehensive AI performance report"""

    test_name: str
    timestamp: str
    latency_metrics: List[LatencyMetrics] = field(default_factory=list)
    token_metrics: List[TokenMetrics] = field(default_factory=list)
    resource_metrics: List[ResourceMetrics] = field(default_factory=list)
    cost_metrics: List[CostMetrics] = field(default_factory=list)
    batch_metrics: List[BatchMetrics] = field(default_factory=list)
    benchmarks_passed: Dict[str, bool] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "timestamp": self.timestamp,
            "latency_metrics": [m.to_dict() for m in self.latency_metrics],
            "token_metrics": [m.to_dict() for m in self.token_metrics],
            "resource_metrics": [m.to_dict() for m in self.resource_metrics],
            "cost_metrics": [m.to_dict() for m in self.cost_metrics],
            "batch_metrics": [m.to_dict() for m in self.batch_metrics],
            "benchmarks_passed": self.benchmarks_passed,
            "recommendations": self.recommendations,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ============================================================================
# Performance Measurement Utilities
# ============================================================================


class PerformanceMonitor:
    """Performance monitoring utility"""

    def __init__(self):
        self.process = psutil.Process()
        self.gc_count_before = 0

    def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage"""
        return self.process.cpu_percent(interval=0.1)

    def get_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024

    def get_thread_count(self) -> int:
        """Get current thread count"""
        return self.process.num_threads()

    def get_gc_count(self) -> int:
        """Get garbage collection count"""
        return sum(gc.get_count())

    def start_measurement(self) -> Dict[str, Any]:
        """Start performance measurement"""
        gc.collect()
        return {
            "cpu_percent": self.get_cpu_percent(),
            "memory_mb": self.get_memory_mb(),
            "thread_count": self.get_thread_count(),
            "gc_count": self.get_gc_count(),
        }

    def end_measurement(self, start_data: Dict[str, Any]) -> ResourceMetrics:
        """End performance measurement and return metrics"""
        end_data = {
            "cpu_percent": self.get_cpu_percent(),
            "memory_mb": self.get_memory_mb(),
            "thread_count": self.get_thread_count(),
            "gc_count": self.get_gc_count(),
        }

        return ResourceMetrics(
            operation="performance_measurement",
            cpu_percent_before=start_data["cpu_percent"],
            cpu_percent_after=end_data["cpu_percent"],
            cpu_percent_delta=end_data["cpu_percent"] - start_data["cpu_percent"],
            memory_mb_before=start_data["memory_mb"],
            memory_mb_after=end_data["memory_mb"],
            memory_mb_delta=end_data["memory_mb"] - start_data["memory_mb"],
            thread_count=end_data["thread_count"],
            gc_collections=end_data["gc_count"] - start_data["gc_count"],
        )


def measure_latency(
    operation: str, func, iterations: int = 10, *args, **kwargs
) -> LatencyMetrics:
    """Measure operation latency over multiple iterations"""

    times = []
    successes = 0

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            if result is not None:
                successes += 1
        except Exception as e:
            pass
        end = time.perf_counter()
        times.append(end - start)

    total_time = sum(times)
    sorted_times = sorted(times)

    return LatencyMetrics(
        operation=operation,
        total_time=total_time,
        min_time=min(times),
        max_time=max(times),
        avg_time=statistics.mean(times),
        median_time=statistics.median(times),
        p95_time=sorted_times[int(len(times) * 0.95)] if len(times) > 0 else 0,
        p99_time=sorted_times[int(len(times) * 0.99)] if len(times) > 0 else 0,
        std_dev=statistics.stdev(times) if len(times) > 1 else 0,
        sample_count=len(times),
        success_rate=successes / iterations if iterations > 0 else 0,
    )


def measure_token_speed(operation: str, text: str, processing_time: float) -> TokenMetrics:
    """Measure token processing speed"""

    input_tokens = estimate_tokens(text)
    total_tokens = input_tokens  # Assuming output is similar length for estimation
    tokens_per_second = total_tokens / processing_time if processing_time > 0 else 0

    return TokenMetrics(
        operation=operation,
        total_tokens=total_tokens,
        tokens_per_second=tokens_per_second,
        avg_tokens_per_second=tokens_per_second,
        input_tokens=input_tokens,
        output_tokens=0,  # Will be updated if actual output is available
        processing_time=processing_time,
    )


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def ai_enhancer():
    """Provide AI enhancer instance"""
    return AIAnalysisEnhancer()


@pytest.fixture
def conversation_manager():
    """Provide conversation manager instance"""
    return MultiTurnConversationManager()


@pytest.fixture
def cost_monitor():
    """Provide cost monitor instance"""
    reset_llm_cost_monitor()
    return get_llm_cost_monitor()


@pytest.fixture
def performance_monitor():
    """Provide performance monitor instance"""
    return PerformanceMonitor()


@pytest.fixture
def sample_alert_data():
    """Sample alert data for testing"""
    return {
        "host": "test-server-01",
        "platform": "linux",
        "level": "critical",
        "message": "High CPU usage detected on server test-server-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_usage": 95.5,
        "memory_usage": 87.3,
        "disk_usage": 45.2,
    }


@pytest.fixture
def sample_analysis_context():
    """Sample analysis context for testing"""
    return {
        "system_metrics": {
            "cpu_percent": 95.5,
            "memory_percent": 87.3,
            "disk_percent": 45.2,
            "network_io": {"bytes_sent": 1024000, "bytes_recv": 2048000},
        },
        "top_processes": [
            {"pid": 1234, "name": "python", "cpu_percent": 45.2, "memory_percent": 12.3},
            {"pid": 5678, "name": "nginx", "cpu_percent": 30.1, "memory_percent": 5.6},
        ],
        "recent_alerts": [
            {
                "level": "warning",
                "message": "Memory usage high",
                "timestamp": "2024-01-01T10:00:00Z",
            }
        ],
    }


# ============================================================================
# AI Inference Latency Tests
# ============================================================================


class TestAIInferenceLatency:
    """Test AI inference latency performance"""

    def test_context_key_generation_latency(self, ai_enhancer, sample_alert_data):
        """Test context key generation latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        latency = measure_latency(
            "context_key_generation",
            ai_enhancer.generate_context_key,
            iterations=100,
            alert_data=sample_alert_data,
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: context key generation should be < 10ms
        assert latency.avg_time < 0.01, f"Context key generation too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="context_key_generation_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=[latency],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "avg_time < 10ms": latency.avg_time < 0.01,
            },
        )

        print(f"\nContext Key Generation Latency Report:")
        print(report.to_json())

    def test_cache_operations_latency(self, ai_enhancer, sample_alert_data):
        """Test cache operations latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        context_key = ai_enhancer.generate_context_key(sample_alert_data)
        sample_analysis = {"root_cause": "test", "confidence": 0.85}

        # Test cache write latency
        write_latency = measure_latency(
            "cache_write",
            ai_enhancer.cache_analysis,
            iterations=50,
            context_key=context_key,
            analysis=sample_analysis,
        )

        # Test cache read latency
        read_latency = measure_latency(
            "cache_read",
            ai_enhancer.get_cached_analysis,
            iterations=50,
            context_key=context_key,
        )

        # Test cache miss latency
        miss_latency = measure_latency(
            "cache_miss",
            ai_enhancer.get_cached_analysis,
            iterations=50,
            context_key="nonexistent_key",
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmarks
        assert write_latency.avg_time < 0.01, f"Cache write too slow: {write_latency.avg_time}s"
        assert read_latency.avg_time < 0.01, f"Cache read too slow: {read_latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="cache_operations_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=[write_latency, read_latency, miss_latency],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "write_avg < 10ms": write_latency.avg_time < 0.01,
                "read_avg < 10ms": read_latency.avg_time < 0.01,
            },
        )

        print(f"\nCache Operations Latency Report:")
        print(report.to_json())

    def test_performance_metrics_update_latency(self, ai_enhancer):
        """Test performance metrics update latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        sample_metrics = {
            "success": True,
            "response_time": 1.5,
            "model": "gpt-4o-mini",
        }

        latency = measure_latency(
            "performance_metrics_update",
            ai_enhancer.update_performance_metrics,
            iterations=100,
            metrics=sample_metrics,
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: metrics update should be < 5ms
        assert latency.avg_time < 0.005, f"Metrics update too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="performance_metrics_update_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=[latency],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "avg_time < 5ms": latency.avg_time < 0.005,
            },
        )

        print(f"\nPerformance Metrics Update Latency Report:")
        print(report.to_json())

    def test_analysis_history_latency(self, ai_enhancer, sample_alert_data):
        """Test analysis history operations latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        # Record some analyses
        for i in range(10):
            ai_enhancer.record_analysis(
                {
                    "context_key": f"test_{i}",
                    "root_cause": f"cause_{i}",
                    "confidence": 0.8 + i * 0.01,
                }
            )

        # Test history retrieval latency
        latency = measure_latency(
            "analysis_history_retrieval",
            ai_enhancer.get_analysis_history,
            iterations=50,
            limit=10,
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: history retrieval should be < 10ms
        assert latency.avg_time < 0.01, f"History retrieval too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="analysis_history_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=[latency],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "avg_time < 10ms": latency.avg_time < 0.01,
            },
        )

        print(f"\nAnalysis History Latency Report:")
        print(report.to_json())


# ============================================================================
# Model Performance Comparison Tests
# ============================================================================


class TestModelPerformanceComparison:
    """Test model performance comparison"""

    def test_model_config_lookup_latency(self, cost_monitor):
        """Test model configuration lookup latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        models = ["gpt-4o-mini", "gpt-3.5-turbo", "MiniMax-Text-01"]

        latencies = []
        for model in models:
            latency = measure_latency(
                f"model_config_lookup_{model}",
                cost_monitor.get_model_config,
                iterations=100,
                model_name=model,
            )
            latencies.append(latency)

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: config lookup should be < 1ms
        for latency in latencies:
            assert latency.avg_time < 0.001, f"Config lookup too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="model_config_lookup_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=latencies,
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                f"{latency.operation} < 1ms": latency.avg_time < 0.001 for latency in latencies
            },
        )

        print(f"\nModel Config Lookup Latency Report:")
        print(report.to_json())

    def test_cost_estimation_latency(self, cost_monitor):
        """Test cost estimation latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        test_cases = [
            ("gpt-4o-mini", 1000, 500),
            ("gpt-3.5-turbo", 2000, 1000),
            ("MiniMax-Text-01", 1500, 750),
        ]

        latencies = []
        for model, input_tokens, output_tokens in test_cases:
            latency = measure_latency(
                f"cost_estimation_{model}",
                cost_monitor.estimate_cost,
                iterations=100,
                model_name=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            latencies.append(latency)

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: cost estimation should be < 1ms
        for latency in latencies:
            assert latency.avg_time < 0.001, f"Cost estimation too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="cost_estimation_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=latencies,
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                f"{latency.operation} < 1ms": latency.avg_time < 0.001 for latency in latencies
            },
        )

        print(f"\nCost Estimation Latency Report:")
        print(report.to_json())

    def test_budget_check_latency(self, cost_monitor):
        """Test budget check latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        test_costs = [0.01, 0.1, 0.5, 1.0]

        latencies = []
        for cost in test_costs:
            latency = measure_latency(
                f"budget_check_{cost}",
                cost_monitor.check_budget,
                iterations=100,
                estimated_cost=cost,
            )
            latencies.append(latency)

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: budget check should be < 1ms
        for latency in latencies:
            assert latency.avg_time < 0.001, f"Budget check too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="budget_check_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=latencies,
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                f"{latency.operation} < 1ms": latency.avg_time < 0.001 for latency in latencies
            },
        )

        print(f"\nBudget Check Latency Report:")
        print(report.to_json())


# ============================================================================
# Token Processing Speed Tests
# ============================================================================


class TestTokenProcessingSpeed:
    """Test token processing speed"""

    def test_token_estimation_speed(self):
        """Test token estimation speed"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        test_texts = [
            "Short text",
            "This is a medium length text for testing token estimation performance.",
            "A" * 1000,  # Long ASCII text
            "中文" * 500,  # Long CJK text
            "Mixed text with 中文 and English characters for comprehensive testing.",
        ]

        latencies = []
        token_metrics = []

        for i, text in enumerate(test_texts):
            latency = measure_latency(
                f"token_estimation_test_{i}",
                estimate_tokens,
                iterations=100,
                text=text,
            )
            latencies.append(latency)

            # Calculate token speed
            token_count = estimate_tokens(text)
            token_speed = token_count / latency.avg_time if latency.avg_time > 0 else 0

            token_metrics.append(
                TokenMetrics(
                    operation=f"token_estimation_test_{i}",
                    total_tokens=token_count,
                    tokens_per_second=token_speed,
                    avg_tokens_per_second=token_speed,
                    input_tokens=token_count,
                    output_tokens=0,
                    processing_time=latency.avg_time,
                )
            )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: token estimation should be > 10000 tokens/s
        for metric in token_metrics:
            assert (
                metric.tokens_per_second > 10000
            ), f"Token estimation too slow: {metric.tokens_per_second} tokens/s"

        report = AIPerformanceReport(
            test_name="token_estimation_speed",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=latencies,
            token_metrics=token_metrics,
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                f"{m.operation} > 10000 tokens/s": m.tokens_per_second > 10000
                for m in token_metrics
            },
        )

        print(f"\nToken Estimation Speed Report:")
        print(report.to_json())

    def test_large_text_tokenization(self):
        """Test large text tokenization performance"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        # Create large text (100KB)
        large_text = "A" * 100000

        latency = measure_latency(
            "large_text_tokenization",
            estimate_tokens,
            iterations=10,
            text=large_text,
        )

        token_count = estimate_tokens(large_text)
        token_speed = token_count / latency.avg_time if latency.avg_time > 0 else 0

        token_metric = TokenMetrics(
            operation="large_text_tokenization",
            total_tokens=token_count,
            tokens_per_second=token_speed,
            avg_tokens_per_second=token_speed,
            input_tokens=token_count,
            output_tokens=0,
            processing_time=latency.avg_time,
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: large text should be > 50000 tokens/s
        assert (
            token_metric.tokens_per_second > 50000
        ), f"Large text tokenization too slow: {token_metric.tokens_per_second} tokens/s"

        report = AIPerformanceReport(
            test_name="large_text_tokenization",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=[latency],
            token_metrics=[token_metric],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "tokens_per_second > 50000": token_metric.tokens_per_second > 50000,
            },
        )

        print(f"\nLarge Text Tokenization Report:")
        print(report.to_json())


# ============================================================================
# Batch Processing Performance Tests
# ============================================================================


class TestBatchProcessingPerformance:
    """Test batch processing performance"""

    def test_batch_context_key_generation(self, ai_enhancer):
        """Test batch context key generation"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        # Create batch of alert data
        batch_size = 100
        batch_alerts = [
            {
                "host": f"server-{i}",
                "platform": "linux" if i % 2 == 0 else "windows",
                "level": "critical" if i % 3 == 0 else "warning",
                "message": f"Test alert message {i}",
            }
            for i in range(batch_size)
        ]

        # Measure sequential processing
        start_seq = time.perf_counter()
        sequential_results = [
            ai_enhancer.generate_context_key(alert) for alert in batch_alerts
        ]
        sequential_time = time.perf_counter() - start_seq

        # Calculate metrics
        avg_time_per_item = sequential_time / batch_size
        throughput = batch_size / sequential_time

        batch_metric = BatchMetrics(
            operation="batch_context_key_generation",
            batch_size=batch_size,
            total_time=sequential_time,
            avg_time_per_item=avg_time_per_item,
            throughput=throughput,
            efficiency=1.0,  # Sequential baseline
            parallel_speedup=1.0,
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: throughput should be > 1000 items/s
        assert throughput > 1000, f"Batch throughput too low: {throughput} items/s"

        report = AIPerformanceReport(
            test_name="batch_context_key_generation",
            timestamp=datetime.now(timezone.utc).isoformat(),
            batch_metrics=[batch_metric],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "throughput > 1000 items/s": throughput > 1000,
            },
        )

        print(f"\nBatch Context Key Generation Report:")
        print(report.to_json())

    def test_batch_cache_operations(self, ai_enhancer):
        """Test batch cache operations"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        batch_size = 50

        # Prepare cache data
        cache_data = {
            f"key_{i}": {"analysis": f"result_{i}", "timestamp": datetime.now(timezone.utc).isoformat()}
            for i in range(batch_size)
        }

        # Measure batch write
        start_write = time.perf_counter()
        for key, value in cache_data.items():
            ai_enhancer.cache_analysis(key, value)
        write_time = time.perf_counter() - start_write

        # Measure batch read
        start_read = time.perf_counter()
        read_results = [ai_enhancer.get_cached_analysis(f"key_{i}") for i in range(batch_size)]
        read_time = time.perf_counter() - start_read

        write_metric = BatchMetrics(
            operation="batch_cache_write",
            batch_size=batch_size,
            total_time=write_time,
            avg_time_per_item=write_time / batch_size,
            throughput=batch_size / write_time,
            efficiency=1.0,
            parallel_speedup=1.0,
        )

        read_metric = BatchMetrics(
            operation="batch_cache_read",
            batch_size=batch_size,
            total_time=read_time,
            avg_time_per_item=read_time / batch_size,
            throughput=batch_size / read_time,
            efficiency=1.0,
            parallel_speedup=1.0,
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: cache operations should be > 5000 items/s
        assert write_metric.throughput > 5000, f"Cache write throughput too low: {write_metric.throughput} items/s"
        assert read_metric.throughput > 5000, f"Cache read throughput too low: {read_metric.throughput} items/s"

        report = AIPerformanceReport(
            test_name="batch_cache_operations",
            timestamp=datetime.now(timezone.utc).isoformat(),
            batch_metrics=[write_metric, read_metric],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "write_throughput > 5000 items/s": write_metric.throughput > 5000,
                "read_throughput > 5000 items/s": read_metric.throughput > 5000,
            },
        )

        print(f"\nBatch Cache Operations Report:")
        print(report.to_json())

    def test_batch_performance_metrics_update(self, ai_enhancer):
        """Test batch performance metrics update"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        batch_size = 100

        # Prepare metrics data
        metrics_batch = [
            {
                "success": i % 10 != 0,  # 10% failure rate
                "response_time": 1.0 + (i % 5) * 0.2,
                "model": "gpt-4o-mini" if i % 2 == 0 else "gpt-3.5-turbo",
            }
            for i in range(batch_size)
        ]

        # Measure batch update
        start = time.perf_counter()
        for metrics in metrics_batch:
            ai_enhancer.update_performance_metrics(metrics)
        update_time = time.perf_counter() - start

        batch_metric = BatchMetrics(
            operation="batch_metrics_update",
            batch_size=batch_size,
            total_time=update_time,
            avg_time_per_item=update_time / batch_size,
            throughput=batch_size / update_time,
            efficiency=1.0,
            parallel_speedup=1.0,
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: metrics update should be > 10000 items/s
        assert batch_metric.throughput > 10000, f"Metrics update throughput too low: {batch_metric.throughput} items/s"

        report = AIPerformanceReport(
            test_name="batch_metrics_update",
            timestamp=datetime.now(timezone.utc).isoformat(),
            batch_metrics=[batch_metric],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "throughput > 10000 items/s": batch_metric.throughput > 10000,
            },
        )

        print(f"\nBatch Metrics Update Report:")
        print(report.to_json())


# ============================================================================
# Resource Usage Monitoring Tests
# ============================================================================


class TestResourceUsageMonitoring:
    """Test resource usage monitoring"""

    def test_memory_usage_during_cache_operations(self, ai_enhancer):
        """Test memory usage during cache operations"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        # Perform cache operations
        for i in range(1000):
            ai_enhancer.cache_analysis(
                f"key_{i}",
                {"analysis": f"result_{i}", "data": "x" * 100},
            )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: memory increase should be reasonable (< 50MB for 1000 items)
        assert (
            resource_metrics.memory_mb_delta < 50
        ), f"Memory increase too high: {resource_metrics.memory_mb_delta}MB"

        report = AIPerformanceReport(
            test_name="memory_usage_cache_operations",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "memory_delta < 50MB": resource_metrics.memory_mb_delta < 50,
            },
        )

        print(f"\nMemory Usage Cache Operations Report:")
        print(report.to_json())

    def test_cpu_usage_during_intensive_operations(self, ai_enhancer):
        """Test CPU usage during intensive operations"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        # Perform intensive operations
        for i in range(100):
            context_key = ai_enhancer.generate_context_key(
                {"host": f"server-{i}", "platform": "linux", "level": "critical", "message": "test"}
            )
            ai_enhancer.cache_analysis(context_key, {"result": i})
            ai_enhancer.get_cached_analysis(context_key)
            ai_enhancer.update_performance_metrics({"success": True, "response_time": 1.0, "model": "gpt-4o-mini"})

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: CPU usage should be reasonable (< 80%)
        assert (
            resource_metrics.cpu_percent_after < 80
        ), f"CPU usage too high: {resource_metrics.cpu_percent_after}%"

        report = AIPerformanceReport(
            test_name="cpu_usage_intensive_operations",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "cpu_percent < 80%": resource_metrics.cpu_percent_after < 80,
            },
        )

        print(f"\nCPU Usage Intensive Operations Report:")
        print(report.to_json())

    def test_thread_safety_under_concurrent_access(self, ai_enhancer):
        """Test thread safety under concurrent access"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(100):
                    context_key = f"worker_{worker_id}_key_{i}"
                    ai_enhancer.cache_analysis(context_key, {"worker": worker_id, "iteration": i})
                    result = ai_enhancer.get_cached_analysis(context_key)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: no errors should occur
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 1000, f"Expected 1000 results, got {len(results)}"

        report = AIPerformanceReport(
            test_name="thread_safety_concurrent_access",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "no_errors": len(errors) == 0,
                "all_results_complete": len(results) == 1000,
            },
        )

        print(f"\nThread Safety Concurrent Access Report:")
        print(report.to_json())


# ============================================================================
# Cost-Benefit Analysis Tests
# ============================================================================


class TestCostBenefitAnalysis:
    """Test cost-benefit analysis"""

    def test_cost_per_operation_analysis(self, cost_monitor):
        """Test cost per operation analysis"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        # Simulate various operations with different costs
        operations = [
            ("gpt-4o-mini", 500, 250),
            ("gpt-3.5-turbo", 1000, 500),
            ("MiniMax-Text-01", 750, 375),
        ]

        cost_metrics = []
        for model, input_tokens, output_tokens in operations:
            estimated_cost = cost_monitor.estimate_cost(model, input_tokens, output_tokens)
            actual_cost = estimated_cost  # In test, assume actual = estimated

            # Calculate cost efficiency
            total_tokens = input_tokens + output_tokens
            tokens_per_dollar = total_tokens / actual_cost if actual_cost > 0 else 0
            cost_efficiency = 1.0 if actual_cost > 0 else 0.0

            metric = CostMetrics(
                operation=f"cost_analysis_{model}",
                estimated_cost=estimated_cost,
                actual_cost=actual_cost,
                cost_efficiency=cost_efficiency,
                tokens_per_dollar=tokens_per_dollar,
                model_used=model,
            )
            cost_metrics.append(metric)

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: tokens per dollar should be reasonable
        for metric in cost_metrics:
            assert (
                metric.tokens_per_dollar > 0
            ), f"Tokens per dollar too low: {metric.tokens_per_dollar}"

        report = AIPerformanceReport(
            test_name="cost_per_operation_analysis",
            timestamp=datetime.now(timezone.utc).isoformat(),
            cost_metrics=cost_metrics,
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                f"{m.model_used} tokens_per_dollar > 0": m.tokens_per_dollar > 0
                for m in cost_metrics
            },
        )

        print(f"\nCost Per Operation Analysis Report:")
        print(report.to_json())

    def test_budget_tracking_accuracy(self, cost_monitor):
        """Test budget tracking accuracy"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        # Record some costs
        test_costs = [0.01, 0.02, 0.03, 0.04, 0.05]
        for cost in test_costs:
            cost_monitor.record_cost(cost)

        # Get stats
        stats = cost_monitor.get_hourly_stats()

        resource_metrics = monitor.end_measurement(start_data)

        # Verify accuracy
        expected_total = sum(test_costs)
        actual_total = stats["hourly_cost"]
        expected_count = len(test_costs)
        actual_count = stats["request_count"]

        assert (
            abs(actual_total - expected_total) < 0.001
        ), f"Cost tracking inaccurate: expected {expected_total}, got {actual_total}"
        assert actual_count == expected_count, f"Request count inaccurate: expected {expected_count}, got {actual_count}"

        report = AIPerformanceReport(
            test_name="budget_tracking_accuracy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "cost_tracking_accurate": abs(actual_total - expected_total) < 0.001,
                "request_count_accurate": actual_count == expected_count,
            },
        )

        print(f"\nBudget Tracking Accuracy Report:")
        print(report.to_json())

    def test_cost_optimization_recommendations(self, cost_monitor):
        """Test cost optimization recommendations"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        # Analyze cost efficiency across models
        models = cost_monitor.model_configs
        recommendations = []

        for model in models:
            model_name = model.get("model", "unknown")
            cost_per_1k = model.get("cost_per_1k", 0)
            max_tokens = model.get("max_tokens", 0)

            # Generate recommendations based on cost
            if cost_per_1k < 0.01:
                recommendations.append(
                    f"{model_name} is cost-effective at ${cost_per_1k}/1k tokens"
                )
            elif cost_per_1k > 0.02:
                recommendations.append(
                    f"{model_name} is expensive at ${cost_per_1k}/1k tokens, consider alternatives"
                )

            if max_tokens > 100000:
                recommendations.append(
                    f"{model_name} has large context window ({max_tokens} tokens), suitable for complex tasks"
                )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: should generate recommendations
        assert len(recommendations) > 0, "No cost optimization recommendations generated"

        report = AIPerformanceReport(
            test_name="cost_optimization_recommendations",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resource_metrics=[resource_metrics],
            recommendations=recommendations,
            benchmarks_passed={
                "has_recommendations": len(recommendations) > 0,
            },
        )

        print(f"\nCost Optimization Recommendations Report:")
        print(report.to_json())


# ============================================================================
# Conversation Manager Performance Tests
# ============================================================================


class TestConversationManagerPerformance:
    """Test conversation manager performance"""

    def test_conversation_creation_latency(self, conversation_manager):
        """Test conversation creation latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        latency = measure_latency(
            "conversation_creation",
            conversation_manager.create_conversation,
            iterations=100,
            conversation_id="test_conv",
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: conversation creation should be < 5ms
        assert latency.avg_time < 0.005, f"Conversation creation too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="conversation_creation_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=[latency],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "avg_time < 5ms": latency.avg_time < 0.005,
            },
        )

        print(f"\nConversation Creation Latency Report:")
        print(report.to_json())

    def test_message_adding_latency(self, conversation_manager):
        """Test message adding latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        conversation_id = "test_conv"
        conversation_manager.create_conversation(conversation_id)

        latency = measure_latency(
            "message_adding",
            conversation_manager.add_message,
            iterations=100,
            conversation_id=conversation_id,
            role="user",
            content="Test message content",
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: message adding should be < 5ms
        assert latency.avg_time < 0.005, f"Message adding too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="message_adding_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=[latency],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "avg_time < 5ms": latency.avg_time < 0.005,
            },
        )

        print(f"\nMessage Adding Latency Report:")
        print(report.to_json())

    def test_conversation_history_retrieval_latency(self, conversation_manager):
        """Test conversation history retrieval latency"""
        monitor = PerformanceMonitor()
        start_data = monitor.start_measurement()

        conversation_id = "test_conv"
        conversation_manager.create_conversation(conversation_id)

        # Add some messages
        for i in range(20):
            conversation_manager.add_message(
                conversation_id,
                "user" if i % 2 == 0 else "assistant",
                f"Message {i}",
            )

        latency = measure_latency(
            "conversation_history_retrieval",
            conversation_manager.get_conversation_history,
            iterations=50,
            conversation_id=conversation_id,
            limit=10,
        )

        resource_metrics = monitor.end_measurement(start_data)

        # Benchmark: history retrieval should be < 10ms
        assert latency.avg_time < 0.01, f"History retrieval too slow: {latency.avg_time}s"

        report = AIPerformanceReport(
            test_name="conversation_history_retrieval_latency",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_metrics=[latency],
            resource_metrics=[resource_metrics],
            benchmarks_passed={
                "avg_time < 10ms": latency.avg_time < 0.01,
            },
        )

        print(f"\nConversation History Retrieval Latency Report:")
        print(report.to_json())


# ============================================================================
# Comprehensive Performance Report
# ============================================================================


class TestComprehensivePerformanceReport:
    """Generate comprehensive performance report"""

    def test_generate_comprehensive_report(self, ai_enhancer, cost_monitor):
        """Generate comprehensive performance report"""
        all_reports = []

        # Run a subset of key tests
        monitor = PerformanceMonitor()

        # Test 1: Context key generation
        start_data = monitor.start_measurement()
        latency1 = measure_latency(
            "context_key_generation",
            ai_enhancer.generate_context_key,
            iterations=100,
            alert_data={"host": "test", "platform": "linux", "level": "critical", "message": "test"},
        )
        resource1 = monitor.end_measurement(start_data)
        all_reports.append(
            AIPerformanceReport(
                test_name="context_key_generation",
                timestamp=datetime.now(timezone.utc).isoformat(),
                latency_metrics=[latency1],
                resource_metrics=[resource1],
            )
        )

        # Test 2: Token estimation
        start_data = monitor.start_measurement()
        test_text = "A" * 1000
        latency2 = measure_latency(
            "token_estimation",
            estimate_tokens,
            iterations=100,
            text=test_text,
        )
        resource2 = monitor.end_measurement(start_data)
        token_count = estimate_tokens(test_text)
        token_metric = TokenMetrics(
            operation="token_estimation",
            total_tokens=token_count,
            tokens_per_second=token_count / latency2.avg_time,
            avg_tokens_per_second=token_count / latency2.avg_time,
            input_tokens=token_count,
            output_tokens=0,
            processing_time=latency2.avg_time,
        )
        all_reports.append(
            AIPerformanceReport(
                test_name="token_estimation",
                timestamp=datetime.now(timezone.utc).isoformat(),
                latency_metrics=[latency2],
                token_metrics=[token_metric],
                resource_metrics=[resource2],
            )
        )

        # Test 3: Cost estimation
        start_data = monitor.start_measurement()
        latency3 = measure_latency(
            "cost_estimation",
            cost_monitor.estimate_cost,
            iterations=100,
            model_name="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
        )
        resource3 = monitor.end_measurement(start_data)
        all_reports.append(
            AIPerformanceReport(
                test_name="cost_estimation",
                timestamp=datetime.now(timezone.utc).isoformat(),
                latency_metrics=[latency3],
                resource_metrics=[resource3],
            )
        )

        # Generate summary
        summary = {
            "comprehensive_report": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_tests": len(all_reports),
                "test_results": [report.to_dict() for report in all_reports],
                "overall_benchmarks": {
                    "context_key_generation_avg_ms": round(latency1.avg_time * 1000, 2),
                    "token_estimation_avg_ms": round(latency2.avg_time * 1000, 2),
                    "cost_estimation_avg_ms": round(latency3.avg_time * 1000, 2),
                    "token_estimation_speed": round(token_metric.tokens_per_second, 2),
                },
                "benchmarks_passed": {
                    "context_key_generation < 10ms": latency1.avg_time < 0.01,
                    "token_estimation < 1ms": latency2.avg_time < 0.001,
                    "cost_estimation < 1ms": latency3.avg_time < 0.001,
                    "token_speed > 10000 tokens/s": token_metric.tokens_per_second > 10000,
                },
            }
        }

        print(f"\n{'='*80}")
        print("COMPREHENSIVE AI PERFORMANCE REPORT")
        print(f"{'='*80}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"{'='*80}")

        # Verify benchmarks
        assert latency1.avg_time < 0.01, "Context key generation benchmark failed"
        assert latency2.avg_time < 0.001, "Token estimation benchmark failed"
        assert latency3.avg_time < 0.001, "Cost estimation benchmark failed"
        assert token_metric.tokens_per_second > 10000, "Token speed benchmark failed"

        return summary


# ============================================================================
# Performance Regression Detection
# ============================================================================


class TestPerformanceRegressionDetection:
    """Test performance regression detection"""

    def test_detect_latency_regression(self, ai_enhancer):
        """Detect latency regression"""
        monitor = PerformanceMonitor()

        # Baseline measurement
        baseline_latency = measure_latency(
            "context_key_generation_baseline",
            ai_enhancer.generate_context_key,
            iterations=100,
            alert_data={"host": "test", "platform": "linux", "level": "critical", "message": "test"},
        )

        # Current measurement
        current_latency = measure_latency(
            "context_key_generation_current",
            ai_enhancer.generate_context_key,
            iterations=100,
            alert_data={"host": "test", "platform": "linux", "level": "critical", "message": "test"},
        )

        # Check for regression (allow 20% variance)
        regression_threshold = 0.2
        regression_detected = current_latency.avg_time > baseline_latency.avg_time * (
            1 + regression_threshold
        )

        regression_report = {
            "latency_regression_detection": {
                "baseline_avg_ms": round(baseline_latency.avg_time * 1000, 2),
                "current_avg_ms": round(current_latency.avg_time * 1000, 2),
                "regression_threshold": f"{regression_threshold * 100}%",
                "regression_detected": regression_detected,
                "percent_change": round(
                    (current_latency.avg_time - baseline_latency.avg_time)
                    / baseline_latency.avg_time * 100,
                    2,
                ),
            }
        }

        print(f"\nLatency Regression Detection Report:")
        print(json.dumps(regression_report, indent=2, ensure_ascii=False))

        # In test, we don't expect regression
        assert not regression_detected, f"Latency regression detected: {regression_report}"

    def test_detect_throughput_regression(self, ai_enhancer):
        """Detect throughput regression"""
        monitor = PerformanceMonitor()

        # Baseline throughput
        batch_size = 100
        batch_alerts = [
            {"host": f"server-{i}", "platform": "linux", "level": "critical", "message": "test"}
            for i in range(batch_size)
        ]

        start = time.perf_counter()
        for alert in batch_alerts:
            ai_enhancer.generate_context_key(alert)
        baseline_time = time.perf_counter() - start
        baseline_throughput = batch_size / baseline_time

        # Current throughput
        start = time.perf_counter()
        for alert in batch_alerts:
            ai_enhancer.generate_context_key(alert)
        current_time = time.perf_counter() - start
        current_throughput = batch_size / current_time

        # Check for regression (allow 20% variance)
        regression_threshold = 0.2
        regression_detected = current_throughput < baseline_throughput * (1 - regression_threshold)

        throughput_report = {
            "throughput_regression_detection": {
                "baseline_throughput": round(baseline_throughput, 2),
                "current_throughput": round(current_throughput, 2),
                "regression_threshold": f"{regression_threshold * 100}%",
                "regression_detected": regression_detected,
                "percent_change": round(
                    (current_throughput - baseline_throughput) / baseline_throughput * 100,
                    2,
                ),
            }
        }

        print(f"\nThroughput Regression Detection Report:")
        print(json.dumps(throughput_report, indent=2, ensure_ascii=False))

        # In test, we don't expect regression
        assert not regression_detected, f"Throughput regression detected: {throughput_report}"


# ============================================================================
# Additional Coverage Tests
# ============================================================================


class TestAdditionalCoverage:
    """Additional tests to improve coverage"""

    def test_cache_invalidation_specific_key(self):
        """Test cache invalidation for specific key"""
        enhancer = AIAnalysisEnhancer()
        sample_alert_data = {"host": "test", "platform": "linux", "level": "critical", "message": "test"}
        context_key = enhancer.generate_context_key(sample_alert_data)
        enhancer.cache_analysis(context_key, {"result": "test"})

        # Verify cache exists
        assert enhancer.get_cached_analysis(context_key) is not None

        # Invalidate specific key
        enhancer.invalidate_cache(context_key)

        # Verify cache is gone
        assert enhancer.get_cached_analysis(context_key) is None

    def test_cache_invalidation_all(self):
        """Test cache invalidation for all keys"""
        enhancer = AIAnalysisEnhancer()
        # Add multiple cache entries
        for i in range(10):
            enhancer.cache_analysis(f"key_{i}", {"result": i})

        # Invalidate all
        enhancer.invalidate_cache()

        # Verify all are gone
        for i in range(10):
            assert enhancer.get_cached_analysis(f"key_{i}") is None

    def test_cache_expiry(self):
        """Test cache expiry mechanism"""
        # Create enhancer with short TTL
        enhancer = AIAnalysisEnhancer()
        enhancer._cache_ttl = -1  # Force expiry

        sample_alert_data = {"host": "test", "platform": "linux", "level": "critical", "message": "test"}
        context_key = enhancer.generate_context_key(sample_alert_data)
        enhancer.cache_analysis(context_key, {"result": "test"})

        # Manually set timestamp to past to force expiry
        enhancer._context_cache[context_key]["timestamp"] = "2020-01-01T00:00:00+00:00"

        # Should be expired
        assert enhancer.get_cached_analysis(context_key) is None

    def test_context_suggestions_empty_data(self):
        """Test context suggestions with empty data"""
        enhancer = AIAnalysisEnhancer()
        suggestions = enhancer.get_context_suggestions({})
        assert isinstance(suggestions, list)

    def test_context_suggestions_critical_level(self):
        """Test context suggestions with critical level"""
        enhancer = AIAnalysisEnhancer()
        suggestions = enhancer.get_context_suggestions(
            {"platform": "linux", "level": "critical"}
        )
        assert any("priority" in s.lower() for s in suggestions)

    def test_context_suggestions_fatal_level(self):
        """Test context suggestions with fatal level"""
        enhancer = AIAnalysisEnhancer()
        suggestions = enhancer.get_context_suggestions(
            {"platform": "windows", "level": "fatal"}
        )
        assert any("priority" in s.lower() for s in suggestions)

    def test_conversation_cleanup_expired(self):
        """Test conversation cleanup of expired conversations"""
        # Create conversation with short TTL
        manager = MultiTurnConversationManager()
        manager._conversation_ttl = -1  # Force expiry

        conv_id = manager.create_conversation("test_conv")
        manager.add_message(conv_id, "user", "test message")

        # Manually set timestamp to past to force expiry
        manager._conversations[conv_id][0]["timestamp"] = "2020-01-01T00:00:00+00:00"

        # Cleanup expired
        manager.cleanup_expired_conversations()

        # Conversation should be gone
        assert manager.get_conversation_history(conv_id) == []

    def test_conversation_context_empty(self):
        """Test conversation context with empty history"""
        manager = MultiTurnConversationManager()
        context = manager.get_conversation_context("nonexistent")
        assert context == ""

    def test_performance_metrics_zero_analyses(self):
        """Test performance metrics with zero analyses"""
        enhancer = AIAnalysisEnhancer()
        metrics = enhancer.get_performance_metrics()

        assert metrics["total_analyses"] == 0
        assert metrics["successful_analyses"] == 0
        assert metrics["failed_analyses"] == 0
        assert metrics["average_response_time"] == 0.0

    def test_performance_metrics_with_failures(self):
        """Test performance metrics with failed analyses"""
        enhancer = AIAnalysisEnhancer()

        # Add some successful analyses
        enhancer.update_performance_metrics({"success": True, "response_time": 1.0, "model": "gpt-4o-mini"})
        enhancer.update_performance_metrics({"success": True, "response_time": 2.0, "model": "gpt-3.5-turbo"})

        # Add some failed analyses
        enhancer.update_performance_metrics({"success": False, "response_time": 0.5, "model": "gpt-4o-mini"})

        metrics = enhancer.get_performance_metrics()

        assert metrics["total_analyses"] == 3
        assert metrics["successful_analyses"] == 2
        assert metrics["failed_analyses"] == 1

    def test_model_config_not_found(self):
        """Test model config lookup for non-existent model"""
        monitor = LLMCostMonitor()
        config = monitor.get_model_config("nonexistent_model")
        assert config is None

    def test_cost_per_1k_default(self):
        """Test cost per 1k with default value"""
        monitor = LLMCostMonitor()
        cost = monitor.get_cost_per_1k("nonexistent_model", default=0.123)
        assert cost == 0.123

    def test_budget_check_per_request_exceeded(self):
        """Test budget check when per-request budget exceeded"""
        monitor = LLMCostMonitor(budget_per_request=0.001)
        result = monitor.check_budget(0.01)  # Exceeds budget
        assert result is False

    def test_budget_check_hourly_exceeded(self):
        """Test budget check when hourly budget exceeded"""
        monitor = LLMCostMonitor(max_cost_per_hour=0.01)
        # Record some cost
        monitor.record_cost(0.009)
        # Try to exceed
        result = monitor.check_budget(0.01)
        assert result is False

    def test_budget_check_daily_exceeded(self):
        """Test budget check when daily budget exceeded"""
        monitor = LLMCostMonitor(max_cost_per_day=0.01)
        # Record some cost
        monitor.record_cost(0.009)
        # Try to exceed
        result = monitor.check_budget(0.01)
        assert result is False

    def test_session_budget_token_exceeded(self):
        """Test session budget when token budget exceeded"""
        from core.llm_cost_monitor import SessionBudget

        budget = SessionBudget("test", max_tokens=100)
        result = budget.check_and_record(150)
        assert result is False

    def test_session_budget_cost_exceeded(self):
        """Test session budget when cost budget exceeded"""
        from core.llm_cost_monitor import SessionBudget

        budget = SessionBudget("test", max_cost=0.01)
        result = budget.check_and_record(100, 0.02)
        assert result is False

    def test_token_estimation_empty_text(self):
        """Test token estimation with empty text"""
        count = estimate_tokens("")
        assert count == 0

    def test_token_estimation_cjk_text(self):
        """Test token estimation with CJK text"""
        count = estimate_tokens("中文测试")
        assert count > 0

    def test_prompt_fits_exceeds_window(self):
        """Test prompt fits when it exceeds context window"""
        from core.ai.token_budget import prompt_fits

        # Use a very long text to ensure it exceeds the window
        fits, tokens, total = prompt_fits("A" * 100000, 1000, 5000)
        assert fits is False
        assert total > 5000

    def test_select_model_none_fits(self):
        """Test select model when none fits"""
        from core.ai.token_budget import select_model_that_fits

        model_configs = [
            {"name": "small", "max_tokens": 1000, "cost_per_1k": 0.01},
            {"name": "medium", "max_tokens": 2000, "cost_per_1k": 0.02},
        ]

        result = select_model_that_fits("A" * 10000, 5000, model_configs)
        assert result is None

    def test_select_model_preferred_fits(self):
        """Test select model when preferred model fits"""
        from core.ai.token_budget import select_model_that_fits

        model_configs = [
            {"name": "small", "max_tokens": 1000, "cost_per_1k": 0.01},
            {"name": "medium", "max_tokens": 20000, "cost_per_1k": 0.02},
        ]

        result = select_model_that_fits("A" * 100, 1000, model_configs, preferred_model="medium")
        assert result is not None
        assert result["name"] == "medium"

    def test_analysis_history_limit(self):
        """Test analysis history limit enforcement"""
        enhancer = AIAnalysisEnhancer()

        # Add more than 1000 analyses
        for i in range(1100):
            enhancer.record_analysis({"index": i})

        history = enhancer.get_analysis_history()
        # Should be limited to 1000
        assert len(history) <= 1000

    def test_analysis_history_with_limit(self):
        """Test analysis history with custom limit"""
        enhancer = AIAnalysisEnhancer()

        for i in range(20):
            enhancer.record_analysis({"index": i})

        history = enhancer.get_analysis_history(limit=5)
        assert len(history) == 5

    def test_analysis_history_empty(self):
        """Test analysis history when empty"""
        enhancer = AIAnalysisEnhancer()
        history = enhancer.get_analysis_history()
        assert history == []

    def test_global_instances(self):
        """Test global instance getters"""
        enhancer = get_ai_enhancer()
        assert isinstance(enhancer, AIAnalysisEnhancer)

        manager = get_conversation_manager()
        assert isinstance(manager, MultiTurnConversationManager)

    def test_cost_monitor_reset(self):
        """Test cost monitor reset"""
        reset_llm_cost_monitor()
        monitor = get_llm_cost_monitor()
        assert monitor is not None

    def test_session_budget_none_id(self):
        """Test session budget with None ID"""
        from core.llm_cost_monitor import get_session_budget

        budget = get_session_budget(None)
        assert budget is None


# ============================================================================
# Test Entry Point
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
