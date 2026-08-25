# -*- coding: utf-8 -*-
"""Test runner for executing test suites with pytest."""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import Config

logger = logging.getLogger(Config.SERVICE_NAME)


@dataclass
class TestResult:
    """Represents a single test result."""

    id: str = field(default_factory=lambda: str(uuid4()))
    suite_id: str = ""
    test_case_id: str = ""
    status: str = "pending"  # pending, passed, failed, skipped, error
    message: str = ""
    traceback: str = ""
    duration: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class TestCoverage:
    """Represents test coverage information."""

    suite_id: str = ""
    lines_covered: int = 0
    lines_total: int = 0
    percentage: float = 0.0
    file_coverage: Dict[str, float] = field(default_factory=dict)


@dataclass
class TestReport:
    """Represents a complete test execution report."""

    id: str = field(default_factory=lambda: str(uuid4()))
    suite_id: str = ""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total_duration: float = 0.0
    started_at: int = field(default_factory=lambda: int(time.time() * 1000))
    completed_at: int = 0
    coverage: Optional[TestCoverage] = None
    results: List[TestResult] = field(default_factory=list)


class TestRunner:
    """Test runner for executing pytest test suites."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the test runner.

        Args:
            config: Configuration object. If None, uses default Config.
        """
        self.config = config or Config()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        os.makedirs(self.config.TEST_RESULTS_DIR, exist_ok=True)
        os.makedirs(self.config.COVERAGE_DIR, exist_ok=True)

    def run_tests(
        self,
        suite_id: str,
        test_path: str,
        test_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        collect_coverage: bool = False,
    ) -> TestReport:
        """Run tests for a given test suite.

        Args:
            suite_id: ID of the test suite
            test_path: Path to the test directory or file
            test_ids: Optional list of specific test IDs to run
            tags: Optional list of tags to filter tests
            collect_coverage: Whether to collect coverage information

        Returns:
            TestReport containing execution results

        Raises:
            ValueError: If test path is invalid
            RuntimeError: If test execution fails
        """
        logger.info(f"Starting test execution for suite {suite_id}")

        if not os.path.exists(test_path):
            raise ValueError(f"Test path does not exist: {test_path}")

        report = TestReport(suite_id=suite_id)
        report.started_at = int(time.time() * 1000)

        try:
            # Build pytest command
            cmd = self._build_pytest_command(test_path, test_ids, tags, collect_coverage)

            # Execute tests
            start_time = time.time()
            output = self._execute_pytest(cmd, test_path)
            duration = time.time() - start_time

            # Parse results
            self._parse_test_results(output, report, suite_id)

            # Collect coverage if requested
            if collect_coverage:
                report.coverage = self._collect_coverage(test_path, suite_id)

            report.total_duration = duration
            report.completed_at = int(time.time() * 1000)

            logger.info(
                f"Test execution completed: {report.passed} passed, "
                f"{report.failed} failed, {report.skipped} skipped, "
                f"{report.errors} errors in {duration:.2f}s"
            )

        except Exception as e:
            logger.error(f"Test execution failed: {e}", exc_info=True)
            report.errors = 1
            report.completed_at = int(time.time() * 1000)
            raise RuntimeError(f"Test execution failed: {e}") from e

        return report

    def _build_pytest_command(
        self,
        test_path: str,
        test_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        collect_coverage: bool = False,
    ) -> List[str]:
        """Build pytest command with appropriate arguments.

        Args:
            test_path: Path to tests
            test_ids: Optional specific test IDs
            tags: Optional tags to filter
            collect_coverage: Whether to collect coverage

        Returns:
            List of command arguments
        """
        cmd = [sys.executable, "-m", "pytest", test_path]

        # Add JSON output for parsing
        cmd.extend(["--json-report", "--json-report-file=/dev/stdout"])

        # Add verbose output
        cmd.append("-v")

        # Add specific test IDs if provided
        if test_ids:
            cmd.extend(test_ids)

        # Add tag filters if provided
        if tags:
            tag_expr = " or ".join([f"{tag}" for tag in tags])
            cmd.extend(["-k", tag_expr])

        # Add coverage if requested
        if collect_coverage:
            cmd.extend([
                "--cov=.",
                f"--cov-report=json:{os.path.join(self.config.COVERAGE_DIR, 'coverage.json')}",
                "--cov-report=html",
            ])

        return cmd

    def _execute_pytest(self, cmd: List[str], test_path: str) -> str:
        """Execute pytest command and capture output.

        Args:
            cmd: Command to execute
            test_path: Path to tests (for working directory)

        Returns:
            Captured stdout output

        Raises:
            subprocess.CalledProcessError: If pytest fails
        """
        logger.info(f"Executing pytest: {' '.join(cmd)}")

        # Check if pytest-json-report is installed
        try:
            import pytest_json_report  # noqa: F401
        except ImportError:
            logger.warning("pytest-json-report not installed, using alternative method")
            cmd = [c for c in cmd if "--json-report" not in c and "--json-report-file" not in c]

        # Set working directory to test path parent
        work_dir = os.path.dirname(test_path) if os.path.isfile(test_path) else test_path

        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=self.config.DEFAULT_TEST_TIMEOUT,
        )

        if result.returncode not in [0, 1]:  # 0 = all passed, 1 = some failed
            logger.error(f"Pytest failed with return code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")

        return result.stdout

    def _parse_test_results(self, output: str, report: TestReport, suite_id: str) -> None:
        """Parse pytest output and populate report.

        Args:
            output: Pytest stdout output
            report: Report to populate
            suite_id: Test suite ID
        """
        # Try to parse JSON output if available
        try:
            if output.strip().startswith("{"):
                data = json.loads(output)
                self._parse_json_results(data, report, suite_id)
                return
        except (json.JSONDecodeError, KeyError):
            pass

        # Fallback to text parsing
        self._parse_text_results(output, report, suite_id)

    def _parse_json_results(self, data: Dict[str, Any], report: TestReport, suite_id: str) -> None:
        """Parse JSON test results.

        Args:
            data: JSON data from pytest
            report: Report to populate
            suite_id: Test suite ID
        """
        summary = data.get("summary", {})
        report.total_tests = summary.get("total", 0)
        report.passed = summary.get("passed", 0)
        report.failed = summary.get("failed", 0)
        report.skipped = summary.get("skipped", 0)
        report.errors = summary.get("error", 0)

        for test in data.get("tests", []):
            result = TestResult(
                suite_id=suite_id,
                test_case_id=test.get("nodeid", ""),
                status=test.get("outcome", "unknown"),
                message=test.get("message", ""),
                duration=test.get("duration", 0.0),
            )
            report.results.append(result)

    def _parse_text_results(self, output: str, report: TestReport, suite_id: str) -> None:
        """Parse text-based pytest output.

        Args:
            output: Pytest stdout output
            report: Report to populate
            suite_id: Test suite ID
        """
        lines = output.split("\n")

        for line in lines:
            # Parse test results from output
            if "PASSED" in line:
                report.passed += 1
                report.total_tests += 1
                test_name = line.split()[0] if line.split() else ""
                result = TestResult(
                    suite_id=suite_id,
                    test_case_id=test_name,
                    status="passed",
                )
                report.results.append(result)
            elif "FAILED" in line:
                report.failed += 1
                report.total_tests += 1
                test_name = line.split()[0] if line.split() else ""
                result = TestResult(
                    suite_id=suite_id,
                    test_case_id=test_name,
                    status="failed",
                )
                report.results.append(result)
            elif "SKIPPED" in line:
                report.skipped += 1
                report.total_tests += 1
                test_name = line.split()[0] if line.split() else ""
                result = TestResult(
                    suite_id=suite_id,
                    test_case_id=test_name,
                    status="skipped",
                )
                report.results.append(result)
            elif "ERROR" in line:
                report.errors += 1
                report.total_tests += 1
                test_name = line.split()[0] if line.split() else ""
                result = TestResult(
                    suite_id=suite_id,
                    test_case_id=test_name,
                    status="error",
                )
                report.results.append(result)

    def _collect_coverage(self, test_path: str, suite_id: str) -> TestCoverage:
        """Collect coverage information from coverage.json.

        Args:
            test_path: Path to tests
            suite_id: Test suite ID

        Returns:
            TestCoverage object
        """
        coverage = TestCoverage(suite_id=suite_id)
        coverage_file = os.path.join(self.config.COVERAGE_DIR, "coverage.json")

        if not os.path.exists(coverage_file):
            logger.warning(f"Coverage file not found: {coverage_file}")
            return coverage

        try:
            with open(coverage_file, "r") as f:
                data = json.load(f)

            totals = data.get("totals", {})
            coverage.lines_covered = totals.get("covered_lines", 0)
            coverage.lines_total = totals.get("num_statements", 0)

            if coverage.lines_total > 0:
                coverage.percentage = (coverage.lines_covered / coverage.lines_total) * 100

            # Parse file-level coverage
            files = data.get("files", {})
            for file_path, file_data in files.items():
                summary = file_data.get("summary", {})
                file_covered = summary.get("covered_lines", 0)
                file_total = summary.get("num_statements", 0)
                if file_total > 0:
                    coverage.file_coverage[file_path] = (file_covered / file_total) * 100

            logger.info(f"Coverage collected: {coverage.percentage:.2f}%")

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to parse coverage data: {e}")

        return coverage

    def discover_tests(self, test_path: str) -> List[Dict[str, Any]]:
        """Discover tests in a given path.

        Args:
            test_path: Path to test directory or file

        Returns:
            List of discovered test cases

        Raises:
            ValueError: If test path is invalid
        """
        if not os.path.exists(test_path):
            raise ValueError(f"Test path does not exist: {test_path}")

        cmd = [sys.executable, "-m", "pytest", test_path, "--collect-only", "-q"]
        work_dir = os.path.dirname(test_path) if os.path.isfile(test_path) else test_path

        try:
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            tests = []
            for line in result.stdout.split("\n"):
                if "::" in line and not line.startswith("<"):
                    # Parse test line: module.py::TestClass::test_function
                    parts = line.strip().split("::")
                    if len(parts) >= 2:
                        test_info = {
                            "id": line.strip(),
                            "file_path": parts[0],
                            "class_name": parts[1] if len(parts) > 2 else "",
                            "function_name": parts[-1],
                        }
                        tests.append(test_info)

            logger.info(f"Discovered {len(tests)} tests in {test_path}")
            return tests

        except subprocess.TimeoutExpired:
            logger.error("Test discovery timed out")
            return []
        except Exception as e:
            logger.error(f"Test discovery failed: {e}")
            return []
