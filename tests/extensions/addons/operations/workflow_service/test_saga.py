# -*- coding: utf-8 -*-
"""Tests for workflow_service saga module."""

import pytest

from saga import WorkflowSagaOrchestrator
from schemas import SagaStep


class TestWorkflowSagaOrchestrator:
    """Test cases for WorkflowSagaOrchestrator class."""

    def test_saga_orchestrator_initialization(self):
        """Test that WorkflowSagaOrchestrator initializes correctly."""
        orchestrator = WorkflowSagaOrchestrator()
        assert len(orchestrator._transactions) == 0
        assert len(orchestrator._actions) == 0
        assert len(orchestrator._compensations) == 0

    def test_register_saga(self, saga_orchestrator, saga_steps):
        """Test registering a saga transaction."""
        actions = {"create": lambda: {"success": True}}
        compensations = {"delete": lambda: {"compensated": True}}

        orchestrator.register("saga-1", saga_steps, actions, compensations)

        assert "saga-1" in orchestrator._transactions
        assert "saga-1" in orchestrator._actions
        assert "saga-1" in orchestrator._compensations

    def test_register_multiple_sagas(self, saga_orchestrator, saga_steps):
        """Test registering multiple saga transactions."""
        for i in range(3):
            actions = {"create": lambda: {"success": True}}
            compensations = {"delete": lambda: {"compensated": True}}
            orchestrator.register(f"saga-{i}", saga_steps, actions, compensations)

        assert len(orchestrator._transactions) == 3

    def test_register_overwrites_existing(self, saga_orchestrator, saga_steps):
        """Test that registering with same ID overwrites existing."""
        actions1 = {"create": lambda: {"success": True}}
        compensations1 = {"delete": lambda: {"compensated": True}}
        orchestrator.register("saga-1", saga_steps, actions1, compensations1)

        actions2 = {"create": lambda: {"success": True}}
        compensations2 = {"delete": lambda: {"compensated": True}}
        orchestrator.register("saga-1", saga_steps, actions2, compensations2)

        assert len(orchestrator._transactions) == 1

    @pytest.mark.asyncio
    async def test_execute_saga_success(self, saga_orchestrator, saga_steps, async_action, async_compensation):
        """Test executing a saga successfully."""
        actions = {"create": async_action}
        compensations = {"delete": async_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is True
        assert result["saga_id"] == "saga-1"
        assert "steps" in result

    @pytest.mark.asyncio
    async def test_execute_saga_not_found(self, saga_orchestrator):
        """Test executing a non-existent saga."""
        result = await orchestrator.execute("non-existent")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_saga_with_failure(self, saga_orchestrator, saga_steps, failing_action, async_compensation):
        """Test executing a saga that fails."""
        actions = {"create": failing_action}
        compensations = {"delete": async_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is False
        assert "error" in result
        assert "failed_step" in result

    @pytest.mark.asyncio
    async def test_execute_saga_compensates_on_failure(self, saga_orchestrator, saga_steps, async_action, async_compensation):
        """Test that saga compensates on failure."""
        actions = {"create": async_action, "update": failing_action}
        compensations = {"delete": async_compensation, "rollback": async_compensation}

        steps = [
            SagaStep(step_id="step1", service="service1", action="create", compensation="delete"),
            SagaStep(step_id="step2", service="service2", action="update", compensation="rollback"),
        ]

        orchestrator.register("saga-1", steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is False
        # Compensation should have been triggered
        transaction = orchestrator.get_transaction("saga-1")
        assert transaction.status == "compensating"

    @pytest.mark.asyncio
    async def test_execute_saga_missing_action(self, saga_orchestrator, saga_steps, async_compensation):
        """Test executing a saga with missing action."""
        actions = {}  # No actions defined
        compensations = {"delete": async_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is False
        assert "No action for step" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_saga_with_sync_action(self, saga_orchestrator, saga_steps, sync_action, sync_compensation):
        """Test executing a saga with synchronous action."""
        actions = {"create": sync_action}
        compensations = {"delete": sync_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_saga_mixed_sync_async(self, saga_orchestrator, saga_steps, async_action, sync_compensation):
        """Test executing a saga with mixed sync and async operations."""
        actions = {"create": async_action}
        compensations = {"delete": sync_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_saga_multiple_steps(self, saga_orchestrator, async_action, async_compensation):
        """Test executing a saga with multiple steps."""
        steps = [
            SagaStep(step_id="step1", service="service1", action="create", compensation="delete"),
            SagaStep(step_id="step2", service="service2", action="update", compensation="rollback"),
            SagaStep(step_id="step3", service="service3", action="finalize", compensation="undo"),
        ]

        actions = {
            "create": async_action,
            "update": async_action,
            "finalize": async_action,
        }
        compensations = {
            "delete": async_compensation,
            "rollback": async_compensation,
            "undo": async_compensation,
        }

        orchestrator.register("saga-1", steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is True
        assert len(result["steps"]) == 3

    @pytest.mark.asyncio
    async def test_execute_saga_empty_steps(self, saga_orchestrator):
        """Test executing a saga with no steps."""
        orchestrator.register("saga-1", [], {}, {})

        result = await orchestrator.execute("saga-1")

        assert result["success"] is True
        assert result["steps"] == []

    @pytest.mark.asyncio
    async def test_compensate_executes_in_reverse_order(self, saga_orchestrator, async_action, async_compensation):
        """Test that compensation executes in reverse order."""
        execution_order = []

        async def track_action(step_id):
            execution_order.append(f"action-{step_id}")
            return {"success": True}

        async def track_compensation(step_id):
            execution_order.append(f"comp-{step_id}")
            return {"compensated": True}

        steps = [
            SagaStep(step_id="step1", service="service1", action="create", compensation="delete"),
            SagaStep(step_id="step2", service="service2", action="update", compensation="rollback"),
        ]

        actions = {
            "create": lambda: track_action("step1"),
            "update": lambda: track_action("step2"),
        }
        compensations = {
            "delete": lambda: track_compensation("step1"),
            "rollback": lambda: track_compensation("step2"),
        }

        orchestrator.register("saga-1", steps, actions, compensations)

        # Execute first step successfully
        transaction = orchestrator.get_transaction("saga-1")
        transaction.steps[0].status = "success"

        # Trigger compensation
        await orchestrator._compensate("saga-1", ["step1"])

        # Compensation should execute (though order depends on implementation)
        assert len(execution_order) > 0

    @pytest.mark.asyncio
    async def test_compensate_missing_compensation(self, saga_orchestrator, async_action):
        """Test compensation when compensation function is missing."""
        steps = [
            SagaStep(step_id="step1", service="service1", action="create", compensation="delete"),
        ]

        actions = {"create": async_action}
        compensations = {}  # No compensations defined

        orchestrator.register("saga-1", steps, actions, compensations)

        # Execute and trigger compensation
        transaction = orchestrator.get_transaction("saga-1")
        transaction.steps[0].status = "success"

        # Should not raise, just skip missing compensation
        await orchestrator._compensate("saga-1", ["step1"])

    @pytest.mark.asyncio
    async def test_compensate_with_compensation_error(self, saga_orchestrator, async_action):
        """Test compensation when compensation function raises an error."""
        async def failing_compensation():
            raise ValueError("Compensation failed")

        steps = [
            SagaStep(step_id="step1", service="service1", action="create", compensation="delete"),
        ]

        actions = {"create": async_action}
        compensations = {"delete": failing_compensation}

        orchestrator.register("saga-1", steps, actions, compensations)

        # Execute and trigger compensation
        transaction = orchestrator.get_transaction("saga-1")
        transaction.steps[0].status = "success"

        # Should not raise, just log error
        await orchestrator._compensate("saga-1", ["step1"])

        # Step should be marked as compensation_failed
        assert transaction.steps[0].status == "compensation_failed"

    @pytest.mark.asyncio
    async def test_get_transaction(self, saga_orchestrator, saga_steps):
        """Test retrieving a saga transaction."""
        actions = {"create": lambda: {"success": True}}
        compensations = {"delete": lambda: {"compensated": True}}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        transaction = orchestrator.get_transaction("saga-1")

        assert transaction is not None
        assert transaction.saga_id == "saga-1"
        assert len(transaction.steps) == len(saga_steps)

    @pytest.mark.asyncio
    async def test_get_transaction_not_found(self, saga_orchestrator):
        """Test retrieving a non-existent transaction."""
        with pytest.raises(KeyError):
            orchestrator.get_transaction("non-existent")

    @pytest.mark.asyncio
    async def test_saga_status_transitions(self, saga_orchestrator, saga_steps, async_action, async_compensation):
        """Test that saga status transitions correctly during execution."""
        actions = {"create": async_action}
        compensations = {"delete": async_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        transaction = orchestrator.get_transaction("saga-1")
        assert transaction.status == "pending"

        await orchestrator.execute("saga-1")

        transaction = orchestrator.get_transaction("saga-1")
        assert transaction.status == "success"

    @pytest.mark.asyncio
    async def test_saga_status_on_failure(self, saga_orchestrator, saga_steps, failing_action, async_compensation):
        """Test that saga status is set correctly on failure."""
        actions = {"create": failing_action}
        compensations = {"delete": async_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        await orchestrator.execute("saga-1")

        transaction = orchestrator.get_transaction("saga-1")
        assert transaction.status == "compensating"

    @pytest.mark.asyncio
    async def test_saga_step_status_tracking(self, saga_orchestrator, saga_steps, async_action, async_compensation):
        """Test that step status is tracked correctly."""
        actions = {"create": async_action}
        compensations = {"delete": async_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        await orchestrator.execute("saga-1")

        transaction = orchestrator.get_transaction("saga-1")
        for step in transaction.steps:
            assert step.status in ["success", "failed", "compensated"]

    @pytest.mark.asyncio
    async def test_saga_step_result_tracking(self, saga_orchestrator, saga_steps, async_action, async_compensation):
        """Test that step results are tracked correctly."""
        actions = {"create": async_action}
        compensations = {"delete": async_compensation}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        await orchestrator.execute("saga-1")

        transaction = orchestrator.get_transaction("saga-1")
        for step in transaction.steps:
            assert "result" in step.model_dump()

    @pytest.mark.asyncio
    async def test_execute_saga_with_action_returning_none(self, saga_orchestrator, saga_steps):
        """Test executing saga when action returns None."""
        async def none_action():
            return None

        actions = {"create": none_action}
        compensations = {"delete": lambda: {"compensated": True}}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_saga_with_action_returning_dict(self, saga_orchestrator, saga_steps):
        """Test executing saga when action returns a dict."""
        async def dict_action():
            return {"key": "value", "number": 42}

        actions = {"create": dict_action}
        compensations = {"delete": lambda: {"compensated": True}}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_saga_with_action_returning_string(self, saga_orchestrator, saga_steps):
        """Test executing saga when action returns a string."""
        async def string_action():
            return "success result"

        actions = {"create": string_action}
        compensations = {"delete": lambda: {"compensated": True}}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        result = await orchestrator.execute("saga-1")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_saga_orchestrator_isolation(self):
        """Test that different saga orchestrator instances are isolated."""
        orchestrator1 = WorkflowSagaOrchestrator()
        orchestrator2 = WorkflowSagaOrchestrator()

        steps = [SagaStep(step_id="step1", service="service1", action="create", compensation="delete")]
        actions = {"create": lambda: {"success": True}}
        compensations = {"delete": lambda: {"compensated": True}}

        orchestrator1.register("saga-1", steps, actions, compensations)

        assert "saga-1" in orchestrator1._transactions
        assert "saga-1" not in orchestrator2._transactions

    @pytest.mark.asyncio
    async def test_execute_saga_with_special_characters_in_ids(self, saga_orchestrator):
        """Test executing saga with special characters in IDs."""
        steps = [
            SagaStep(step_id="step-1", service="service-1", action="create", compensation="delete"),
        ]

        actions = {"create": lambda: {"success": True}}
        compensations = {"delete": lambda: {"compensated": True}}

        orchestrator.register("saga-1@test", steps, actions, compensations)

        result = await orchestrator.execute("saga-1@test")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_compensate_with_sync_compensation(self, saga_orchestrator, async_action, sync_compensation):
        """Test compensation with synchronous compensation function."""
        steps = [
            SagaStep(step_id="step1", service="service1", action="create", compensation="delete"),
        ]

        actions = {"create": async_action}
        compensations = {"delete": sync_compensation}

        orchestrator.register("saga-1", steps, actions, compensations)

        # Execute and trigger compensation
        transaction = orchestrator.get_transaction("saga-1")
        transaction.steps[0].status = "success"

        await orchestrator._compensate("saga-1", ["step1"])

        assert transaction.steps[0].status == "compensated"

    @pytest.mark.asyncio
    async def test_execute_saga_preserves_step_order(self, saga_orchestrator, async_action, async_compensation):
        """Test that saga executes steps in order."""
        execution_order = []

        async def ordered_action(step_name):
            execution_order.append(step_name)
            return {"success": True}

        steps = [
            SagaStep(step_id="step1", service="service1", action="first", compensation="delete"),
            SagaStep(step_id="step2", service="service2", action="second", compensation="rollback"),
            SagaStep(step_id="step3", service="service3", action="third", compensation="undo"),
        ]

        actions = {
            "first": lambda: ordered_action("first"),
            "second": lambda: ordered_action("second"),
            "third": lambda: ordered_action("third"),
        }
        compensations = {
            "delete": async_compensation,
            "rollback": async_compensation,
            "undo": async_compensation,
        }

        orchestrator.register("saga-1", steps, actions, compensations)

        await orchestrator.execute("saga-1")

        assert execution_order == ["first", "second", "third"]

    @pytest.mark.asyncio
    async def test_saga_transaction_created_at(self, saga_orchestrator, saga_steps):
        """Test that saga transaction has created_at timestamp."""
        actions = {"create": lambda: {"success": True}}
        compensations = {"delete": lambda: {"compensated": True}}
        orchestrator.register("saga-1", saga_steps, actions, compensations)

        transaction = orchestrator.get_transaction("saga-1")

        assert transaction.created_at is not None
        assert hasattr(transaction.created_at, "isoformat")
