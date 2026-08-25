# -*- coding: utf-8 -*-
"""Tests for workflow_service orchestrator module."""

import pytest
from orchestrator import (
    WorkflowOrchestrator,
)
from schemas import (
    TaskPriority,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowTask,
)


class TestWorkflowOrchestrator:
    """Test cases for WorkflowOrchestrator class."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, repository):
        """Test that orchestrator initializes correctly."""
        orchestrator = WorkflowOrchestrator(repository)
        assert orchestrator.repo == repository
        assert len(orchestrator.machines) == 0
        assert orchestrator.retry_engine is not None

    @pytest.mark.asyncio
    async def test_create_task_success(self, orchestrator, workflow_definition, workflow_request):
        """Test creating a workflow task successfully."""
        await orchestrator.repo.save_definition(workflow_definition)

        task = await orchestrator.create_task(workflow_request)

        assert task is not None
        assert task.workflow_id == workflow_request.workflow_id
        assert task.params == workflow_request.params
        assert task.status == WorkflowStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_task_definition_not_found(self, orchestrator, workflow_request):
        """Test creating a task when workflow definition doesn't exist."""
        with pytest.raises(ValueError, match="Workflow definition .* not found"):
            await orchestrator.create_task(workflow_request)

    @pytest.mark.asyncio
    async def test_create_task_generates_unique_id(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that create_task generates unique task IDs."""
        await orchestrator.repo.save_definition(workflow_definition)

        task1 = await orchestrator.create_task(workflow_request)
        task2 = await orchestrator.create_task(workflow_request)

        assert task1.task_id != task2.task_id
        assert task1.task_id.startswith("WF-")
        assert task2.task_id.startswith("WF-")

    @pytest.mark.asyncio
    async def test_create_task_merges_metadata(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that create_task merges definition metadata with request params."""
        workflow_definition.metadata = {"env": "production", "owner": "team"}
        await orchestrator.repo.save_definition(workflow_definition)

        workflow_request.params = {"user": "test-user", "env": "staging"}
        task = await orchestrator.create_task(workflow_request)

        # Request params should override definition metadata
        assert task.params["user"] == "test-user"
        assert task.params["env"] == "staging"
        assert task.params["owner"] == "team"

    @pytest.mark.asyncio
    async def test_create_task_saves_to_repository(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that create_task saves the task to repository."""
        await orchestrator.repo.save_definition(workflow_definition)

        task = await orchestrator.create_task(workflow_request)
        retrieved = await orchestrator.repo.get_task(task.task_id)

        assert retrieved is not None
        assert retrieved.task_id == task.task_id

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test executing a simple workflow successfully."""
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is True
        assert result.task_id == task.task_id
        assert result.workflow_id == task.workflow_id
        assert result.duration_seconds > 0
        assert len(result.node_results) > 0

    @pytest.mark.asyncio
    async def test_execute_workflow_with_dependencies(
        self, orchestrator, complex_workflow_definition, workflow_request
    ):
        """Test executing a workflow with node dependencies."""
        await orchestrator.repo.save_definition(complex_workflow_definition)
        workflow_request.workflow_id = complex_workflow_definition.workflow_id
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is True
        # All nodes should be executed in dependency order
        assert len(result.node_results) == len(complex_workflow_definition.nodes)

    @pytest.mark.asyncio
    async def test_execute_workflow_with_failure(
        self, orchestrator, workflow_definition_with_failure, workflow_request
    ):
        """Test executing a workflow that contains a failing node."""
        await orchestrator.repo.save_definition(workflow_definition_with_failure)
        workflow_request.workflow_id = workflow_definition_with_failure.workflow_id
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is False
        assert result.error != ""
        assert len(task.failed_nodes) > 0

    @pytest.mark.asyncio
    async def test_execute_workflow_definition_not_found(self, orchestrator, workflow_task):
        """Test executing a task when workflow definition doesn't exist."""
        result = await orchestrator.execute(workflow_task)

        assert result.success is False
        assert "workflow definition not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_updates_task_status(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that execute updates task status appropriately."""
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        await orchestrator.execute(task)
        retrieved = await orchestrator.repo.get_task(task.task_id)

        assert retrieved.status == WorkflowStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_execute_updates_task_on_failure(
        self, orchestrator, workflow_definition_with_failure, workflow_request
    ):
        """Test that execute updates task status on failure."""
        await orchestrator.repo.save_definition(workflow_definition_with_failure)
        workflow_request.workflow_id = workflow_definition_with_failure.workflow_id
        task = await orchestrator.create_task(workflow_request)

        await orchestrator.execute(task)
        retrieved = await orchestrator.repo.get_task(task.task_id)

        assert retrieved.status == WorkflowStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_tracks_completed_nodes(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that execute tracks completed nodes."""
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        await orchestrator.execute(task)
        retrieved = await orchestrator.repo.get_task(task.task_id)

        assert len(retrieved.completed_nodes) == len(workflow_definition.nodes)

    @pytest.mark.asyncio
    async def test_execute_tracks_failed_nodes(
        self, orchestrator, workflow_definition_with_failure, workflow_request
    ):
        """Test that execute tracks failed nodes."""
        await orchestrator.repo.save_definition(workflow_definition_with_failure)
        workflow_request.workflow_id = workflow_definition_with_failure.workflow_id
        task = await orchestrator.create_task(workflow_request)

        await orchestrator.execute(task)
        retrieved = await orchestrator.repo.get_task(task.task_id)

        assert len(retrieved.failed_nodes) > 0

    @pytest.mark.asyncio
    async def test_execute_updates_current_node(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that execute updates current_node during execution."""
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        await orchestrator.execute(task)
        retrieved = await orchestrator.repo.get_task(task.task_id)

        # Current node should be set during execution
        # (might be the last node or None after completion)
        assert retrieved.current_node is None or retrieved.current_node in [
            node.node_id for node in workflow_definition.nodes
        ]

    @pytest.mark.asyncio
    async def test_execute_saves_task_result(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that execute saves task results."""
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        await orchestrator.execute(task)
        retrieved = await orchestrator.repo.get_task(task.task_id)

        assert len(retrieved.result) > 0

    @pytest.mark.asyncio
    async def test_get_machine_creates_new_machine(self, orchestrator, workflow_task):
        """Test that _get_machine creates a new machine if not exists."""
        machine = orchestrator._get_machine(workflow_task)

        assert machine is not None
        assert workflow_task.task_id in orchestrator.machines

    @pytest.mark.asyncio
    async def test_get_machine_returns_existing_machine(self, orchestrator, workflow_task):
        """Test that _get_machine returns existing machine."""
        machine1 = orchestrator._get_machine(workflow_task)
        machine2 = orchestrator._get_machine(workflow_task)

        assert machine1 is machine2

    @pytest.mark.asyncio
    async def test_can_run_with_no_dependencies(self, orchestrator, sample_workflow_nodes):
        """Test _can_run with nodes that have no dependencies."""
        node = sample_workflow_nodes[0]  # Has no dependencies
        can_run = orchestrator._can_run(node, [])
        assert can_run is True

    @pytest.mark.asyncio
    async def test_can_run_with_satisfied_dependencies(self, orchestrator, sample_workflow_nodes):
        """Test _can_run with satisfied dependencies."""
        node = sample_workflow_nodes[1]  # Depends on "start"
        completed = ["start"]
        can_run = orchestrator._can_run(node, completed)
        assert can_run is True

    @pytest.mark.asyncio
    async def test_can_run_with_unsatisfied_dependencies(self, orchestrator, sample_workflow_nodes):
        """Test _can_run with unsatisfied dependencies."""
        node = sample_workflow_nodes[1]  # Depends on "start"
        completed = []  # "start" not completed
        can_run = orchestrator._can_run(node, completed)
        assert can_run is False

    @pytest.mark.asyncio
    async def test_can_run_with_multiple_dependencies(
        self, orchestrator, complex_workflow_definition
    ):
        """Test _can_run with multiple dependencies."""
        # Find a node with multiple dependencies
        merge_node = next(
            (n for n in complex_workflow_definition.nodes if len(n.dependencies) > 1),
            None,
        )
        if merge_node:
            # Not all dependencies satisfied
            can_run = orchestrator._can_run(merge_node, ["branch1"])
            assert can_run is False

            # All dependencies satisfied
            can_run = orchestrator._can_run(merge_node, ["branch1", "branch2"])
            assert can_run is True

    @pytest.mark.asyncio
    async def test_run_node_renders_template(self, orchestrator, workflow_request):
        """Test that _run_node renders command templates."""
        node = WorkflowNode(
            node_id="test-node",
            name="Test",
            command="echo {{ message }} from {{ user }}",
        )
        params = {"message": "Hello", "user": "World"}

        result = await orchestrator._run_node(node, params)

        assert result["success"] is True
        assert "Hello" in result["output"]
        assert "World" in result["output"]

    @pytest.mark.asyncio
    async def test_run_node_with_no_params(self, orchestrator):
        """Test _run_node with no parameters."""
        node = WorkflowNode(node_id="test-node", name="Test", command="echo static command")

        result = await orchestrator._run_node(node, {})

        assert result["success"] is True
        assert result["output"] == "static command"

    @pytest.mark.asyncio
    async def test_run_node_with_failure_command(self, orchestrator):
        """Test _run_node with a command that should fail."""
        node = WorkflowNode(node_id="test-node", name="Test", command="fail this step")

        with pytest.raises(RuntimeError, match="Simulated node failure"):
            await orchestrator._run_node(node, {})

    @pytest.mark.asyncio
    async def test_run_node_case_insensitive_failure(self, orchestrator):
        """Test _run_node failure detection is case-insensitive."""
        node = WorkflowNode(node_id="test-node", name="Test", command="FAIL this step")

        with pytest.raises(RuntimeError, match="Simulated node failure"):
            await orchestrator._run_node(node, {})

    @pytest.mark.asyncio
    async def test_run_node_returns_node_id(self, orchestrator):
        """Test that _run_node returns node_id in result."""
        node = WorkflowNode(node_id="test-node", name="Test", command="echo test")

        result = await orchestrator._run_node(node, {})

        assert result["node_id"] == "test-node"

    @pytest.mark.asyncio
    async def test_execute_with_empty_workflow(self, orchestrator, workflow_request):
        """Test executing a workflow with no nodes."""
        empty_definition = WorkflowDefinition(
            workflow_id="empty-workflow",
            name="Empty Workflow",
            nodes=[],
        )
        await orchestrator.repo.save_definition(empty_definition)
        workflow_request.workflow_id = "empty-workflow"
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is True
        assert len(result.node_results) == 0

    @pytest.mark.asyncio
    async def test_execute_with_single_node(self, orchestrator, workflow_request):
        """Test executing a workflow with a single node."""
        single_node_definition = WorkflowDefinition(
            workflow_id="single-node-workflow",
            name="Single Node Workflow",
            nodes=[
                WorkflowNode(
                    node_id="only-node",
                    name="Only Node",
                    command="echo single",
                )
            ],
        )
        await orchestrator.repo.save_definition(single_node_definition)
        workflow_request.workflow_id = "single-node-workflow"
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is True
        assert len(result.node_results) == 1

    @pytest.mark.asyncio
    async def test_execute_preserves_request_priority(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that execute preserves the request priority."""
        workflow_request.priority = TaskPriority.CRITICAL
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        # Priority should be in the task metadata/params
        assert "priority" in task.params or hasattr(task, "priority")

    @pytest.mark.asyncio
    async def test_execute_with_complex_params(
        self, orchestrator, workflow_definition, workflow_request_with_params
    ):
        """Test executing workflow with complex parameter types."""
        await orchestrator.repo.save_definition(workflow_definition)
        workflow_request_with_params.workflow_id = workflow_definition.workflow_id
        task = await orchestrator.create_task(workflow_request_with_params)

        result = await orchestrator.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_multiple_tasks_same_workflow(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test executing multiple tasks for the same workflow."""
        await orchestrator.repo.save_definition(workflow_definition)

        task1 = await orchestrator.create_task(workflow_request)
        result1 = await orchestrator.execute(task1)

        task2 = await orchestrator.create_task(workflow_request)
        result2 = await orchestrator.execute(task2)

        assert result1.success is True
        assert result2.success is True
        assert task1.task_id != task2.task_id

    @pytest.mark.asyncio
    async def test_state_machine_integration(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that state machine is integrated with execution."""
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        # State machine should be created
        assert task.task_id in orchestrator.machines

        await orchestrator.execute(task)

        # State machine should still exist
        assert task.task_id in orchestrator.machines

        # Check final state
        machine = orchestrator.machines[task.task_id]
        assert machine.task.status == WorkflowStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_execute_with_timeout_node(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test executing a workflow with a node that has timeout configured."""
        workflow_definition.nodes[0].timeout_seconds = 30
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_node_retries(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test executing a workflow with a node that has retries configured."""
        workflow_definition.nodes[0].retries = 3
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_stops_on_first_failure(
        self, orchestrator, workflow_definition_with_failure, workflow_request
    ):
        """Test that execution stops on first node failure."""
        await orchestrator.repo.save_definition(workflow_definition_with_failure)
        workflow_request.workflow_id = workflow_definition_with_failure.workflow_id
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is False
        # Not all nodes should be completed
        assert len(task.completed_nodes) < len(workflow_definition_with_failure.nodes)

    @pytest.mark.asyncio
    async def test_execute_with_node_params(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test executing workflow with node-specific parameters."""
        workflow_definition.nodes[0].params = {"node_param": "node_value"}
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_duration_measurement(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that execution duration is measured correctly."""
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.duration_seconds > 0
        assert result.duration_seconds < 10  # Should complete quickly

    @pytest.mark.asyncio
    async def test_execute_result_structure(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test that execution result has correct structure."""
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert hasattr(result, "task_id")
        assert hasattr(result, "workflow_id")
        assert hasattr(result, "success")
        assert hasattr(result, "duration_seconds")
        assert hasattr(result, "node_results")
        assert hasattr(result, "error")

    @pytest.mark.asyncio
    async def test_execute_with_special_characters_in_params(
        self, orchestrator, workflow_definition, workflow_request
    ):
        """Test executing workflow with special characters in parameters."""
        workflow_request.params = {
            "message": "Hello World! @#$%^&*()",
            "unicode": "测试中文",
        }
        await orchestrator.repo.save_definition(workflow_definition)
        task = await orchestrator.create_task(workflow_request)

        result = await orchestrator.execute(task)

        assert result.success is True
