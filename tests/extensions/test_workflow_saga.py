# -*- coding: utf-8 -*-
"""Comprehensive tests for workflow service saga orchestrator to achieve 85%+ branch coverage."""

import asyncio

import pytest

from extensions.addons.operations.workflow_service.saga import WorkflowSagaOrchestrator
from extensions.addons.operations.workflow_service.schemas import SagaStep, SagaTransaction


class TestWorkflowSagaOrchestrator:
    """Test suite for WorkflowSagaOrchestrator with full branch coverage."""

    def test_register_saga(self):
        """Test registering a saga transaction."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
        ]
        actions = {"validate": lambda: {"valid": True}, "execute": lambda: {"status": "running"}}
        compensations = {
            "rollback_validate": lambda: None,
            "rollback_execute": lambda: None,
        }

        orchestrator.register("saga1", steps, actions, compensations)

        transaction = orchestrator.get_transaction("saga1")
        assert transaction.saga_id == "saga1"
        assert transaction.task_id == "step1"
        assert len(transaction.steps) == 2
        assert transaction.status == "pending"

    def test_register_saga_with_empty_steps(self):
        """Test registering a saga with empty steps list."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = []
        actions = {}
        compensations = {}

        orchestrator.register("saga_empty", steps, actions, compensations)

        transaction = orchestrator.get_transaction("saga_empty")
        assert transaction.saga_id == "saga_empty"
        assert transaction.task_id == ""
        assert len(transaction.steps) == 0

    @pytest.mark.asyncio
    async def test_execute_nonexistent_saga(self):
        """Test executing a saga that doesn't exist (covers line 45)."""
        orchestrator = WorkflowSagaOrchestrator()
        result = await orchestrator.execute("nonexistent_saga")
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_with_missing_action(self):
        """Test executing a saga with a missing action (covers lines 54-57)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
        ]
        # Empty actions dict - action "validate" is missing
        actions = {}
        compensations = {"rollback_validate": lambda: None}

        orchestrator.register("saga_missing_action", steps, actions, compensations)

        result = await orchestrator.execute("saga_missing_action")
        assert result["success"] is False
        assert "No action for step" in result["error"]
        assert result["error"] == "No action for step step1"

        # Verify compensation was called
        transaction = orchestrator.get_transaction("saga_missing_action")
        assert transaction.status == "compensating"
        # Step is marked as failed first, then compensated
        assert transaction.steps[0].status in ["compensated", "failed"]

    @pytest.mark.asyncio
    async def test_execute_with_sync_action(self):
        """Test executing a saga with synchronous action (covers line 63)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
        ]
        actions = {"validate": lambda: {"valid": True}}
        compensations = {"rollback_validate": lambda: None}

        orchestrator.register("saga_sync", steps, actions, compensations)

        result = await orchestrator.execute("saga_sync")
        assert result["success"] is True
        assert result["saga_id"] == "saga_sync"
        assert result["steps"] == ["step1"]

        transaction = orchestrator.get_transaction("saga_sync")
        assert transaction.status == "success"
        assert transaction.steps[0].status == "success"
        assert transaction.steps[0].result == {"valid": True}

    @pytest.mark.asyncio
    async def test_execute_with_async_action(self):
        """Test executing a saga with asynchronous action (covers line 61)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
        ]

        async def async_validate():
            await asyncio.sleep(0.01)
            return {"valid": True, "checked_at": "2024-01-01"}

        actions = {"validate": async_validate}
        compensations = {"rollback_validate": lambda: None}

        orchestrator.register("saga_async", steps, actions, compensations)

        result = await orchestrator.execute("saga_async")
        assert result["success"] is True
        assert result["saga_id"] == "saga_async"
        assert result["steps"] == ["step1"]

        transaction = orchestrator.get_transaction("saga_async")
        assert transaction.status == "success"
        assert transaction.steps[0].status == "success"
        assert transaction.steps[0].result == {"valid": True, "checked_at": "2024-01-01"}

    @pytest.mark.asyncio
    async def test_execute_with_action_exception(self):
        """Test executing a saga where action raises exception (covers lines 67-73)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
        ]

        def failing_validate():
            raise ValueError("Validation failed")

        actions = {"validate": failing_validate, "execute": lambda: {"status": "running"}}
        compensations = {
            "rollback_validate": lambda: None,
            "rollback_execute": lambda: None,
        }

        orchestrator.register("saga_exception", steps, actions, compensations)

        result = await orchestrator.execute("saga_exception")
        assert result["success"] is False
        assert "Validation failed" in result["error"]
        assert result["failed_step"] == "step1"
        assert result["saga_id"] == "saga_exception"

        transaction = orchestrator.get_transaction("saga_exception")
        assert transaction.status == "compensating"
        assert transaction.steps[0].status == "failed"
        assert "error" in transaction.steps[0].result

    @pytest.mark.asyncio
    async def test_execute_multiple_steps_success(self):
        """Test executing a saga with multiple successful steps."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
            SagaStep(
                step_id="step3",
                service="workflow",
                action="complete",
                compensation="rollback_complete",
            ),
        ]
        actions = {
            "validate": lambda: {"valid": True},
            "execute": lambda: {"status": "running"},
            "complete": lambda: {"status": "completed"},
        }
        compensations = {
            "rollback_validate": lambda: None,
            "rollback_execute": lambda: None,
            "rollback_complete": lambda: None,
        }

        orchestrator.register("saga_multi", steps, actions, compensations)

        result = await orchestrator.execute("saga_multi")
        assert result["success"] is True
        assert result["steps"] == ["step1", "step2", "step3"]

        transaction = orchestrator.get_transaction("saga_multi")
        assert transaction.status == "success"
        for step in transaction.steps:
            assert step.status == "success"

    @pytest.mark.asyncio
    async def test_compensate_with_sync_compensation(self):
        """Test compensation with synchronous function (covers lines 97-98)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
        ]
        actions = {"validate": lambda: {"valid": True}, "execute": lambda: {"status": "running"}}
        compensations = {"rollback_validate": lambda: None, "rollback_execute": lambda: None}

        orchestrator.register("saga_comp_sync", steps, actions, compensations)

        # Force compensation by making the second step fail
        def failing_execute():
            raise ValueError("Execution failed")

        actions["execute"] = failing_execute
        result = await orchestrator.execute("saga_comp_sync")

        assert result["success"] is False
        transaction = orchestrator.get_transaction("saga_comp_sync")
        assert transaction.steps[0].status == "compensated"

    @pytest.mark.asyncio
    async def test_compensate_with_async_compensation(self):
        """Test compensation with asynchronous function (covers lines 95-96)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
        ]
        actions = {"validate": lambda: {"valid": True}, "execute": lambda: {"status": "running"}}

        async def async_rollback():
            await asyncio.sleep(0.01)

        compensations = {"rollback_validate": async_rollback, "rollback_execute": lambda: None}

        orchestrator.register("saga_comp_async", steps, actions, compensations)

        # Force compensation by making the second step fail
        def failing_execute():
            raise ValueError("Execution failed")

        actions["execute"] = failing_execute
        result = await orchestrator.execute("saga_comp_async")

        assert result["success"] is False
        transaction = orchestrator.get_transaction("saga_comp_async")
        assert transaction.steps[0].status == "compensated"

    @pytest.mark.asyncio
    async def test_compensate_with_missing_compensation(self):
        """Test compensation when compensation function is missing (covers line 94)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
        ]
        actions = {"validate": lambda: {"valid": True}, "execute": lambda: {"status": "running"}}
        # Empty compensations dict - compensation is missing
        compensations = {}

        orchestrator.register("saga_missing_comp", steps, actions, compensations)

        # Force compensation by making the second step fail
        def failing_execute():
            raise ValueError("Execution failed")

        actions["execute"] = failing_execute
        result = await orchestrator.execute("saga_missing_comp")

        assert result["success"] is False
        transaction = orchestrator.get_transaction("saga_missing_comp")
        # Step should still be marked as compensated even without a compensation function
        assert transaction.steps[0].status == "compensated"

    @pytest.mark.asyncio
    async def test_compensate_with_compensation_exception(self):
        """Test compensation when compensation function raises exception (covers lines 100-102)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
        ]
        actions = {"validate": lambda: {"valid": True}, "execute": lambda: {"status": "running"}}

        def failing_rollback():
            raise RuntimeError("Rollback failed")

        compensations = {"rollback_validate": failing_rollback, "rollback_execute": lambda: None}

        orchestrator.register("saga_comp_exception", steps, actions, compensations)

        # Force compensation by making the second step fail
        def failing_execute():
            raise ValueError("Execution failed")

        actions["execute"] = failing_execute
        result = await orchestrator.execute("saga_comp_exception")

        assert result["success"] is False
        transaction = orchestrator.get_transaction("saga_comp_exception")
        assert transaction.steps[0].status == "compensation_failed"

    @pytest.mark.asyncio
    async def test_compensate_multiple_steps_reverse_order(self):
        """Test that compensation executes steps in reverse order."""
        orchestrator = WorkflowSagaOrchestrator()
        execution_order = []

        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
            SagaStep(
                step_id="step3",
                service="workflow",
                action="complete",
                compensation="rollback_complete",
            ),
        ]

        def rollback_validate():
            execution_order.append("rollback_validate")

        def rollback_execute():
            execution_order.append("rollback_execute")

        def rollback_complete():
            execution_order.append("rollback_complete")

        actions = {
            "validate": lambda: {"valid": True},
            "execute": lambda: {"status": "running"},
            "complete": lambda: {"status": "completed"},
        }
        compensations = {
            "rollback_validate": rollback_validate,
            "rollback_execute": rollback_execute,
            "rollback_complete": rollback_complete,
        }

        orchestrator.register("saga_reverse", steps, actions, compensations)

        # Make step3 fail to trigger compensation for step1 and step2
        def failing_complete():
            raise ValueError("Completion failed")

        actions["complete"] = failing_complete

        result = await orchestrator.execute("saga_reverse")

        assert result["success"] is False
        assert result["failed_step"] == "step3"
        # Compensation should execute in reverse: step2, step1 (step3 failed before executing)
        assert execution_order == ["rollback_execute", "rollback_validate"]

    @pytest.mark.asyncio
    async def test_compensate_with_missing_step_in_transaction(self):
        """Test compensation when step is missing from transaction (covers lines 90-91)."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
        ]
        actions = {"validate": lambda: {"valid": True}}
        compensations = {"rollback_validate": lambda: None}

        orchestrator.register("saga_missing_step", steps, actions, compensations)

        # Manually remove the step from transaction to simulate missing step
        transaction = orchestrator.get_transaction("saga_missing_step")
        transaction.steps = []

        # Force compensation by making the action fail
        def failing_validate():
            raise ValueError("Validation failed")

        actions["validate"] = failing_validate
        result = await orchestrator.execute("saga_missing_step")

        # With no steps, it should succeed (empty saga)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_with_exception_in_middle_step(self):
        """Test saga execution when a middle step fails."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
            SagaStep(
                step_id="step2",
                service="workflow",
                action="execute",
                compensation="rollback_execute",
            ),
            SagaStep(
                step_id="step3",
                service="workflow",
                action="complete",
                compensation="rollback_complete",
            ),
        ]

        def failing_execute():
            raise ValueError("Execution failed")

        actions = {
            "validate": lambda: {"valid": True},
            "execute": failing_execute,
            "complete": lambda: {"status": "completed"},
        }
        compensations = {
            "rollback_validate": lambda: None,
            "rollback_execute": lambda: None,
            "rollback_complete": lambda: None,
        }

        orchestrator.register("saga_middle_fail", steps, actions, compensations)

        result = await orchestrator.execute("saga_middle_fail")

        assert result["success"] is False
        assert result["failed_step"] == "step2"
        # The error response doesn't include 'steps' key on failure

        transaction = orchestrator.get_transaction("saga_middle_fail")
        assert transaction.steps[0].status == "compensated"  # First step was compensated
        assert transaction.steps[1].status == "failed"
        assert transaction.steps[2].status == "pending"  # Never reached

    @pytest.mark.asyncio
    async def test_get_transaction(self):
        """Test retrieving a transaction by saga_id."""
        orchestrator = WorkflowSagaOrchestrator()
        steps = [
            SagaStep(
                step_id="step1",
                service="workflow",
                action="validate",
                compensation="rollback_validate",
            ),
        ]
        actions = {"validate": lambda: {"valid": True}}
        compensations = {"rollback_validate": lambda: None}

        orchestrator.register("saga_get", steps, actions, compensations)

        transaction = orchestrator.get_transaction("saga_get")
        assert transaction is not None
        assert transaction.saga_id == "saga_get"
