# -*- coding: utf-8 -*-
"""
Test suite for Test Automation Advanced Router (Database-backed)
测试自动化高级路由测试套件（数据库版本）
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.test_automation_advanced_router import (
    ExecutionStatus,
    TestExecution,
    TestExecutionCreate,
    TestSuite,
    TestSuiteCreate,
    TestSuiteStatus,
    TestSuiteUpdate,
    get_current_user,
    router,
    get_test_suites,
    create_test_suite,
    get_test_suite,
    update_test_suite,
    delete_test_suite,
    get_test_executions,
    create_test_execution,
    get_test_execution,
    cancel_test_execution,
)
from core.authentication import UserInDB
from core.database import SessionLocal
from core.models import TestSuiteDB, TestExecutionDB


# ============ Fixtures ============


@pytest.fixture
def mock_user():
    """Create a mock user"""
    return UserInDB(
        id=1,
        username="testuser",
        full_name="Test User",
        email="test@example.com",
        role="admin",
        disabled=False,
        hashed_password="hashed",
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user"""
    return UserInDB(
        id=2,
        username="regularuser",
        full_name="Regular User",
        email="regular@example.com",
        role="user",
        disabled=False,
        hashed_password="hashed",
    )


@pytest.fixture
def client():
    """Create a test client"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def cleanup_database(db_session):
    """Clean up database before and after each test"""
    # Clean up before test
    db_session.query(TestExecutionDB).delete()
    db_session.query(TestSuiteDB).delete()
    db_session.commit()
    yield
    # Clean up after test
    db_session.query(TestExecutionDB).delete()
    db_session.query(TestSuiteDB).delete()
    db_session.commit()


@pytest.fixture
def sample_suite(db_session):
    """Create a sample test suite"""
    suite = TestSuiteDB(
        id="TS-12345678",
        name="Sample Test Suite",
        description="A sample test suite",
        test_type="integration",
        framework="pytest",
        status="active",
        created_by="testuser",
    )
    db_session.add(suite)
    db_session.commit()
    return suite


@pytest.fixture
def sample_execution(db_session, sample_suite):
    """Create a sample test execution"""
    execution = TestExecutionDB(
        id="TE-12345678",
        suite_id=sample_suite.id,
        suite_name=sample_suite.name,
        status="completed",
        started_at=datetime.now(),
        completed_at=datetime.now(),
        total_tests=10,
        passed_tests=8,
        failed_tests=2,
        skipped_tests=0,
        trigger_type="manual",
        triggered_by="testuser",
    )
    db_session.add(execution)
    db_session.commit()
    return execution


# ============ Suite Endpoints Tests ============


class TestSuiteEndpoints:
    """Test suite endpoints"""

    @pytest.mark.asyncio
    async def test_get_test_suites_success(self, mock_user, db_session):
        """Test successful test suites retrieval"""
        # Create a test suite
        suite = TestSuiteDB(
            id="TS-12345678",
            name="Test Suite 1",
            description="Test suite 1",
            test_type="integration",
            framework="pytest",
            status="active",
            created_by="testuser",
        )
        db_session.add(suite)
        db_session.commit()

        result = await get_test_suites(current_user=mock_user, db=db_session)

        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_test_suites_with_status_filter(self, mock_user, db_session):
        """Test test suites retrieval with status filter"""
        # Create test suites with different statuses
        suite1 = TestSuiteDB(
            id="TS-12345678",
            name="Active Suite",
            description="Active suite",
            test_type="integration",
            framework="pytest",
            status="active",
            created_by="testuser",
        )
        suite2 = TestSuiteDB(
            id="TS-87654321",
            name="Inactive Suite",
            description="Inactive suite",
            test_type="unit",
            framework="pytest",
            status="inactive",
            created_by="testuser",
        )
        db_session.add(suite1)
        db_session.add(suite2)
        db_session.commit()

        result = await get_test_suites(status=TestSuiteStatus.ACTIVE, current_user=mock_user, db=db_session)

        assert isinstance(result, list)
        assert all(s.status == TestSuiteStatus.ACTIVE for s in result)

    @pytest.mark.asyncio
    async def test_get_test_suites_with_pagination(self, mock_user, db_session):
        """Test test suites retrieval with pagination"""
        # Create multiple test suites
        for i in range(3):
            suite = TestSuiteDB(
                id=f"TS-{i:08d}",
                name=f"Test Suite {i}",
                description=f"Test suite {i}",
                test_type="integration",
                framework="pytest",
                status="active",
                created_by="testuser",
            )
            db_session.add(suite)
        db_session.commit()

        result = await get_test_suites(limit=2, offset=0, current_user=mock_user, db=db_session)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_create_test_suite_success(self, mock_user, db_session):
        """Test successful test suite creation"""
        suite_create = TestSuiteCreate(
            name="New Test Suite",
            description="A new test suite",
            test_type="integration",
            framework="pytest",
        )

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await create_test_suite(suite_create, request, current_user=mock_user, db=db_session)

        assert isinstance(result, TestSuite)
        assert result.name == "New Test Suite"
        assert result.test_type == "integration"
        assert result.status == TestSuiteStatus.ACTIVE
        assert result.created_by == "testuser"

    @pytest.mark.asyncio
    async def test_create_test_suite_validation_name_min(self, mock_user, db_session):
        """Test test suite creation with name too short"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestSuiteCreate(name="", test_type="integration")

    @pytest.mark.asyncio
    async def test_create_test_suite_validation_name_max(self, mock_user, db_session):
        """Test test suite creation with name too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestSuiteCreate(name="a" * 201, test_type="integration")

    @pytest.mark.asyncio
    async def test_create_test_suite_validation_test_type(self, mock_user, db_session):
        """Test test suite creation with invalid test type"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestSuiteCreate(name="Test", test_type="invalid")

    @pytest.mark.asyncio
    async def test_get_test_suite_success(self, mock_user, sample_suite, db_session):
        """Test successful test suite retrieval"""
        result = await get_test_suite(sample_suite.id, current_user=mock_user, db=db_session)

        assert isinstance(result, TestSuite)
        assert result.id == sample_suite.id

    @pytest.mark.asyncio
    async def test_get_test_suite_not_found(self, mock_user, db_session):
        """Test test suite retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await get_test_suite("nonexistent", current_user=mock_user, db=db_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test suite not found"

    @pytest.mark.asyncio
    async def test_update_test_suite_success(self, mock_user, sample_suite, db_session):
        """Test successful test suite update"""
        suite_update = TestSuiteUpdate(name="Updated Name", status=TestSuiteStatus.INACTIVE)

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await update_test_suite(
            sample_suite.id, suite_update, request, current_user=mock_user, db=db_session
        )

        assert isinstance(result, TestSuite)
        assert result.name == "Updated Name"
        assert result.status == TestSuiteStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_update_test_suite_not_found(self, mock_user, db_session):
        """Test test suite update when not found"""
        suite_update = TestSuiteUpdate(name="Updated Name")

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await update_test_suite(
                "nonexistent", suite_update, request, current_user=mock_user, db=db_session
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test suite not found"

    @pytest.mark.asyncio
    async def test_delete_test_suite_success(self, mock_user, sample_suite, db_session):
        """Test successful test suite deletion"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        await delete_test_suite(sample_suite.id, request, current_user=mock_user, db=db_session)

        # Verify deletion
        deleted = db_session.query(TestSuiteDB).filter(TestSuiteDB.id == sample_suite.id).first()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_test_suite_not_found(self, mock_user, db_session):
        """Test test suite deletion when not found"""
        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await delete_test_suite("nonexistent", request, current_user=mock_user, db=db_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test suite not found"

    @pytest.mark.asyncio
    async def test_delete_test_suite_cascades_executions(self, mock_user, sample_suite, db_session):
        """Test test suite deletion cascades to executions"""
        # Create an execution for the suite
        execution = TestExecutionDB(
            id="TE-12345678",
            suite_id=sample_suite.id,
            suite_name=sample_suite.name,
            status="completed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            skipped_tests=0,
            trigger_type="manual",
            triggered_by="testuser",
        )
        db_session.add(execution)
        db_session.commit()

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Save execution ID before deletion
        execution_id = execution.id

        await delete_test_suite(sample_suite.id, request, current_user=mock_user, db=db_session)

        # Verify execution is also deleted
        db_session.expire_all()
        deleted_exec = db_session.query(TestExecutionDB).filter(TestExecutionDB.id == execution_id).first()
        assert deleted_exec is None


# ============ Execution Endpoints Tests ============


class TestExecutionEndpoints:
    """Test execution endpoints"""

    @pytest.mark.asyncio
    async def test_get_test_executions_success(self, mock_user, db_session, sample_suite):
        """Test successful test executions retrieval"""
        # Create test executions
        for i in range(2):
            execution = TestExecutionDB(
                id=f"TE-{i:08d}",
                suite_id=sample_suite.id,
                suite_name=sample_suite.name,
                status="completed",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                total_tests=10,
                passed_tests=8,
                failed_tests=2,
                skipped_tests=0,
                trigger_type="manual",
                triggered_by="testuser",
            )
            db_session.add(execution)
        db_session.commit()

        result = await get_test_executions(current_user=mock_user, db=db_session)

        assert isinstance(result, list)
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_get_test_executions_with_suite_filter(self, mock_user, sample_suite, db_session):
        """Test test executions retrieval with suite filter"""
        # Create an execution for the suite
        execution = TestExecutionDB(
            id="TE-12345678",
            suite_id=sample_suite.id,
            suite_name=sample_suite.name,
            status="completed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            skipped_tests=0,
            trigger_type="manual",
            triggered_by="testuser",
        )
        db_session.add(execution)
        db_session.commit()

        result = await get_test_executions(suite_id=sample_suite.id, current_user=mock_user, db=db_session)

        assert isinstance(result, list)
        assert all(e.suite_id == sample_suite.id for e in result)

    @pytest.mark.asyncio
    async def test_get_test_executions_with_status_filter(self, mock_user, db_session, sample_suite):
        """Test test executions retrieval with status filter"""
        # Create executions with different statuses
        exec1 = TestExecutionDB(
            id="TE-12345678",
            suite_id=sample_suite.id,
            suite_name=sample_suite.name,
            status="completed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            skipped_tests=0,
            trigger_type="manual",
            triggered_by="testuser",
        )
        exec2 = TestExecutionDB(
            id="TE-87654321",
            suite_id=sample_suite.id,
            suite_name=sample_suite.name,
            status="pending",
            started_at=datetime.now(),
            total_tests=10,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            trigger_type="manual",
            triggered_by="testuser",
        )
        db_session.add(exec1)
        db_session.add(exec2)
        db_session.commit()

        result = await get_test_executions(
            status=ExecutionStatus.COMPLETED, current_user=mock_user, db=db_session
        )

        assert isinstance(result, list)
        assert all(e.status == ExecutionStatus.COMPLETED for e in result)

    @pytest.mark.asyncio
    async def test_get_test_executions_with_pagination(self, mock_user, db_session, sample_suite):
        """Test test executions retrieval with pagination"""
        # Create multiple executions
        for i in range(3):
            execution = TestExecutionDB(
                id=f"TE-{i:08d}",
                suite_id=sample_suite.id,
                suite_name=sample_suite.name,
                status="completed",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                total_tests=10,
                passed_tests=8,
                failed_tests=2,
                skipped_tests=0,
                trigger_type="manual",
                triggered_by="testuser",
            )
            db_session.add(execution)
        db_session.commit()

        result = await get_test_executions(limit=2, offset=0, current_user=mock_user, db=db_session)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_create_test_execution_success(self, mock_user, sample_suite, db_session):
        """Test successful test execution creation"""
        execution_create = TestExecutionCreate(suite_id=sample_suite.id, trigger_type="manual")

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await create_test_execution(
            execution_create, request, current_user=mock_user, db=db_session
        )

        assert isinstance(result, TestExecution)
        assert result.suite_id == sample_suite.id
        assert result.status == ExecutionStatus.PENDING
        assert result.triggered_by == "testuser"

    @pytest.mark.asyncio
    async def test_create_test_execution_not_found(self, mock_user, db_session):
        """Test test execution creation when suite not found"""
        execution_create = TestExecutionCreate(suite_id="nonexistent")

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await create_test_execution(execution_create, request, current_user=mock_user, db=db_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test suite not found"

    @pytest.mark.asyncio
    async def test_create_test_execution_validation_trigger_type(self, mock_user, db_session):
        """Test test execution creation with invalid trigger type"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestExecutionCreate(suite_id="test", trigger_type="invalid")

    @pytest.mark.asyncio
    async def test_get_test_execution_success(self, mock_user, sample_execution, db_session):
        """Test successful test execution retrieval"""
        result = await get_test_execution(sample_execution.id, current_user=mock_user, db=db_session)

        assert isinstance(result, TestExecution)
        assert result.id == sample_execution.id

    @pytest.mark.asyncio
    async def test_get_test_execution_not_found(self, mock_user, db_session):
        """Test test execution retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await get_test_execution("nonexistent", current_user=mock_user, db=db_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Execution not found"

    @pytest.mark.asyncio
    async def test_cancel_test_execution_success(self, mock_user, sample_execution, db_session):
        """Test successful test execution cancellation"""
        # Set execution to pending
        sample_execution.status = "pending"
        db_session.commit()

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await cancel_test_execution(
            sample_execution.id, request, current_user=mock_user, db=db_session
        )

        assert isinstance(result, TestExecution)
        assert result.status == ExecutionStatus.CANCELLED
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_test_execution_not_found(self, mock_user, db_session):
        """Test test execution cancellation when not found"""
        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await cancel_test_execution("nonexistent", request, current_user=mock_user, db=db_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Execution not found"

    @pytest.mark.asyncio
    async def test_cancel_test_execution_invalid_status(
        self, mock_user, sample_execution, db_session
    ):
        """Test test execution cancellation with invalid status"""
        # Set execution to completed
        sample_execution.status = "completed"
        db_session.commit()

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await cancel_test_execution(sample_execution.id, request, current_user=mock_user, db=db_session)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot cancel" in exc_info.value.detail.lower()


# ============ Authentication Tests ============


class TestAuthentication:
    """Test authentication and authorization"""

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """Test get_current_user with no token returns fake admin"""
        result = await get_current_user(token=None)

        assert result.username == "dev-admin"
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token returns fake admin"""
        with patch("api.test_automation_advanced_router.verify_token", return_value=None):
            result = await get_current_user(token="invalid")

            assert result.username == "dev-admin"


# ============ Data Validation Tests ============


class TestDataValidation:
    """Test data validation for models"""

    def test_test_suite_create_name_min_validation(self):
        """Test TestSuiteCreate name min length validation"""
        with pytest.raises(Exception):
            TestSuiteCreate(name="", test_type="integration")

    def test_test_suite_create_name_max_validation(self):
        """Test TestSuiteCreate name max length validation"""
        with pytest.raises(Exception):
            TestSuiteCreate(name="a" * 201, test_type="integration")

    def test_test_suite_create_description_max_validation(self):
        """Test TestSuiteCreate description max length validation"""
        with pytest.raises(Exception):
            TestSuiteCreate(name="Test", description="a" * 1001, test_type="integration")

    def test_test_suite_create_test_type_validation(self):
        """Test TestSuiteCreate test type pattern validation"""
        with pytest.raises(Exception):
            TestSuiteCreate(name="Test", test_type="invalid")

    def test_test_suite_create_schedule_max_validation(self):
        """Test TestSuiteCreate schedule max length validation"""
        with pytest.raises(Exception):
            TestSuiteCreate(name="Test", test_type="integration", schedule="a" * 101)

    def test_test_suite_update_name_min_validation(self):
        """Test TestSuiteUpdate name min length validation"""
        with pytest.raises(Exception):
            TestSuiteUpdate(name="")

    def test_test_suite_update_name_max_validation(self):
        """Test TestSuiteUpdate name max length validation"""
        with pytest.raises(Exception):
            TestSuiteUpdate(name="a" * 201)

    def test_test_execution_create_trigger_type_validation(self):
        """Test TestExecutionCreate trigger type pattern validation"""
        with pytest.raises(Exception):
            TestExecutionCreate(suite_id="test", trigger_type="invalid")

    def test_test_execution_create_environment_max_validation(self):
        """Test TestExecutionCreate environment max length validation"""
        with pytest.raises(Exception):
            TestExecutionCreate(suite_id="test", environment="a" * 51)


# ============ Enum Tests ============


class TestEnums:
    """Test enum values"""

    def test_test_suite_status_values(self):
        """Test TestSuiteStatus enum values"""
        assert TestSuiteStatus.ACTIVE == "active"
        assert TestSuiteStatus.INACTIVE == "inactive"
        assert TestSuiteStatus.ARCHIVED == "archived"

    def test_execution_status_values(self):
        """Test ExecutionStatus enum values"""
        assert ExecutionStatus.PENDING == "pending"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.FAILED == "failed"
        assert ExecutionStatus.CANCELLED == "cancelled"
