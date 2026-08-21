# -*- coding: utf-8 -*-
"""Pytest fixtures for workflow_service tests."""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch

import pytest

# Add the workflow_service directory to Python path
sys.path.insert(0, "C:/aiops-sre-agent/extensions/addons/operations/workflow_service")

# Clear prometheus metrics registry to avoid duplicate registration errors
# This must be done before importing any workflow_service modules
from prometheus_client import REGISTRY
try:
    REGISTRY._collector_to_names.clear()
    REGISTRY._names_to_collectors.clear()
except:
    pass  # Registry may not have these attributes in all versions

from extensions.addons.operations.workflow_service.config import WorkflowServiceSettings
from extensions.addons.operations.workflow_service.grpc.client import WorkflowRPCClient
from extensions.addons.operations.workflow_service.grpc.server import WorkflowRPCServer
from extensions.addons.operations.workflow_service.health_check import HealthCheckEngine
from extensions.addons.operations.workflow_service.orchestrator import WorkflowOrchestrator
from extensions.addons.operations.workflow_service.repository import (
    InMemoryWorkflowRepository,
    WorkflowRepository,
)
from extensions.addons.operations.workflow_service.retry import RetryEngine
from extensions.addons.operations.workflow_service.saga import WorkflowSagaOrchestrator
from extensions.addons.operations.workflow_service.schemas import (
    RetryPolicy,
    SagaStep,
    ScheduledTask,
    TaskPriority,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowTask,
    WorkflowTemplate,
)
from extensions.addons.operations.workflow_service.scheduler import WorkflowScheduler
from extensions.addons.operations.workflow_service.state_machine import WorkflowStateMachine
from extensions.addons.operations.workflow_service.templates import TemplateManager
from extensions.addons.operations.workflow_service.versioning import WorkflowVersionManager


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def repository() -> AsyncGenerator[WorkflowRepository, None]:
    """Provide an in-memory repository instance."""
    repo = InMemoryWorkflowRepository()
    yield repo
    # Cleanup is automatic since it's in-memory


@pytest.fixture
def workflow_definition() -> WorkflowDefinition:
    """Provide a sample workflow definition."""
    return WorkflowDefinition(
        workflow_id="test-workflow-1",
        name="Test Workflow",
        description="A test workflow for unit testing",
        nodes=[
            WorkflowNode(
                node_id="node1",
                name="First Node",
                command="echo {{ message }}",
                dependencies=[],
            ),
            WorkflowNode(
                node_id="node2",
                name="Second Node",
                command="echo {{ message }} again",
                dependencies=["node1"],
            ),
            WorkflowNode(
                node_id="node3",
                name="Third Node",
                command="echo final",
                dependencies=["node2"],
            ),
        ],
        metadata={"environment": "test", "owner": "test-team"},
    )


@pytest.fixture
def workflow_definition_with_failure() -> WorkflowDefinition:
    """Provide a workflow definition with a failing node."""
    return WorkflowDefinition(
        workflow_id="test-workflow-fail",
        name="Test Workflow with Failure",
        description="A test workflow that includes a failing node",
        nodes=[
            WorkflowNode(
                node_id="node1",
                name="First Node",
                command="echo {{ message }}",
                dependencies=[],
            ),
            WorkflowNode(
                node_id="node2",
                name="Failing Node",
                command="fail this step",
                dependencies=["node1"],
            ),
            WorkflowNode(
                node_id="node3",
                name="Third Node",
                command="echo final",
                dependencies=["node2"],
            ),
        ],
        metadata={"environment": "test"},
    )


@pytest.fixture
def workflow_request() -> WorkflowRequest:
    """Provide a sample workflow execution request."""
    return WorkflowRequest(
        workflow_id="test-workflow-1",
        params={"message": "Hello World"},
        requested_by="test-user",
        priority=TaskPriority.HIGH,
    )


@pytest.fixture
def workflow_task() -> WorkflowTask:
    """Provide a sample workflow task."""
    return WorkflowTask(
        task_id="TASK-001",
        workflow_id="test-workflow-1",
        status=WorkflowStatus.PENDING,
        params={"message": "Hello World"},
    )


@pytest.fixture
def retry_policy() -> RetryPolicy:
    """Provide a sample retry policy."""
    return RetryPolicy(
        name="test_policy",
        max_retries=3,
        base_delay_seconds=0.1,
        max_delay_seconds=1.0,
        exponential_base=2.0,
        retryable_errors=["timeout", "connection"],
    )


@pytest.fixture
def retry_engine() -> RetryEngine:
    """Provide a retry engine instance."""
    return RetryEngine()


@pytest.fixture
def orchestrator(repository: WorkflowRepository) -> WorkflowOrchestrator:
    """Provide a workflow orchestrator instance."""
    return WorkflowOrchestrator(repository)


@pytest.fixture
def state_machine(workflow_task: WorkflowTask) -> WorkflowStateMachine:
    """Provide a workflow state machine instance."""
    return WorkflowStateMachine(workflow_task)


@pytest.fixture
def scheduler() -> WorkflowScheduler:
    """Provide a workflow scheduler instance."""
    return WorkflowScheduler(poll_interval=0.1)


@pytest.fixture
def template_manager() -> TemplateManager:
    """Provide a template manager instance."""
    return TemplateManager()


@pytest.fixture
def workflow_template() -> WorkflowTemplate:
    """Provide a sample workflow template."""
    return WorkflowTemplate(
        template_id="template-1",
        name="Test Template",
        description="A test template",
        source="echo {{ message }} from {{ user }}",
        default_params={"user": "system"},
    )


@pytest.fixture
def version_manager() -> WorkflowVersionManager:
    """Provide a workflow version manager instance."""
    return WorkflowVersionManager()


@pytest.fixture
def saga_orchestrator() -> WorkflowSagaOrchestrator:
    """Provide a saga orchestrator instance."""
    return WorkflowSagaOrchestrator()


@pytest.fixture
def saga_steps() -> list[SagaStep]:
    """Provide sample saga steps."""
    return [
        SagaStep(
            step_id="step1",
            service="service1",
            action="create",
            compensation="delete",
        ),
        SagaStep(
            step_id="step2",
            service="service2",
            action="update",
            compensation="rollback",
        ),
    ]


@pytest.fixture
def scheduled_task() -> ScheduledTask:
    """Provide a sample scheduled task."""
    return ScheduledTask(
        schedule_id="SCHEDULE-001",
        workflow_id="test-workflow-1",
        cron="0 * * * *",
        enabled=True,
        params={"message": "Scheduled message"},
    )


@pytest.fixture
def grpc_server() -> WorkflowRPCServer:
    """Provide a gRPC server instance."""
    return WorkflowRPCServer()


@pytest.fixture
def health_check_engine() -> HealthCheckEngine:
    """Provide a health check engine instance."""
    return HealthCheckEngine()


@pytest.fixture
def settings() -> WorkflowServiceSettings:
    """Provide workflow service settings."""
    return WorkflowServiceSettings()


@pytest.fixture
async def populated_repository(
    repository: WorkflowRepository,
    workflow_definition: WorkflowDefinition,
    workflow_task: WorkflowTask,
) -> AsyncGenerator[WorkflowRepository, None]:
    """Provide a repository with sample data."""
    await repository.save_definition(workflow_definition)
    await repository.save_task(workflow_task)
    yield repository


@pytest.fixture
def mock_psutil():
    """Mock psutil for health check tests."""
    with patch("extensions.addons.operations.workflow_service.health_check.psutil") as mock:
        mock.virtual_memory.return_value.percent = 50
        mock.disk_usage.return_value.percent = 60
        yield mock


@pytest.fixture
def mock_psutil_high_usage():
    """Mock psutil with high resource usage."""
    with patch("extensions.addons.operations.workflow_service.health_check.psutil") as mock:
        mock.virtual_memory.return_value.percent = 96
        mock.disk_usage.return_value.percent = 99
        yield mock


@pytest.fixture
def mock_psutil_exception():
    """Mock psutil that raises an exception."""
    with patch("extensions.addons.operations.workflow_service.health_check.psutil") as mock:
        mock.virtual_memory.side_effect = ImportError("psutil not installed")
        yield mock


@pytest.fixture
def sample_workflow_nodes() -> list[WorkflowNode]:
    """Provide sample workflow nodes for testing."""
    return [
        WorkflowNode(
            node_id="start",
            name="Start Node",
            command="initialize",
            dependencies=[],
        ),
        WorkflowNode(
            node_id="process",
            name="Process Node",
            command="process {{ data }}",
            dependencies=["start"],
        ),
        WorkflowNode(
            node_id="end",
            name="End Node",
            command="finalize",
            dependencies=["process"],
        ),
    ]


@pytest.fixture
def complex_workflow_definition() -> WorkflowDefinition:
    """Provide a complex workflow definition with multiple branches."""
    return WorkflowDefinition(
        workflow_id="complex-workflow",
        name="Complex Workflow",
        description="A workflow with multiple execution paths",
        nodes=[
            WorkflowNode(
                node_id="init",
                name="Initialize",
                command="init",
                dependencies=[],
            ),
            WorkflowNode(
                node_id="branch1",
                name="Branch 1",
                command="process branch1",
                dependencies=["init"],
            ),
            WorkflowNode(
                node_id="branch2",
                name="Branch 2",
                command="process branch2",
                dependencies=["init"],
            ),
            WorkflowNode(
                node_id="merge",
                name="Merge",
                command="merge results",
                dependencies=["branch1", "branch2"],
            ),
            WorkflowNode(
                node_id="finalize",
                name="Finalize",
                command="finalize",
                dependencies=["merge"],
            ),
        ],
    )


@pytest.fixture
def workflow_request_with_params() -> WorkflowRequest:
    """Provide a workflow request with various parameter types."""
    return WorkflowRequest(
        workflow_id="test-workflow-1",
        params={
            "string_param": "test",
            "number_param": 42,
            "bool_param": True,
            "list_param": [1, 2, 3],
            "dict_param": {"key": "value"},
        },
        priority=TaskPriority.MEDIUM,
    )


@pytest.fixture
def retry_policies() -> list[RetryPolicy]:
    """Provide various retry policies for testing."""
    return [
        RetryPolicy(name="no_retry", max_retries=0, base_delay_seconds=0, max_delay_seconds=0),
        RetryPolicy(name="fixed_1s", max_retries=3, base_delay_seconds=1, max_delay_seconds=1),
        RetryPolicy(name="exponential", max_retries=5, base_delay_seconds=1, max_delay_seconds=60),
        RetryPolicy(name="jitter", max_retries=5, base_delay_seconds=1, max_delay_seconds=60),
    ]


@pytest.fixture
def async_action():
    """Provide an async action function for saga testing."""
    async def action():
        await asyncio.sleep(0.01)
        return {"success": True}

    return action


@pytest.fixture
def async_compensation():
    """Provide an async compensation function for saga testing."""
    async def compensation():
        await asyncio.sleep(0.01)
        return {"compensated": True}

    return compensation


@pytest.fixture
def failing_action():
    """Provide a failing action function for saga testing."""
    async def action():
        await asyncio.sleep(0.01)
        raise ValueError("Action failed")

    return action


@pytest.fixture
def sync_action():
    """Provide a sync action function for saga testing."""
    def action():
        return {"success": True}

    return action


@pytest.fixture
def sync_compensation():
    """Provide a sync compensation function for saga testing."""
    def compensation():
        return {"compensated": True}

    return compensation
