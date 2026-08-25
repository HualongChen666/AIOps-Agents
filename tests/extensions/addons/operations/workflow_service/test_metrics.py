# -*- coding: utf-8 -*-
"""Tests for workflow_service metrics module."""

import pytest
from metrics import (
    WORKFLOW_ACTIVE_EXECUTIONS,
    WORKFLOW_EXECUTION_DURATION,
    WORKFLOW_NODE_EXECUTION_DURATION,
    WORKFLOW_RETRY_ATTEMPTS,
    WORKFLOW_SAGA_STATUS,
    WORKFLOW_SCHEDULED_TASKS,
    WORKFLOW_TEMPLATE_RENDERS,
    WORKFLOW_VERSION_COMMITS,
    WORKFLOWS_COMPLETED,
    WORKFLOWS_CREATED,
)


class TestWorkflowsCreated:
    """Test cases for WORKFLOWS_CREATED counter."""

    def test_workflows_created_is_counter(self):
        """Test that WORKFLOWS_CREATED is a Counter metric."""
        from prometheus_client import Counter

        assert isinstance(WORKFLOWS_CREATED, Counter)

    def test_workflows_created_has_labels(self):
        """Test that WORKFLOWS_CREATED has priority label."""
        assert "priority" in WORKFLOWS_CREATED._labelnames

    def test_workflows_created_increment(self):
        """Test incrementing WORKFLOWS_CREATED counter."""
        initial_value = WORKFLOWS_CREATED.labels(priority="high")._value.get()
        WORKFLOWS_CREATED.labels(priority="high").inc()
        new_value = WORKFLOWS_CREATED.labels(priority="high")._value.get()
        assert new_value == initial_value + 1

    def test_workflows_created_multiple_priorities(self):
        """Test WORKFLOWS_CREATED with different priority labels."""
        priorities = ["low", "medium", "high", "critical"]
        for priority in priorities:
            WORKFLOWS_CREATED.labels(priority=priority).inc()

        for priority in priorities:
            value = WORKFLOWS_CREATED.labels(priority=priority)._value.get()
            assert value >= 1

    def test_workflows_created_increment_by_amount(self):
        """Test incrementing WORKFLOWS_CREATED by specific amount."""
        initial_value = WORKFLOWS_CREATED.labels(priority="medium")._value.get()
        WORKFLOWS_CREATED.labels(priority="medium").inc(5)
        new_value = WORKFLOWS_CREATED.labels(priority="medium")._value.get()
        assert new_value == initial_value + 5


class TestWorkflowsCompleted:
    """Test cases for WORKFLOWS_COMPLETED counter."""

    def test_workflows_completed_is_counter(self):
        """Test that WORKFLOWS_COMPLETED is a Counter metric."""
        from prometheus_client import Counter

        assert isinstance(WORKFLOWS_COMPLETED, Counter)

    def test_workflows_completed_has_labels(self):
        """Test that WORKFLOWS_COMPLETED has status label."""
        assert "status" in WORKFLOWS_COMPLETED._labelnames

    def test_workflows_completed_increment(self):
        """Test incrementing WORKFLOWS_COMPLETED counter."""
        initial_value = WORKFLOWS_COMPLETED.labels(status="succeeded")._value.get()
        WORKFLOWS_COMPLETED.labels(status="succeeded").inc()
        new_value = WORKFLOWS_COMPLETED.labels(status="succeeded")._value.get()
        assert new_value == initial_value + 1

    def test_workflows_completed_multiple_statuses(self):
        """Test WORKFLOWS_COMPLETED with different status labels."""
        statuses = ["succeeded", "failed", "timeout"]
        for status in statuses:
            WORKFLOWS_COMPLETED.labels(status=status).inc()

        for status in statuses:
            value = WORKFLOWS_COMPLETED.labels(status=status)._value.get()
            assert value >= 1


class TestWorkflowExecutionDuration:
    """Test cases for WORKFLOW_EXECUTION_DURATION histogram."""

    def test_workflow_execution_duration_is_histogram(self):
        """Test that WORKFLOW_EXECUTION_DURATION is a Histogram metric."""
        from prometheus_client import Histogram

        assert isinstance(WORKFLOW_EXECUTION_DURATION, Histogram)

    def test_workflow_execution_duration_has_labels(self):
        """Test that WORKFLOW_EXECUTION_DURATION has workflow_id label."""
        assert "workflow_id" in WORKFLOW_EXECUTION_DURATION._labelnames

    def test_workflow_execution_duration_observe(self):
        """Test observing workflow execution duration."""
        WORKFLOW_EXECUTION_DURATION.labels(workflow_id="test-1").observe(1.5)
        WORKFLOW_EXECUTION_DURATION.labels(workflow_id="test-1").observe(2.5)
        # Should not raise any exceptions

    def test_workflow_execution_duration_multiple_workflows(self):
        """Test WORKFLOW_EXECUTION_DURATION with different workflow IDs."""
        workflow_ids = ["workflow-1", "workflow-2", "workflow-3"]
        for wid in workflow_ids:
            WORKFLOW_EXECUTION_DURATION.labels(workflow_id=wid).observe(1.0)

        for wid in workflow_ids:
            # Should not raise any exceptions
            WORKFLOW_EXECUTION_DURATION.labels(workflow_id=wid).observe(0.5)

    def test_workflow_execution_duration_observe_small_value(self):
        """Test observing very small duration values."""
        WORKFLOW_EXECUTION_DURATION.labels(workflow_id="test").observe(0.001)
        WORKFLOW_EXECUTION_DURATION.labels(workflow_id="test").observe(0.0001)

    def test_workflow_execution_duration_observe_large_value(self):
        """Test observing large duration values."""
        WORKFLOW_EXECUTION_DURATION.labels(workflow_id="test").observe(3600.0)
        WORKFLOW_EXECUTION_DURATION.labels(workflow_id="test").observe(7200.0)


class TestWorkflowNodeExecutionDuration:
    """Test cases for WORKFLOW_NODE_EXECUTION_DURATION histogram."""

    def test_workflow_node_execution_duration_is_histogram(self):
        """Test that WORKFLOW_NODE_EXECUTION_DURATION is a Histogram metric."""
        from prometheus_client import Histogram

        assert isinstance(WORKFLOW_NODE_EXECUTION_DURATION, Histogram)

    def test_workflow_node_execution_duration_has_labels(self):
        """Test that WORKFLOW_NODE_EXECUTION_DURATION has node_id label."""
        assert "node_id" in WORKFLOW_NODE_EXECUTION_DURATION._labelnames

    def test_workflow_node_execution_duration_observe(self):
        """Test observing node execution duration."""
        WORKFLOW_NODE_EXECUTION_DURATION.labels(node_id="node-1").observe(0.5)
        WORKFLOW_NODE_EXECUTION_DURATION.labels(node_id="node-1").observe(1.0)

    def test_workflow_node_execution_duration_multiple_nodes(self):
        """Test WORKFLOW_NODE_EXECUTION_DURATION with different node IDs."""
        node_ids = ["node-1", "node-2", "node-3"]
        for nid in node_ids:
            WORKFLOW_NODE_EXECUTION_DURATION.labels(node_id=nid).observe(0.5)

    def test_workflow_node_execution_duration_observe_zero(self):
        """Test observing zero duration."""
        WORKFLOW_NODE_EXECUTION_DURATION.labels(node_id="test").observe(0.0)


class TestWorkflowRetryAttempts:
    """Test cases for WORKFLOW_RETRY_ATTEMPTS counter."""

    def test_workflow_retry_attempts_is_counter(self):
        """Test that WORKFLOW_RETRY_ATTEMPTS is a Counter metric."""
        from prometheus_client import Counter

        assert isinstance(WORKFLOW_RETRY_ATTEMPTS, Counter)

    def test_workflow_retry_attempts_has_labels(self):
        """Test that WORKFLOW_RETRY_ATTEMPTS has node_id label."""
        assert "node_id" in WORKFLOW_RETRY_ATTEMPTS._labelnames

    def test_workflow_retry_attempts_increment(self):
        """Test incrementing WORKFLOW_RETRY_ATTEMPTS counter."""
        initial_value = WORKFLOW_RETRY_ATTEMPTS.labels(node_id="node-1")._value.get()
        WORKFLOW_RETRY_ATTEMPTS.labels(node_id="node-1").inc()
        new_value = WORKFLOW_RETRY_ATTEMPTS.labels(node_id="node-1")._value.get()
        assert new_value == initial_value + 1

    def test_workflow_retry_attempts_multiple_nodes(self):
        """Test WORKFLOW_RETRY_ATTEMPTS with different node IDs."""
        node_ids = ["node-1", "node-2", "node-3"]
        for nid in node_ids:
            WORKFLOW_RETRY_ATTEMPTS.labels(node_id=nid).inc()

        for nid in node_ids:
            value = WORKFLOW_RETRY_ATTEMPTS.labels(node_id=nid)._value.get()
            assert value >= 1

    def test_workflow_retry_attempts_increment_multiple(self):
        """Test incrementing retry attempts multiple times."""
        for _ in range(5):
            WORKFLOW_RETRY_ATTEMPTS.labels(node_id="test").inc()
        value = WORKFLOW_RETRY_ATTEMPTS.labels(node_id="test")._value.get()
        assert value >= 5


class TestWorkflowScheduledTasks:
    """Test cases for WORKFLOW_SCHEDULED_TASKS gauge."""

    def test_workflow_scheduled_tasks_is_gauge(self):
        """Test that WORKFLOW_SCHEDULED_TASKS is a Gauge metric."""
        from prometheus_client import Gauge

        assert isinstance(WORKFLOW_SCHEDULED_TASKS, Gauge)

    def test_workflow_scheduled_tasks_has_labels(self):
        """Test that WORKFLOW_SCHEDULED_TASKS has workflow_id label."""
        assert "workflow_id" in WORKFLOW_SCHEDULED_TASKS._labelnames

    def test_workflow_scheduled_tasks_set(self):
        """Test setting WORKFLOW_SCHEDULED_TASKS gauge."""
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test-1").set(5)
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test-1").set(10)

    def test_workflow_scheduled_tasks_multiple_workflows(self):
        """Test WORKFLOW_SCHEDULED_TASKS with different workflow IDs."""
        workflow_ids = ["workflow-1", "workflow-2", "workflow-3"]
        for wid in workflow_ids:
            WORKFLOW_SCHEDULED_TASKS.labels(workflow_id=wid).set(5)

    def test_workflow_scheduled_tasks_set_zero(self):
        """Test setting gauge to zero."""
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test").set(0)

    def test_workflow_scheduled_tasks_set_large_value(self):
        """Test setting gauge to large value."""
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test").set(10000)

    def test_workflow_scheduled_tasks_increment(self):
        """Test incrementing WORKFLOW_SCHEDULED_TASKS gauge."""
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test").inc()
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test").inc(5)

    def test_workflow_scheduled_tasks_decrement(self):
        """Test decrementing WORKFLOW_SCHEDULED_TASKS gauge."""
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test").set(10)
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test").dec()
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id="test").dec(3)


class TestWorkflowActiveExecutions:
    """Test cases for WORKFLOW_ACTIVE_EXECUTIONS gauge."""

    def test_workflow_active_executions_is_gauge(self):
        """Test that WORKFLOW_ACTIVE_EXECUTIONS is a Gauge metric."""
        from prometheus_client import Gauge

        assert isinstance(WORKFLOW_ACTIVE_EXECUTIONS, Gauge)

    def test_workflow_active_executions_no_labels(self):
        """Test that WORKFLOW_ACTIVE_EXECUTIONS has no labels."""
        assert len(WORKFLOW_ACTIVE_EXECUTIONS._labelnames) == 0

    def test_workflow_active_executions_set(self):
        """Test setting WORKFLOW_ACTIVE_EXECUTIONS gauge."""
        WORKFLOW_ACTIVE_EXECUTIONS.set(5)
        WORKFLOW_ACTIVE_EXECUTIONS.set(10)

    def test_workflow_active_executions_set_zero(self):
        """Test setting gauge to zero."""
        WORKFLOW_ACTIVE_EXECUTIONS.set(0)

    def test_workflow_active_executions_increment(self):
        """Test incrementing WORKFLOW_ACTIVE_EXECUTIONS gauge."""
        WORKFLOW_ACTIVE_EXECUTIONS.inc()
        WORKFLOW_ACTIVE_EXECUTIONS.inc(5)

    def test_workflow_active_executions_decrement(self):
        """Test decrementing WORKFLOW_ACTIVE_EXECUTIONS gauge."""
        WORKFLOW_ACTIVE_EXECUTIONS.set(10)
        WORKFLOW_ACTIVE_EXECUTIONS.dec()
        WORKFLOW_ACTIVE_EXECUTIONS.dec(3)


class TestWorkflowVersionCommits:
    """Test cases for WORKFLOW_VERSION_COMMITS counter."""

    def test_workflow_version_commits_is_counter(self):
        """Test that WORKFLOW_VERSION_COMMITS is a Counter metric."""
        from prometheus_client import Counter

        assert isinstance(WORKFLOW_VERSION_COMMITS, Counter)

    def test_workflow_version_commits_has_labels(self):
        """Test that WORKFLOW_VERSION_COMMITS has workflow_id label."""
        assert "workflow_id" in WORKFLOW_VERSION_COMMITS._labelnames

    def test_workflow_version_commits_increment(self):
        """Test incrementing WORKFLOW_VERSION_COMMITS counter."""
        initial_value = WORKFLOW_VERSION_COMMITS.labels(workflow_id="test-1")._value.get()
        WORKFLOW_VERSION_COMMITS.labels(workflow_id="test-1").inc()
        new_value = WORKFLOW_VERSION_COMMITS.labels(workflow_id="test-1")._value.get()
        assert new_value == initial_value + 1

    def test_workflow_version_commits_multiple_workflows(self):
        """Test WORKFLOW_VERSION_COMMITS with different workflow IDs."""
        workflow_ids = ["workflow-1", "workflow-2", "workflow-3"]
        for wid in workflow_ids:
            WORKFLOW_VERSION_COMMITS.labels(workflow_id=wid).inc()

        for wid in workflow_ids:
            value = WORKFLOW_VERSION_COMMITS.labels(workflow_id=wid)._value.get()
            assert value >= 1


class TestWorkflowTemplateRenders:
    """Test cases for WORKFLOW_TEMPLATE_RENDERS counter."""

    def test_workflow_template_renders_is_counter(self):
        """Test that WORKFLOW_TEMPLATE_RENDERS is a Counter metric."""
        from prometheus_client import Counter

        assert isinstance(WORKFLOW_TEMPLATE_RENDERS, Counter)

    def test_workflow_template_renders_has_labels(self):
        """Test that WORKFLOW_TEMPLATE_RENDERS has template_id label."""
        assert "template_id" in WORKFLOW_TEMPLATE_RENDERS._labelnames

    def test_workflow_template_renders_increment(self):
        """Test incrementing WORKFLOW_TEMPLATE_RENDERS counter."""
        initial_value = WORKFLOW_TEMPLATE_RENDERS.labels(template_id="template-1")._value.get()
        WORKFLOW_TEMPLATE_RENDERS.labels(template_id="template-1").inc()
        new_value = WORKFLOW_TEMPLATE_RENDERS.labels(template_id="template-1")._value.get()
        assert new_value == initial_value + 1

    def test_workflow_template_renders_multiple_templates(self):
        """Test WORKFLOW_TEMPLATE_RENDERS with different template IDs."""
        template_ids = ["template-1", "template-2", "template-3"]
        for tid in template_ids:
            WORKFLOW_TEMPLATE_RENDERS.labels(template_id=tid).inc()

        for tid in template_ids:
            value = WORKFLOW_TEMPLATE_RENDERS.labels(template_id=tid)._value.get()
            assert value >= 1


class TestWorkflowSagaStatus:
    """Test cases for WORKFLOW_SAGA_STATUS gauge."""

    def test_workflow_saga_status_is_gauge(self):
        """Test that WORKFLOW_SAGA_STATUS is a Gauge metric."""
        from prometheus_client import Gauge

        assert isinstance(WORKFLOW_SAGA_STATUS, Gauge)

    def test_workflow_saga_status_has_labels(self):
        """Test that WORKFLOW_SAGA_STATUS has saga_id label."""
        assert "saga_id" in WORKFLOW_SAGA_STATUS._labelnames

    def test_workflow_saga_status_set_pending(self):
        """Test setting saga status to pending (0)."""
        WORKFLOW_SAGA_STATUS.labels(saga_id="saga-1").set(0)

    def test_workflow_saga_status_set_success(self):
        """Test setting saga status to success (1)."""
        WORKFLOW_SAGA_STATUS.labels(saga_id="saga-1").set(1)

    def test_workflow_saga_status_set_failed(self):
        """Test setting saga status to failed (2)."""
        WORKFLOW_SAGA_STATUS.labels(saga_id="saga-1").set(2)

    def test_workflow_saga_status_set_compensating(self):
        """Test setting saga status to compensating (3)."""
        WORKFLOW_SAGA_STATUS.labels(saga_id="saga-1").set(3)

    def test_workflow_saga_status_multiple_sagas(self):
        """Test WORKFLOW_SAGA_STATUS with different saga IDs."""
        saga_ids = ["saga-1", "saga-2", "saga-3"]
        for sid in saga_ids:
            WORKFLOW_SAGA_STATUS.labels(saga_id=sid).set(0)

    def test_workflow_saga_status_transitions(self):
        """Test saga status transitions."""
        saga_id = "test-saga"
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(0)  # pending
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(1)  # success
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(2)  # failed
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(3)  # compensating

    def test_workflow_saga_status_set_invalid_value(self):
        """Test setting saga status to invalid value (should still work)."""
        WORKFLOW_SAGA_STATUS.labels(saga_id="test").set(99)


class TestMetricsIntegration:
    """Integration tests for metrics working together."""

    def test_metrics_workflow_lifecycle(self):
        """Test metrics through a complete workflow lifecycle."""
        workflow_id = "test-workflow"
        node_id = "test-node"

        # Create workflow
        WORKFLOWS_CREATED.labels(priority="high").inc()

        # Execute workflow
        WORKFLOW_ACTIVE_EXECUTIONS.inc()
        WORKFLOW_EXECUTION_DURATION.labels(workflow_id=workflow_id).observe(5.0)

        # Execute node
        WORKFLOW_NODE_EXECUTION_DURATION.labels(node_id=node_id).observe(1.0)

        # Retry attempt
        WORKFLOW_RETRY_ATTEMPTS.labels(node_id=node_id).inc()

        # Complete workflow
        WORKFLOW_ACTIVE_EXECUTIONS.dec()
        WORKFLOWS_COMPLETED.labels(status="succeeded").inc()

    def test_metrics_saga_lifecycle(self):
        """Test metrics through a complete saga lifecycle."""
        saga_id = "test-saga"

        # Start saga
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(0)  # pending

        # Execute
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(1)  # success

        # Alternative: fail and compensate
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(2)  # failed
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(3)  # compensating

    def test_metrics_template_lifecycle(self):
        """Test metrics through template lifecycle."""
        template_id = "test-template"

        # Render template multiple times
        for _ in range(5):
            WORKFLOW_TEMPLATE_RENDERS.labels(template_id=template_id).inc()

    def test_metrics_version_lifecycle(self):
        """Test metrics through version lifecycle."""
        workflow_id = "test-workflow"

        # Commit multiple versions
        for _ in range(3):
            WORKFLOW_VERSION_COMMITS.labels(workflow_id=workflow_id).inc()

    def test_metrics_scheduler_lifecycle(self):
        """Test metrics through scheduler lifecycle."""
        workflow_id = "test-workflow"

        # Schedule tasks
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id=workflow_id).set(10)
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id=workflow_id).inc()
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id=workflow_id).dec()
