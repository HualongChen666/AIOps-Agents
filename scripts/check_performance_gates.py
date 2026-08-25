#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance Gate Checker
========================

Checks performance results against configured quality gates including:
- Performance baseline checks
- Regression detection
- Resource usage limits
- Coverage requirements

Usage:
    python scripts/check_performance_gates.py --report FILE --regression-report FILE --coverage-threshold N
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GateConfig:
    """Configuration for performance gates"""

    # Performance thresholds
    max_response_time_ms: float = 1000.0
    min_throughput_ops: float = 100.0
    max_error_rate_percent: float = 5.0

    # Resource thresholds
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_disk_percent: float = 90.0

    # Coverage threshold
    min_coverage_percent: float = 70.0

    # Regression threshold
    max_regression_percent: float = 10.0


@dataclass
class GateResult:
    """Result of a gate check"""

    gate_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


class PerformanceGateChecker:
    """Checks performance against quality gates"""

    def __init__(self, config: Optional[GateConfig] = None):
        self.config = config or GateConfig()
        self.results: List[GateResult] = []

    def check_performance_gate(self, performance_report: Dict[str, Any]) -> GateResult:
        """Check performance metrics against thresholds"""
        details = {}
        passed = True
        messages = []

        # Check response time if available
        if "avg_latency_ns" in performance_report:
            avg_latency_ms = performance_report["avg_latency_ns"] / 1_000_000
            details["avg_latency_ms"] = avg_latency_ms

            if avg_latency_ms > self.config.max_response_time_ms:
                passed = False
                messages.append(
                    f"Average latency {avg_latency_ms:.2f}ms exceeds threshold {self.config.max_response_time_ms}ms"
                )

        # Check throughput if available
        if "throughput_ops_per_sec" in performance_report:
            throughput = performance_report["throughput_ops_per_sec"]
            details["throughput_ops_per_sec"] = throughput

            if throughput < self.config.min_throughput_ops:
                passed = False
                messages.append(
                    f"Throughput {throughput:.2f} ops/s below minimum {self.config.min_throughput_ops} ops/s"
                )

        # Check benchmark results if available
        if "benchmarks" in performance_report:
            benchmarks = performance_report["benchmarks"].get("benchmarks", {})
            for bench_name, bench_data in benchmarks.items():
                stats = bench_data.get("stats", {})
                mean = stats.get("mean", 0)

                if mean > self.config.max_response_time_ms:
                    passed = False
                    messages.append(
                        f"Benchmark {bench_name} mean {mean:.2f}ms exceeds threshold {self.config.max_response_time_ms}ms"
                    )

        message = "; ".join(messages) if messages else "Performance metrics within acceptable range"

        result = GateResult(
            gate_name="performance", passed=passed, message=message, details=details
        )
        self.results.append(result)
        return result

    def check_regression_gate(self, regression_report: Dict[str, Any]) -> GateResult:
        """Check for performance regressions"""
        details = {}
        passed = True
        messages = []

        regressions_detected = regression_report.get("regressions_detected", 0)
        details["regressions_detected"] = regressions_detected

        if regressions_detected > 0:
            passed = False
            messages.append(f"Detected {regressions_detected} performance regression(s)")

            # Add details about regressions
            regressions = regression_report.get("regressions", [])
            for reg in regressions[:5]:  # Show first 5
                messages.append(
                    f"  - {reg.get('test_name', 'unknown')}: {reg.get('metric', 'unknown')} "
                    f"regression of {reg.get('change_percent', 0):.2f}%"
                )
        else:
            messages.append("No significant performance regressions detected")

        message = "; ".join(messages)

        result = GateResult(gate_name="regression", passed=passed, message=message, details=details)
        self.results.append(result)
        return result

    def check_resource_gate(self, performance_report: Dict[str, Any]) -> GateResult:
        """Check resource usage against thresholds"""
        details = {}
        passed = True
        messages = []

        resource_metrics = performance_report.get("resource_metrics", {})

        # Check CPU usage
        if "cpu" in resource_metrics:
            cpu_percent = resource_metrics["cpu"].get("percent", 0)
            details["cpu_percent"] = cpu_percent

            if cpu_percent > self.config.max_cpu_percent:
                passed = False
                messages.append(
                    f"CPU usage {cpu_percent:.1f}% exceeds threshold {self.config.max_cpu_percent}%"
                )

        # Check memory usage
        if "memory" in resource_metrics:
            memory_percent = resource_metrics["memory"].get("percent", 0)
            details["memory_percent"] = memory_percent

            if memory_percent > self.config.max_memory_percent:
                passed = False
                messages.append(
                    f"Memory usage {memory_percent:.1f}% exceeds threshold {self.config.max_memory_percent}%"
                )

        # Check disk usage
        if "disk" in resource_metrics:
            disk_percent = resource_metrics["disk"].get("percent", 0)
            details["disk_percent"] = disk_percent

            if disk_percent > self.config.max_disk_percent:
                passed = False
                messages.append(
                    f"Disk usage {disk_percent:.1f}% exceeds threshold {self.config.max_disk_percent}%"
                )

        message = "; ".join(messages) if messages else "Resource usage within acceptable range"

        result = GateResult(gate_name="resource", passed=passed, message=message, details=details)
        self.results.append(result)
        return result

    def check_coverage_gate(self, coverage_threshold: float) -> GateResult:
        """Check code coverage threshold"""
        details = {}
        passed = True
        messages = []

        # Try to read coverage from coverage.xml
        coverage_file = Path("coverage.xml")
        if coverage_file.exists():
            try:
                import xml.etree.ElementTree as ET

                tree = ET.parse(coverage_file)
                root = tree.getroot()

                # Find coverage percentage
                coverage_elem = root.find(".//coverage")
                if coverage_elem is not None:
                    coverage_percent = float(coverage_elem.get("line-rate", 0)) * 100
                    details["coverage_percent"] = coverage_percent

                    if coverage_percent < coverage_threshold:
                        passed = False
                        messages.append(
                            f"Coverage {coverage_percent:.2f}% below threshold {coverage_threshold}%"
                        )
                    else:
                        messages.append(
                            f"Coverage {coverage_percent:.2f}% meets threshold {coverage_threshold}%"
                        )
            except Exception as e:
                messages.append(f"Could not parse coverage file: {e}")
        else:
            messages.append("Coverage file not found, skipping coverage check")

        message = "; ".join(messages)

        result = GateResult(gate_name="coverage", passed=passed, message=message, details=details)
        self.results.append(result)
        return result

    def check_all_gates(
        self,
        performance_report: Dict[str, Any],
        regression_report: Optional[Dict[str, Any]] = None,
        coverage_threshold: float = 70.0,
    ) -> Dict[str, Any]:
        """Check all performance gates"""

        # Check performance gate
        self.check_performance_gate(performance_report)

        # Check regression gate if report provided
        if regression_report:
            self.check_regression_gate(regression_report)

        # Check resource gate
        self.check_resource_gate(performance_report)

        # Check coverage gate
        self.check_coverage_gate(coverage_threshold)

        # Determine overall status
        all_passed = all(result.passed for result in self.results)

        return {
            "all_passed": all_passed,
            "performance_passed": self.results[0].passed if len(self.results) > 0 else True,
            "regression_passed": self.results[1].passed if len(self.results) > 1 else True,
            "resource_passed": self.results[2].passed if len(self.results) > 2 else True,
            "coverage_passed": self.results[3].passed if len(self.results) > 3 else True,
            "gates": [result.to_dict() for result in self.results],
            "summary": {
                "total_gates": len(self.results),
                "passed_gates": sum(1 for r in self.results if r.passed),
                "failed_gates": sum(1 for r in self.results if not r.passed),
            },
        }


def main():
    parser = argparse.ArgumentParser(description="Check performance quality gates")
    parser.add_argument("--report", required=True, help="Path to performance report JSON")
    parser.add_argument("--regression-report", help="Path to regression analysis JSON")
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=70.0,
        help="Minimum coverage percentage threshold",
    )
    parser.add_argument("--output", help="Path to output gate check JSON")
    parser.add_argument(
        "--max-response-time",
        type=float,
        default=1000.0,
        help="Maximum acceptable response time in ms",
    )
    parser.add_argument(
        "--min-throughput", type=float, default=100.0, help="Minimum acceptable throughput in ops/s"
    )
    parser.add_argument(
        "--max-cpu", type=float, default=80.0, help="Maximum acceptable CPU usage percentage"
    )
    parser.add_argument(
        "--max-memory", type=float, default=85.0, help="Maximum acceptable memory usage percentage"
    )

    args = parser.parse_args()

    # Load performance report
    with open(args.report, "r") as f:
        performance_report = json.load(f)

    # Load regression report if provided
    regression_report = None
    if args.regression_report and Path(args.regression_report).exists():
        with open(args.regression_report, "r") as f:
            regression_report = json.load(f)

    # Configure gate checker
    config = GateConfig(
        max_response_time_ms=args.max_response_time,
        min_throughput_ops=args.min_throughput,
        max_cpu_percent=args.max_cpu,
        max_memory_percent=args.max_memory,
        min_coverage_percent=args.coverage_threshold,
    )

    checker = PerformanceGateChecker(config)

    # Check all gates
    result = checker.check_all_gates(
        performance_report=performance_report,
        regression_report=regression_report,
        coverage_threshold=args.coverage_threshold,
    )

    # Output results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Gate check results written to {args.output}")

    # Print summary
    print("\n" + "=" * 60)
    print("PERFORMANCE GATE CHECK RESULTS")
    print("=" * 60)
    print(f"Overall Status: {'✅ PASSED' if result['all_passed'] else '❌ FAILED'}")
    print(f"Passed Gates: {result['summary']['passed_gates']}/{result['summary']['total_gates']}")
    print()

    for gate_result in result["gates"]:
        status = "✅ PASSED" if gate_result["passed"] else "❌ FAILED"
        print(f"{gate_result['gate_name'].upper()}: {status}")
        print(f"  {gate_result['message']}")
        print()

    # Exit with appropriate code
    sys.exit(0 if result["all_passed"] else 1)


if __name__ == "__main__":
    main()
