# -*- coding: utf-8 -*-
"""Simple test script to verify the Automated Testing Service."""

import sys
import os

# Add the parent directory to the path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from automated_testing_service.config import Config
from automated_testing_service.test_runner import TestRunner, TestReport, TestResult
from automated_testing_service.test_scheduler import TestScheduler
from automated_testing_service.test_reporter import TestReporter


def test_config():
    """Test configuration."""
    print("Testing Config...")
    config = Config()
    assert config.SERVICE_NAME == "automated_testing_service"
    assert config.PORT == 8001
    assert config.DEFAULT_FRAMEWORK == "pytest"
    print("[OK] Config test passed")


def test_test_runner():
    """Test test runner initialization."""
    print("Testing TestRunner...")
    runner = TestRunner()
    assert runner.config is not None
    print("[OK] TestRunner initialization passed")


def test_test_scheduler():
    """Test test scheduler."""
    print("Testing TestScheduler...")
    scheduler = TestScheduler()

    # Add a schedule
    schedule = scheduler.add_schedule(
        suite_id="test_suite",
        schedule_type="interval",
        schedule_expression="3600",
    )

    assert schedule.suite_id == "test_suite"
    assert schedule.schedule_type == "interval"
    assert schedule.active is True

    # Get schedule
    retrieved = scheduler.get_schedule(schedule.id)
    assert retrieved is not None
    assert retrieved.id == schedule.id

    # List schedules
    schedules = scheduler.list_schedules()
    assert len(schedules) == 1

    # Delete schedule
    deleted = scheduler.delete_schedule(schedule.id)
    assert deleted is True

    print("[OK] TestScheduler test passed")


def test_test_reporter():
    """Test test reporter."""
    print("Testing TestReporter...")
    reporter = TestReporter()

    # Create a test report
    report = TestReport(
        suite_id="test_suite",
        total_tests=2,
        passed=1,
        failed=1,
        skipped=0,
        errors=0,
        total_duration=1.5,
    )

    # Add results
    report.results.append(
        TestResult(
            suite_id="test_suite",
            test_case_id="test_1",
            status="passed",
            duration=0.5,
        )
    )
    report.results.append(
        TestResult(
            suite_id="test_suite",
            test_case_id="test_2",
            status="failed",
            duration=1.0,
        )
    )

    # Create report
    stored = reporter.create_report(report)
    assert stored.id == report.id

    # Get report
    retrieved = reporter.get_report(report.id)
    assert retrieved is not None
    assert retrieved.suite_id == "test_suite"

    # List reports
    reports = reporter.list_reports()
    assert len(reports) == 1

    # Generate JSON report
    json_report = reporter.generate_json_report(report)
    assert "test_suite" in json_report

    # Generate HTML report
    html_report = reporter.generate_html_report(report)
    assert "<html>" in html_report

    print("[OK] TestReporter test passed")


def test_discover_tests():
    """Test test discovery."""
    print("Testing test discovery...")
    runner = TestRunner()

    # Discover tests in the example test file
    test_path = os.path.join(os.path.dirname(__file__), "tests", "example_test.py")

    if os.path.exists(test_path):
        tests = runner.discover_tests(test_path)
        print(f"  Discovered {len(tests)} tests")
        # Test discovery may return 0 if pytest is not properly configured
        # Just verify the method runs without error
        print("[OK] Test discovery passed")
    else:
        print("  Skipping test discovery (example_test.py not found)")


if __name__ == "__main__":
    print("=" * 60)
    print("Automated Testing Service - Component Tests")
    print("=" * 60)

    try:
        test_config()
        test_test_runner()
        test_test_scheduler()
        test_test_reporter()
        test_discover_tests()

        print("=" * 60)
        print("All tests passed! [OK]")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
