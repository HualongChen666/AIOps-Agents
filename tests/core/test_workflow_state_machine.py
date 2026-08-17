# -*- coding: utf-8 -*-
"""Tests for core/workflow/engine/state_machine.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.workflow.engine.state_machine import (
    WorkflowEvent,
    WorkflowState,
    WorkflowStateMachine,
)


def test_initial_state_and_transitions():
    sm = WorkflowStateMachine("wf1")
    assert sm.current_state == WorkflowState.IDLE
    assert sm.can_transition(WorkflowEvent.START) is True
    assert sm.can_transition(WorkflowEvent.COMPLETE) is False
    sm.transition(WorkflowEvent.START)
    assert sm.current_state == WorkflowState.RUNNING
    sm.transition(WorkflowEvent.COMPLETE)
    assert sm.current_state == WorkflowState.COMPLETED
    assert sm.is_terminal() is True
    assert sm.is_running() is False


def test_invalid_transition():
    sm = WorkflowStateMachine("wf2")
    with pytest.raises(ValueError):
        sm.transition(WorkflowEvent.COMPLETE)


def test_transition_history_and_reset():
    sm = WorkflowStateMachine("wf3")
    sm.transition(WorkflowEvent.START)
    sm.transition(WorkflowEvent.FAIL)
    history = sm.get_history()
    assert len(history) == 2
    assert history[0]["from_state"] == "idle"
    sm.reset()
    assert sm.current_state == WorkflowState.IDLE
    assert len(sm.get_history()) == 0


def test_transition_action():
    sm = WorkflowStateMachine("wf4")
    called = {"value": False}

    def action(context):
        called["value"] = True

    sm.register_transition_action(WorkflowState.IDLE, WorkflowEvent.START, action)
    sm.transition(WorkflowEvent.START)
    assert called["value"] is True
