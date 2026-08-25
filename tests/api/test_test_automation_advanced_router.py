# -*- coding: utf-8 -*-
"""
Test suite for test_automation_advanced_router.py
Tests all endpoints with comprehensive coverage including:
- GET, POST, PATCH, DELETE operations
- Normal and error cases
- Data validation
- Permission control
- Mock dependencies
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.test_automation_advanced_router import (
    FAKE_ADMIN,
    ExecutionStatus,
    TestExecution,
    TestExecutionCreate,
    TestSuite,
    TestSuiteCreate,
    TestSuiteStatus,
    TestSuiteUpdate,
    _init_test_executions,
    _init_test_suites,
    _test_executions,
    _test_suites,
    get_current_user,
    router,
)
from core.authentication import UserInDB

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
def clear_data():
    """Clear in-memory data before each test"""
    _test_suites.clear()
    _test_executions.clear()
    yield
    _test_suites.clear()
    _test_executions.clear()


@pytest.fixture
def sample_suite(clear_data):
    """Create a sample test suite"""
    _init_test_suites()
    return list(_test_suites.values())[0]


@pytest.fixture
def sample_execution(clear_data):
    """Create a sample test execution"""
    _init_test_suites()
    _init_test_executions()
    return list(_test_executions.values())[0]


# ============ Suite Endpoints Tests ============


class TestSuiteEndpoints:
    """Test suite endpoints"""

    @pytest.mark.asyncio
    async def test_get_test_suites_success(self, mock_user, clear_data):
        """Test successful test suites retrieval"""
        _init_test_suites()
        result = await router.get_test_suites(current_user=mock_user)

        assert isinstance(result, list)
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_get_test_suites_with_status_filter(self, mock_user, clear_data):
        """Test test suites retrieval with status filter"""
        _init_test_suites()
        result = await router.get_test_suites(status=TestSuiteStatus.ACTIVE, current_user=mock_user)

        assert isinstance(result, list)
        assert all(s.status == TestSuiteStatus.ACTIVE for s in result)

    @pytest.mark.asyncio
    async def test_get_test_suites_with_pagination(self, mock_user, clear_data):
        """Test test suites retrieval with pagination"""
        _init_test_suites()
        result = await router.get_test_suites(limit=1, offset=0, current_user=mock_user)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_test_suite_success(self, mock_user, clear_data):
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

        result = await router.create_test_suite(suite_create, request, current_user=mock_user)

        assert isinstance(result, TestSuite)
        assert result.name == "New Test Suite"
        assert result.test_type == "integration"
        assert result.status == TestSuiteStatus.ACTIVE
        assert result.created_by == "testuser"

    @pytest.mark.asyncio
    async def test_create_test_suite_validation_name_min(self, mock_user, clear_data):
        """Test test suite creation with name too short"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestSuiteCreate(name="", test_type="integration")

    @pytest.mark.asyncio
    async def test_create_test_suite_validation_name_max(self, mock_user, clear_data):
        """Test test suite creation with name too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestSuiteCreate(name="a" * 201, test_type="integration")

    @pytest.mark.asyncio
    async def test_create_test_suite_validation_test_type(self, mock_user, clear_data):
        """Test test suite creation with invalid test type"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestSuiteCreate(name="Test", test_type="invalid")

    @pytest.mark.asyncio
    async def test_get_test_suite_success(self, mock_user, sample_suite, clear_data):
        """Test successful test suite retrieval"""
        result = await router.get_test_suite(sample_suite.id, current_user=mock_user)

        assert isinstance(result, TestSuite)
        assert result.id == sample_suite.id

    @pytest.mark.asyncio
    async def test_get_test_suite_not_found(self, mock_user, clear_data):
        """Test test suite retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.get_test_suite("nonexistent", current_user=mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test suite not found"

    @pytest.mark.asyncio
    async def test_update_test_suite_success(self, mock_user, sample_suite, clear_data):
        """Test successful test suite update"""
        suite_update = TestSuiteUpdate(name="Updated Name", status=TestSuiteStatus.INACTIVE)

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await router.update_test_suite(
            sample_suite.id, suite_update, request, current_user=mock_user
        )

        assert isinstance(result, TestSuite)
        assert result.name == "Updated Name"
        assert result.status == TestSuiteStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_update_test_suite_not_found(self, mock_user, clear_data):
        """Test test suite update when not found"""
        suite_update = TestSuiteUpdate(name="Updated Name")

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.update_test_suite(
                "nonexistent", suite_update, request, current_user=mock_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test suite not found"

    @pytest.mark.asyncio
    async def test_delete_test_suite_success(self, mock_user, sample_suite, clear_data):
        """Test successful test suite deletion"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        await router.delete_test_suite(sample_suite.id, request, current_user=mock_user)

        assert sample_suite.id not in _test_suites

    @pytest.mark.asyncio
    async def test_delete_test_suite_not_found(self, mock_user, clear_data):
        """Test test suite deletion when not found"""
        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.delete_test_suite("nonexistent", request, current_user=mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test suite not found"

    @pytest.mark.asyncio
    async def test_delete_test_suite_cascades_executions(self, mock_user, sample_suite, clear_data):
        """Test test suite deletion cascades to executions"""
        _init_test_executions()

        # Create an execution for the suite
        execution_id = "exec-1"
        _test_executions[execution_id] = TestExecution(
            id=execution_id,
            suite_id=sample_suite.id,
            suite_name=sample_suite.name,
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now(),
            total_tests=10,
            triggered_by="testuser",
        )

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        await router.delete_test_suite(sample_suite.id, request, current_user=mock_user)

        assert execution_id not in _test_executions


# ============ Execution Endpoints Tests ============


class TestExecutionEndpoints:
    """Test execution endpoints"""

    @pytest.mark.asyncio
    async def test_get_test_executions_success(self, mock_user, clear_data):
        """Test successful test executions retrieval"""
        _init_test_suites()
        _init_test_executions()
        result = await router.get_test_executions(current_user=mock_user)

        assert isinstance(result, list)
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_get_test_executions_with_suite_filter(self, mock_user, sample_suite, clear_data):
        """Test test executions retrieval with suite filter"""
        _init_test_executions()
        result = await router.get_test_executions(suite_id=sample_suite.id, current_user=mock_user)

        assert isinstance(result, list)
        assert all(e.suite_id == sample_suite.id for e in result)

    @pytest.mark.asyncio
    async def test_get_test_executions_with_status_filter(self, mock_user, clear_data):
        """Test test executions retrieval with status filter"""
        _init_test_executions()
        result = await router.get_test_executions(
            status=ExecutionStatus.COMPLETED, current_user=mock_user
        )

        assert isinstance(result, list)
        assert all(e.status == ExecutionStatus.COMPLETED for e in result)

    @pytest.mark.asyncio
    async def test_get_test_executions_with_pagination(self, mock_user, clear_data):
        """Test test executions retrieval with pagination"""
        _init_test_executions()
        result = await router.get_test_executions(limit=1, offset=0, current_user=mock_user)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_test_execution_success(self, mock_user, sample_suite, clear_data):
        """Test successful test execution creation"""
        execution_create = TestExecutionCreate(suite_id=sample_suite.id, trigger_type="manual")

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await router.create_test_execution(
            execution_create, request, current_user=mock_user
        )

        assert isinstance(result, TestExecution)
        assert result.suite_id == sample_suite.id
        assert result.status == ExecutionStatus.PENDING
        assert result.triggered_by == "testuser"

    @pytest.mark.asyncio
    async def test_create_test_execution_not_found(self, mock_user, clear_data):
        """Test test execution creation when suite not found"""
        execution_create = TestExecutionCreate(suite_id="nonexistent")

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.create_test_execution(execution_create, request, current_user=mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test suite not found"

    @pytest.mark.asyncio
    async def test_create_test_execution_validation_trigger_type(self, mock_user, clear_data):
        """Test test execution creation with invalid trigger type"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestExecutionCreate(suite_id="test", trigger_type="invalid")

    @pytest.mark.asyncio
    async def test_get_test_execution_success(self, mock_user, sample_execution, clear_data):
        """Test successful test execution retrieval"""
        result = await router.get_test_execution(sample_execution.id, current_user=mock_user)

        assert isinstance(result, TestExecution)
        assert result.id == sample_execution.id

    @pytest.mark.asyncio
    async def test_get_test_execution_not_found(self, mock_user, clear_data):
        """Test test execution retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.get_test_execution("nonexistent", current_user=mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Execution not found"

    @pytest.mark.asyncio
    async def test_cancel_test_execution_success(self, mock_user, sample_execution, clear_data):
        """Test successful test execution cancellation"""
        # Set execution to pending
        sample_execution.status = ExecutionStatus.PENDING
        _test_executions[sample_execution.id] = sample_execution

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await router.cancel_test_execution(
            sample_execution.id, request, current_user=mock_user
        )

        assert isinstance(result, TestExecution)
        assert result.status == ExecutionStatus.CANCELLED
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_test_execution_not_found(self, mock_user, clear_data):
        """Test test execution cancellation when not found"""
        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.cancel_test_execution("nonexistent", request, current_user=mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Execution not found"

    @pytest.mark.asyncio
    async def test_cancel_test_execution_invalid_status(
        self, mock_user, sample_execution, clear_data
    ):
        """Test test execution cancellation with invalid status"""
        # Set execution to completed
        sample_execution.status = ExecutionStatus.COMPLETED
        _test_executions[sample_execution.id] = sample_execution

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.cancel_test_execution(sample_execution.id, request, current_user=mock_user)

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


# ============ Integration Tests ============


class TestIntegration:
    """Integration tests for test automation operations"""

    @pytest.mark.asyncio
    async def test_full_suite_workflow(self, mock_user, clear_data):
        """Test complete suite workflow"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create suite
        suite_create = TestSuiteCreate(name="Workflow Test Suite", test_type="integration")
        suite = await router.create_test_suite(suite_create, request, current_user=mock_user)
        assert suite.name == "Workflow Test Suite"

        # Get suite
        retrieved = await router.get_test_suite(suite.id, current_user=mock_user)
        assert retrieved.id == suite.id

        # Update suite
        suite_update = TestSuiteUpdate(name="Updated Workflow Suite")
        updated = await router.update_test_suite(
            suite.id, suite_update, request, current_user=mock_user
        )
        assert updated.name == "Updated Workflow Suite"

        # Delete suite
        await router.delete_test_suite(suite.id, request, current_user=mock_user)
        assert suite.id not in _test_suites

    @pytest.mark.asyncio
    async def test_full_execution_workflow(self, mock_user, clear_data):
        """Test complete execution workflow"""
        _init_test_suites()
        suite = list(_test_suites.values())[0]

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create execution
        execution_create = TestExecutionCreate(suite_id=suite.id)
        execution = await router.create_test_execution(
            execution_create, request, current_user=mock_user
        )
        assert execution.status == ExecutionStatus.PENDING

        # Get execution
        retrieved = await router.get_test_execution(execution.id, current_user=mock_user)
        assert retrieved.id == execution.id

        # Cancel execution
        cancelled = await router.cancel_test_execution(
            execution.id, request, current_user=mock_user
        )
        assert cancelled.status == ExecutionStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_suite_with_executions_workflow(self, mock_user, clear_data):
        """Test suite with multiple executions"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create suite
        suite_create = TestSuiteCreate(name="Multi-Exec Suite", test_type="integration")
        suite = await router.create_test_suite(suite_create, request, current_user=mock_user)

        # Create multiple executions
        for i in range(3):
            execution_create = TestExecutionCreate(suite_id=suite.id)
            await router.create_test_execution(execution_create, request, current_user=mock_user)

        # Get executions for suite
        executions = await router.get_test_executions(suite_id=suite.id, current_user=mock_user)
        assert len(executions) == 3


# ============ Error Handling Tests ============


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_concurrent_suite_creation(self, mock_user, clear_data):
        """Test concurrent suite creation"""
        import asyncio

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        async def create_suite():
            suite_create = TestSuiteCreate(
                name=f"Suite-{asyncio.current_task().get_name()}", test_type="integration"
            )
            await router.create_test_suite(suite_create, request, current_user=mock_user)

        # Run multiple concurrent creations
        await asyncio.gather(*[create_suite() for _ in range(5)])

        # Should not raise errors
        suites = await router.get_test_suites(current_user=mock_user)
        assert len(suites) >= 5

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, mock_user, clear_data):
        """Test handling of large datasets"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create many suites
        for i in range(50):
            suite_create = TestSuiteCreate(name=f"Suite-{i}", test_type="integration")
            await router.create_test_suite(suite_create, request, current_user=mock_user)

        # Should handle pagination correctly
        result = await router.get_test_suites(limit=20, current_user=mock_user)
        assert len(result) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
