#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance Regression Analyzer
===============================

Analyzes current performance results against baseline to detect regressions.
Supports configurable regression thresholds and detailed reporting.

Usage:
    python scripts/analyze_performance_regression.py --current FILE --baseline FILE --threshold N
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Dict, List, Optional


@dataclass
class RegressionConfig:
    """Configuration for regression detection"""

    threshold_percent: float = 10.0  # Default 10% regression threshold
    min_samples: int = 3  # Minimum samples for statistical significance
    confidence_level: float = 0.95  # Statistical confidence level


@dataclass
class RegressionResult:
    """Result of regression analysis for a single metric"""

    metric_name: str
    baseline_value: float
    current_value: float
    change_percent: float
    regression_detected: bool
    severity: str  # 'none', 'minor', 'moderate', 'severe'
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "change_percent": self.change_percent,
            "regression_detected": self.regression_detected,
            "severity": self.severity,
            "details": self.details,
        }


class PerformanceRegressionAnalyzer:
    """Analyzes performance data for regressions"""

    def __init__(self, config: Optional[RegressionConfig] = None):
        self.config = config or RegressionConfig()
        self.regressions: List[RegressionResult] = []

    def calculate_change_percent(self, baseline: float, current: float) -> float:
        """Calculate percentage change from baseline to current"""
        if baseline == 0:
            return 0.0 if current == 0 else 100.0
        return ((current - baseline) / baseline) * 100

    def determine_severity(self, change_percent: float) -> str:
        """Determine severity of regression based on change percentage"""
        if change_percent < self.config.threshold_percent:
            return "none"
        elif change_percent < self.config.threshold_percent * 2:
            return "minor"
        elif change_percent < self.config.threshold_percent * 3:
            return "moderate"
        else:
            return "severe"

    def compare_metric(
        self,
        metric_name: str,
        baseline_value: float,
        current_value: float,
        higher_is_better: bool = False,
    ) -> RegressionResult:
        """
        Compare a single metric between baseline and current

        Args:
            metric_name: Name of the metric
            baseline_value: Baseline value
            current_value: Current value
            higher_is_better: Whether higher values are better (e.g., throughput)

        Returns:
            RegressionResult with analysis
        """
        change_percent = self.calculate_change_percent(baseline_value, current_value)

        # Determine if regression occurred
        if higher_is_better:
            # For metrics where higher is better (e.g., throughput)
            regression_detected = change_percent < -self.config.threshold_percent
        else:
            # For metrics where lower is better (e.g., latency)
            regression_detected = change_percent > self.config.threshold_percent

        severity = self.determine_severity(abs(change_percent))

        result = RegressionResult(
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            change_percent=change_percent,
            regression_detected=regression_detected,
            severity=severity,
            details={
                "higher_is_better": higher_is_better,
                "threshold": self.config.threshold_percent,
            },
        )

        if regression_detected:
            self.regressions.append(result)

        return result

    def analyze_benchmark_results(
        self, baseline_benchmarks: Dict[str, Any], current_benchmarks: Dict[str, Any]
    ) -> List[RegressionResult]:
        """Compare benchmark results between baseline and current"""
        results = []

        baseline_data = baseline_benchmarks.get("benchmarks", {})
        current_data = current_benchmarks.get("benchmarks", {})

        # Compare common benchmarks
        for bench_name in set(baseline_data.keys()) & set(current_data.keys()):
            baseline_stats = baseline_data[bench_name].get("stats", {})
            current_stats = current_data[bench_name].get("stats", {})

            # Compare mean values
            if "mean" in baseline_stats and "mean" in current_stats:
                result = self.compare_metric(
                    metric_name=f"{bench_name}_mean",
                    baseline_value=baseline_stats["mean"],
                    current_value=current_stats["mean"],
                    higher_is_better=False,  # Lower latency is better
                )
                results.append(result)

            # Compare p95 values
            if "p95" in baseline_stats and "p95" in current_stats:
                result = self.compare_metric(
                    metric_name=f"{bench_name}_p95",
                    baseline_value=baseline_stats["p95"],
                    current_value=current_stats["p95"],
                    higher_is_better=False,
                )
                results.append(result)

            # Compare p99 values
            if "p99" in baseline_stats and "p99" in current_stats:
                result = self.compare_metric(
                    metric_name=f"{bench_name}_p99",
                    baseline_value=baseline_stats["p99"],
                    current_value=current_stats["p99"],
                    higher_is_better=False,
                )
                results.append(result)

        return results

    def analyze_performance_metrics(
        self, baseline_report: Dict[str, Any], current_report: Dict[str, Any]
    ) -> List[RegressionResult]:
        """Analyze high-level performance metrics"""
        results = []

        # Compare throughput (higher is better)
        if (
            "throughput_ops_per_sec" in baseline_report
            and "throughput_ops_per_sec" in current_report
        ):
            result = self.compare_metric(
                metric_name="throughput_ops_per_sec",
                baseline_value=baseline_report["throughput_ops_per_sec"],
                current_value=current_report["throughput_ops_per_sec"],
                higher_is_better=True,
            )
            results.append(result)

        # Compare average latency (lower is better)
        if "avg_latency_ns" in baseline_report and "avg_latency_ns" in current_report:
            result = self.compare_metric(
                metric_name="avg_latency_ns",
                baseline_value=baseline_report["avg_latency_ns"],
                current_value=current_report["avg_latency_ns"],
                higher_is_better=False,
            )
            results.append(result)

        # Compare p99 latency (lower is better)
        if "p99_latency_ns" in baseline_report and "p99_latency_ns" in current_report:
            result = self.compare_metric(
                metric_name="p99_latency_ns",
                baseline_value=baseline_report["p99_latency_ns"],
                current_value=current_report["p99_latency_ns"],
                higher_is_better=False,
            )
            results.append(result)

        return results

    def analyze_resource_metrics(
        self, baseline_report: Dict[str, Any], current_report: Dict[str, Any]
    ) -> List[RegressionResult]:
        """Analyze resource usage metrics"""
        results = []

        baseline_resources = baseline_report.get("resource_metrics", {})
        current_resources = current_report.get("resource_metrics", {})

        # Compare CPU usage (lower is better)
        if "cpu" in baseline_resources and "cpu" in current_resources:
            baseline_cpu = baseline_resources["cpu"].get("percent", 0)
            current_cpu = current_resources["cpu"].get("percent", 0)

            result = self.compare_metric(
                metric_name="cpu_usage_percent",
                baseline_value=baseline_cpu,
                current_value=current_cpu,
                higher_is_better=False,
            )
            results.append(result)

        # Compare memory usage (lower is better)
        if "memory" in baseline_resources and "memory" in current_resources:
            baseline_mem = baseline_resources["memory"].get("percent", 0)
            current_mem = current_resources["memory"].get("percent", 0)

            result = self.compare_metric(
                metric_name="memory_usage_percent",
                baseline_value=baseline_mem,
                current_value=current_mem,
                higher_is_better=False,
            )
            results.append(result)

        return results

    def analyze_full_report(
        self, baseline_report: Dict[str, Any], current_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform complete regression analysis"""
        self.regressions = []

        all_results = []

        # Analyze performance metrics
        perf_results = self.analyze_performance_metrics(baseline_report, current_report)
        all_results.extend(perf_results)

        # Analyze benchmark results
        if "benchmarks" in baseline_report and "benchmarks" in current_report:
            bench_results = self.analyze_benchmark_results(
                baseline_report["benchmarks"], current_report["benchmarks"]
            )
            all_results.extend(bench_results)

        # Analyze resource metrics
        resource_results = self.analyze_resource_metrics(baseline_report, current_report)
        all_results.extend(resource_results)

        # Generate summary
        regressions_by_severity = {"none": 0, "minor": 0, "moderate": 0, "severe": 0}

        for result in all_results:
            regressions_by_severity[result.severity] += 1

        return {
            "regressions_detected": len(self.regressions),
            "total_metrics_compared": len(all_results),
            "regressions_by_severity": regressions_by_severity,
            "regressions": [r.to_dict() for r in self.regressions],
            "all_comparisons": [r.to_dict() for r in all_results],
            "threshold_percent": self.config.threshold_percent,
            "summary": {
                "status": "REGRESSION_DETECTED" if self.regressions else "NO_REGRESSION",
                "message": f"Detected {len(self.regressions)} regression(s) out of {len(all_results)} metrics compared",
            },
        }


def main():
    parser = argparse.ArgumentParser(description="Analyze performance regression")
    parser.add_argument("--current", required=True, help="Path to current performance report")
    parser.add_argument("--baseline", required=True, help="Path to baseline performance report")
    parser.add_argument(
        "--threshold",
        type=float,
        default=10.0,
        help="Regression threshold percentage (default: 10)",
    )
    parser.add_argument("--output", help="Path to output analysis JSON")
    parser.add_argument(
        "--min-samples", type=int, default=3, help="Minimum samples for statistical significance"
    )

    args = parser.parse_args()

    # Load current report
    with open(args.current, "r") as f:
        current_report = json.load(f)

    # Load baseline report
    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"Warning: Baseline file not found at {args.baseline}")
        print("Creating baseline from current report...")
        baseline_report = current_report.copy()
    else:
        with open(baseline_path, "r") as f:
            baseline_report = json.load(f)

    # Configure analyzer
    config = RegressionConfig(threshold_percent=args.threshold, min_samples=args.min_samples)

    analyzer = PerformanceRegressionAnalyzer(config)

    # Perform analysis
    analysis = analyzer.analyze_full_report(baseline_report, current_report)

    # Output results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"Regression analysis written to {args.output}")

    # Print summary
    print("\n" + "=" * 60)
    print("PERFORMANCE REGRESSION ANALYSIS")
    print("=" * 60)
    print(f"Status: {analysis['summary']['status']}")
    print(f"Regressions Detected: {analysis['regressions_detected']}")
    print(f"Total Metrics Compared: {analysis['total_metrics_compared']}")
    print(f"Threshold: {analysis['threshold_percent']}%")
    print()

    print("Regressions by Severity:")
    for severity, count in analysis["regressions_by_severity"].items():
        print(f"  {severity.capitalize()}: {count}")
    print()

    if analysis["regressions_detected"] > 0:
        print("Regression Details:")
        for reg in analysis["regressions"]:
            print(f"  - {reg['metric_name']}:")
            print(f"      Baseline: {reg['baseline_value']:.4f}")
            print(f"      Current: {reg['current_value']:.4f}")
            print(f"      Change: {reg['change_percent']:.2f}%")
            print(f"      Severity: {reg['severity']}")
        print()

    # Exit with appropriate code
    sys.exit(0 if analysis["regressions_detected"] == 0 else 1)


if __name__ == "__main__":
    main()
