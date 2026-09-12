# -*- coding: utf-8 -*-
"""
Performance Integration Testing (Phase 5)
Enterprise-grade performance integration testing system
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class PerformanceTestType(Enum):
    """Performance test type"""

    LOAD_TEST = "load_test"
    STRESS_TEST = "stress_test"
    SPIKE_TEST = "spike_test"
    ENDURANCE_TEST = "endurance_test"
    SCALABILITY_TEST = "scalability_test"


class PerformanceMetric(Enum):
    """Performance metric"""

    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    CONCURRENT_USERS = "concurrent_users"


@dataclass
class PerformanceTest:
    """Performance test configuration"""

    test_id: str
    test_name: str
    test_type: PerformanceTestType
    target_endpoint: str
    duration: int = 300
    target_users: int = 100
    ramp_up_time: int = 60
    metrics: List[PerformanceMetric] = field(default_factory=list)
    thresholds: Dict[str, float] = field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceTestExecution:
    """Performance test execution"""

    execution_id: str
    test_id: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0
    results: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, List[float]] = field(default_factory=dict)
    passed: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceIntegrationTester:
    """Enterprise-grade performance integration tester"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize performance integration tester

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Performance tests
        self.performance_tests: Dict[str, PerformanceTest] = {}
        self._initialize_default_tests()

        # Test executions
        self.test_executions: Dict[str, PerformanceTestExecution] = {}

        # Performance reports
        self.performance_reports: Dict[str, Dict[str, Any]] = {}

        # Report storage
        self.reports_dir = Path(self.config.get("reports_dir", "./performance_reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.total_executions = 0
        self.passed_tests = 0
        self.failed_tests = 0

        logger.info("Performance integration tester initialized")

    def _initialize_default_tests(self):
        """Initialize default performance tests"""
        # Load test
        self.performance_tests["load_test_api"] = PerformanceTest(
            test_id="load_test_api",
            test_name="API Load Test",
            test_type=PerformanceTestType.LOAD_TEST,
            target_endpoint="/api/v1/analysis",
            duration=300,
            target_users=100,
            ramp_up_time=60,
            metrics=[
                PerformanceMetric.RESPONSE_TIME,
                PerformanceMetric.THROUGHPUT,
                PerformanceMetric.ERROR_RATE,
            ],
            thresholds={"response_time_p95": 500.0, "error_rate": 1.0},
            enabled=True,
        )

        # Stress test
        self.performance_tests["stress_test_api"] = PerformanceTest(
            test_id="stress_test_api",
            test_name="API Stress Test",
            test_type=PerformanceTestType.STRESS_TEST,
            target_endpoint="/api/v1/analysis",
            duration=600,
            target_users=500,
            ramp_up_time=120,
            metrics=[
                PerformanceMetric.RESPONSE_TIME,
                PerformanceMetric.THROUGHPUT,
                PerformanceMetric.ERROR_RATE,
                PerformanceMetric.CPU_USAGE,
            ],
            thresholds={"response_time_p99": 1000.0, "error_rate": 5.0},
            enabled=True,
        )

        # Spike test
        self.performance_tests["spike_test_api"] = PerformanceTest(
            test_id="spike_test_api",
            test_name="API Spike Test",
            test_type=PerformanceTestType.SPIKE_TEST,
            target_endpoint="/api/v1/analysis",
            duration=300,
            target_users=200,
            ramp_up_time=30,
            metrics=[
                PerformanceMetric.RESPONSE_TIME,
                PerformanceMetric.THROUGHPUT,
                PerformanceMetric.ERROR_RATE,
            ],
            thresholds={"response_time_p95": 800.0, "error_rate": 3.0},
            enabled=True,
        )

        # Scalability test
        self.performance_tests["scalability_test"] = PerformanceTest(
            test_id="scalability_test",
            test_name="Scalability Test",
            test_type=PerformanceTestType.SCALABILITY_TEST,
            target_endpoint="/api/v1/analysis",
            duration=600,
            target_users=1000,
            ramp_up_time=300,
            metrics=[
                PerformanceMetric.THROUGHPUT,
                PerformanceMetric.RESPONSE_TIME,
                PerformanceMetric.CPU_USAGE,
                PerformanceMetric.MEMORY_USAGE,
            ],
            thresholds={"throughput_per_user": 10.0, "response_time_p95": 1000.0},
            enabled=True,
        )

        logger.info(f"Initialized {len(self.performance_tests)} default performance tests")

    def register_test(self, test: PerformanceTest) -> None:
        """
        Register performance test

        Args:
            test: Performance test
        """
        self.performance_tests[test.test_id] = test
        logger.info(f"Registered performance test: {test.test_id}")

    async def run_performance_test(self, test_id: str) -> str:
        """
        Run performance test

        Args:
            test_id: Test ID

        Returns:
            Execution ID
        """
        if test_id not in self.performance_tests:
            raise ValueError(f"Test not found: {test_id}")

        test = self.performance_tests[test_id]

        if not test.enabled:
            raise ValueError(f"Test is not enabled: {test_id}")

        # Create execution instance
        execution_id = f"exec_{test_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        execution = PerformanceTestExecution(
            execution_id=execution_id, test_id=test_id, status="pending"
        )

        self.test_executions[execution_id] = execution
        self.total_executions += 1

        logger.info(f"Starting performance test: {test_id}")

        # Execute test asynchronously
        asyncio.create_task(self._execute_performance_test(execution_id))

        return execution_id

    async def _execute_performance_test(self, execution_id: str) -> None:
        """
        Execute performance test

        对 ``test.target_endpoint`` 发起**真实**负载（httpx，支持网络 base_url 或
        进程内 ASGI app），测量真实响应时间分位/吞吐/错误率，并按阈值判定通过与否。
        目标未配置或请求异常时如实报 error，绝不伪造指标。

        Args:
            execution_id: Execution ID
        """
        if execution_id not in self.test_executions:
            return

        execution = self.test_executions[execution_id]
        test = self.performance_tests.get(execution.test_id)

        if test is None:
            execution.status = "error"
            execution.error_message = f"Performance test not found: {execution.test_id}"
            execution.completed_at = datetime.now(timezone.utc)
            self.failed_tests += 1
            return

        try:
            execution.status = "running"
            execution.started_at = datetime.now(timezone.utc)

            outcome = await self._run_load(test)

            execution.metrics = outcome["metrics"]
            execution.results = outcome["results"]
            execution.passed = outcome["passed"]
            execution.status = "completed"

            if outcome["passed"]:
                self.passed_tests += 1
            else:
                self.failed_tests += 1
                execution.error_message = "Performance thresholds not met"

            logger.info(
                f"Performance test completed: {execution_id}, passed: {outcome['passed']}"
            )

        except Exception as e:
            execution.status = "error"
            execution.error_message = str(e)
            self.failed_tests += 1
            logger.error(f"Performance test failed: {execution_id}, error: {e}")
        finally:
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at is not None:
                execution.duration = (execution.completed_at - execution.started_at).total_seconds()

    @staticmethod
    def _percentile(sorted_values: List[float], pct: float) -> float:
        """线性插值百分位。"""
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * pct
        floor_idx = int(k)
        ceil_idx = min(floor_idx + 1, len(sorted_values) - 1)
        if floor_idx == ceil_idx:
            return sorted_values[floor_idx]
        return sorted_values[floor_idx] + (sorted_values[ceil_idx] - sorted_values[floor_idx]) * (
            k - floor_idx
        )

    def _build_load_client(self):
        """构造真实 httpx 客户端：优先进程内 ASGI app，其次网络 base_url。"""
        import httpx

        app = self.config.get("app")
        if app is None and self.config.get("asgi_app"):
            module_name, _, attr = str(self.config["asgi_app"]).partition(":")
            module = __import__(module_name, fromlist=[attr or "app"])
            app = getattr(module, attr or "app")

        if app is not None:
            return httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url=self.config.get("base_url", "http://testserver"),
                timeout=self.config.get("timeout", 30.0),
            )

        base_url = self.config.get("base_url") or self.config.get("target_base_url")
        if not base_url:
            raise RuntimeError(
                "no performance target configured; set config['base_url'] or config['app']"
            )
        return httpx.AsyncClient(base_url=base_url, timeout=self.config.get("timeout", 30.0))

    async def _run_load(self, test: PerformanceTest) -> Dict[str, Any]:
        """对目标发起真实负载并返回真实统计与阈值判定。"""
        import time

        import httpx

        requests_count = int(
            test.metadata.get("requests", self.config.get("requests_per_test", 40))
        )
        concurrency = int(
            test.metadata.get("concurrency", self.config.get("concurrency", 10))
        )
        method = str(test.metadata.get("method", "GET")).upper()
        concurrency = max(1, min(concurrency, requests_count))

        latencies: List[float] = []
        errors = 0
        semaphore = asyncio.Semaphore(concurrency)

        # 真实资源占用采样（如指标含 CPU/内存）
        cpu_samples: List[float] = []
        mem_samples: List[float] = []
        try:
            import psutil

            proc = psutil.Process()
            psutil_available = True
        except Exception:  # noqa: BLE001 - psutil 缺失时跳过资源采样
            psutil_available = False

        start = time.perf_counter()
        async with self._build_load_client() as client:

            async def _one() -> None:
                nonlocal errors
                async with semaphore:
                    req_start = time.perf_counter()
                    try:
                        response = await client.request(method, test.target_endpoint)
                        latency_ms = (time.perf_counter() - req_start) * 1000.0
                        latencies.append(latency_ms)
                        if response.status_code >= 400:
                            errors += 1
                    except httpx.HTTPError:
                        errors += 1
                        latencies.append((time.perf_counter() - req_start) * 1000.0)
                    if psutil_available:
                        cpu_samples.append(proc.cpu_percent(interval=None))
                        mem_samples.append(proc.memory_info().rss / (1024 * 1024))

            await asyncio.gather(*(_one() for _ in range(requests_count)))

        elapsed = max(time.perf_counter() - start, 1e-9)
        latencies.sort()
        p50 = self._percentile(latencies, 0.50)
        p95 = self._percentile(latencies, 0.95)
        p99 = self._percentile(latencies, 0.99)
        avg = sum(latencies) / len(latencies) if latencies else 0.0
        throughput = requests_count / elapsed
        error_rate = (errors / requests_count * 100.0) if requests_count else 0.0

        results: Dict[str, Any] = {
            "response_time_p50": round(p50, 3),
            "response_time_p95": round(p95, 3),
            "response_time_p99": round(p99, 3),
            "avg_response_time": round(avg, 3),
            "avg_throughput": round(throughput, 2),
            "avg_error_rate": round(error_rate, 3),
            "target_users": test.target_users,
            "actual_users": requests_count,
            "requests": requests_count,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 3),
        }

        metrics: Dict[str, List[float]] = {
            "response_time": latencies,
            "throughput": [round(throughput, 2)],
            "error_rate": [round(error_rate, 3)],
        }
        if psutil_available and cpu_samples:
            results["avg_cpu_usage"] = round(sum(cpu_samples) / len(cpu_samples), 2)
            results["avg_memory_usage"] = round(sum(mem_samples) / len(mem_samples), 2)
            metrics["cpu_usage"] = cpu_samples
            metrics["memory_usage"] = mem_samples

        passed = True
        thresholds = test.thresholds or {}
        if "response_time_p95" in thresholds and p95 > thresholds["response_time_p95"]:
            passed = False
        if "response_time_p99" in thresholds and p99 > thresholds["response_time_p99"]:
            passed = False
        if "error_rate" in thresholds and error_rate > thresholds["error_rate"]:
            passed = False
        if "throughput_per_user" in thresholds:
            per_user = throughput / test.target_users if test.target_users else 0.0
            if per_user < thresholds["throughput_per_user"]:
                passed = False

        return {"passed": passed, "results": results, "metrics": metrics}


    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution status

        Args:
            execution_id: Execution ID

        Returns:
            Execution status
        """
        if execution_id not in self.test_executions:
            return None

        execution = self.test_executions[execution_id]

        return {
            "execution_id": execution.execution_id,
            "test_id": execution.test_id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration": execution.duration,
            "passed": execution.passed,
            "error_message": execution.error_message,
            "results": execution.results,
        }

    async def generate_performance_report(self, test_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate performance report

        Args:
            test_id: Filter by test ID (optional)

        Returns:
            Performance report
        """
        report_id = f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # Filter executions
        if test_id:
            executions = [e for e in self.test_executions.values() if e.test_id == test_id]
        else:
            executions = list(self.test_executions.values())

        # Calculate summary
        total = len(executions)
        passed = len([e for e in executions if e.passed])
        failed = len([e for e in executions if not e.passed])

        report = {
            "report_id": report_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "test_id": test_id,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / total if total > 0 else 0.0,
            },
            "executions": [
                {
                    "execution_id": e.execution_id,
                    "test_id": e.test_id,
                    "status": e.status,
                    "passed": e.passed,
                    "duration": e.duration,
                    "results": e.results,
                }
                for e in executions
            ],
        }

        self.performance_reports[report_id] = report

        # Save report
        report_path = self.reports_dir / f"{report_id}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated performance report: {report_id}")

        return report

    def get_statistics(self) -> Dict[str, Any]:
        """Get performance testing statistics"""
        return {
            "total_tests": len(self.performance_tests),
            "enabled_tests": len([t for t in self.performance_tests.values() if t.enabled]),
            "total_executions": self.total_executions,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "pass_rate": (
                self.passed_tests / self.total_executions if self.total_executions > 0 else 0.0
            ),
        }


def get_performance_integration_tester(
    config: Optional[Dict[str, Any]] = None,
) -> PerformanceIntegrationTester:
    """
    Factory function to get performance integration tester instance

    Args:
        config: Optional configuration dictionary

    Returns:
        PerformanceIntegrationTester: Tester instance
    """
    return PerformanceIntegrationTester(config)
