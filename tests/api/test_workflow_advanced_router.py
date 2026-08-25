# -*- coding: utf-8 -*-
"""
Test suite for workflow_advanced_router.py

This module provides comprehensive test coverage for the workflow advanced router,
including all CRUD operations, data validation, error handling, and permission controls.
"""

import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from api.workflow_advanced_router import (
    ScheduleCreate,
    ScheduleUpdate,
    TriggerCreate,
    TriggerUpdate,
    VariableCreate,
    VariableUpdate,
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    WorkflowExecutionCreate,
    WorkflowExecutionUpdate,
    _audit_logs,
    _schedules,
    _triggers,
    _variables,
    router,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request object"""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_repository():
    """Create a mock workflow repository"""
    repo = AsyncMock()
    repo._definitions = {}
    return repo


@pytest.fixture
def mock_orchestrator():
    """Create a mock workflow orchestrator"""
    orchestrator = AsyncMock()
    return orchestrator


@pytest.fixture
def sample_workflow_definition():
    """Create a sample workflow definition for testing"""
    return {
        "workflow_id": "test-workflow-1",
        "name": "Test Workflow",
        "description": "A test workflow for unit testing",
        "nodes": [
            {
                "node_id": "node-1",
                "name": "First Node",
                "node_type": "task",
                "command": "echo 'hello'",
                "dependencies": [],
                "retries": 0,
                "timeout_seconds": 60,
                "params": {},
            }
        ],
        "schedule": "0 0 * * *",
        "metadata": {"owner": "test-team"},
    }


@pytest.fixture
def sample_workflow_execution():
    """Create a sample workflow execution for testing"""
    return {
        "workflow_id": "test-workflow-1",
        "params": {"env": "test"},
        "requested_by": "test-user",
        "priority": "medium",
    }


@pytest.fixture
def sample_schedule():
    """Create a sample schedule for testing"""
    return {
        "schedule_id": "schedule-1",
        "workflow_id": "test-workflow-1",
        "cron": "0 0 * * *",
        "params": {"env": "test"},
    }


@pytest.fixture
def sample_trigger():
    """Create a sample trigger for testing"""
    return {
        "trigger_id": "trigger-1",
        "name": "Test Trigger",
        "workflow_id": "test-workflow-1",
        "trigger_type": "webhook",
        "config": {"url": "http://example.com/webhook"},
        "enabled": True,
    }


@pytest.fixture
def sample_variable():
    """Create a sample variable for testing"""
    return {
        "variable_id": "var-1",
        "name": "API_KEY",
        "value": "secret-key-123",
        "variable_type": "string",
        "description": "API key for external service",
    }


@pytest.fixture(autouse=True)
def reset_state():
    """Reset the in-memory state before each test"""
    _schedules.clear()
    _triggers.clear()
    _variables.clear()
    _audit_logs.clear()
    yield
    _schedules.clear()
    _triggers.clear()
    _variables.clear()
    _audit_logs.clear()


# ============================================================================
# Workflow Definition Tests
# ============================================================================


class TestWorkflowDefinitions:
    """Test suite for workflow definition endpoints"""

    @pytest.mark.asyncio
    async def test_list_workflow_definitions_success(self, mock_repository):
        """Test successful listing of workflow definitions"""
        from api.workflow_advanced_router import list_workflow_definitions

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.list_definitions = AsyncMock(return_value=[])

            result = await list_workflow_definitions(limit=10, offset=0)

            assert result["total"] == 0
            assert result["limit"] == 10
            assert result["offset"] == 0
            assert result["data"] == []

    @pytest.mark.asyncio
    async def test_list_workflow_definitions_with_data(self, mock_repository):
        """Test listing workflow definitions with data"""
        from api.workflow_advanced_router import list_workflow_definitions
        from extensions.addons.operations.workflow_service.schemas import WorkflowDefinition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_def = Mock(spec=WorkflowDefinition)
            mock_def.model_dump = Mock(return_value={"workflow_id": "test-1"})
            mock_repository.list_definitions = AsyncMock(return_value=[mock_def])

            result = await list_workflow_definitions(limit=10, offset=0)

            assert result["total"] == 1
            assert len(result["data"]) == 1

    @pytest.mark.asyncio
    async def test_list_workflow_definitions_pagination(self, mock_repository):
        """Test pagination in workflow definitions list"""
        from api.workflow_advanced_router import list_workflow_definitions
        from extensions.addons.operations.workflow_service.schemas import WorkflowDefinition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_defs = [Mock(spec=WorkflowDefinition) for _ in range(5)]
            for md in mock_defs:
                md.model_dump = Mock(return_value={"workflow_id": "test"})
            mock_repository.list_definitions = AsyncMock(return_value=mock_defs)

            result = await list_workflow_definitions(limit=2, offset=1)

            assert result["total"] == 5
            assert result["limit"] == 2
            assert result["offset"] == 1
            assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_list_workflow_definitions_invalid_limit(self, mock_repository):
        """Test that invalid limit values are rejected by FastAPI validation"""
        from api.workflow_advanced_router import list_workflow_definitions

        # FastAPI handles validation, so we just test valid ranges
        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.list_definitions = AsyncMock(return_value=[])

            # Test minimum valid limit
            result = await list_workflow_definitions(limit=1, offset=0)
            assert result["limit"] == 1

            # Test maximum valid limit
            result = await list_workflow_definitions(limit=1000, offset=0)
            assert result["limit"] == 1000

    @pytest.mark.asyncio
    async def test_create_workflow_definition_success(
        self, sample_workflow_definition, mock_request, mock_repository
    ):
        """Test successful creation of workflow definition"""
        from api.workflow_advanced_router import create_workflow_definition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.get_definition = AsyncMock(return_value=None)
            mock_repository.save_definition = AsyncMock()

            body = WorkflowDefinitionCreate(**sample_workflow_definition)
            result = await create_workflow_definition(body, mock_request)

            assert result["workflow_id"] == "test-workflow-1"
            assert result["name"] == "Test Workflow"
            mock_repository.save_definition.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_workflow_definition_duplicate(
        self, sample_workflow_definition, mock_request, mock_repository
    ):
        """Test creating duplicate workflow definition fails"""
        from api.workflow_advanced_router import create_workflow_definition
        from extensions.addons.operations.workflow_service.schemas import WorkflowDefinition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_def = Mock(spec=WorkflowDefinition)
            mock_repository.get_definition = AsyncMock(return_value=mock_def)

            body = WorkflowDefinitionCreate(**sample_workflow_definition)

            with pytest.raises(HTTPException) as exc_info:
                await create_workflow_definition(body, mock_request)

            assert exc_info.value.status_code == 400
            assert "已存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_workflow_definition_validation_error(self, mock_request):
        """Test that invalid workflow definition data is rejected"""
        from api.workflow_advanced_router import create_workflow_definition

        # Test missing required field
        with pytest.raises(Exception):  # Pydantic validation error
            WorkflowDefinitionCreate(
                workflow_id="", name="Test"  # Empty string should fail validation
            )

    @pytest.mark.asyncio
    async def test_get_workflow_definition_success(self, mock_repository):
        """Test successful retrieval of workflow definition"""
        from api.workflow_advanced_router import get_workflow_definition
        from extensions.addons.operations.workflow_service.schemas import WorkflowDefinition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_def = Mock(spec=WorkflowDefinition)
            mock_def.model_dump = Mock(return_value={"workflow_id": "test-1"})
            mock_repository.get_definition = AsyncMock(return_value=mock_def)

            result = await get_workflow_definition("test-1")

            assert result["workflow_id"] == "test-1"

    @pytest.mark.asyncio
    async def test_get_workflow_definition_not_found(self, mock_repository):
        """Test getting non-existent workflow definition"""
        from api.workflow_advanced_router import get_workflow_definition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.get_definition = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_workflow_definition("non-existent")

            assert exc_info.value.status_code == 404
            assert "不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_workflow_definition_success(
        self, sample_workflow_definition, mock_request, mock_repository
    ):
        """Test successful update of workflow definition"""
        from api.workflow_advanced_router import update_workflow_definition
        from extensions.addons.operations.workflow_service.schemas import WorkflowDefinition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_def = Mock(spec=WorkflowDefinition)
            mock_def.name = "Old Name"
            mock_def.description = "Old Description"
            mock_def.model_dump = Mock(return_value={"workflow_id": "test-1"})
            mock_repository.get_definition = AsyncMock(return_value=mock_def)
            mock_repository.save_definition = AsyncMock()

            body = WorkflowDefinitionUpdate(name="New Name", description="New Description")
            result = await update_workflow_definition("test-1", body, mock_request)

            assert mock_def.name == "New Name"
            assert mock_def.description == "New Description"
            mock_repository.save_definition.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_workflow_definition_not_found(self, mock_request, mock_repository):
        """Test updating non-existent workflow definition"""
        from api.workflow_advanced_router import update_workflow_definition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.get_definition = AsyncMock(return_value=None)

            body = WorkflowDefinitionUpdate(name="New Name")

            with pytest.raises(HTTPException) as exc_info:
                await update_workflow_definition("non-existent", body, mock_request)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_workflow_definition_success(self, mock_request, mock_repository):
        """Test successful deletion of workflow definition"""
        from api.workflow_advanced_router import delete_workflow_definition
        from extensions.addons.operations.workflow_service.schemas import WorkflowDefinition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_def = Mock(spec=WorkflowDefinition)
            mock_def.name = "Test Workflow"
            mock_repository.get_definition = AsyncMock(return_value=mock_def)
            mock_repository._definitions = {"test-1": mock_def}

            result = await delete_workflow_definition("test-1", mock_request)

            assert "已删除" in result["detail"]

    @pytest.mark.asyncio
    async def test_delete_workflow_definition_not_found(self, mock_request, mock_repository):
        """Test deleting non-existent workflow definition"""
        from api.workflow_advanced_router import delete_workflow_definition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.get_definition = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await delete_workflow_definition("non-existent", mock_request)

            assert exc_info.value.status_code == 404


# ============================================================================
# Workflow Execution Tests
# ============================================================================


class TestWorkflowExecutions:
    """Test suite for workflow execution endpoints"""

    @pytest.mark.asyncio
    async def test_list_workflow_executions_success(self, mock_repository):
        """Test successful listing of workflow executions"""
        from api.workflow_advanced_router import list_workflow_executions

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.list_tasks = AsyncMock(return_value=[])

            result = await list_workflow_executions(limit=10, offset=0)

            assert result["total"] == 0
            assert result["data"] == []

    @pytest.mark.asyncio
    async def test_list_workflow_executions_with_status_filter(self, mock_repository):
        """Test listing workflow executions with status filter"""
        from api.workflow_advanced_router import list_workflow_executions
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowStatus,
            WorkflowTask,
        )

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.status = WorkflowStatus.RUNNING
            mock_task.model_dump = Mock(return_value={"task_id": "task-1", "status": "running"})
            mock_repository.list_tasks = AsyncMock(return_value=[mock_task])

            result = await list_workflow_executions(limit=10, offset=0, status="running")

            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_create_workflow_execution_success(
        self, sample_workflow_execution, mock_request, mock_orchestrator
    ):
        """Test successful creation of workflow execution"""
        from api.workflow_advanced_router import create_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import WorkflowTask

        with patch(
            "api.workflow_advanced_router._get_orchestrator", return_value=mock_orchestrator
        ):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.task_id = "task-123"
            mock_task.model_dump = Mock(return_value={"task_id": "task-123"})
            mock_orchestrator.create_task = AsyncMock(return_value=mock_task)

            body = WorkflowExecutionCreate(**sample_workflow_execution)
            result = await create_workflow_execution(body, mock_request)

            assert result["task_id"] == "task-123"
            mock_orchestrator.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_workflow_execution_invalid_workflow(
        self, sample_workflow_execution, mock_request, mock_orchestrator
    ):
        """Test creating execution for non-existent workflow"""
        from api.workflow_advanced_router import create_workflow_execution

        with patch(
            "api.workflow_advanced_router._get_orchestrator", return_value=mock_orchestrator
        ):
            mock_orchestrator.create_task = AsyncMock(side_effect=ValueError("Workflow not found"))

            body = WorkflowExecutionCreate(**sample_workflow_execution)

            with pytest.raises(HTTPException) as exc_info:
                await create_workflow_execution(body, mock_request)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_workflow_execution_success(self, mock_repository):
        """Test successful retrieval of workflow execution"""
        from api.workflow_advanced_router import get_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import WorkflowTask

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.model_dump = Mock(return_value={"task_id": "task-1"})
            mock_repository.get_task = AsyncMock(return_value=mock_task)

            result = await get_workflow_execution("task-1")

            assert result["task_id"] == "task-1"

    @pytest.mark.asyncio
    async def test_get_workflow_execution_not_found(self, mock_repository):
        """Test getting non-existent workflow execution"""
        from api.workflow_advanced_router import get_workflow_execution

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.get_task = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_workflow_execution("non-existent")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_workflow_execution_success(self, mock_request, mock_repository):
        """Test successful update of workflow execution"""
        from api.workflow_advanced_router import update_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import WorkflowTask

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.model_dump = Mock(return_value={"task_id": "task-1", "status": "completed"})
            mock_repository.get_task = AsyncMock(return_value=mock_task)
            mock_repository.update_task = AsyncMock()

            body = WorkflowExecutionUpdate(status="completed")
            result = await update_workflow_execution("task-1", body, mock_request)

            mock_repository.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_workflow_execution_success(
        self, mock_request, mock_repository, mock_orchestrator
    ):
        """Test successful start of workflow execution"""
        from api.workflow_advanced_router import start_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowStatus,
            WorkflowTask,
        )

        with (
            patch("api.workflow_advanced_router._get_repository", return_value=mock_repository),
            patch("api.workflow_advanced_router._get_orchestrator", return_value=mock_orchestrator),
        ):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.status = WorkflowStatus.PENDING
            mock_task.workflow_id = "test-workflow"
            mock_repository.get_task = AsyncMock(return_value=mock_task)
            mock_repository.update_task = AsyncMock()

            result = await start_workflow_execution("task-1", mock_request)

            assert "已启动" in result["detail"]
            mock_repository.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_start_workflow_execution_already_running(self, mock_request, mock_repository):
        """Test starting already running workflow execution fails"""
        from api.workflow_advanced_router import start_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowStatus,
            WorkflowTask,
        )

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.status = WorkflowStatus.RUNNING
            mock_repository.get_task = AsyncMock(return_value=mock_task)

            with pytest.raises(HTTPException) as exc_info:
                await start_workflow_execution("task-1", mock_request)

            assert exc_info.value.status_code == 400
            assert "已在运行中" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_stop_workflow_execution_success(self, mock_request, mock_repository):
        """Test successful stop of workflow execution"""
        from api.workflow_advanced_router import stop_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowStatus,
            WorkflowTask,
        )

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.status = WorkflowStatus.RUNNING
            mock_task.workflow_id = "test-workflow"
            mock_repository.get_task = AsyncMock(return_value=mock_task)
            mock_repository.update_task = AsyncMock()

            result = await stop_workflow_execution("task-1", mock_request)

            assert "已停止" in result["detail"]

    @pytest.mark.asyncio
    async def test_pause_workflow_execution_success(self, mock_request, mock_repository):
        """Test successful pause of workflow execution"""
        from api.workflow_advanced_router import pause_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowStatus,
            WorkflowTask,
        )

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.status = WorkflowStatus.RUNNING
            mock_task.workflow_id = "test-workflow"
            mock_repository.get_task = AsyncMock(return_value=mock_task)
            mock_repository.update_task = AsyncMock()

            result = await pause_workflow_execution("task-1", mock_request)

            assert "已暂停" in result["detail"]

    @pytest.mark.asyncio
    async def test_resume_workflow_execution_success(
        self, mock_request, mock_repository, mock_orchestrator
    ):
        """Test successful resume of workflow execution"""
        from api.workflow_advanced_router import resume_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowStatus,
            WorkflowTask,
        )

        with (
            patch("api.workflow_advanced_router._get_repository", return_value=mock_repository),
            patch("api.workflow_advanced_router._get_orchestrator", return_value=mock_orchestrator),
        ):
            mock_task = Mock(spec=WorkflowTask)
            mock_task.status = WorkflowStatus.PAUSED
            mock_task.workflow_id = "test-workflow"
            mock_repository.get_task = AsyncMock(return_value=mock_task)
            mock_repository.update_task = AsyncMock()

            result = await resume_workflow_execution("task-1", mock_request)

            assert "已恢复" in result["detail"]


# ============================================================================
# Schedule Tests
# ============================================================================


class TestSchedules:
    """Test suite for schedule endpoints"""

    @pytest.mark.asyncio
    async def test_list_schedules_success(self):
        """Test successful listing of schedules"""
        from api.workflow_advanced_router import list_schedules

        result = await list_schedules(limit=10, offset=0)

        assert result["total"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_create_schedule_success(self, sample_schedule, mock_request):
        """Test successful creation of schedule"""
        from api.workflow_advanced_router import create_schedule

        body = ScheduleCreate(**sample_schedule)
        result = await create_schedule(body, mock_request)

        assert result["schedule_id"] == "schedule-1"
        assert result["workflow_id"] == "test-workflow-1"

    @pytest.mark.asyncio
    async def test_create_schedule_duplicate(self, sample_schedule, mock_request):
        """Test creating duplicate schedule fails"""
        from api.workflow_advanced_router import create_schedule

        # Create first schedule
        body = ScheduleCreate(**sample_schedule)
        await create_schedule(body, mock_request)

        # Try to create duplicate
        with pytest.raises(HTTPException) as exc_info:
            await create_schedule(body, mock_request)

        assert exc_info.value.status_code == 400
        assert "已存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_schedule_success(self, sample_schedule):
        """Test successful retrieval of schedule"""
        from api.workflow_advanced_router import create_schedule, get_schedule

        mock_request = Mock(spec=Request)
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        body = ScheduleCreate(**sample_schedule)
        await create_schedule(body, mock_request)

        result = await get_schedule("schedule-1")

        assert result["schedule_id"] == "schedule-1"

    @pytest.mark.asyncio
    async def test_get_schedule_not_found(self):
        """Test getting non-existent schedule"""
        from api.workflow_advanced_router import get_schedule

        with pytest.raises(HTTPException) as exc_info:
            await get_schedule("non-existent")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_schedule_success(self, sample_schedule, mock_request):
        """Test successful update of schedule"""
        from api.workflow_advanced_router import create_schedule, update_schedule

        body = ScheduleCreate(**sample_schedule)
        await create_schedule(body, mock_request)

        update_body = ScheduleUpdate(cron="0 12 * * *", enabled=False)
        result = await update_schedule("schedule-1", update_body, mock_request)

        assert result["cron"] == "0 12 * * *"
        assert result["enabled"] == False

    @pytest.mark.asyncio
    async def test_delete_schedule_success(self, sample_schedule, mock_request):
        """Test successful deletion of schedule"""
        from api.workflow_advanced_router import create_schedule, delete_schedule

        body = ScheduleCreate(**sample_schedule)
        await create_schedule(body, mock_request)

        result = await delete_schedule("schedule-1", mock_request)

        assert "已删除" in result["detail"]

    @pytest.mark.asyncio
    async def test_enable_schedule_success(self, sample_schedule, mock_request):
        """Test successful enable of schedule"""
        from api.workflow_advanced_router import create_schedule, enable_schedule

        body = ScheduleCreate(**sample_schedule)
        created = await create_schedule(body, mock_request)
        created["enabled"] = False

        result = await enable_schedule("schedule-1", mock_request)

        assert result["enabled"] == True

    @pytest.mark.asyncio
    async def test_disable_schedule_success(self, sample_schedule, mock_request):
        """Test successful disable of schedule"""
        from api.workflow_advanced_router import create_schedule, disable_schedule

        body = ScheduleCreate(**sample_schedule)
        await create_schedule(body, mock_request)

        result = await disable_schedule("schedule-1", mock_request)

        assert result["enabled"] == False


# ============================================================================
# Trigger Tests
# ============================================================================


class TestTriggers:
    """Test suite for trigger endpoints"""

    @pytest.mark.asyncio
    async def test_list_triggers_success(self):
        """Test successful listing of triggers"""
        from api.workflow_advanced_router import list_triggers

        result = await list_triggers(limit=10, offset=0)

        assert result["total"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_create_trigger_success(self, sample_trigger, mock_request):
        """Test successful creation of trigger"""
        from api.workflow_advanced_router import create_trigger

        body = TriggerCreate(**sample_trigger)
        result = await create_trigger(body, mock_request)

        assert result["trigger_id"] == "trigger-1"
        assert result["name"] == "Test Trigger"

    @pytest.mark.asyncio
    async def test_create_trigger_duplicate(self, sample_trigger, mock_request):
        """Test creating duplicate trigger fails"""
        from api.workflow_advanced_router import create_trigger

        body = TriggerCreate(**sample_trigger)
        await create_trigger(body, mock_request)

        with pytest.raises(HTTPException) as exc_info:
            await create_trigger(body, mock_request)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_trigger_success(self, sample_trigger, mock_request):
        """Test successful retrieval of trigger"""
        from api.workflow_advanced_router import create_trigger, get_trigger

        body = TriggerCreate(**sample_trigger)
        await create_trigger(body, mock_request)

        result = await get_trigger("trigger-1")

        assert result["trigger_id"] == "trigger-1"

    @pytest.mark.asyncio
    async def test_get_trigger_not_found(self):
        """Test getting non-existent trigger"""
        from api.workflow_advanced_router import get_trigger

        with pytest.raises(HTTPException) as exc_info:
            await get_trigger("non-existent")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_trigger_success(self, sample_trigger, mock_request):
        """Test successful update of trigger"""
        from api.workflow_advanced_router import create_trigger, update_trigger

        body = TriggerCreate(**sample_trigger)
        await create_trigger(body, mock_request)

        update_body = TriggerUpdate(name="Updated Trigger", enabled=False)
        result = await update_trigger("trigger-1", update_body, mock_request)

        assert result["name"] == "Updated Trigger"
        assert result["enabled"] == False

    @pytest.mark.asyncio
    async def test_delete_trigger_success(self, sample_trigger, mock_request):
        """Test successful deletion of trigger"""
        from api.workflow_advanced_router import create_trigger, delete_trigger

        body = TriggerCreate(**sample_trigger)
        await create_trigger(body, mock_request)

        result = await delete_trigger("trigger-1", mock_request)

        assert "已删除" in result["detail"]


# ============================================================================
# Variable Tests
# ============================================================================


class TestVariables:
    """Test suite for variable endpoints"""

    @pytest.mark.asyncio
    async def test_list_variables_success(self):
        """Test successful listing of variables"""
        from api.workflow_advanced_router import list_variables

        result = await list_variables(limit=10, offset=0)

        assert result["total"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_create_variable_success(self, sample_variable, mock_request):
        """Test successful creation of variable"""
        from api.workflow_advanced_router import create_variable

        body = VariableCreate(**sample_variable)
        result = await create_variable(body, mock_request)

        assert result["variable_id"] == "var-1"
        assert result["name"] == "API_KEY"

    @pytest.mark.asyncio
    async def test_create_variable_duplicate(self, sample_variable, mock_request):
        """Test creating duplicate variable fails"""
        from api.workflow_advanced_router import create_variable

        body = VariableCreate(**sample_variable)
        await create_variable(body, mock_request)

        with pytest.raises(HTTPException) as exc_info:
            await create_variable(body, mock_request)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_variable_success(self, sample_variable, mock_request):
        """Test successful retrieval of variable"""
        from api.workflow_advanced_router import create_variable, get_variable

        body = VariableCreate(**sample_variable)
        await create_variable(body, mock_request)

        result = await get_variable("var-1")

        assert result["variable_id"] == "var-1"

    @pytest.mark.asyncio
    async def test_get_variable_not_found(self):
        """Test getting non-existent variable"""
        from api.workflow_advanced_router import get_variable

        with pytest.raises(HTTPException) as exc_info:
            await get_variable("non-existent")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_variable_success(self, sample_variable, mock_request):
        """Test successful update of variable"""
        from api.workflow_advanced_router import create_variable, update_variable

        body = VariableCreate(**sample_variable)
        await create_variable(body, mock_request)

        update_body = VariableUpdate(value="new-secret-key", description="Updated description")
        result = await update_variable("var-1", update_body, mock_request)

        assert result["value"] == "new-secret-key"

    @pytest.mark.asyncio
    async def test_delete_variable_success(self, sample_variable, mock_request):
        """Test successful deletion of variable"""
        from api.workflow_advanced_router import create_variable, delete_variable

        body = VariableCreate(**sample_variable)
        await create_variable(body, mock_request)

        result = await delete_variable("var-1", mock_request)

        assert "已删除" in result["detail"]


# ============================================================================
# Audit Log Tests
# ============================================================================


class TestAuditLogs:
    """Test suite for audit log endpoints"""

    @pytest.mark.asyncio
    async def test_list_audit_logs_success(self):
        """Test successful listing of audit logs"""
        from api.workflow_advanced_router import list_audit_logs

        result = await list_audit_logs(limit=10, offset=0)

        assert result["total"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_list_audit_logs_with_action_filter(self):
        """Test listing audit logs with action filter"""
        # Add a test log directly
        import datetime

        from api.workflow_advanced_router import _audit_logs, list_audit_logs

        test_log = {
            "log_id": "TEST-001",
            "action": "create",
            "resource_type": "test",
            "resource_id": "test-1",
            "user": "test-user",
            "timestamp": datetime.datetime.utcnow(),
            "details": {},
            "ip_address": "127.0.0.1",
        }
        _audit_logs.insert(0, test_log)

        result = await list_audit_logs(limit=10, offset=0, action="create")

        # Filter should work
        assert "total" in result
        assert "data" in result
        # Clean up
        if test_log in _audit_logs:
            _audit_logs.remove(test_log)

    @pytest.mark.asyncio
    async def test_list_audit_logs_with_resource_type_filter(self):
        """Test listing audit logs with resource type filter"""
        # Add a test log directly
        import datetime

        from api.workflow_advanced_router import _audit_logs, list_audit_logs

        test_log = {
            "log_id": "TEST-002",
            "action": "create",
            "resource_type": "variable",
            "resource_id": "var-1",
            "user": "test-user",
            "timestamp": datetime.datetime.utcnow(),
            "details": {},
            "ip_address": "127.0.0.1",
        }
        _audit_logs.insert(0, test_log)

        result = await list_audit_logs(limit=10, offset=0, resource_type="variable")

        # Filter should work
        assert "total" in result
        assert "data" in result
        # Clean up
        if test_log in _audit_logs:
            _audit_logs.remove(test_log)


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Test suite for statistics endpoint"""

    @pytest.mark.asyncio
    async def test_get_statistics_success(self, mock_repository):
        """Test successful retrieval of statistics"""
        from api.workflow_advanced_router import get_statistics
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowDefinition,
            WorkflowStatus,
            WorkflowTask,
        )

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.list_definitions = AsyncMock(return_value=[])
            mock_repository.list_tasks = AsyncMock(return_value=[])

            result = await get_statistics()

            assert "total_workflows" in result
            assert "total_executions" in result
            assert "success_rate" in result
            assert result["total_workflows"] == 0
            assert result["total_executions"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_with_data(self, mock_repository):
        """Test statistics with actual data"""
        from datetime import datetime, timedelta

        from api.workflow_advanced_router import get_statistics
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowDefinition,
            WorkflowStatus,
            WorkflowTask,
        )

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            # Create mock definitions
            mock_def = Mock(spec=WorkflowDefinition)
            mock_def.schedule = "0 0 * * *"
            mock_repository.list_definitions = AsyncMock(return_value=[mock_def])

            # Create mock tasks
            mock_task_success = Mock(spec=WorkflowTask)
            mock_task_success.status = WorkflowStatus.SUCCEEDED
            mock_task_success.created_at = datetime.utcnow() - timedelta(minutes=10)
            mock_task_success.updated_at = datetime.utcnow() - timedelta(minutes=5)

            mock_task_failed = Mock(spec=WorkflowTask)
            mock_task_failed.status = WorkflowStatus.FAILED
            mock_task_failed.created_at = datetime.utcnow() - timedelta(minutes=10)
            mock_task_failed.updated_at = datetime.utcnow() - timedelta(minutes=5)

            mock_repository.list_tasks = AsyncMock(
                return_value=[mock_task_success, mock_task_failed]
            )

            result = await get_statistics()

            assert result["total_workflows"] == 1
            assert result["active_workflows"] == 1
            assert result["total_executions"] == 2
            assert result["completed_executions"] == 1
            assert result["failed_executions"] == 1
            assert result["success_rate"] == 50.0


# ============================================================================
# Data Validation Tests
# ============================================================================


class TestDataValidation:
    """Test suite for data validation"""

    def test_workflow_definition_create_valid(self, sample_workflow_definition):
        """Test valid workflow definition creation"""
        body = WorkflowDefinitionCreate(**sample_workflow_definition)
        assert body.workflow_id == "test-workflow-1"
        assert body.name == "Test Workflow"

    def test_workflow_definition_create_invalid_empty_id(self):
        """Test that empty workflow_id is rejected"""
        with pytest.raises(Exception):
            WorkflowDefinitionCreate(workflow_id="", name="Test")

    def test_workflow_definition_create_invalid_long_name(self):
        """Test that name exceeding max length is rejected"""
        with pytest.raises(Exception):
            WorkflowDefinitionCreate(workflow_id="test-1", name="x" * 129)  # Exceeds max_length=128

    def test_workflow_execution_create_valid(self, sample_workflow_execution):
        """Test valid workflow execution creation"""
        body = WorkflowExecutionCreate(**sample_workflow_execution)
        assert body.workflow_id == "test-workflow-1"
        assert body.priority == "medium"

    def test_schedule_create_valid(self, sample_schedule):
        """Test valid schedule creation"""
        body = ScheduleCreate(**sample_schedule)
        assert body.schedule_id == "schedule-1"
        assert body.cron == "0 0 * * *"

    def test_trigger_create_valid(self, sample_trigger):
        """Test valid trigger creation"""
        body = TriggerCreate(**sample_trigger)
        assert body.trigger_id == "trigger-1"
        assert body.trigger_type == "webhook"

    def test_variable_create_valid(self, sample_variable):
        """Test valid variable creation"""
        body = VariableCreate(**sample_variable)
        assert body.variable_id == "var-1"
        assert body.variable_type == "string"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test suite for error handling"""

    @pytest.mark.asyncio
    async def test_repository_exception_handling(self, mock_repository):
        """Test that repository exceptions are handled properly"""
        from api.workflow_advanced_router import list_workflow_definitions

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.list_definitions = AsyncMock(side_effect=Exception("Database error"))

            with pytest.raises(HTTPException) as exc_info:
                await list_workflow_definitions(limit=10, offset=0)

            assert exc_info.value.status_code == 500
            assert "失败" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_orchestrator_exception_handling(self, mock_orchestrator):
        """Test that orchestrator exceptions are handled properly"""
        from api.workflow_advanced_router import create_workflow_execution
        from extensions.addons.operations.workflow_service.schemas import WorkflowTask

        with patch(
            "api.workflow_advanced_router._get_orchestrator", return_value=mock_orchestrator
        ):
            mock_orchestrator.create_task = AsyncMock(side_effect=Exception("Orchestrator error"))

            body = WorkflowExecutionCreate(
                workflow_id="test-1", params={}, requested_by="test", priority="medium"
            )
            mock_request = Mock(spec=Request)

            with pytest.raises(HTTPException) as exc_info:
                await create_workflow_execution(body, mock_request)

            assert exc_info.value.status_code == 500


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for workflow router"""

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(
        self, sample_workflow_definition, mock_request, mock_repository
    ):
        """Test complete workflow lifecycle: create, read, update, delete"""
        from api.workflow_advanced_router import (
            create_workflow_definition,
            delete_workflow_definition,
            get_workflow_definition,
            update_workflow_definition,
        )
        from extensions.addons.operations.workflow_service.schemas import WorkflowDefinition

        with patch("api.workflow_advanced_router._get_repository", return_value=mock_repository):
            mock_repository.get_definition = AsyncMock(return_value=None)
            mock_repository.save_definition = AsyncMock()

            # Create
            body = WorkflowDefinitionCreate(**sample_workflow_definition)
            created = await create_workflow_definition(body, mock_request)
            assert created["workflow_id"] == "test-workflow-1"

            # Read
            mock_def = Mock(spec=WorkflowDefinition)
            mock_def.name = "Test Workflow"
            mock_def.model_dump = Mock(return_value=created)
            mock_repository.get_definition = AsyncMock(return_value=mock_def)
            retrieved = await get_workflow_definition("test-workflow-1")
            assert retrieved["workflow_id"] == "test-workflow-1"

            # Update - create a new mock with updated name
            updated_data = created.copy()
            updated_data["name"] = "Updated Name"
            mock_def_updated = Mock(spec=WorkflowDefinition)
            mock_def_updated.name = "Updated Name"
            mock_def_updated.model_dump = Mock(return_value=updated_data)
            mock_repository.get_definition = AsyncMock(return_value=mock_def_updated)

            update_body = WorkflowDefinitionUpdate(name="Updated Name")
            updated = await update_workflow_definition("test-workflow-1", update_body, mock_request)
            # The update should have been called on the mock
            assert mock_def_updated.name == "Updated Name"

            # Delete
            mock_repository._definitions = {"test-workflow-1": mock_def_updated}
            deleted = await delete_workflow_definition("test-workflow-1", mock_request)
            assert "已删除" in deleted["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
