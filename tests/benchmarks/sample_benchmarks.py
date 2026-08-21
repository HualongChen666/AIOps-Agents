# -*- coding: utf-8 -*-
"""
Sample Performance Benchmark Tests
===================================

Example performance benchmarks demonstrating the framework usage with real operations.
"""

import asyncio
import time
from typing import Any

from tests.benchmarks.benchmark_base import BenchmarkBase, PerformanceMetricType
from tests.benchmarks.performance_utils import WarmupExecutor


class SimpleComputationBenchmark(BenchmarkBase):
    """Benchmark for simple computational operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for computational operations"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.001,
            good=0.01,
            acceptable=0.1,
            warning=0.5,
            critical=1.0,
            unit="seconds"
        )
        self.add_threshold(
            PerformanceMetricType.CPU_USAGE,
            excellent=10.0,
            good=30.0,
            acceptable=50.0,
            warning=70.0,
            critical=90.0,
            unit="percent"
        )
    
    async def run_workload(self) -> Any:
        """Execute simple computational workload"""
        # Simulate CPU-intensive computation
        result = 0
        for i in range(10000):
            result += i * i
        return result


class DataProcessingBenchmark(BenchmarkBase):
    """Benchmark for data processing operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for data processing"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.01,
            good=0.1,
            acceptable=0.5,
            warning=1.0,
            critical=2.0,
            unit="seconds"
        )
        self.add_threshold(
            PerformanceMetricType.MEMORY_USAGE,
            excellent=20.0,
            good=40.0,
            acceptable=60.0,
            warning=80.0,
            critical=95.0,
            unit="percent"
        )
    
    async def run_workload(self) -> Any:
        """Execute data processing workload"""
        # Simulate data processing
        data = list(range(10000))
        
        # Process data
        processed = []
        for item in data:
            processed.append(item * 2)
        
        # Sort data
        processed.sort()
        
        return len(processed)


class AsyncIobenchmark(BenchmarkBase):
    """Benchmark for async I/O operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for async I/O"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.01,
            good=0.05,
            acceptable=0.1,
            warning=0.5,
            critical=1.0,
            unit="seconds"
        )
        self.add_threshold(
            PerformanceMetricType.THROUGHPUT,
            excellent=1000.0,
            good=500.0,
            acceptable=100.0,
            warning=50.0,
            critical=10.0,
            unit="ops_per_second"
        )
    
    async def run_workload(self) -> Any:
        """Execute async I/O workload"""
        # Simulate async I/O operations
        await asyncio.sleep(0.001)
        
        # Simulate multiple async operations
        tasks = [asyncio.sleep(0.001) for _ in range(10)]
        await asyncio.gather(*tasks)
        
        return "completed"


class MemoryAllocationBenchmark(BenchmarkBase):
    """Benchmark for memory allocation operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for memory operations"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.01,
            good=0.1,
            acceptable=0.5,
            warning=1.0,
            critical=2.0,
            unit="seconds"
        )
        self.add_threshold(
            PerformanceMetricType.MEMORY_USAGE,
            excellent=10.0,
            good=30.0,
            acceptable=50.0,
            warning=70.0,
            critical=90.0,
            unit="percent"
        )
    
    async def run_workload(self) -> Any:
        """Execute memory allocation workload"""
        # Simulate memory allocation
        data = []
        for i in range(1000):
            # Allocate memory
            chunk = [0] * 1000
            data.append(chunk)
        
        # Clean up
        data.clear()
        
        return len(data)


class DatabaseQueryBenchmark(BenchmarkBase):
    """Benchmark for database-like query operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for database operations"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.01,
            good=0.05,
            acceptable=0.1,
            warning=0.5,
            critical=1.0,
            unit="seconds"
        )
        self.add_threshold(
            PerformanceMetricType.THROUGHPUT,
            excellent=100.0,
            good=50.0,
            acceptable=20.0,
            warning=10.0,
            critical=5.0,
            unit="ops_per_second"
        )
    
    async def run_workload(self) -> Any:
        """Execute database query simulation"""
        # Simulate database query
        mock_data = {
            "user_1": {"name": "Alice", "age": 30},
            "user_2": {"name": "Bob", "age": 25},
            "user_3": {"name": "Charlie", "age": 35}
        }
        
        # Simulate query processing
        results = []
        for user_id, user_data in mock_data.items():
            if user_data["age"] > 25:
                results.append(user_data)
        
        await asyncio.sleep(0.001)  # Simulate I/O delay
        
        return results


class NetworkRequestBenchmark(BenchmarkBase):
    """Benchmark for network request operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for network operations"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.05,
            good=0.1,
            acceptable=0.5,
            warning=1.0,
            critical=2.0,
            unit="seconds"
        )
        self.add_threshold(
            PerformanceMetricType.ERROR_RATE,
            excellent=0.0,
            good=0.1,
            acceptable=1.0,
            warning=5.0,
            critical=10.0,
            unit="percent"
        )
    
    async def run_workload(self) -> Any:
        """Execute network request simulation"""
        # Simulate network request
        await asyncio.sleep(0.01)  # Simulate network latency
        
        # Simulate response processing
        response_data = {"status": "success", "data": [1, 2, 3, 4, 5]}
        
        # Process response
        processed = sum(response_data["data"])
        
        return processed


class CacheOperationBenchmark(BenchmarkBase):
    """Benchmark for cache operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for cache operations"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.0001,
            good=0.001,
            acceptable=0.01,
            warning=0.1,
            critical=0.5,
            unit="seconds"
        )
        self.add_threshold(
            PerformanceMetricType.THROUGHPUT,
            excellent=10000.0,
            good=5000.0,
            acceptable=1000.0,
            warning=500.0,
            critical=100.0,
            unit="ops_per_second"
        )
    
    def __init__(self, name: str = "cache_operations", config: Any = None):
        """Initialize cache benchmark with mock cache"""
        super().__init__(name, config)
        self.cache = {}
    
    async def run_workload(self) -> Any:
        """Execute cache operations"""
        # Simulate cache write
        for i in range(100):
            self.cache[f"key_{i}"] = f"value_{i}"
        
        # Simulate cache read
        values = []
        for i in range(100):
            value = self.cache.get(f"key_{i}")
            if value:
                values.append(value)
        
        return len(values)


class JsonProcessingBenchmark(BenchmarkBase):
    """Benchmark for JSON processing operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for JSON operations"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.001,
            good=0.01,
            acceptable=0.1,
            warning=0.5,
            critical=1.0,
            unit="seconds"
        )
    
    async def run_workload(self) -> Any:
        """Execute JSON processing workload"""
        import json
        
        # Simulate JSON serialization
        data = {
            "users": [
                {"id": i, "name": f"user_{i}", "email": f"user_{i}@example.com"}
                for i in range(100)
            ]
        }
        
        # Serialize
        json_str = json.dumps(data)
        
        # Deserialize
        parsed = json.loads(json_str)
        
        return len(parsed["users"])


class StringProcessingBenchmark(BenchmarkBase):
    """Benchmark for string processing operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for string operations"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.001,
            good=0.01,
            acceptable=0.1,
            warning=0.5,
            critical=1.0,
            unit="seconds"
        )
    
    async def run_workload(self) -> Any:
        """Execute string processing workload"""
        # Generate test string
        text = " ".join([f"word_{i}" for i in range(1000)])
        
        # Process string
        words = text.split()
        upper_words = [word.upper() for word in words]
        filtered = [word for word in upper_words if len(word) > 5]
        
        return len(filtered)


class ListOperationsBenchmark(BenchmarkBase):
    """Benchmark for list operations"""
    
    def _setup_thresholds(self):
        """Setup performance thresholds for list operations"""
        self.add_threshold(
            PerformanceMetricType.RESPONSE_TIME,
            excellent=0.001,
            good=0.01,
            acceptable=0.1,
            warning=0.5,
            critical=1.0,
            unit="seconds"
        )
    
    async def run_workload(self) -> Any:
        """Execute list operations workload"""
        # Create list
        data = list(range(10000))
        
        # Filter
        filtered = [x for x in data if x % 2 == 0]
        
        # Map
        mapped = [x * 2 for x in filtered]
        
        # Reduce
        total = sum(mapped)
        
        return total


async def run_sample_benchmarks():
    """Run all sample benchmarks and generate reports"""
    import tempfile
    from pathlib import Path
    
    benchmarks = [
        SimpleComputationBenchmark("simple_computation"),
        DataProcessingBenchmark("data_processing"),
        AsyncIobenchmark("async_io"),
        MemoryAllocationBenchmark("memory_allocation"),
        DatabaseQueryBenchmark("database_query"),
        NetworkRequestBenchmark("network_request"),
        CacheOperationBenchmark("cache_operations"),
        JsonProcessingBenchmark("json_processing"),
        StringProcessingBenchmark("string_processing"),
        ListOperationsBenchmark("list_operations")
    ]
    
    # Create output directory
    output_dir = Path(tempfile.gettempdir()) / "benchmark_reports"
    output_dir.mkdir(exist_ok=True)
    
    results = []
    
    for benchmark in benchmarks:
        print(f"\nRunning benchmark: {benchmark.name}")
        
        # Run with warmup
        warmup = WarmupExecutor(warmup_iterations=2)
        await warmup.execute_async(benchmark.run_workload)
        
        # Execute benchmark
        result = await benchmark.execute(iterations=5)
        results.append(result)
        
        # Generate and save report
        report_path = output_dir / f"{benchmark.name}_report.json"
        benchmark.generate_report(result, report_path, format="json")
        
        text_report_path = output_dir / f"{benchmark.name}_report.txt"
        benchmark.generate_report(result, text_report_path, format="text")
        
        print(f"  Duration: {result.duration:.4f}s")
        print(f"  Samples: {result.sample_count}")
        print(f"  Report saved to: {report_path}")
    
    # Run concurrent benchmarks
    print("\n" + "="*80)
    print("Running concurrent benchmarks")
    print("="*80)
    
    for benchmark in benchmarks[:3]:  # Run first 3 with concurrency
        print(f"\nRunning concurrent benchmark: {benchmark.name}")
        
        result = await benchmark.execute_concurrent(concurrency=10, total_requests=50)
        
        report_path = output_dir / f"{benchmark.name}_concurrent_report.json"
        benchmark.generate_report(result, report_path, format="json")
        
        print(f"  Duration: {result.duration:.4f}s")
        print(f"  Throughput: {result.metadata.get('throughput', 'N/A')}")
        print(f"  Report saved to: {report_path}")
    
    print(f"\nAll reports saved to: {output_dir}")
    return results


if __name__ == "__main__":
    # Run sample benchmarks
    asyncio.run(run_sample_benchmarks())
