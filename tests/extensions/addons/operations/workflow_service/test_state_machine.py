# -*- coding: utf-8 -*-
"""Tests for workflow_service state_machine module."""

import pytest
from schemas import (
    WorkflowStatus,
    WorkflowTask,
)
from state_machine import (
    StateTransition,
    WorkflowStateMachine,
)


class TestStateTransition:
    """Test cases for StateTransition class."""

    def test_state_transition_creation(self):
        """Test creating a StateTransition."""
        transition = StateTransition(event="start", source="pending", target="running")
        assert transition.event == "start"
        assert transition.source == "pending"
        assert transition.target == "running"

    def test_state_transition_attributes(self):
        """Test StateTransition attributes are set correctly."""
        transition = StateTransition(event="fail", source="running", target="failed")
        assert hasattr(transition, "event")
        assert hasattr(transition, "source")
        assert hasattr(transition, "target")

    def test_state_transition_different_events(self):
        """Test StateTransition with different events."""
        events = ["start", "pause", "resume", "succeed", "fail", "timeout"]
        for event in events:
            transition = StateTransition(event=event, source="pending", target="running")
            assert transition.event == event


class TestWorkflowStateMachine:
    """Test cases for WorkflowStateMachine class."""

    def test_state_machine_initialization(self, workflow_task):
        """Test state machine initialization."""
        machine = WorkflowStateMachine(workflow_task)
        assert machine.task == workflow_task
        assert len(machine.history) == 1
        assert machine.history[0]["state"] == workflow_task.status.value
        assert machine.history[0]["event"] == "init"

    def test_state_machine_history_initial_entry(self, workflow_task):
        """Test that initial history entry is correct."""
        machine = WorkflowStateMachine(workflow_task)
        initial_entry = machine.history[0]
        assert initial_entry["state"] == workflow_task.status.value
        assert initial_entry["event"] == "init"
        assert "reason" in initial_entry

    def test_state_machine_transitions_list(self):
        """Test that TRANSITIONS list is defined."""
        assert hasattr(WorkflowStateMachine, "TRANSITIONS")
        assert len(WorkflowStateMachine.TRANSITIONS) > 0

    def test_state_machine_transitions_structure(self):
        """Test that transitions have correct structure."""
        for transition in WorkflowStateMachine.TRANSITIONS:
            assert isinstance(transition, StateTransition)
            assert hasattr(transition, "event")
            assert hasattr(transition, "source")
            assert hasattr(transition, "target")

    def test_transition_pending_to_running(self, workflow_task):
        """Test transition from PENDING to RUNNING."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.RUNNING, "Starting workflow")
        assert result is True
        assert machine.task.status == WorkflowStatus.RUNNING
        assert len(machine.history) == 2

    def test_transition_scheduled_to_running(self, workflow_task):
        """Test transition from SCHEDULED to RUNNING."""
        workflow_task.status = WorkflowStatus.SCHEDULED
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.RUNNING, "Starting scheduled workflow")
        assert result is True
        assert machine.task.status == WorkflowStatus.RUNNING

    def test_transition_running_to_paused(self, workflow_task):
        """Test transition from RUNNING to PAUSED."""
        workflow_task.status = WorkflowStatus.RUNNING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.PAUSED, "Pausing workflow")
        assert result is True
        assert machine.task.status == WorkflowStatus.PAUSED

    def test_transition_paused_to_running(self, workflow_task):
        """Test transition from PAUSED to RUNNING."""
        workflow_task.status = WorkflowStatus.PAUSED
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.RUNNING, "Resuming workflow")
        assert result is True
        assert machine.task.status == WorkflowStatus.RUNNING

    def test_transition_running_to_succeeded(self, workflow_task):
        """Test transition from RUNNING to SUCCEEDED."""
        workflow_task.status = WorkflowStatus.RUNNING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.SUCCEEDED, "Workflow completed")
        assert result is True
        assert machine.task.status == WorkflowStatus.SUCCEEDED

    def test_transition_failed_to_retrying(self, workflow_task):
        """Test transition from FAILED to RETRYING."""
        workflow_task.status = WorkflowStatus.FAILED
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.RETRYING, "Retrying workflow")
        assert result is True
        assert machine.task.status == WorkflowStatus.RETRYING

    def test_transition_running_to_failed(self, workflow_task):
        """Test transition from RUNNING to FAILED."""
        workflow_task.status = WorkflowStatus.RUNNING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.FAILED, "Workflow failed")
        assert result is True
        assert machine.task.status == WorkflowStatus.FAILED

    def test_transition_running_to_timeout(self, workflow_task):
        """Test transition from RUNNING to TIMEOUT."""
        workflow_task.status = WorkflowStatus.RUNNING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.TIMEOUT, "Workflow timed out")
        assert result is True
        assert machine.task.status == WorkflowStatus.TIMEOUT

    def test_transition_succeeded_to_completed(self, workflow_task):
        """Test transition from SUCCEEDED to COMPLETED."""
        workflow_task.status = WorkflowStatus.SUCCEEDED
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.COMPLETED, "Workflow finalized")
        assert result is True
        assert machine.task.status == WorkflowStatus.COMPLETED

    def test_transition_failed_to_completed(self, workflow_task):
        """Test transition from FAILED to COMPLETED."""
        workflow_task.status = WorkflowStatus.FAILED
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.COMPLETED, "Workflow finalized after failure")
        assert result is True
        assert machine.task.status == WorkflowStatus.COMPLETED

    def test_transition_invalid(self, workflow_task):
        """Test that invalid transition returns False."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        # Invalid transition: PENDING to COMPLETED (not in TRANSITIONS)
        result = machine.transition(WorkflowStatus.COMPLETED, "Invalid transition")
        assert result is False
        assert machine.task.status == WorkflowStatus.PENDING  # Status unchanged

    def test_transition_same_state(self, workflow_task):
        """Test that transition to same state returns True."""
        workflow_task.status = WorkflowStatus.RUNNING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.RUNNING, "Staying in running")
        assert result is True
        assert machine.task.status == WorkflowStatus.RUNNING

    def test_transition_history_tracking(self, workflow_task):
        """Test that transition history is tracked correctly."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        machine.transition(WorkflowStatus.RUNNING, "Start")
        machine.transition(WorkflowStatus.PAUSED, "Pause")
        machine.transition(WorkflowStatus.RUNNING, "Resume")

        assert len(machine.history) == 4  # Initial + 3 transitions
        assert machine.history[1]["state"] == "running"
        assert machine.history[2]["state"] == "paused"
        assert machine.history[3]["state"] == "running"

    def test_transition_history_with_reason(self, workflow_task):
        """Test that transition reason is recorded in history."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        reason = "Starting execution"
        machine.transition(WorkflowStatus.RUNNING, reason)

        assert machine.history[1]["reason"] == reason

    def test_transition_history_event_field(self, workflow_task):
        """Test that event field is recorded in history."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        machine.transition(WorkflowStatus.RUNNING, "Start")

        assert machine.history[1]["event"] == "running"

    def test_get_state(self, workflow_task):
        """Test get_state method."""
        workflow_task.status = WorkflowStatus.RUNNING
        machine = WorkflowStateMachine(workflow_task)

        state = machine.get_state()
        assert state["task_id"] == workflow_task.task_id
        assert state["status"] == "running"
        assert "history" in state
        assert isinstance(state["history"], list)

    def test_get_state_includes_history(self, workflow_task):
        """Test that get_state includes complete history."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        machine.transition(WorkflowStatus.RUNNING, "Start")
        machine.transition(WorkflowStatus.SUCCEEDED, "Complete")

        state = machine.get_state()
        assert len(state["history"]) == 3

    def test_multiple_transitions_sequence(self, workflow_task):
        """Test a complete sequence of valid transitions."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        # Complete lifecycle
        assert machine.transition(WorkflowStatus.RUNNING, "Start")
        assert machine.transition(WorkflowStatus.PAUSED, "Pause")
        assert machine.transition(WorkflowStatus.RUNNING, "Resume")
        assert machine.transition(WorkflowStatus.SUCCEEDED, "Complete")
        assert machine.transition(WorkflowStatus.COMPLETED, "Finalize")

        assert machine.task.status == WorkflowStatus.COMPLETED
        assert len(machine.history) == 6

    def test_transition_from_all_statuses(self, workflow_task):
        """Test transitions from all possible starting statuses."""
        statuses = [
            WorkflowStatus.PENDING,
            WorkflowStatus.APPROVED,
            WorkflowStatus.SCHEDULED,
            WorkflowStatus.RUNNING,
            WorkflowStatus.PAUSED,
            WorkflowStatus.SUCCEEDED,
            WorkflowStatus.FAILED,
            WorkflowStatus.RETRYING,
            WorkflowStatus.TIMEOUT,
            WorkflowStatus.COMPLETED,
        ]

        for status in statuses:
            workflow_task.status = status
            machine = WorkflowStateMachine(workflow_task)
            # At minimum, same-state transition should work
            result = machine.transition(status, "Test")
            assert result is True

    def test_transition_with_empty_reason(self, workflow_task):
        """Test transition with empty reason string."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.RUNNING, "")
        assert result is True
        assert machine.history[1]["reason"] == ""

    def test_transition_with_long_reason(self, workflow_task):
        """Test transition with very long reason string."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        long_reason = "a" * 1000
        result = machine.transition(WorkflowStatus.RUNNING, long_reason)
        assert result is True
        assert machine.history[1]["reason"] == long_reason

    def test_transition_preserves_task_other_fields(self, workflow_task):
        """Test that transition doesn't modify other task fields."""
        workflow_task.status = WorkflowStatus.PENDING
        workflow_task.params = {"key": "value"}
        workflow_task.retry_count = 5
        machine = WorkflowStateMachine(workflow_task)

        machine.transition(WorkflowStatus.RUNNING, "Start")

        assert machine.task.params == {"key": "value"}
        assert machine.task.retry_count == 5
        assert machine.task.status == WorkflowStatus.RUNNING

    def test_state_machine_with_different_initial_statuses(self):
        """Test state machine initialization with different initial statuses."""
        for status in WorkflowStatus:
            task = WorkflowTask(task_id="test", workflow_id="test", status=status)
            machine = WorkflowStateMachine(task)
            assert machine.task.status == status
            assert machine.history[0]["state"] == status.value

    def test_transition_running_to_approved_invalid(self, workflow_task):
        """Test that RUNNING to APPROVED is invalid."""
        workflow_task.status = WorkflowStatus.RUNNING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.APPROVED, "Invalid")
        assert result is False
        assert machine.task.status == WorkflowStatus.RUNNING

    def test_transition_completed_to_running_invalid(self, workflow_task):
        """Test that COMPLETED to RUNNING is invalid."""
        workflow_task.status = WorkflowStatus.COMPLETED
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.RUNNING, "Invalid")
        assert result is False
        assert machine.task.status == WorkflowStatus.COMPLETED

    def test_transition_count_in_history(self, workflow_task):
        """Test that history count matches transition count."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        transition_count = 5
        for i in range(transition_count):
            machine.transition(WorkflowStatus.RUNNING, f"Transition {i}")

        assert len(machine.history) == transition_count + 1  # +1 for initial

    def test_get_state_returns_dict(self, workflow_task):
        """Test that get_state returns a dictionary."""
        machine = WorkflowStateMachine(workflow_task)
        state = machine.get_state()
        assert isinstance(state, dict)

    def test_get_state_dict_structure(self, workflow_task):
        """Test that get_state dict has correct structure."""
        machine = WorkflowStateMachine(workflow_task)
        state = machine.get_state()

        required_keys = ["task_id", "status", "history"]
        for key in required_keys:
            assert key in state

    def test_transition_does_not_modify_original_task_reference(self, workflow_task):
        """Test that transitions modify the task object, not create a new one."""
        original_id = id(workflow_task)
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        machine.transition(WorkflowStatus.RUNNING, "Start")

        assert id(machine.task) == original_id

    def test_state_machine_with_complex_workflow(self):
        """Test state machine with a complex workflow scenario."""
        task = WorkflowTask(
            task_id="complex-task",
            workflow_id="complex-workflow",
            status=WorkflowStatus.PENDING,
        )
        machine = WorkflowStateMachine(task)

        # Simulate a complex workflow with retries
        assert machine.transition(WorkflowStatus.RUNNING, "Start")
        assert machine.transition(WorkflowStatus.FAILED, "First attempt failed")
        assert machine.transition(WorkflowStatus.RETRYING, "Retrying")
        assert machine.transition(WorkflowStatus.RUNNING, "Retry attempt")
        assert machine.transition(WorkflowStatus.SUCCEEDED, "Success on retry")
        assert machine.transition(WorkflowStatus.COMPLETED, "Finalize")

        assert len(machine.history) == 7
        assert machine.task.status == WorkflowStatus.COMPLETED

    def test_transition_timeout_to_completed(self, workflow_task):
        """Test transition from TIMEOUT to COMPLETED."""
        workflow_task.status = WorkflowStatus.TIMEOUT
        machine = WorkflowStateMachine(workflow_task)

        # This is not in the default TRANSITIONS list, so should fail
        result = machine.transition(WorkflowStatus.COMPLETED, "Finalize timeout")
        assert result is False
        assert machine.task.status == WorkflowStatus.TIMEOUT

    def test_transition_retrying_to_running_invalid(self, workflow_task):
        """Test that RETRYING to RUNNING is not in default transitions."""
        workflow_task.status = WorkflowStatus.RETRYING
        machine = WorkflowStateMachine(workflow_task)

        result = machine.transition(WorkflowStatus.RUNNING, "Resume retry")
        assert result is False
        assert machine.task.status == WorkflowStatus.RETRYING

    def test_state_machine_history_order(self, workflow_task):
        """Test that history maintains chronological order."""
        workflow_task.status = WorkflowStatus.PENDING
        machine = WorkflowStateMachine(workflow_task)

        transitions = [
            (WorkflowStatus.RUNNING, "Step 1"),
            (WorkflowStatus.PAUSED, "Step 2"),
            (WorkflowStatus.RUNNING, "Step 3"),
        ]

        for status, reason in transitions:
            machine.transition(status, reason)

        for i, (expected_status, expected_reason) in enumerate(transitions, 1):
            assert machine.history[i]["state"] == expected_status.value
            assert machine.history[i]["reason"] == expected_reason
