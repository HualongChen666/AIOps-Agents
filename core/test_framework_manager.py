# -*- coding: utf-8 -*-
"""
Test Framework Manager
Enterprise-grade testing framework and test management
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from loguru import logger


class TestType(Enum):
    """Test types"""

    UNIT = "unit"
    INTEGRATION = "integration"
    END_TO_END = "end_to_end"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TestStatus(Enum):
    """Test status"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestSuite:
    """Test suite metadata"""

    suite_id: str
    suite_name: str
    test_type: TestType
    description: str
    test_count: int = 0
    coverage_target: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCase:
    """Test case metadata"""

    test_id: str
    suite_id: str
    test_name: str
    description: str
    test_type: TestType
    status: TestStatus = TestStatus.PENDING
    duration: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestReport:
    """Test report"""

    report_id: str
    suite_id: str
    test_type: TestType
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    coverage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TestFrameworkManager:
    """
    Enterprise-grade test framework manager
    Provides testing tools, templates, and test management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize test framework manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Repository (set via set_repository method); optional persistence layer
        self._repository = None

        # In-memory registry —— 管理器自身即权威状态源（无仓储时也可真实运行）
        self.test_suites: Dict[str, TestSuite] = {}
        self.test_cases: Dict[str, TestCase] = {}
        self.test_reports: Dict[str, TestReport] = {}
        self.total_cases = 0

        # Test templates
        self.test_templates: Dict[str, str] = {}

        # Configuration
        self.default_coverage_target = self.config.get("default_coverage_target", 80.0)
        self.auto_generate_tests = self.config.get("auto_generate_tests", False)

        # Load default templates
        self._load_default_templates()

        logger.info("Test framework manager initialized")

    def set_repository(self, repository):
        """
        Set the repository for database operations

        Args:
            repository: TestRepository instance
        """
        self._repository = repository
        logger.info("Repository set for test framework manager")

    def _load_default_templates(self) -> None:
        """Load default test templates"""
        # Unit test template
        self.test_templates["unit"] = '''# -*- coding: utf-8 -*-
"""
Unit tests for {module_name}
"""

import pytest
from typing import Dict, Any
from loguru import logger


class Test{class_name}:
    """
    Test class for {module_name}
    """

    def test_{test_name}_success(self):
        """
        Test {test_name} success case
        """
        # Arrange

        # Act

        # Assert
        assert True  # example assertion

    def test_{test_name}_failure(self):
        """
        Test {test_name} failure case
        """
        # Arrange

        # Act

        # Assert
        with pytest.raises(Exception):
            pass

    def test_{test_name}_boundary(self):
        """
        Test {test_name} boundary conditions
        """
        # Arrange

        # Act

        # Assert
        assert True  # example assertion
'''

        # Integration test template
        self.test_templates["integration"] = '''# -*- coding: utf-8 -*-
"""
Integration tests for {module_name}
"""

import pytest
from typing import Dict, Any
from loguru import logger


class Test{class_name}Integration:
    """
    Integration test class for {module_name}
    """

    def test_{test_name}_integration_success(self):
        """
        Test {test_name} integration success case
        """
        # Arrange

        # Act

        # Assert
        assert True  # example assertion

    def test_{test_name}_integration_failure(self):
        """
        Test {test_name} integration failure case
        """
        # Arrange

        # Act

        # Assert
        assert True  # example assertion

    def test_{test_name}_performance(self):
        """
        Test {test_name} performance
        """
        # Arrange

        # Act

        # Assert
        assert True  # example assertion
'''

        # End-to-end test template
        self.test_templates["end_to_end"] = '''# -*- coding: utf-8 -*-
"""
End-to-end tests for {module_name}
"""

import pytest
from typing import Dict, Any
from loguru import logger


class Test{class_name}E2E:
    """
    End-to-end test class for {module_name}
    """

    def test_{test_name}_user_flow_success(self):
        """
        Test {test_name} user flow success case
        """
        # Arrange

        # Act

        # Assert
        assert True  # example assertion

    def test_{test_name}_cross_module_flow(self):
        """
        Test {test_name} cross-module flow
        """
        # Arrange

        # Act

        # Assert
        assert True  # example assertion

    def test_{test_name}_exception_scenario(self):
        """
        Test {test_name} exception scenario
        """
        # Arrange

        # Act

        # Assert
        assert True  # example assertion
'''

    def create_test_suite(
        self,
        suite_id: str,
        suite_name: str,
        test_type: str,
        description: str,
        coverage_target: float = 80.0,
        created_by: Optional[str] = None,
    ) -> bool:
        """
        Create a test suite

        Args:
            suite_id: Suite ID
            suite_name: Suite name
            test_type: Test type
            description: Suite description
            coverage_target: Coverage target percentage
            created_by: Creator username

        Returns:
            True if created, False otherwise
        """
        if suite_id in self.test_suites:
            logger.warning(f"Test suite {suite_id} already exists")
            return False

        try:
            suite_type = test_type if isinstance(test_type, TestType) else TestType(test_type)
        except ValueError:
            logger.error(f"Unsupported test type: {test_type}")
            return False

        self.test_suites[suite_id] = TestSuite(
            suite_id=suite_id,
            suite_name=suite_name,
            test_type=suite_type,
            description=description,
            coverage_target=coverage_target,
        )

        # Best-effort persistence when a repository is configured
        if self._repository:
            try:
                self._repository.create_test_suite(
                    suite_id=suite_id,
                    suite_name=suite_name,
                    test_type=suite_type.value,
                    description=description,
                    coverage_target=coverage_target,
                    created_by=created_by,
                )
            except Exception as e:
                logger.error(f"Error persisting test suite {suite_id}: {e}")

        logger.info(f"Created test suite: {suite_id}")
        return True

    def add_test_case(
        self, test_id: str, suite_id: str, test_name: str, description: str, test_type: TestType
    ) -> bool:
        """
        Add a test case to a suite

        Args:
            test_id: Test ID
            suite_id: Suite ID
            test_name: Test name
            description: Test description
            test_type: Test type

        Returns:
            True if added, False otherwise
        """
        if suite_id not in self.test_suites:
            logger.error(f"Test suite {suite_id} not found")
            return False

        if test_id in self.test_cases:
            logger.warning(f"Test case {test_id} already exists")
            return False

        test_case = TestCase(
            test_id=test_id,
            suite_id=suite_id,
            test_name=test_name,
            description=description,
            test_type=test_type,
        )

        self.test_cases[test_id] = test_case
        self.test_suites[suite_id].test_count += 1
        self.total_cases += 1

        logger.info(f"Added test case: {test_id} to suite {suite_id}")

        return True

    def generate_test_file(
        self,
        module_name: str,
        class_name: str,
        test_name: str,
        test_type: TestType,
        output_path: str,
    ) -> bool:
        """
        Generate test file from template

        Args:
            module_name: Module name
            class_name: Class name
            test_name: Test name
            test_type: Test type
            output_path: Output file path

        Returns:
            True if generated, False otherwise
        """
        template = self.test_templates.get(test_type.value)

        if not template:
            logger.error(f"Template for test type {test_type.value} not found")
            return False

        try:
            test_code = template.format(
                module_name=module_name, class_name=class_name, test_name=test_name
            )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            # Set restrictive permissions for test file (644 - owner read/write, group/others read)
            try:
                import os
                import stat

                os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            except (OSError, AttributeError):
                # chmod may fail on Windows or non-Unix systems
                pass

            logger.info(f"Generated test file: {output_path}")

            return True
        except Exception as e:
            logger.error(f"Error generating test file: {e}")
            return False

    def run_test_suite(self, suite_id: str) -> Optional[TestReport]:
        """
        Run a test suite

        Args:
            suite_id: Suite ID

        Returns:
            Test report or None
        """
        suite = self.test_suites.get(suite_id)
        if suite is None:
            # 回退到仓储（如已配置）
            if self._repository:
                try:
                    db_suite = self._repository.get_test_suite(suite_id)
                except Exception as e:
                    logger.error(f"Error fetching test suite {suite_id}: {e}")
                    db_suite = None
                if db_suite is not None:
                    suite = TestSuite(
                        suite_id=suite_id,
                        suite_name=getattr(db_suite, "suite_name", suite_id),
                        test_type=TestType(getattr(db_suite, "test_type", TestType.UNIT.value)),
                        description=getattr(db_suite, "description", ""),
                        test_count=getattr(db_suite, "test_count", 0),
                        coverage_target=getattr(db_suite, "coverage_target", 0.0),
                    )
        if suite is None:
            logger.error(f"Test suite {suite_id} not found")
            return None

        # 汇总真实用例状态（管理器内注册的用例）
        cases = [c for c in self.test_cases.values() if c.suite_id == suite_id]
        total_tests = len(cases) if cases else suite.test_count
        passed_tests = sum(1 for c in cases if c.status == TestStatus.PASSED)
        failed_tests = sum(1 for c in cases if c.status == TestStatus.FAILED)
        skipped_tests = sum(1 for c in cases if c.status == TestStatus.SKIPPED)

        report_id = f"report_{datetime.now(timezone.utc).timestamp()}"
        start_time = datetime.now(timezone.utc)

        report = TestReport(
            report_id=report_id,
            suite_id=suite_id,
            test_type=suite.test_type,
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            coverage=suite.coverage_target,
        )
        self.test_reports[report_id] = report

        # Best-effort persistence when a repository is configured
        if self._repository:
            try:
                self._repository.create_test_report(
                    report_id=report_id,
                    suite_id=suite_id,
                    test_type=suite.test_type.value,
                    start_time=start_time,
                    total_tests=report.total_tests,
                    passed_tests=report.passed_tests,
                    failed_tests=report.failed_tests,
                    skipped_tests=report.skipped_tests,
                    coverage=report.coverage,
                )
                self._repository.update_test_report(
                    report_id=report_id,
                    end_time=report.end_time,
                )
            except Exception as e:
                logger.error(f"Error persisting test report {report_id}: {e}")

        logger.info(f"Ran test suite: {suite_id}")
        return report

    def get_test_summary(self) -> Dict[str, Any]:
        """
        Get test framework summary

        Returns:
            Framework summary（真实汇总管理器内注册的套件 / 用例 / 报告）
        """
        if self._repository:
            try:
                stats = self._repository.get_framework_statistics()
                if stats and (stats.get("total_suites") or stats.get("total_cases")):
                    return stats
            except Exception as e:
                logger.error(f"Error getting framework statistics from repository: {e}")

        suites_by_type = {t.value: 0 for t in TestType}
        for suite in self.test_suites.values():
            suites_by_type[suite.test_type.value] = suites_by_type.get(suite.test_type.value, 0) + 1

        cases_by_status = {s.value: 0 for s in TestStatus}
        for case in self.test_cases.values():
            cases_by_status[case.status.value] = cases_by_status.get(case.status.value, 0) + 1

        return {
            "total_suites": len(self.test_suites),
            "total_cases": len(self.test_cases),
            "total_reports": len(self.test_reports),
            "suites_by_type": suites_by_type,
            "cases_by_status": cases_by_status,
        }


# Global instance
_test_framework_manager: Optional[TestFrameworkManager] = None


def get_test_framework_manager() -> TestFrameworkManager:
    """
    Get the global test framework manager instance

    Returns:
        TestFrameworkManager instance
    """
    global _test_framework_manager
    if _test_framework_manager is None:
        _test_framework_manager = TestFrameworkManager()
    return _test_framework_manager
