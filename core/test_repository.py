# -*- coding: utf-8 -*-
"""
Test Repository
Database operations for Testing models
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from core.models import (
    TestingAutomationJobDB as AutomationJobDB,
    TestingCICDPipelineConfigDB as CICDPipelineConfigDB,
    TestingCoverageThresholdDB as CoverageThresholdDB,
    TestingCaseDB as TestCaseDB,
    TestingCoverageDB as TestCoverageDB,
    TestingNotificationConfigDB as TestNotificationConfigDB,
    TestingReportDB as TestReportDB,
    TestingSuiteDB as TestSuiteDB,
)


class TestRepository:
    """
    Repository for Testing-related database operations
    Provides CRUD operations for all testing models
    """

    def __init__(self, db: Session):
        """
        Initialize repository with database session

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    # ==================== Test Suite Operations ====================

    def create_test_suite(
        self,
        suite_id: str,
        suite_name: str,
        test_type: str,
        description: str,
        coverage_target: float = 80.0,
        created_by: Optional[str] = None,
    ) -> TestSuiteDB:
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
            Created TestSuiteDB instance
        """
        try:
            suite = TestSuiteDB(
                id=str(uuid.uuid4()),
                suite_id=suite_id,
                suite_name=suite_name,
                test_type=test_type,
                description=description,
                coverage_target=coverage_target,
                created_by=created_by,
            )
            self.db.add(suite)
            self.db.commit()
            self.db.refresh(suite)
            logger.info(f"Created test suite: {suite_id}")
            return suite
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating test suite {suite_id}: {e}")
            raise

    def get_test_suite(self, suite_id: str) -> Optional[TestSuiteDB]:
        """
        Get a test suite by ID

        Args:
            suite_id: Suite ID

        Returns:
            TestSuiteDB instance or None
        """
        return self.db.query(TestSuiteDB).filter(TestSuiteDB.suite_id == suite_id).first()

    def get_all_test_suites(self, test_type: Optional[str] = None) -> List[TestSuiteDB]:
        """
        Get all test suites, optionally filtered by type

        Args:
            test_type: Optional test type filter

        Returns:
            List of TestSuiteDB instances
        """
        query = self.db.query(TestSuiteDB)
        if test_type:
            query = query.filter(TestSuiteDB.test_type == test_type)
        return query.all()

    def update_test_suite(
        self,
        suite_id: str,
        suite_name: Optional[str] = None,
        description: Optional[str] = None,
        coverage_target: Optional[float] = None,
        status: Optional[str] = None,
    ) -> Optional[TestSuiteDB]:
        """
        Update a test suite

        Args:
            suite_id: Suite ID
            suite_name: New suite name
            description: New description
            coverage_target: New coverage target
            status: New status

        Returns:
            Updated TestSuiteDB instance or None
        """
        try:
            suite = self.get_test_suite(suite_id)
            if not suite:
                return None

            if suite_name is not None:
                suite.suite_name = suite_name
            if description is not None:
                suite.description = description
            if coverage_target is not None:
                suite.coverage_target = coverage_target
            if status is not None:
                suite.status = status

            suite.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(suite)
            logger.info(f"Updated test suite: {suite_id}")
            return suite
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating test suite {suite_id}: {e}")
            raise

    def delete_test_suite(self, suite_id: str) -> bool:
        """
        Delete a test suite

        Args:
            suite_id: Suite ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            suite = self.get_test_suite(suite_id)
            if not suite:
                return False

            self.db.delete(suite)
            self.db.commit()
            logger.info(f"Deleted test suite: {suite_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting test suite {suite_id}: {e}")
            raise

    # ==================== Test Case Operations ====================

    def create_test_case(
        self,
        test_id: str,
        suite_id: str,
        test_name: str,
        description: str,
        test_type: str,
    ) -> TestCaseDB:
        """
        Create a test case

        Args:
            test_id: Test ID
            suite_id: Suite ID
            test_name: Test name
            description: Test description
            test_type: Test type

        Returns:
            Created TestCaseDB instance
        """
        try:
            test_case = TestCaseDB(
                id=str(uuid.uuid4()),
                test_id=test_id,
                suite_id=suite_id,
                test_name=test_name,
                description=description,
                test_type=test_type,
            )
            self.db.add(test_case)
            self.db.commit()
            self.db.refresh(test_case)

            # Update suite test count
            suite = self.get_test_suite(suite_id)
            if suite:
                suite.test_count += 1
                self.db.commit()

            logger.info(f"Created test case: {test_id}")
            return test_case
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating test case {test_id}: {e}")
            raise

    def get_test_case(self, test_id: str) -> Optional[TestCaseDB]:
        """
        Get a test case by ID

        Args:
            test_id: Test ID

        Returns:
            TestCaseDB instance or None
        """
        return self.db.query(TestCaseDB).filter(TestCaseDB.test_id == test_id).first()

    def get_test_cases_by_suite(self, suite_id: str) -> List[TestCaseDB]:
        """
        Get all test cases for a suite

        Args:
            suite_id: Suite ID

        Returns:
            List of TestCaseDB instances
        """
        return self.db.query(TestCaseDB).filter(TestCaseDB.suite_id == suite_id).all()

    def update_test_case(
        self,
        test_id: str,
        status: Optional[str] = None,
        duration: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> Optional[TestCaseDB]:
        """
        Update a test case

        Args:
            test_id: Test ID
            status: New status
            duration: Test duration
            error_message: Error message

        Returns:
            Updated TestCaseDB instance or None
        """
        try:
            test_case = self.get_test_case(test_id)
            if not test_case:
                return None

            if status is not None:
                test_case.status = status
            if duration is not None:
                test_case.duration = duration
            if error_message is not None:
                test_case.error_message = error_message

            test_case.updated_at = datetime.now(timezone.utc)
            if status in ["passed", "failed", "skipped"]:
                test_case.executed_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(test_case)
            logger.info(f"Updated test case: {test_id}")
            return test_case
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating test case {test_id}: {e}")
            raise

    # ==================== Test Report Operations ====================

    def create_test_report(
        self,
        report_id: str,
        suite_id: str,
        test_type: str,
        start_time: datetime,
        total_tests: int = 0,
        passed_tests: int = 0,
        failed_tests: int = 0,
        skipped_tests: int = 0,
        coverage: float = 0.0,
    ) -> TestReportDB:
        """
        Create a test report

        Args:
            report_id: Report ID
            suite_id: Suite ID
            test_type: Test type
            start_time: Start time
            total_tests: Total test count
            passed_tests: Passed test count
            failed_tests: Failed test count
            skipped_tests: Skipped test count
            coverage: Coverage percentage

        Returns:
            Created TestReportDB instance
        """
        try:
            report = TestReportDB(
                id=str(uuid.uuid4()),
                report_id=report_id,
                suite_id=suite_id,
                test_type=test_type,
                start_time=start_time,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                coverage=coverage,
            )
            self.db.add(report)
            self.db.commit()
            self.db.refresh(report)
            logger.info(f"Created test report: {report_id}")
            return report
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating test report {report_id}: {e}")
            raise

    def get_test_report(self, report_id: str) -> Optional[TestReportDB]:
        """
        Get a test report by ID

        Args:
            report_id: Report ID

        Returns:
            TestReportDB instance or None
        """
        return self.db.query(TestReportDB).filter(TestReportDB.report_id == report_id).first()

    def get_reports_by_suite(self, suite_id: str) -> List[TestReportDB]:
        """
        Get all reports for a suite

        Args:
            suite_id: Suite ID

        Returns:
            List of TestReportDB instances
        """
        return self.db.query(TestReportDB).filter(TestReportDB.suite_id == suite_id).all()

    def update_test_report(
        self,
        report_id: str,
        end_time: Optional[datetime] = None,
        total_tests: Optional[int] = None,
        passed_tests: Optional[int] = None,
        failed_tests: Optional[int] = None,
        skipped_tests: Optional[int] = None,
        coverage: Optional[float] = None,
    ) -> Optional[TestReportDB]:
        """
        Update a test report

        Args:
            report_id: Report ID
            end_time: End time
            total_tests: Total test count
            passed_tests: Passed test count
            failed_tests: Failed test count
            skipped_tests: Skipped test count
            coverage: Coverage percentage

        Returns:
            Updated TestReportDB instance or None
        """
        try:
            report = self.get_test_report(report_id)
            if not report:
                return None

            if end_time is not None:
                report.end_time = end_time
                if report.start_time:
                    report.duration_sec = (end_time - report.start_time).total_seconds()
            if total_tests is not None:
                report.total_tests = total_tests
            if passed_tests is not None:
                report.passed_tests = passed_tests
            if failed_tests is not None:
                report.failed_tests = failed_tests
            if skipped_tests is not None:
                report.skipped_tests = skipped_tests
            if coverage is not None:
                report.coverage = coverage

            self.db.commit()
            self.db.refresh(report)
            logger.info(f"Updated test report: {report_id}")
            return report
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating test report {report_id}: {e}")
            raise

    # ==================== Test Coverage Operations ====================

    def create_or_update_coverage(
        self,
        module_id: str,
        module_name: str,
        module_type: str,
        total_lines: int,
        covered_lines: int,
    ) -> TestCoverageDB:
        """
        Create or update test coverage

        Args:
            module_id: Module ID
            module_name: Module name
            module_type: Module type
            total_lines: Total lines
            covered_lines: Covered lines

        Returns:
            Created or updated TestCoverageDB instance
        """
        try:
            coverage_percentage = (covered_lines / total_lines * 100.0) if total_lines > 0 else 0.0
            coverage_level = self._calculate_coverage_level(coverage_percentage)

            existing = self.db.query(TestCoverageDB).filter(TestCoverageDB.module_id == module_id).first()

            if existing:
                existing.module_name = module_name
                existing.module_type = module_type
                existing.total_lines = total_lines
                existing.covered_lines = covered_lines
                existing.coverage_percentage = coverage_percentage
                existing.coverage_level = coverage_level
                existing.last_updated = datetime.now(timezone.utc)
                self.db.commit()
                self.db.refresh(existing)
                logger.info(f"Updated coverage for module: {module_id}")
                return existing
            else:
                coverage = TestCoverageDB(
                    id=str(uuid.uuid4()),
                    module_id=module_id,
                    module_name=module_name,
                    module_type=module_type,
                    total_lines=total_lines,
                    covered_lines=covered_lines,
                    coverage_percentage=coverage_percentage,
                    coverage_level=coverage_level,
                )
                self.db.add(coverage)
                self.db.commit()
                self.db.refresh(coverage)
                logger.info(f"Created coverage for module: {module_id}")
                return coverage
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating/updating coverage for module {module_id}: {e}")
            raise

    def get_coverage(self, module_id: str) -> Optional[TestCoverageDB]:
        """
        Get coverage by module ID

        Args:
            module_id: Module ID

        Returns:
            TestCoverageDB instance or None
        """
        return self.db.query(TestCoverageDB).filter(TestCoverageDB.module_id == module_id).first()

    def get_all_coverages(self, module_type: Optional[str] = None) -> List[TestCoverageDB]:
        """
        Get all coverages, optionally filtered by type

        Args:
            module_type: Optional module type filter

        Returns:
            List of TestCoverageDB instances
        """
        query = self.db.query(TestCoverageDB)
        if module_type:
            query = query.filter(TestCoverageDB.module_type == module_type)
        return query.all()

    def _calculate_coverage_level(self, percentage: float) -> str:
        """
        Calculate coverage level from percentage

        Args:
            percentage: Coverage percentage

        Returns:
            Coverage level string
        """
        if percentage >= 90.0:
            return "excellent"
        elif percentage >= 80.0:
            return "good"
        elif percentage >= 70.0:
            return "acceptable"
        else:
            return "needs_improvement"

    # ==================== Coverage Threshold Operations ====================

    def get_coverage_threshold(self, module_type: str) -> Optional[CoverageThresholdDB]:
        """
        Get coverage threshold by module type

        Args:
            module_type: Module type

        Returns:
            CoverageThresholdDB instance or None
        """
        return self.db.query(CoverageThresholdDB).filter(CoverageThresholdDB.module_type == module_type).first()

    def get_all_coverage_thresholds(self) -> List[CoverageThresholdDB]:
        """
        Get all coverage thresholds

        Returns:
            List of CoverageThresholdDB instances
        """
        return self.db.query(CoverageThresholdDB).all()

    # ==================== Automation Job Operations ====================

    def create_automation_job(
        self,
        job_id: str,
        job_name: str,
        job_type: str,
        trigger_type: str = "manual",
        created_by: Optional[str] = None,
    ) -> AutomationJobDB:
        """
        Create an automation job

        Args:
            job_id: Job ID
            job_name: Job name
            job_type: Job type
            trigger_type: Trigger type
            created_by: Creator username

        Returns:
            Created AutomationJobDB instance
        """
        try:
            job = AutomationJobDB(
                id=str(uuid.uuid4()),
                job_id=job_id,
                job_name=job_name,
                job_type=job_type,
                status="idle",
                trigger_type=trigger_type,
                created_by=created_by,
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            logger.info(f"Created automation job: {job_id}")
            return job
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating automation job {job_id}: {e}")
            raise

    def get_automation_job(self, job_id: str) -> Optional[AutomationJobDB]:
        """
        Get an automation job by ID

        Args:
            job_id: Job ID

        Returns:
            AutomationJobDB instance or None
        """
        return self.db.query(AutomationJobDB).filter(AutomationJobDB.job_id == job_id).first()

    def get_all_automation_jobs(self, status: Optional[str] = None) -> List[AutomationJobDB]:
        """
        Get all automation jobs, optionally filtered by status

        Args:
            status: Optional status filter

        Returns:
            List of AutomationJobDB instances
        """
        query = self.db.query(AutomationJobDB)
        if status:
            query = query.filter(AutomationJobDB.status == status)
        return query.all()

    def update_automation_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Optional[AutomationJobDB]:
        """
        Update an automation job

        Args:
            job_id: Job ID
            status: New status
            start_time: Start time
            end_time: End time

        Returns:
            Updated AutomationJobDB instance or None
        """
        try:
            job = self.get_automation_job(job_id)
            if not job:
                return None

            if status is not None:
                job.status = status
            if start_time is not None:
                job.start_time = start_time
            if end_time is not None:
                job.end_time = end_time
                if job.start_time:
                    job.duration_sec = (end_time - job.start_time).total_seconds()

            job.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(job)
            logger.info(f"Updated automation job: {job_id}")
            return job
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating automation job {job_id}: {e}")
            raise

    # ==================== CI/CD Pipeline Config Operations ====================

    def create_cicd_config(
        self,
        config_id: str,
        name: str,
        platform: str,
        config_content: str,
        created_by: Optional[str] = None,
    ) -> CICDPipelineConfigDB:
        """
        Create a CI/CD pipeline configuration

        Args:
            config_id: Config ID
            name: Config name
            platform: Platform name
            config_content: Configuration content
            created_by: Creator username

        Returns:
            Created CICDPipelineConfigDB instance
        """
        try:
            config = CICDPipelineConfigDB(
                id=str(uuid.uuid4()),
                config_id=config_id,
                name=name,
                platform=platform,
                config_content=config_content,
                created_by=created_by,
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            logger.info(f"Created CI/CD config: {config_id}")
            return config
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating CI/CD config {config_id}: {e}")
            raise

    def get_cicd_config(self, config_id: str) -> Optional[CICDPipelineConfigDB]:
        """
        Get a CI/CD config by ID

        Args:
            config_id: Config ID

        Returns:
            CICDPipelineConfigDB instance or None
        """
        return self.db.query(CICDPipelineConfigDB).filter(CICDPipelineConfigDB.config_id == config_id).first()

    # ==================== Notification Config Operations ====================

    def get_notification_config(self, config_name: str = "default") -> Optional[TestNotificationConfigDB]:
        """
        Get notification config by name

        Args:
            config_name: Config name

        Returns:
            TestNotificationConfigDB instance or None
        """
        return self.db.query(TestNotificationConfigDB).filter(TestNotificationConfigDB.config_name == config_name).first()

    def update_notification_config(
        self,
        config_name: str,
        enabled: Optional[bool] = None,
        on_success: Optional[bool] = None,
        on_failure: Optional[bool] = None,
        channels: Optional[List[str]] = None,
    ) -> Optional[TestNotificationConfigDB]:
        """
        Update notification config

        Args:
            config_name: Config name
            enabled: Enabled flag
            on_success: Notify on success
            on_failure: Notify on failure
            channels: Notification channels

        Returns:
            Updated TestNotificationConfigDB instance or None
        """
        try:
            config = self.get_notification_config(config_name)
            if not config:
                return None

            if enabled is not None:
                config.enabled = enabled
            if on_success is not None:
                config.on_success = on_success
            if on_failure is not None:
                config.on_failure = on_failure
            if channels is not None:
                config.channels = channels

            config.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(config)
            logger.info(f"Updated notification config: {config_name}")
            return config
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating notification config {config_name}: {e}")
            raise

    # ==================== Statistics Operations ====================

    def get_automation_statistics(self) -> Dict[str, Any]:
        """
        Get automation job statistics

        Returns:
            Statistics dictionary
        """
        total = self.db.query(AutomationJobDB).count()
        completed = self.db.query(AutomationJobDB).filter(AutomationJobDB.status == "completed").count()
        failed = self.db.query(AutomationJobDB).filter(AutomationJobDB.status == "failed").count()
        running = self.db.query(AutomationJobDB).filter(AutomationJobDB.status == "running").count()

        return {
            "total_jobs": total,
            "completed_jobs": completed,
            "failed_jobs": failed,
            "running_jobs": running,
            "success_rate": (completed / total * 100) if total > 0 else 0.0,
        }

    def get_coverage_statistics(self) -> Dict[str, Any]:
        """
        Get coverage statistics

        Returns:
            Statistics dictionary
        """
        coverages = self.get_all_coverages()
        total_modules = len(coverages)

        if total_modules == 0:
            return {
                "total_modules": 0,
                "average_coverage": 0.0,
                "modules_by_level": {},
            }

        avg_coverage = sum(c.coverage_percentage for c in coverages) / total_modules

        modules_by_level = {}
        for level in ["excellent", "good", "acceptable", "needs_improvement"]:
            modules_by_level[level] = len([c for c in coverages if c.coverage_level == level])

        return {
            "total_modules": total_modules,
            "average_coverage": avg_coverage,
            "modules_by_level": modules_by_level,
        }

    def get_framework_statistics(self) -> Dict[str, Any]:
        """
        Get test framework statistics

        Returns:
            Statistics dictionary
        """
        total_suites = self.db.query(TestSuiteDB).count()
        total_cases = self.db.query(TestCaseDB).count()
        total_reports = self.db.query(TestReportDB).count()

        suites_by_type = {}
        for test_type in ["unit", "integration", "end_to_end", "performance", "security"]:
            suites_by_type[test_type] = self.db.query(TestSuiteDB).filter(TestSuiteDB.test_type == test_type).count()

        cases_by_status = {}
        for status in ["pending", "running", "passed", "failed", "skipped"]:
            cases_by_status[status] = self.db.query(TestCaseDB).filter(TestCaseDB.status == status).count()

        return {
            "total_suites": total_suites,
            "total_cases": total_cases,
            "total_reports": total_reports,
            "suites_by_type": suites_by_type,
            "cases_by_status": cases_by_status,
        }
