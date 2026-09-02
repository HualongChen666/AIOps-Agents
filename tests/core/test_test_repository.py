# -*- coding: utf-8 -*-
"""
Unit tests for TestRepository
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.database import Base
from core.test_repository import TestRepository


@pytest.fixture(scope="function")
def db():
    """Create a fresh in-memory database for each test"""
    # Import models here to avoid circular import issues
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

    # Create in-memory database for this test
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def repository(db):
    """Create a TestRepository instance"""
    return TestRepository(db)


class TestTestRepository:
    """Test TestRepository CRUD operations"""

    def test_create_test_suite(self, repository):
        """Test creating a test suite"""
        suite = repository.create_test_suite(
            suite_id="test_suite_1",
            suite_name="Test Suite 1",
            test_type="unit",
            description="Unit test suite",
            coverage_target=80.0,
            created_by="test_user",
        )

        assert suite is not None
        assert suite.suite_id == "test_suite_1"
        assert suite.suite_name == "Test Suite 1"
        assert suite.test_type == "unit"
        assert suite.coverage_target == 80.0

    def test_get_test_suite(self, repository):
        """Test getting a test suite"""
        repository.create_test_suite(
            suite_id="test_suite_1",
            suite_name="Test Suite 1",
            test_type="unit",
            description="Unit test suite",
        )

        suite = repository.get_test_suite("test_suite_1")

        assert suite is not None
        assert suite.suite_id == "test_suite_1"

    def test_get_all_test_suites(self, repository):
        """Test getting all test suites"""
        repository.create_test_suite(
            suite_id="test_suite_1",
            suite_name="Test Suite 1",
            test_type="unit",
            description="Unit test suite",
        )
        repository.create_test_suite(
            suite_id="test_suite_2",
            suite_name="Test Suite 2",
            test_type="integration",
            description="Integration test suite",
        )

        suites = repository.get_all_test_suites()

        assert len(suites) == 2

    def test_create_test_coverage(self, repository):
        """Test creating test coverage"""
        coverage = repository.create_or_update_coverage(
            module_id="module_1",
            module_name="Module 1",
            module_type="core",
            total_lines=1000,
            covered_lines=800,
        )

        assert coverage is not None
        assert coverage.module_id == "module_1"
        assert coverage.coverage_percentage == 80.0
        assert coverage.coverage_level == "good"

    def test_update_test_coverage(self, repository):
        """Test updating test coverage"""
        repository.create_or_update_coverage(
            module_id="module_1",
            module_name="Module 1",
            module_type="core",
            total_lines=1000,
            covered_lines=800,
        )

        coverage = repository.create_or_update_coverage(
            module_id="module_1",
            module_name="Module 1",
            module_type="core",
            total_lines=1000,
            covered_lines=900,
        )

        assert coverage.coverage_percentage == 90.0
        assert coverage.coverage_level == "excellent"

    def test_create_automation_job(self, repository):
        """Test creating an automation job"""
        job = repository.create_automation_job(
            job_id="job_1",
            job_name="Test Job 1",
            job_type="unit_test",
            trigger_type="manual",
            created_by="test_user",
        )

        assert job is not None
        assert job.job_id == "job_1"
        assert job.job_name == "Test Job 1"
        assert job.status == "idle"

    def test_update_automation_job(self, repository):
        """Test updating an automation job"""
        repository.create_automation_job(
            job_id="job_1",
            job_name="Test Job 1",
            job_type="unit_test",
            trigger_type="manual",
        )

        start_time = datetime.now(timezone.utc)
        job = repository.update_automation_job(
            job_id="job_1",
            status="running",
            start_time=start_time,
        )

        assert job is not None
        assert job.status == "running"
        assert job.start_time is not None

    def test_get_coverage_statistics(self, repository):
        """Test getting coverage statistics"""
        repository.create_or_update_coverage(
            module_id="module_1",
            module_name="Module 1",
            module_type="core",
            total_lines=1000,
            covered_lines=800,
        )
        repository.create_or_update_coverage(
            module_id="module_2",
            module_name="Module 2",
            module_type="core",
            total_lines=1000,
            covered_lines=900,
        )

        stats = repository.get_coverage_statistics()

        assert stats["total_modules"] == 2
        assert stats["average_coverage"] == 85.0

    def test_get_automation_statistics(self, repository):
        """Test getting automation statistics"""
        repository.create_automation_job(
            job_id="job_1",
            job_name="Test Job 1",
            job_type="unit_test",
            trigger_type="manual",
        )
        repository.create_automation_job(
            job_id="job_2",
            job_name="Test Job 2",
            job_type="unit_test",
            trigger_type="manual",
        )

        repository.update_automation_job(job_id="job_1", status="completed")
        repository.update_automation_job(job_id="job_2", status="failed")

        stats = repository.get_automation_statistics()

        assert stats["total_jobs"] == 2
        assert stats["completed_jobs"] == 1
        assert stats["failed_jobs"] == 1

    def test_get_framework_statistics(self, repository):
        """Test getting framework statistics"""
        repository.create_test_suite(
            suite_id="test_suite_1",
            suite_name="Test Suite 1",
            test_type="unit",
            description="Unit test suite",
        )
        repository.create_test_suite(
            suite_id="test_suite_2",
            suite_name="Test Suite 2",
            test_type="integration",
            description="Integration test suite",
        )

        stats = repository.get_framework_statistics()

        assert stats["total_suites"] == 2
        assert stats["suites_by_type"]["unit"] == 1
        assert stats["suites_by_type"]["integration"] == 1
