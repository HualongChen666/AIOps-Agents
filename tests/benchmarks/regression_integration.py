# -*- coding: utf-8 -*-
"""
Performance Regression Detection Integration for Testing Framework
================================================================
Provides integration with pytest for automatic regression detection:
- Automatic baseline updates
- CI/CD integration
- Test failure mechanism
- Historical data storage
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest
from loguru import logger

from core.performance_regression_detector import (
    AlertConfig,
    BaselineData,
    DetectionMethod,
    PerformanceRegressionDetector,
    RegressionResult,
    RegressionSeverity,
)
from tests.benchmarks.benchmark_base import PerformanceMetricType, PerformanceResult


class RegressionTestConfig:
    """Configuration for regression testing"""

    def __init__(self):
        """Initialize regression test configuration"""
        self.enabled = os.getenv("REGRESSION_DETECTION_ENABLED", "true").lower() == "true"
        self.auto_update_baseline = os.getenv("AUTO_UPDATE_BASELINE", "false").lower() == "true"
        self.fail_on_regression = os.getenv("FAIL_ON_REGRESSION", "true").lower() == "true"
        self.storage_path = os.getenv("REGRESSION_STORAGE_PATH", ".benchmarks/history")
        self.alpha = float(os.getenv("REGRESSION_ALPHA", "0.05"))
        self.methods = self._parse_methods(os.getenv("REGRESSION_METHODS", "t_test,mann_whitney_u"))
        self.severity_threshold = RegressionSeverity(
            os.getenv("REGRESSION_SEVERITY_THRESHOLD", "warning")
        )

        # Alert configuration
        self.alert_enabled = os.getenv("REGRESSION_ALERT_ENABLED", "true").lower() == "true"
        self.alert_webhook = os.getenv("REGRESSION_ALERT_WEBHOOK")
        self.alert_slack = os.getenv("REGRESSION_ALERT_SLACK")

    def _parse_methods(self, methods_str: str) -> List[DetectionMethod]:
        """Parse detection methods from string"""
        method_map = {
            "t_test": DetectionMethod.T_TEST,
            "mann_whitney_u": DetectionMethod.MANN_WHITNEY_U,
            "z_test": DetectionMethod.Z_TEST,
            "percentile_comparison": DetectionMethod.PERCENTILE_COMPARISON,
            "regression_analysis": DetectionMethod.REGRESSION_ANALYSIS,
            "change_point_detection": DetectionMethod.CHANGE_POINT_DETECTION,
            "seasonal_decomposition": DetectionMethod.SEASONAL_DECOMPOSITION,
        }

        methods = []
        for method_name in methods_str.split(","):
            method_name = method_name.strip()
            if method_name in method_map:
                methods.append(method_map[method_name])

        return methods or [DetectionMethod.T_TEST, DetectionMethod.MANN_WHITNEY_U]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "enabled": self.enabled,
            "auto_update_baseline": self.auto_update_baseline,
            "fail_on_regression": self.fail_on_regression,
            "storage_path": self.storage_path,
            "alpha": self.alpha,
            "methods": [m.value for m in self.methods],
            "severity_threshold": self.severity_threshold.value,
            "alert_enabled": self.alert_enabled,
            "alert_webhook": self.alert_webhook,
            "alert_slack": self.alert_slack,
        }


class RegressionTestHelper:
    """Helper class for regression testing in pytest"""

    def __init__(self, config: Optional[RegressionTestConfig] = None):
        """
        Initialize regression test helper

        Args:
            config: Optional configuration
        """
        self.config = config or RegressionTestConfig()

        # Initialize detector
        alert_config = AlertConfig(
            enabled=self.config.alert_enabled,
            severity_threshold=self.config.severity_threshold,
            webhook_url=self.config.alert_webhook,
            slack_channel=self.config.alert_slack,
        )

        self.detector = PerformanceRegressionDetector(
            storage_path=self.config.storage_path, alert_config=alert_config
        )

        self.test_results: List[RegressionResult] = []
        self.baseline_updates: List[str] = []

    def check_regression(
        self, test_name: str, metric_type: str, current_values: List[float]
    ) -> RegressionResult:
        """
        Check for performance regression

        Args:
            test_name: Test name
            metric_type: Metric type
            current_values: Current performance values

        Returns:
            Regression result
        """
        if not self.config.enabled:
            # Return a non-detected result if disabled
            return RegressionResult(
                test_name=test_name,
                metric_type=metric_type,
                baseline_data=BaselineData(test_name, metric_type, [], []),
                current_values=current_values,
                detection_method=DetectionMethod.T_TEST,
                detected=False,
                severity=RegressionSeverity.INFO,
                message="Regression detection disabled",
            )

        result = self.detector.detect_regression(
            test_name=test_name,
            metric_type=metric_type,
            current_values=current_values,
            methods=self.config.methods,
            alpha=self.config.alpha,
        )

        self.test_results.append(result)

        # Auto-update baseline if configured and no regression detected
        if self.config.auto_update_baseline and not result.detected:
            self.detector.data_manager.update_baseline(
                test_name=test_name,
                metric_type=metric_type,
                new_values=current_values,
                timestamps=[datetime.now() for _ in current_values],
            )
            self.baseline_updates.append(f"{test_name}/{metric_type}")

        return result

    def check_performance_result(
        self, performance_result: PerformanceResult, metric_type: PerformanceMetricType
    ) -> RegressionResult:
        """
        Check regression from a PerformanceResult object

        Args:
            performance_result: Performance result from benchmark
            metric_type: Metric type to check

        Returns:
            Regression result
        """
        values = performance_result.get_metric_values(metric_type)
        return self.check_regression(
            test_name=performance_result.test_name,
            metric_type=metric_type.value,
            current_values=values,
        )

    def assert_no_regression(self, result: RegressionResult):
        """
        Assert that no regression was detected

        Args:
            result: Regression result

        Raises:
            AssertionError: If regression detected
        """
        if result.detected:
            error_msg = (
                f"Performance regression detected in {result.test_name}/{result.metric_type}\n"
                f"Severity: {result.severity.value}\n"
                f"Message: {result.message}\n"
                f"P-value: {result.p_value}\n"
                f"Effect size: {result.effect_size}"
            )
            if self.config.fail_on_regression:
                pytest.fail(error_msg)
            else:
                logger.warning(error_msg)

    def assert_regression_below_severity(
        self, result: RegressionResult, max_severity: RegressionSeverity
    ):
        """
        Assert that regression severity is below threshold

        Args:
            result: Regression result
            max_severity: Maximum allowed severity

        Raises:
            AssertionError: If severity exceeds threshold
        """
        severity_order = [
            RegressionSeverity.INFO,
            RegressionSeverity.WARNING,
            RegressionSeverity.CRITICAL,
            RegressionSeverity.BLOCKER,
        ]

        if severity_order.index(result.severity) > severity_order.index(max_severity):
            error_msg = (
                f"Regression severity {result.severity.value} exceeds "
                f"maximum allowed {max_severity.value} in {result.test_name}/{result.metric_type}"
            )
            if self.config.fail_on_regression:
                pytest.fail(error_msg)
            else:
                logger.warning(error_msg)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of regression tests

        Returns:
            Summary dictionary
        """
        return {
            "total_tests": len(self.test_results),
            "regressions_detected": sum(1 for r in self.test_results if r.detected),
            "by_severity": {
                severity.value: sum(1 for r in self.test_results if r.severity == severity)
                for severity in RegressionSeverity
            },
            "baseline_updates": len(self.baseline_updates),
            "config": self.config.to_dict(),
        }

    def save_report(self, output_path: Union[str, Path], format: str = "json"):
        """
        Save regression test report

        Args:
            output_path: Path to save report
            format: Report format
        """
        from core.performance_regression_detector import RegressionReportGenerator

        generator = RegressionReportGenerator(self.detector)
        generator.save_report(self.test_results, output_path, format)


@pytest.fixture(scope="session")
def regression_config():
    """Fixture providing regression test configuration"""
    return RegressionTestConfig()


@pytest.fixture(scope="session")
def regression_helper(regression_config):
    """Fixture providing regression test helper"""
    helper = RegressionTestHelper(regression_config)
    yield helper

    # Save report at end of session
    if helper.test_results:
        report_path = Path(".benchmarks") / "regression_report.json"
        helper.save_report(report_path, "json")
        logger.info(f"Regression report saved to {report_path}")


@pytest.fixture(scope="function")
def regression_checker(regression_helper):
    """Fixture for checking regression in individual tests"""

    def check(test_name: str, metric_type: str, values: List[float]) -> RegressionResult:
        result = regression_helper.check_regression(test_name, metric_type, values)
        regression_helper.assert_no_regression(result)
        return result

    return check


class RegressionTestMixin:
    """Mixin class for adding regression detection to test classes"""

    @property
    def regression_helper(self) -> RegressionTestHelper:
        """Get regression helper instance"""
        if not hasattr(self, "_regression_helper"):
            self._regression_helper = RegressionTestHelper()
        return self._regression_helper

    def check_performance_regression(
        self, test_name: str, metric_type: str, current_values: List[float]
    ) -> RegressionResult:
        """
        Check for performance regression

        Args:
            test_name: Test name
            metric_type: Metric type
            current_values: Current performance values

        Returns:
            Regression result
        """
        result = self.regression_helper.check_regression(test_name, metric_type, current_values)
        self.regression_helper.assert_no_regression(result)
        return result

    def assert_no_performance_regression(self, result: RegressionResult):
        """
        Assert no performance regression

        Args:
            result: Regression result
        """
        self.regression_helper.assert_no_regression(result)


def pytest_configure(config):
    """Configure pytest hooks for regression detection"""
    # Add custom markers
    config.addinivalue_line("markers", "regression: mark test for regression detection")
    config.addinivalue_line("markers", "baseline: mark test to establish baseline")
    config.addinivalue_line("markers", "noregression: disable regression detection for this test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection for regression detection"""
    regression_config = RegressionTestConfig()

    if not regression_config.enabled:
        # Skip regression tests if disabled
        skip_regression = pytest.mark.skip(reason="Regression detection disabled")
        for item in items:
            if "regression" in item.keywords:
                item.add_marker(skip_regression)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Generate regression test reports"""
    outcome = yield
    report = outcome.get_result()

    # Check if test has regression marker
    if "regression" in item.keywords and call.when == "call":
        # Store regression results in report
        if hasattr(item, "funcargs") and "regression_helper" in item.funcargs:
            helper = item.funcargs["regression_helper"]
            if helper.test_results:
                report.regression_results = helper.test_results


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print regression summary at end of test run"""
    regression_config = RegressionTestConfig()

    if not regression_config.enabled:
        return

    # Check if any regression helper was used
    for item in terminalreporter.stats.get("passed", []) + terminalreporter.stats.get("failed", []):
        if hasattr(item, "regression_results"):
            results = item.regression_results
            regressions = [r for r in results if r.detected]

            if regressions:
                terminalreporter.write_sep("=", "REGRESSION DETECTION SUMMARY")
                terminalreporter.write_line(f"Total tests: {len(results)}")
                terminalreporter.write_line(f"Regressions detected: {len(regressions)}")

                for result in regressions:
                    terminalreporter.write_line(
                        f"  - {result.test_name}/{result.metric_type}: "
                        f"{result.severity.value} - {result.message}"
                    )

                terminalreporter.write_sep("=")


# CI/CD Integration helpers
class CIRegressionChecker:
    """Helper for CI/CD regression checking"""

    def __init__(self, config: Optional[RegressionTestConfig] = None):
        """
        Initialize CI regression checker

        Args:
            config: Optional configuration
        """
        self.config = config or RegressionTestConfig()
        self.helper = RegressionTestHelper(self.config)

    def check_and_report(
        self, test_name: str, metric_type: str, current_values: List[float]
    ) -> Dict[str, Any]:
        """
        Check regression and generate CI report

        Args:
            test_name: Test name
            metric_type: Metric type
            current_values: Current performance values

        Returns:
            CI report dictionary
        """
        result = self.helper.check_regression(test_name, metric_type, current_values)

        report = {
            "test_name": test_name,
            "metric_type": metric_type,
            "regression_detected": result.detected,
            "severity": result.severity.value,
            "should_fail": result.detected and self.config.fail_on_regression,
            "details": result.to_dict(),
        }

        # Write to CI output file
        ci_output_path = Path(".benchmarks") / "ci_regression_report.json"
        ci_output_path.parent.mkdir(parents=True, exist_ok=True)

        existing_reports = []
        if ci_output_path.exists():
            with open(ci_output_path, "r") as f:
                existing_reports = json.load(f)

        existing_reports.append(report)

        with open(ci_output_path, "w") as f:
            json.dump(existing_reports, f, indent=2, default=str)

        return report

    def get_exit_code(self) -> int:
        """
        Get exit code for CI based on regression results

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        if not self.config.fail_on_regression:
            return 0

        regressions = [r for r in self.helper.test_results if r.detected]
        if regressions:
            return 1

        return 0


# Command-line interface for standalone usage
def main():
    """Main entry point for standalone regression checking"""
    import argparse

    parser = argparse.ArgumentParser(description="Performance Regression Detection")
    parser.add_argument("--test-name", required=True, help="Test name")
    parser.add_argument("--metric-type", required=True, help="Metric type")
    parser.add_argument("--values", required=True, help="Comma-separated performance values")
    parser.add_argument(
        "--establish-baseline", action="store_true", help="Establish baseline instead of checking"
    )
    parser.add_argument("--config", help="Path to config file")

    args = parser.parse_args()

    # Parse values
    values = [float(v.strip()) for v in args.values.split(",")]

    # Initialize detector
    config = RegressionTestConfig()
    detector = PerformanceRegressionDetector(storage_path=config.storage_path)

    if args.establish_baseline:
        # Establish baseline
        success = detector.establish_baseline(
            test_name=args.test_name, metric_type=args.metric_type, values=values
        )
        print(f"Baseline establishment: {'SUCCESS' if success else 'FAILED'}")
    else:
        # Check regression
        result = detector.detect_regression(
            test_name=args.test_name, metric_type=args.metric_type, current_values=values
        )

        print(f"Regression detected: {result.detected}")
        print(f"Severity: {result.severity.value}")
        print(f"Message: {result.message}")

        if result.detected and config.fail_on_regression:
            exit(1)


if __name__ == "__main__":
    main()
