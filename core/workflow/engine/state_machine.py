# -*- coding: utf-8 -*-
"""
Workflow State Machine
Manages workflow execution states and transitions
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow execution states"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowEvent(Enum):
    """Workflow events"""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    COMPLETE = "complete"
    FAIL = "fail"
    CANCEL = "cancel"
    RETRY = "retry"


@dataclass
class StateTransition:
    """
    State transition definition

    Attributes:
        from_state: Source state
        to_state: Target state
        event: Event triggering transition
        action: Optional action to execute on transition
    """

    from_state: WorkflowState
    to_state: WorkflowState
    event: WorkflowEvent
    action: Optional[Callable] = None


class WorkflowStateMachine:
    """
    State machine for workflow execution

    Manages state transitions and ensures valid state changes
    """

    # Valid state transitions
    TRANSITIONS = {
        WorkflowState.IDLE: {
            WorkflowEvent.START: WorkflowState.RUNNING,
        },
        WorkflowState.RUNNING: {
            WorkflowEvent.PAUSE: WorkflowState.PAUSED,
            WorkflowEvent.COMPLETE: WorkflowState.COMPLETED,
            WorkflowEvent.FAIL: WorkflowState.FAILED,
            WorkflowEvent.CANCEL: WorkflowState.CANCELLED,
        },
        WorkflowState.PAUSED: {
            WorkflowEvent.RESUME: WorkflowState.RUNNING,
            WorkflowEvent.CANCEL: WorkflowState.CANCELLED,
        },
        WorkflowState.FAILED: {
            WorkflowEvent.RETRY: WorkflowState.RUNNING,
        },
        WorkflowState.COMPLETED: {},
        WorkflowState.CANCELLED: {},
    }

    def __init__(self, workflow_id: str):
        """
        Initialize state machine

        Args:
            workflow_id: Workflow identifier
        """
        self.workflow_id = workflow_id
        self._current_state = WorkflowState.IDLE
        self._history: List[tuple[WorkflowState, WorkflowEvent, WorkflowState]] = []
        self._transition_actions: Dict[WorkflowState, Dict[WorkflowEvent, Callable]] = {}

    @property
    def current_state(self) -> WorkflowState:
        """Get current state"""
        return self._current_state

    def can_transition(self, event: WorkflowEvent) -> bool:
        """
        Check if transition is valid

        Args:
            event: Event to check

        Returns:
            True if transition is valid
        """
        valid_transitions = self.TRANSITIONS.get(self._current_state, {})
        return event in valid_transitions

    def transition(self, event: WorkflowEvent, context: Optional[Dict] = None) -> bool:
        """
        Execute state transition

        Args:
            event: Event triggering transition
            context: Optional context data

        Returns:
            True if transition succeeded

        Raises:
            ValueError: If transition is invalid
        """
        if not self.can_transition(event):
            raise ValueError(f"Invalid transition: {self._current_state} --[{event}]--> ?")

        valid_transitions = self.TRANSITIONS[self._current_state]
        new_state = valid_transitions[event]

        # Record transition
        self._history.append((self._current_state, event, new_state))

        # Execute action if defined
        action = self._transition_actions.get(self._current_state, {}).get(event)
        if action:
            try:
                action(context or {})
            except Exception as e:
                logger.error(f"Transition action failed: {e}")

        # Update state
        old_state = self._current_state
        self._current_state = new_state

        logger.info(
            f"Workflow {self.workflow_id}: {old_state.value} -> {new_state.value} "
            f"(event: {event.value})"
        )

        return True

    def register_transition_action(
        self, state: WorkflowState, event: WorkflowEvent, action: Callable
    ) -> None:
        """
        Register action to execute on state transition

        Args:
            state: Source state
            event: Event
            action: Action function
        """
        if state not in self._transition_actions:
            self._transition_actions[state] = {}
        self._transition_actions[state][event] = action

    def get_history(self) -> List[Dict]:
        """
        Get transition history

        Returns:
            List of transition records
        """
        return [
            {"from_state": from_state.value, "event": event.value, "to_state": to_state.value}
            for from_state, event, to_state in self._history
        ]

    def reset(self) -> None:
        """Reset state machine to initial state"""
        self._current_state = WorkflowState.IDLE
        self._history.clear()
        logger.info(f"Workflow {self.workflow_id} state machine reset")

    def is_terminal(self) -> bool:
        """
        Check if current state is terminal

        Returns:
            True if in terminal state
        """
        return self._current_state in [
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        ]

    def is_running(self) -> bool:
        """
        Check if workflow is running

        Returns:
            True if running
        """
        return self._current_state == WorkflowState.RUNNING

    def is_paused(self) -> bool:
        """
        Check if workflow is paused

        Returns:
            True if paused
        """
        return self._current_state == WorkflowState.PAUSED
