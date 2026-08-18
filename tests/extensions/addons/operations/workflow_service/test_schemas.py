# -*- coding: utf-8 -*-
"""Tests for workflow_service schemas module."""

from datetime import datetime
from enum import Enum

import pytest
from pydantic import ValidationError

from schemas import (
    RetryPolicy,
    SagaStep,
    SagaTransaction,
    ScheduledTask,
    ServiceHealth,
    TaskPriority,
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowMetric,
    WorkflowNode,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowTask,
    WorkflowTemplate,
    WorkflowVersion,
)


class TestWorkflowStatus:
    """Test cases for WorkflowStatus enum."""

    def test_workflow_status_values(self):
        """Test that WorkflowStatus has all expected values."""
        expected_values = [
            "pending",
            "approved",
            "scheduled",
            "running",
            "paused",
            "succeeded",
            "failed",
            "retrying",
            "timeout",
            "completed",
        ]
        actual_values = [status.value for status in WorkflowStatus]
        for value in expected_values:
            assert value in actual_values

    def test_workflow_status_is_enum(self):
        """Test that WorkflowStatus is an Enum."""
        assert issubclass(WorkflowStatus, Enum)

    def test_workflow_status_string_enum(self):
        """Test that WorkflowStatus is a string enum."""
        assert issubclass(WorkflowStatus, str)

    def test_workflow_status_comparison(self):
        """Test WorkflowStatus comparison operations."""
        assert WorkflowStatus.PENDING == "pending"
        assert WorkflowStatus.RUNNING == "running"
        assert WorkflowStatus.PENDING != WorkflowStatus.RUNNING

    def test_workflow_status_iteration(self):
        """Test iterating over WorkflowStatus values."""
        statuses = list(WorkflowStatus)
        assert len(statuses) == 10
        assert WorkflowStatus.PENDING in statuses


class TestTaskPriority:
    """Test cases for TaskPriority enum."""

    def test_task_priority_values(self):
        """Test that TaskPriority has all expected values."""
        expected_values = ["low", "medium", "high", "critical"]
        actual_values = [priority.value for priority in TaskPriority]
        for value in expected_values:
            assert value in actual_values

    def test_task_priority_is_enum(self):
        """Test that TaskPriority is an Enum."""
        assert issubclass(TaskPriority, Enum)

    def test_task_priority_string_enum(self):
        """Test that TaskPriority is a string enum."""
        assert issubclass(TaskPriority, str)

    def test_task_priority_comparison(self):
        """Test TaskPriority comparison operations."""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.LOW != TaskPriority.HIGH


class TestWorkflowNode:
    """Test cases for WorkflowNode model."""

    def test_workflow_node_creation(self):
        """Test creating a valid WorkflowNode."""
        node = WorkflowNode(
            node_id="node-1",
            name="Test Node",
            command="echo test",
        )
        assert node.node_id == "node-1"
        assert node.name == "Test Node"
        assert node.command == "echo test"
        assert node.node_type == "task"
        assert node.dependencies == []
        assert node.retries == 0
        assert node.timeout_seconds == 60
        assert node.params == {}

    def test_workflow_node_with_dependencies(self):
        """Test WorkflowNode with dependencies."""
        node = WorkflowNode(
            node_id="node-2",
            name="Node with deps",
            command="test",
            dependencies=["node-1", "node-0"],
        )
        assert len(node.dependencies) == 2
        assert "node-1" in node.dependencies
        assert "node-0" in node.dependencies

    def test_workflow_node_with_params(self):
        """Test WorkflowNode with parameters."""
        node = WorkflowNode(
            node_id="node-3",
            name="Node with params",
            command="test",
            params={"key": "value", "number": 42},
        )
        assert node.params == {"key": "value", "number": 42}

    def test_workflow_node_custom_retries(self):
        """Test WorkflowNode with custom retry count."""
        node = WorkflowNode(
            node_id="node-4",
            name="Node with retries",
            command="test",
            retries=5,
        )
        assert node.retries == 5

    def test_workflow_node_custom_timeout(self):
        """Test WorkflowNode with custom timeout."""
        node = WorkflowNode(
            node_id="node-5",
            name="Node with timeout",
            command="test",
            timeout_seconds=120,
        )
        assert node.timeout_seconds == 120

    def test_workflow_node_custom_type(self):
        """Test WorkflowNode with custom node type."""
        node = WorkflowNode(
            node_id="node-6",
            name="Node with type",
            command="test",
            node_type="gateway",
        )
        assert node.node_type == "gateway"

    def test_workflow_node_min_length_validation(self):
        """Test WorkflowNode node_id and name minimum length validation."""
        with pytest.raises(ValidationError):
            WorkflowNode(node_id="", name="Test", command="test")

        with pytest.raises(ValidationError):
            WorkflowNode(node_id="test", name="", command="test")

    def test_workflow_node_max_length_validation(self):
        """Test WorkflowNode node_id and name maximum length validation."""
        long_id = "a" * 129
        with pytest.raises(ValidationError):
            WorkflowNode(node_id=long_id, name="Test", command="test")

        long_name = "a" * 129
        with pytest.raises(ValidationError):
            WorkflowNode(node_id="test", name=long_name, command="test")

    def test_workflow_node_boundary_lengths(self):
        """Test WorkflowNode at boundary lengths."""
        # Minimum valid length
        node_min = WorkflowNode(node_id="a", name="b", command="test")
        assert node_min.node_id == "a"
        assert node_min.name == "b"

        # Maximum valid length
        node_max = WorkflowNode(
            node_id="a" * 128, name="b" * 128, command="test"
        )
        assert len(node_max.node_id) == 128
        assert len(node_max.name) == 128

    def test_workflow_node_model_dump(self):
        """Test WorkflowNode serialization."""
        node = WorkflowNode(node_id="test", name="Test", command="test")
        dumped = node.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["node_id"] == "test"
        assert dumped["name"] == "Test"

    def test_workflow_node_model_validate(self):
        """Test WorkflowNode deserialization."""
        data = {
            "node_id": "test",
            "name": "Test",
            "command": "test",
            "dependencies": ["dep1"],
        }
        node = WorkflowNode.model_validate(data)
        assert node.node_id == "test"
        assert len(node.dependencies) == 1


class TestWorkflowDefinition:
    """Test cases for WorkflowDefinition model."""

    def test_workflow_definition_creation(self):
        """Test creating a valid WorkflowDefinition."""
        definition = WorkflowDefinition(
            workflow_id="workflow-1",
            name="Test Workflow",
            description="A test workflow",
        )
        assert definition.workflow_id == "workflow-1"
        assert definition.name == "Test Workflow"
        assert definition.description == "A test workflow"
        assert definition.nodes == []
        assert definition.schedule is None
        assert definition.metadata == {}

    def test_workflow_definition_with_nodes(self):
        """Test WorkflowDefinition with nodes."""
        nodes = [
            WorkflowNode(node_id="node-1", name="Node 1", command="test"),
            WorkflowNode(node_id="node-2", name="Node 2", command="test"),
        ]
        definition = WorkflowDefinition(
            workflow_id="workflow-2", name="Test", nodes=nodes
        )
        assert len(definition.nodes) == 2

    def test_workflow_definition_with_schedule(self):
        """Test WorkflowDefinition with schedule."""
        definition = WorkflowDefinition(
            workflow_id="workflow-3", name="Test", schedule="0 * * * *"
        )
        assert definition.schedule == "0 * * * *"

    def test_workflow_definition_with_metadata(self):
        """Test WorkflowDefinition with metadata."""
        metadata = {"owner": "team", "environment": "prod"}
        definition = WorkflowDefinition(
            workflow_id="workflow-4", name="Test", metadata=metadata
        )
        assert definition.metadata == metadata

    def test_workflow_definition_min_length_validation(self):
        """Test WorkflowDefinition workflow_id and name minimum length."""
        with pytest.raises(ValidationError):
            WorkflowDefinition(workflow_id="", name="Test")

        with pytest.raises(ValidationError):
            WorkflowDefinition(workflow_id="test", name="")

    def test_workflow_definition_max_length_validation(self):
        """Test WorkflowDefinition workflow_id and name maximum length."""
        long_id = "a" * 129
        with pytest.raises(ValidationError):
            WorkflowDefinition(workflow_id=long_id, name="Test")

        long_name = "a" * 129
        with pytest.raises(ValidationError):
            WorkflowDefinition(workflow_id="test", name=long_name)

    def test_workflow_definition_boundary_lengths(self):
        """Test WorkflowDefinition at boundary lengths."""
        definition = WorkflowDefinition(
            workflow_id="a" * 128, name="b" * 128
        )
        assert len(definition.workflow_id) == 128
        assert len(definition.name) == 128

    def test_workflow_definition_complex_metadata(self):
        """Test WorkflowDefinition with complex metadata."""
        metadata = {
            "owner": "team",
            "tags": ["important", "scheduled"],
            "settings": {"timeout": 300, "retries": 3},
        }
        definition = WorkflowDefinition(
            workflow_id="workflow-5", name="Test", metadata=metadata
        )
        assert definition.metadata == metadata


class TestWorkflowRequest:
    """Test cases for WorkflowRequest model."""

    def test_workflow_request_creation(self):
        """Test creating a valid WorkflowRequest."""
        request = WorkflowRequest(workflow_id="workflow-1")
        assert request.workflow_id == "workflow-1"
        assert request.params == {}
        assert request.requested_by == "system"
        assert request.priority == TaskPriority.MEDIUM

    def test_workflow_request_with_params(self):
        """Test WorkflowRequest with parameters."""
        params = {"message": "hello", "count": 5}
        request = WorkflowRequest(workflow_id="workflow-1", params=params)
        assert request.params == params

    def test_workflow_request_with_requested_by(self):
        """Test WorkflowRequest with requested_by field."""
        request = WorkflowRequest(
            workflow_id="workflow-1", requested_by="user-123"
        )
        assert request.requested_by == "user-123"

    def test_workflow_request_with_priority(self):
        """Test WorkflowRequest with priority."""
        request = WorkflowRequest(
            workflow_id="workflow-1", priority=TaskPriority.HIGH
        )
        assert request.priority == TaskPriority.HIGH

    def test_workflow_request_all_priorities(self):
        """Test WorkflowRequest with all priority levels."""
        for priority in TaskPriority:
            request = WorkflowRequest(
                workflow_id="workflow-1", priority=priority
            )
            assert request.priority == priority

    def test_workflow_request_complex_params(self):
        """Test WorkflowRequest with complex parameters."""
        params = {
            "string": "test",
            "number": 42,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        request = WorkflowRequest(workflow_id="workflow-1", params=params)
        assert request.params == params

    def test_workflow_request_min_length_validation(self):
        """Test WorkflowRequest workflow_id minimum length."""
        with pytest.raises(ValidationError):
            WorkflowRequest(workflow_id="")

    def test_workflow_request_max_length_validation(self):
        """Test WorkflowRequest workflow_id maximum length."""
        long_id = "a" * 129
        with pytest.raises(ValidationError):
            WorkflowRequest(workflow_id=long_id)

    def test_workflow_request_boundary_length(self):
        """Test WorkflowRequest at boundary length."""
        request = WorkflowRequest(workflow_id="a" * 128)
        assert len(request.workflow_id) == 128


class TestWorkflowTask:
    """Test cases for WorkflowTask model."""

    def test_workflow_task_creation(self):
        """Test creating a valid WorkflowTask."""
        task = WorkflowTask(
            task_id="task-1",
            workflow_id="workflow-1",
            status=WorkflowStatus.PENDING,
        )
        assert task.task_id == "task-1"
        assert task.workflow_id == "workflow-1"
        assert task.status == WorkflowStatus.PENDING
        assert task.current_node is None
        assert task.completed_nodes == []
        assert task.failed_nodes == []
        assert task.params == {}
        assert task.result == {}
        assert task.retry_count == 0

    def test_workflow_task_with_current_node(self):
        """Test WorkflowTask with current_node."""
        task = WorkflowTask(
            task_id="task-1",
            workflow_id="workflow-1",
            current_node="node-1",
        )
        assert task.current_node == "node-1"

    def test_workflow_task_with_completed_nodes(self):
        """Test WorkflowTask with completed nodes."""
        task = WorkflowTask(
            task_id="task-1",
            workflow_id="workflow-1",
            completed_nodes=["node-1", "node-2"],
        )
        assert len(task.completed_nodes) == 2

    def test_workflow_task_with_failed_nodes(self):
        """Test WorkflowTask with failed nodes."""
        task = WorkflowTask(
            task_id="task-1",
            workflow_id="workflow-1",
            failed_nodes=["node-3"],
        )
        assert len(task.failed_nodes) == 1

    def test_workflow_task_with_params(self):
        """Test WorkflowTask with parameters."""
        params = {"key": "value"}
        task = WorkflowTask(
            task_id="task-1", workflow_id="workflow-1", params=params
        )
        assert task.params == params

    def test_workflow_task_with_result(self):
        """Test WorkflowTask with result."""
        result = {"output": "success"}
        task = WorkflowTask(
            task_id="task-1", workflow_id="workflow-1", result=result
        )
        assert task.result == result

    def test_workflow_task_with_retry_count(self):
        """Test WorkflowTask with retry count."""
        task = WorkflowTask(
            task_id="task-1", workflow_id="workflow-1", retry_count=5
        )
        assert task.retry_count == 5

    def test_workflow_task_all_statuses(self):
        """Test WorkflowTask with all possible statuses."""
        for status in WorkflowStatus:
            task = WorkflowTask(
                task_id="task-1", workflow_id="workflow-1", status=status
            )
            assert task.status == status

    def test_workflow_task_datetime_defaults(self):
        """Test WorkflowTask datetime field defaults."""
        task = WorkflowTask(task_id="task-1", workflow_id="workflow-1")
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    def test_workflow_task_min_length_validation(self):
        """Test WorkflowTask task_id minimum length."""
        with pytest.raises(ValidationError):
            WorkflowTask(task_id="", workflow_id="workflow-1")

    def test_workflow_task_max_length_validation(self):
        """Test WorkflowTask task_id maximum length."""
        long_id = "a" * 129
        with pytest.raises(ValidationError):
            WorkflowTask(task_id=long_id, workflow_id="workflow-1")

    def test_workflow_task_boundary_length(self):
        """Test WorkflowTask at boundary length."""
        task = WorkflowTask(task_id="a" * 128, workflow_id="workflow-1")
        assert len(task.task_id) == 128


class TestWorkflowExecutionResult:
    """Test cases for WorkflowExecutionResult model."""

    def test_workflow_execution_result_creation(self):
        """Test creating a valid WorkflowExecutionResult."""
        result = WorkflowExecutionResult(
            task_id="task-1",
            workflow_id="workflow-1",
            success=True,
            duration_seconds=5.0,
        )
        assert result.task_id == "task-1"
        assert result.workflow_id == "workflow-1"
        assert result.success is True
        assert result.duration_seconds == 5.0
        assert result.node_results == {}
        assert result.error == ""

    def test_workflow_execution_result_with_node_results(self):
        """Test WorkflowExecutionResult with node results."""
        node_results = {"node-1": {"output": "success"}}
        result = WorkflowExecutionResult(
            task_id="task-1",
            workflow_id="workflow-1",
            success=True,
            duration_seconds=5.0,
            node_results=node_results,
        )
        assert result.node_results == node_results

    def test_workflow_execution_result_with_error(self):
        """Test WorkflowExecutionResult with error."""
        result = WorkflowExecutionResult(
            task_id="task-1",
            workflow_id="workflow-1",
            success=False,
            duration_seconds=5.0,
            error="Node failed",
        )
        assert result.error == "Node failed"

    def test_workflow_execution_result_failure(self):
        """Test WorkflowExecutionResult for failed execution."""
        result = WorkflowExecutionResult(
            task_id="task-1",
            workflow_id="workflow-1",
            success=False,
            duration_seconds=5.0,
        )
        assert result.success is False

    def test_workflow_execution_result_zero_duration(self):
        """Test WorkflowExecutionResult with zero duration."""
        result = WorkflowExecutionResult(
            task_id="task-1",
            workflow_id="workflow-1",
            success=True,
            duration_seconds=0.0,
        )
        assert result.duration_seconds == 0.0

    def test_workflow_execution_result_large_duration(self):
        """Test WorkflowExecutionResult with large duration."""
        result = WorkflowExecutionResult(
            task_id="task-1",
            workflow_id="workflow-1",
            success=True,
            duration_seconds=3600.0,
        )
        assert result.duration_seconds == 3600.0


class TestWorkflowVersion:
    """Test cases for WorkflowVersion model."""

    def test_workflow_version_creation(self):
        """Test creating a valid WorkflowVersion."""
        version = WorkflowVersion(
            version="v1.0.0",
            workflow_id="workflow-1",
            commit_hash="abc123",
            message="Initial version",
        )
        assert version.version == "v1.0.0"
        assert version.workflow_id == "workflow-1"
        assert version.commit_hash == "abc123"
        assert version.message == "Initial version"

    def test_workflow_version_datetime_default(self):
        """Test WorkflowVersion datetime field default."""
        version = WorkflowVersion(
            version="v1.0.0",
            workflow_id="workflow-1",
            commit_hash="abc123",
            message="Test",
        )
        assert isinstance(version.created_at, datetime)

    def test_workflow_version_various_versions(self):
        """Test WorkflowVersion with various version strings."""
        versions = ["v1.0.0", "v2.1.3", "v3.0.0-beta", "v1.2.3-rc1"]
        for ver in versions:
            version = WorkflowVersion(
                version=ver,
                workflow_id="workflow-1",
                commit_hash="abc123",
                message="Test",
            )
            assert version.version == ver


class TestWorkflowTemplate:
    """Test cases for WorkflowTemplate model."""

    def test_workflow_template_creation(self):
        """Test creating a valid WorkflowTemplate."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test Template",
            description="A test template",
            source="echo {{ message }}",
        )
        assert template.template_id == "template-1"
        assert template.name == "Test Template"
        assert template.description == "A test template"
        assert template.source == "echo {{ message }}"
        assert template.default_params == {}

    def test_workflow_template_with_default_params(self):
        """Test WorkflowTemplate with default parameters."""
        default_params = {"user": "system", "timeout": 60}
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="test",
            default_params=default_params,
        )
        assert template.default_params == default_params

    def test_workflow_template_min_length_validation(self):
        """Test WorkflowTemplate template_id and name minimum length."""
        with pytest.raises(ValidationError):
            WorkflowTemplate(template_id="", name="Test", source="test")

        with pytest.raises(ValidationError):
            WorkflowTemplate(template_id="test", name="", source="test")

    def test_workflow_template_max_length_validation(self):
        """Test WorkflowTemplate template_id and name maximum length."""
        long_id = "a" * 129
        with pytest.raises(ValidationError):
            WorkflowTemplate(template_id=long_id, name="Test", source="test")

        long_name = "a" * 129
        with pytest.raises(ValidationError):
            WorkflowTemplate(template_id="test", name=long_name, source="test")

    def test_workflow_template_boundary_lengths(self):
        """Test WorkflowTemplate at boundary lengths."""
        template = WorkflowTemplate(
            template_id="a" * 128, name="b" * 128, source="test"
        )
        assert len(template.template_id) == 128
        assert len(template.name) == 128


class TestRetryPolicy:
    """Test cases for RetryPolicy model."""

    def test_retry_policy_creation(self):
        """Test creating a valid RetryPolicy."""
        policy = RetryPolicy(
            name="test-policy",
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
        )
        assert policy.name == "test-policy"
        assert policy.max_retries == 3
        assert policy.base_delay_seconds == 1.0
        assert policy.max_delay_seconds == 60.0
        assert policy.exponential_base == 2.0
        assert policy.retryable_errors == []

    def test_retry_policy_with_retryable_errors(self):
        """Test RetryPolicy with retryable errors."""
        errors = ["timeout", "connection", "network"]
        policy = RetryPolicy(
            name="test-policy",
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            retryable_errors=errors,
        )
        assert policy.retryable_errors == errors

    def test_retry_policy_custom_exponential_base(self):
        """Test RetryPolicy with custom exponential base."""
        policy = RetryPolicy(
            name="test-policy",
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            exponential_base=3.0,
        )
        assert policy.exponential_base == 3.0

    def test_retry_policy_zero_retries(self):
        """Test RetryPolicy with zero retries."""
        policy = RetryPolicy(
            name="test-policy",
            max_retries=0,
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
        )
        assert policy.max_retries == 0

    def test_retry_policy_validation_ge_zero(self):
        """Test RetryPolicy validation for >= 0 constraints."""
        with pytest.raises(ValidationError):
            RetryPolicy(
                name="test-policy",
                max_retries=-1,
                base_delay_seconds=1.0,
                max_delay_seconds=60.0,
            )

        with pytest.raises(ValidationError):
            RetryPolicy(
                name="test-policy",
                max_retries=3,
                base_delay_seconds=-1.0,
                max_delay_seconds=60.0,
            )

        with pytest.raises(ValidationError):
            RetryPolicy(
                name="test-policy",
                max_retries=3,
                base_delay_seconds=1.0,
                max_delay_seconds=-1.0,
            )

    def test_retry_policy_exponential_base_validation(self):
        """Test RetryPolicy exponential_base >= 1.0 constraint."""
        with pytest.raises(ValidationError):
            RetryPolicy(
                name="test-policy",
                max_retries=3,
                base_delay_seconds=1.0,
                max_delay_seconds=60.0,
                exponential_base=0.5,
            )


class TestScheduledTask:
    """Test cases for ScheduledTask model."""

    def test_scheduled_task_creation(self):
        """Test creating a valid ScheduledTask."""
        task = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
        )
        assert task.schedule_id == "schedule-1"
        assert task.workflow_id == "workflow-1"
        assert task.cron == "0 * * * *"
        assert task.next_run is None
        assert task.enabled is True
        assert task.params == {}

    def test_scheduled_task_with_next_run(self):
        """Test ScheduledTask with next_run datetime."""
        next_run = datetime(2024, 1, 1, 12, 0, 0)
        task = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
            next_run=next_run,
        )
        assert task.next_run == next_run

    def test_scheduled_task_disabled(self):
        """Test ScheduledTask with enabled=False."""
        task = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
            enabled=False,
        )
        assert task.enabled is False

    def test_scheduled_task_with_params(self):
        """Test ScheduledTask with parameters."""
        params = {"message": "scheduled"}
        task = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
            params=params,
        )
        assert task.params == params

    def test_scheduled_task_various_cron_expressions(self):
        """Test ScheduledTask with various cron expressions."""
        cron_expressions = [
            "0 * * * *",
            "*/5 * * * *",
            "0 0 * * *",
            "0 0 * * 0",
            "0 0 1 * *",
        ]
        for cron in cron_expressions:
            task = ScheduledTask(
                schedule_id="schedule-1",
                workflow_id="workflow-1",
                cron=cron,
            )
            assert task.cron == cron


class TestWorkflowMetric:
    """Test cases for WorkflowMetric model."""

    def test_workflow_metric_creation(self):
        """Test creating a valid WorkflowMetric."""
        metric = WorkflowMetric(
            metric_name="test_metric",
            value=42.5,
        )
        assert metric.metric_name == "test_metric"
        assert metric.value == 42.5
        assert metric.labels == {}
        assert isinstance(metric.timestamp, datetime)

    def test_workflow_metric_with_labels(self):
        """Test WorkflowMetric with labels."""
        labels = {"workflow_id": "test", "status": "success"}
        metric = WorkflowMetric(
            metric_name="test_metric", value=42.5, labels=labels
        )
        assert metric.labels == labels

    def test_workflow_metric_with_timestamp(self):
        """Test WorkflowMetric with custom timestamp."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        metric = WorkflowMetric(
            metric_name="test_metric", value=42.5, timestamp=timestamp
        )
        assert metric.timestamp == timestamp

    def test_workflow_metric_zero_value(self):
        """Test WorkflowMetric with zero value."""
        metric = WorkflowMetric(metric_name="test_metric", value=0.0)
        assert metric.value == 0.0

    def test_workflow_metric_negative_value(self):
        """Test WorkflowMetric with negative value."""
        metric = WorkflowMetric(metric_name="test_metric", value=-10.5)
        assert metric.value == -10.5

    def test_workflow_metric_large_value(self):
        """Test WorkflowMetric with large value."""
        metric = WorkflowMetric(metric_name="test_metric", value=1e10)
        assert metric.value == 1e10


class TestServiceHealth:
    """Test cases for ServiceHealth model."""

    def test_service_health_creation(self):
        """Test creating a valid ServiceHealth."""
        health = ServiceHealth(status="ok", service="test-service")
        assert health.status == "ok"
        assert health.service == "test-service"
        assert health.uptime_seconds == 0
        assert health.workflow_count == 0

    def test_service_health_with_uptime(self):
        """Test ServiceHealth with uptime."""
        health = ServiceHealth(
            status="ok", service="test-service", uptime_seconds=3600
        )
        assert health.uptime_seconds == 3600

    def test_service_health_with_workflow_count(self):
        """Test ServiceHealth with workflow count."""
        health = ServiceHealth(
            status="ok", service="test-service", workflow_count=10
        )
        assert health.workflow_count == 10

    def test_service_health_degraded_status(self):
        """Test ServiceHealth with degraded status."""
        health = ServiceHealth(status="degraded", service="test-service")
        assert health.status == "degraded"

    def test_service_health_various_statuses(self):
        """Test ServiceHealth with various status values."""
        statuses = ["ok", "degraded", "error", "unavailable"]
        for status in statuses:
            health = ServiceHealth(status=status, service="test-service")
            assert health.status == status


class TestSagaStep:
    """Test cases for SagaStep model."""

    def test_saga_step_creation(self):
        """Test creating a valid SagaStep."""
        step = SagaStep(
            step_id="step-1",
            service="service-1",
            action="create",
            compensation="delete",
        )
        assert step.step_id == "step-1"
        assert step.service == "service-1"
        assert step.action == "create"
        assert step.compensation == "delete"
        assert step.status == "pending"
        assert step.result == {}

    def test_saga_step_with_result(self):
        """Test SagaStep with result."""
        result = {"output": "success"}
        step = SagaStep(
            step_id="step-1",
            service="service-1",
            action="create",
            compensation="delete",
            result=result,
        )
        assert step.result == result

    def test_saga_step_custom_status(self):
        """Test SagaStep with custom status."""
        step = SagaStep(
            step_id="step-1",
            service="service-1",
            action="create",
            compensation="delete",
            status="executing",
        )
        assert step.status == "executing"

    def test_saga_step_various_statuses(self):
        """Test SagaStep with various status values."""
        statuses = ["pending", "executing", "success", "failed", "compensated"]
        for status in statuses:
            step = SagaStep(
                step_id="step-1",
                service="service-1",
                action="create",
                compensation="delete",
                status=status,
            )
            assert step.status == status


class TestSagaTransaction:
    """Test cases for SagaTransaction model."""

    def test_saga_transaction_creation(self):
        """Test creating a valid SagaTransaction."""
        transaction = SagaTransaction(
            saga_id="saga-1",
            task_id="task-1",
        )
        assert transaction.saga_id == "saga-1"
        assert transaction.task_id == "task-1"
        assert transaction.steps == []
        assert transaction.status == "pending"
        assert isinstance(transaction.created_at, datetime)

    def test_saga_transaction_with_steps(self):
        """Test SagaTransaction with steps."""
        steps = [
            SagaStep(
                step_id="step-1",
                service="service-1",
                action="create",
                compensation="delete",
            )
        ]
        transaction = SagaTransaction(
            saga_id="saga-1", task_id="task-1", steps=steps
        )
        assert len(transaction.steps) == 1

    def test_saga_transaction_with_status(self):
        """Test SagaTransaction with custom status."""
        transaction = SagaTransaction(
            saga_id="saga-1", task_id="task-1", status="executing"
        )
        assert transaction.status == "executing"

    def test_saga_transaction_datetime_default(self):
        """Test SagaTransaction datetime field default."""
        transaction = SagaTransaction(saga_id="saga-1", task_id="task-1")
        assert isinstance(transaction.created_at, datetime)

    def test_saga_transaction_various_statuses(self):
        """Test SagaTransaction with various status values."""
        statuses = ["pending", "executing", "success", "failed", "compensating"]
        for status in statuses:
            transaction = SagaTransaction(
                saga_id="saga-1", task_id="task-1", status=status
            )
            assert transaction.status == status
