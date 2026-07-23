# -*- coding: utf-8 -*-
"""测试工作流执行器模块"""

import asyncio

import pytest


class TestWorkflowExecutorModule:
    """测试工作流执行器模块"""

    def test_executor_module_exists(self):
        """测试执行器模块存在"""
        from core.workflow.engine import executor

        assert executor is not None

    def test_executor_has_dataclasses(self):
        """测试执行器模块有数据类"""
        from core.workflow.engine import executor

        # 检查模块有数据类
        assert hasattr(executor, "ExecutionContext")

    def test_executor_has_classes(self):
        """测试执行器模块有类"""
        from core.workflow.engine import executor

        # 检查模块有类
        assert hasattr(executor, "WorkflowExecutor")


class TestExecutionContext:
    """测试执行上下文数据类"""

    def test_execution_context_creation(self):
        """测试执行上下文创建"""
        from core.workflow.engine.executor import ExecutionContext
        from core.workflow.engine.state_machine import WorkflowState

        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="run_1",
            status=WorkflowState.RUNNING,
        )

        assert context.workflow_id == "test_workflow"
        assert context.run_id == "run_1"
        assert context.status == WorkflowState.RUNNING

    def test_execution_context_to_dict(self):
        """测试执行上下文转字典"""
        from core.workflow.engine.executor import ExecutionContext
        from core.workflow.engine.state_machine import WorkflowState

        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="run_1",
            status=WorkflowState.RUNNING,
        )

        context_dict = context.to_dict()

        assert context_dict["workflow_id"] == "test_workflow"
        assert context_dict["run_id"] == "run_1"
        assert context_dict["status"] == "running"


class TestWorkflowExecutor:
    """测试工作流执行器类"""

    def test_executor_initialization(self):
        """测试执行器初始化"""
        from core.workflow.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor()

        assert executor.max_parallel_nodes == 5
        assert executor.default_timeout == 300
        assert executor.default_max_retries == 3
        assert executor._handlers == {}
        assert executor._active_executions == {}

    def test_executor_initialization_with_params(self):
        """测试执行器初始化（带参数）"""
        from core.workflow.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor(
            max_parallel_nodes=10,
            default_timeout=600,
            default_max_retries=5,
        )

        assert executor.max_parallel_nodes == 10
        assert executor.default_timeout == 600
        assert executor.default_max_retries == 5

    def test_register_handler(self):
        """测试注册处理器"""
        from core.workflow.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor()

        async def dummy_handler(node, context):
            return "result"

        executor.register_handler("task", dummy_handler)

        assert "task" in executor._handlers
        assert executor._handlers["task"] == dummy_handler

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self):
        """测试执行简单工作流"""
        from core.workflow.engine.dag import DAG, DAGNode, NodeStatus
        from core.workflow.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor()

        async def dummy_handler(node, context):
            return f"result_{node.id}"

        executor.register_handler("task", dummy_handler)

        dag = DAG("test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1", type="task")

        dag.add_node(node1)

        context = await executor.execute(dag)

        assert context.workflow_id == "test_workflow"
        assert node1.status == NodeStatus.SUCCESS
        assert "node_1" in context.results

    @pytest.mark.asyncio
    async def test_execute_with_handler_not_registered(self):
        """测试执行（处理器未注册）"""
        from core.workflow.engine.dag import DAG, DAGNode, NodeStatus
        from core.workflow.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor()

        dag = DAG("test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1", type="task")

        dag.add_node(node1)

        context = await executor.execute(dag)

        assert node1.status == NodeStatus.FAILED
        assert "node_1" in context.errors

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """测试执行（超时）"""
        from core.workflow.engine.dag import DAG, DAGNode, NodeStatus
        from core.workflow.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor(default_timeout=1)

        async def slow_handler(node, context):
            await asyncio.sleep(2)
            return "result"

        executor.register_handler("task", slow_handler)

        dag = DAG("test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1", type="task", config={"timeout": 0.5})

        dag.add_node(node1)

        context = await executor.execute(dag)

        assert node1.status == NodeStatus.FAILED
        assert "timed out" in context.errors["node_1"]

    @pytest.mark.asyncio
    async def test_execute_with_retry(self):
        """测试执行（重试）"""
        from core.workflow.engine.dag import DAG, DAGNode, NodeStatus
        from core.workflow.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor(default_max_retries=2, retry_backoff_base=0.1)

        attempt_count = 0

        async def flaky_handler(node, context):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary error")
            return "success"

        executor.register_handler("task", flaky_handler)

        dag = DAG("test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1", type="task")

        dag.add_node(node1)

        context = await executor.execute(dag)

        assert node1.status == NodeStatus.SUCCESS
        assert context.results["node_1"] == "success"

    @pytest.mark.asyncio
    async def test_pause_workflow(self):
        """测试暂停工作流"""
        from core.workflow.engine.executor import ExecutionContext, WorkflowExecutor
        from core.workflow.engine.state_machine import WorkflowState

        executor = WorkflowExecutor()

        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="run_1",
            status=WorkflowState.RUNNING,
        )

        executor._active_executions["run_1"] = context

        result = executor.pause_workflow("run_1")

        assert result is True
        assert context.status == WorkflowState.PAUSED

    @pytest.mark.asyncio
    async def test_pause_workflow_not_running(self):
        """测试暂停工作流（未运行）"""
        from core.workflow.engine.executor import ExecutionContext, WorkflowExecutor
        from core.workflow.engine.state_machine import WorkflowState

        executor = WorkflowExecutor()

        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="run_1",
            status=WorkflowState.IDLE,
        )

        executor._active_executions["run_1"] = context

        result = executor.pause_workflow("run_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_resume_workflow(self):
        """测试恢复工作流"""
        from core.workflow.engine.executor import ExecutionContext, WorkflowExecutor
        from core.workflow.engine.state_machine import WorkflowState

        executor = WorkflowExecutor()

        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="run_1",
            status=WorkflowState.PAUSED,
        )

        executor._active_executions["run_1"] = context

        result = executor.resume_workflow("run_1")

        assert result is True
        assert context.status == WorkflowState.RUNNING

    @pytest.mark.asyncio
    async def test_cancel_workflow(self):
        """测试取消工作流"""
        from core.workflow.engine.executor import ExecutionContext, WorkflowExecutor
        from core.workflow.engine.state_machine import WorkflowState

        executor = WorkflowExecutor()

        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="run_1",
            status=WorkflowState.RUNNING,
        )

        executor._active_executions["run_1"] = context

        result = executor.cancel_workflow("run_1")

        assert result is True
        assert context.status == WorkflowState.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_workflow_completed(self):
        """测试取消工作流（已完成）"""
        from core.workflow.engine.executor import ExecutionContext, WorkflowExecutor
        from core.workflow.engine.state_machine import WorkflowState

        executor = WorkflowExecutor()

        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="run_1",
            status=WorkflowState.COMPLETED,
        )

        executor._active_executions["run_1"] = context

        result = executor.cancel_workflow("run_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_execution_status(self):
        """测试获取执行状态"""
        from core.workflow.engine.executor import ExecutionContext, WorkflowExecutor

        executor = WorkflowExecutor()

        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="run_1",
        )

        executor._active_executions["run_1"] = context

        status = executor.get_execution_status("run_1")

        assert status is not None
        assert status["workflow_id"] == "test_workflow"
        assert status["run_id"] == "run_1"

    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self):
        """测试获取执行状态（未找到）"""
        from core.workflow.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor()

        status = executor.get_execution_status("invalid_run_id")

        assert status is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
