# -*- coding: utf-8 -*-
"""测试工作流状态机模块"""

import pytest


class TestWorkflowStateMachineModule:
    """测试工作流状态机模块"""

    def test_state_machine_module_exists(self):
        """测试状态机模块存在"""
        from core.workflow.engine import state_machine

        assert state_machine is not None

    def test_state_machine_has_enums(self):
        """测试状态机模块有枚举"""
        from core.workflow.engine import state_machine

        # 检查模块有枚举
        assert hasattr(state_machine, "WorkflowState")
        assert hasattr(state_machine, "WorkflowEvent")

    def test_state_machine_has_dataclasses(self):
        """测试状态机模块有数据类"""
        from core.workflow.engine import state_machine

        # 检查模块有数据类
        assert hasattr(state_machine, "StateTransition")

    def test_state_machine_has_classes(self):
        """测试状态机模块有类"""
        from core.workflow.engine import state_machine

        # 检查模块有类
        assert hasattr(state_machine, "WorkflowStateMachine")


class TestWorkflowState:
    """测试工作流状态枚举"""

    def test_workflow_state_values(self):
        """测试工作流状态值"""
        from core.workflow.engine.state_machine import WorkflowState

        assert WorkflowState.IDLE.value == "idle"
        assert WorkflowState.RUNNING.value == "running"
        assert WorkflowState.PAUSED.value == "paused"
        assert WorkflowState.COMPLETED.value == "completed"
        assert WorkflowState.FAILED.value == "failed"
        assert WorkflowState.CANCELLED.value == "cancelled"


class TestWorkflowEvent:
    """测试工作流事件枚举"""

    def test_workflow_event_values(self):
        """测试工作流事件值"""
        from core.workflow.engine.state_machine import WorkflowEvent

        assert WorkflowEvent.START.value == "start"
        assert WorkflowEvent.PAUSE.value == "pause"
        assert WorkflowEvent.RESUME.value == "resume"
        assert WorkflowEvent.COMPLETE.value == "complete"
        assert WorkflowEvent.FAIL.value == "fail"
        assert WorkflowEvent.CANCEL.value == "cancel"
        assert WorkflowEvent.RETRY.value == "retry"


class TestStateTransition:
    """测试状态转换数据类"""

    def test_state_transition_creation(self):
        """测试状态转换创建"""
        from core.workflow.engine.state_machine import (
            StateTransition,
            WorkflowEvent,
            WorkflowState,
        )

        transition = StateTransition(
            from_state=WorkflowState.IDLE,
            to_state=WorkflowState.RUNNING,
            event=WorkflowEvent.START,
        )

        assert transition.from_state == WorkflowState.IDLE
        assert transition.to_state == WorkflowState.RUNNING
        assert transition.event == WorkflowEvent.START


class TestWorkflowStateMachine:
    """测试工作流状态机类"""

    def test_state_machine_initialization(self):
        """测试状态机初始化"""
        from core.workflow.engine.state_machine import (
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        assert state_machine.workflow_id == "test_workflow"
        assert state_machine.current_state == WorkflowState.IDLE
        assert state_machine._history == []

    def test_can_transition_valid(self):
        """测试可以转换（有效）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        can_start = state_machine.can_transition(WorkflowEvent.START)

        assert can_start is True

    def test_can_transition_invalid(self):
        """测试可以转换（无效）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        can_complete = state_machine.can_transition(WorkflowEvent.COMPLETE)

        assert can_complete is False

    def test_transition_start(self):
        """测试转换（开始）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)

        assert state_machine.current_state == WorkflowState.RUNNING

    def test_transition_pause(self):
        """测试转换（暂停）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)
        state_machine.transition(WorkflowEvent.PAUSE)

        assert state_machine.current_state == WorkflowState.PAUSED

    def test_transition_resume(self):
        """测试转换（恢复）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)
        state_machine.transition(WorkflowEvent.PAUSE)
        state_machine.transition(WorkflowEvent.RESUME)

        assert state_machine.current_state == WorkflowState.RUNNING

    def test_transition_complete(self):
        """测试转换（完成）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)
        state_machine.transition(WorkflowEvent.COMPLETE)

        assert state_machine.current_state == WorkflowState.COMPLETED

    def test_transition_fail(self):
        """测试转换（失败）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)
        state_machine.transition(WorkflowEvent.FAIL)

        assert state_machine.current_state == WorkflowState.FAILED

    def test_transition_cancel(self):
        """测试转换（取消）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)
        state_machine.transition(WorkflowEvent.CANCEL)

        assert state_machine.current_state == WorkflowState.CANCELLED

    def test_transition_invalid(self):
        """测试转换（无效）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        with pytest.raises(ValueError, match="Invalid transition"):
            state_machine.transition(WorkflowEvent.COMPLETE)

    def test_transition_retry(self):
        """测试转换（重试）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)
        state_machine.transition(WorkflowEvent.FAIL)
        state_machine.transition(WorkflowEvent.RETRY)

        assert state_machine.current_state == WorkflowState.RUNNING

    def test_register_transition_action(self):
        """测试注册转换动作"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        action_called = []

        def action(context):
            action_called.append(True)

        state_machine.register_transition_action(WorkflowState.IDLE, WorkflowEvent.START, action)

        state_machine.transition(WorkflowEvent.START)

        assert len(action_called) == 1

    def test_register_transition_action_with_error(self):
        """测试注册转换动作（有错误）"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        def action(context):
            raise ValueError("Test error")

        state_machine.register_transition_action(WorkflowState.IDLE, WorkflowEvent.START, action)

        # Should not raise, action error is caught
        state_machine.transition(WorkflowEvent.START)

        assert state_machine.current_state == WorkflowState.RUNNING

    def test_get_history(self):
        """测试获取历史"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)
        state_machine.transition(WorkflowEvent.COMPLETE)

        history = state_machine.get_history()

        assert len(history) == 2
        assert history[0]["from_state"] == "idle"
        assert history[0]["event"] == "start"
        assert history[0]["to_state"] == "running"

    def test_reset(self):
        """测试重置"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowState,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        state_machine.transition(WorkflowEvent.START)
        state_machine.transition(WorkflowEvent.COMPLETE)

        state_machine.reset()

        assert state_machine.current_state == WorkflowState.IDLE
        assert len(state_machine._history) == 0

    def test_is_terminal(self):
        """测试是否终端状态"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        assert state_machine.is_terminal() is False

        state_machine.transition(WorkflowEvent.START)
        assert state_machine.is_terminal() is False

        state_machine.transition(WorkflowEvent.COMPLETE)
        assert state_machine.is_terminal() is True

    def test_is_running(self):
        """测试是否运行中"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        assert state_machine.is_running() is False

        state_machine.transition(WorkflowEvent.START)
        assert state_machine.is_running() is True

        state_machine.transition(WorkflowEvent.PAUSE)
        assert state_machine.is_running() is False

    def test_is_paused(self):
        """测试是否暂停"""
        from core.workflow.engine.state_machine import (
            WorkflowEvent,
            WorkflowStateMachine,
        )

        state_machine = WorkflowStateMachine("test_workflow")

        assert state_machine.is_paused() is False

        state_machine.transition(WorkflowEvent.START)
        assert state_machine.is_paused() is False

        state_machine.transition(WorkflowEvent.PAUSE)
        assert state_machine.is_paused() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
