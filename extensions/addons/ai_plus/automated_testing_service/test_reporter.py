# -*- coding: utf-8 -*-
"""Test reporter for generating and formatting test reports."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import Config
from .test_runner import TestCoverage, TestReport, TestResult

logger = logging.getLogger(Config.SERVICE_NAME)


class TestReporter:
    """Reporter for generating test execution reports."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the test reporter.

        Args:
            config: Configuration object. If None, uses default Config.
        """
        self.config = config or Config()
        self.reports: Dict[str, TestReport] = {}
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure reports directory exists."""
        os.makedirs(self.config.TEST_RESULTS_DIR, exist_ok=True)

    def create_report(self, report: TestReport) -> TestReport:
        """Create and store a test report.

        Args:
            report: TestReport object

        Returns:
            Stored TestReport object
        """
        self.reports[report.id] = report
        logger.info(f"Created report {report.id} for suite {report.suite_id}")
        return report

    def get_report(self, report_id: str) -> Optional[TestReport]:
        """Get a report by ID.

        Args:
            report_id: ID of the report

        Returns:
            TestReport object or None if not found
        """
        return self.reports.get(report_id)

    def list_reports(self, suite_id: Optional[str] = None, limit: int = 100) -> List[TestReport]:
        """List reports.

        Args:
            suite_id: Optional filter by suite ID
            limit: Maximum number of reports to return

        Returns:
            List of TestReport objects
        """
        reports = list(self.reports.values())

        if suite_id:
            reports = [r for r in reports if r.suite_id == suite_id]

        # Sort by completion time (newest first)
        reports.sort(key=lambda r: r.completed_at, reverse=True)

        return reports[:limit]

    def delete_report(self, report_id: str) -> bool:
        """Delete a report.

        Args:
            report_id: ID of the report

        Returns:
            True if deleted, False if not found
        """
        if report_id in self.reports:
            del self.reports[report_id]
            logger.info(f"Deleted report {report_id}")
            return True
        return False

    def generate_json_report(self, report: TestReport) -> str:
        """Generate a JSON-formatted report.

        Args:
            report: TestReport object

        Returns:
            JSON string
        """
        report_dict = {
            "id": report.id,
            "suite_id": report.suite_id,
            "summary": {
                "total": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "errors": report.errors,
                "duration": report.total_duration,
            },
            "timing": {
                "started_at": report.started_at,
                "completed_at": report.completed_at,
            },
            "coverage": (
                {
                    "lines_covered": report.coverage.lines_covered,
                    "lines_total": report.coverage.lines_total,
                    "percentage": report.coverage.percentage,
                    "file_coverage": report.coverage.file_coverage,
                }
                if report.coverage
                else None
            ),
            "results": [
                {
                    "id": r.id,
                    "test_case_id": r.test_case_id,
                    "status": r.status,
                    "message": r.message,
                    "duration": r.duration,
                    "timestamp": r.timestamp,
                }
                for r in report.results
            ],
        }

        return json.dumps(report_dict, indent=2)

    def generate_html_report(self, report: TestReport) -> str:
        """Generate an HTML-formatted report.

        Args:
            report: TestReport object

        Returns:
            HTML string
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {report.suite_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ padding: 15px; border-radius: 5px; text-align: center; }}
        .metric.passed {{ background: #d4edda; color: #155724; }}
        .metric.failed {{ background: #f8d7da; color: #721c24; }}
        .metric.skipped {{ background: #fff3cd; color: #856404; }}
        .metric.errors {{ background: #f5c6cb; color: #721c24; }}
        .results {{ margin-top: 20px; }}
        .result {{ padding: 10px; margin: 5px 0; border-radius: 3px; }}
        .result.passed {{ background: #d4edda; }}
        .result.failed {{ background: #f8d7da; }}
        .result.skipped {{ background: #fff3cd; }}
        .result.error {{ background: #f5c6cb; }}
        .coverage {{ margin-top: 20px; padding: 15px; background: #e2e3e5; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Report</h1>
        <p><strong>Suite ID:</strong> {report.suite_id}</p>
        <p><strong>Report ID:</strong> {report.id}</p>
        <p><strong>Started:</strong> {datetime.fromtimestamp(report.started_at / 1000).strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Completed:</strong> {datetime.fromtimestamp(report.completed_at / 1000).strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Duration:</strong> {report.total_duration:.2f}s</p>
    </div>

    <div class="summary">
        <div class="metric passed">
            <h2>{report.passed}</h2>
            <p>Passed</p>
        </div>
        <div class="metric failed">
            <h2>{report.failed}</h2>
            <p>Failed</p>
        </div>
        <div class="metric skipped">
            <h2>{report.skipped}</h2>
            <p>Skipped</p>
        </div>
        <div class="metric errors">
            <h2>{report.errors}</h2>
            <p>Errors</p>
        </div>
    </div>

    <div class="coverage">
        <h2>Coverage</h2>
        {self._generate_coverage_html(report.coverage) if report.coverage else '<p>No coverage data available</p>'}
    </div>

    <div class="results">
        <h2>Test Results</h2>
        {self._generate_results_html(report.results)}
    </div>
</body>
</html>
"""
        return html

    def _generate_coverage_html(self, coverage: TestCoverage) -> str:
        """Generate HTML for coverage section.

        Args:
            coverage: TestCoverage object

        Returns:
            HTML string
        """
        html = f"""
        <p><strong>Total Coverage:</strong> {coverage.percentage:.2f}%</p>
        <p><strong>Lines Covered:</strong> {coverage.lines_covered} / {coverage.lines_total}</p>
        <h3>File Coverage</h3>
        <ul>
"""
        for file_path, percentage in coverage.file_coverage.items():
            html += f"            <li>{file_path}: {percentage:.2f}%</li>\n"

        html += "        </ul>"
        return html

    def _generate_results_html(self, results: List[TestResult]) -> str:
        """Generate HTML for test results.

        Args:
            results: List of TestResult objects

        Returns:
            HTML string
        """
        if not results:
            return "<p>No test results available</p>"

        html = ""
        for result in results:
            status_class = result.status.lower()
            html += f"""
        <div class="result {status_class}">
            <strong>{result.test_case_id}</strong> - {result.status}
            <br/>
            <small>Duration: {result.duration:.3f}s</small>
"""
            if result.message:
                html += f"            <p>{result.message}</p>\n"
            if result.traceback:
                html += f"            <pre>{result.traceback}</pre>\n"

            html += "        </div>\n"

        return html

    def save_report(self, report: TestReport, format: str = "json") -> str:
        """Save a report to disk.

        Args:
            report: TestReport object
            format: Output format (json or html)

        Returns:
            Path to saved file

        Raises:
            ValueError: If format is invalid
        """
        if format == "json":
            content = self.generate_json_report(report)
            filename = f"report_{report.id}.json"
        elif format == "html":
            content = self.generate_html_report(report)
            filename = f"report_{report.id}.html"
        else:
            raise ValueError(f"Invalid format: {format}")

        filepath = os.path.join(self.config.TEST_RESULTS_DIR, filename)

        with open(filepath, "w") as f:
            f.write(content)

        logger.info(f"Saved report to {filepath}")
        return filepath

    def generate_summary(self, reports: List[TestReport]) -> Dict[str, Any]:
        """Generate a summary from multiple reports.

        Args:
            reports: List of TestReport objects

        Returns:
            Summary dictionary
        """
        if not reports:
            return {
                "total_reports": 0,
                "total_tests": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_skipped": 0,
                "total_errors": 0,
                "average_duration": 0.0,
                "average_coverage": 0.0,
            }

        total_tests = sum(r.total_tests for r in reports)
        total_passed = sum(r.passed for r in reports)
        total_failed = sum(r.failed for r in reports)
        total_skipped = sum(r.skipped for r in reports)
        total_errors = sum(r.errors for r in reports)
        total_duration = sum(r.total_duration for r in reports)

        # Calculate average coverage
        coverages = [r.coverage.percentage for r in reports if r.coverage]
        average_coverage = sum(coverages) / len(coverages) if coverages else 0.0

        return {
            "total_reports": len(reports),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_errors": total_errors,
            "average_duration": total_duration / len(reports),
            "average_coverage": average_coverage,
            "pass_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0.0,
        }
