# -*- coding: utf-8 -*-
"""
Comprehensive tests for core/ai/langgraph modules.
"""

import asyncio
import types

import pytest

from core.ai.langgraph.dsl import define_workflow
from core.ai.langgraph.executor import WorkflowExecutor, WorkflowOrchestrator
from core.ai.langgraph.nodes import (
    AggregatorNode,
    ConditionalNode,
    LLMNode,
    ParallelNode,
    ToolNode,
)
from core.ai.langgraph.visualizer import WorkflowVisualizer
from core.ai.langgraph.workflow import (
    Workflow,
    WorkflowContext,
    WorkflowEdge,
    WorkflowState,
)


@pytest.fixture
def simple_workflow():
    """Build a simple linear workflow for reuse."""

    async def end_func(ctx):
        return {"result": "done"}

    workflow = (
        define_workflow("simple", "A simple workflow")
        .llm_node("start", model="gpt-4", prompt="Hello {name}")
        .tool_node("end", tool_func=end_func)
        .edge("start", "end")
        .start("start")
        .end("end")
        .build()
    )
    return workflow


@pytest.fixture
def conditional_workflow():
    """Build a conditional workflow."""
    workflow = (
        define_workflow("conditional", "A conditional workflow")
        .llm_node("start", model="gpt-4", prompt="")
        .conditional_node(
            "check",
            condition=lambda ctx: ctx.get("value", 0) > 0,
            true_branch="positive",
            false_branch="negative",
        )
        .llm_node("positive", model="gpt-4", prompt="positive")
        .llm_node("negative", model="gpt-4", prompt="negative")
        .edge("start", "check")
        .edge("check", "positive")
        .edge("check", "negative")
        .start("start")
        .end("positive")
        .end("negative")
        .build()
    )
    return workflow


# ----------------------------------------------------------------------
# WorkflowContext
# ----------------------------------------------------------------------


class TestWorkflowContext:
    def test_context_get_set(self):
        ctx = WorkflowContext(input_data={"x": 1})
        ctx.set("key", "value")
        assert ctx.get("key") == "value"
        assert ctx.get("missing") is None
        assert ctx.get("missing", "default") == "default"

    def test_context_add_history(self):
        ctx = WorkflowContext()
        ctx.add_history("node1", "result")
        assert len(ctx.history) == 1
        assert ctx.history[0]["node"] == "node1"


# ----------------------------------------------------------------------
# WorkflowEdge
# ----------------------------------------------------------------------


class TestWorkflowEdge:
    def test_edge_unconditional(self):
        edge = WorkflowEdge("a", "b")
        assert edge.should_traverse(WorkflowContext()) is True

    def test_edge_conditional_true(self):
        edge = WorkflowEdge("a", "b", condition=lambda ctx: ctx.get("flag", False))
        ctx = WorkflowContext()
        ctx.set("flag", True)
        assert edge.should_traverse(ctx) is True

    def test_edge_conditional_false(self):
        edge = WorkflowEdge("a", "b", condition=lambda ctx: ctx.get("flag", False))
        assert edge.should_traverse(WorkflowContext()) is False


# ----------------------------------------------------------------------
# Workflow
# ----------------------------------------------------------------------


class TestWorkflow:
    def test_workflow_initialization(self):
        wf = Workflow("test", "desc")
        assert wf.name == "test"
        assert wf.description == "desc"
        assert wf.state == WorkflowState.PENDING

    def test_add_node(self):
        wf = Workflow("test")
        node = LLMNode("n1")
        wf.add_node(node)
        assert "n1" in wf.nodes

    def test_add_edge(self):
        wf = Workflow("test")
        node = LLMNode("n1")
        wf.add_node(node)
        wf.add_edge("n1", "n1")
        assert len(wf.edges) == 1

    def test_set_start_node_missing(self):
        wf = Workflow("test")
        with pytest.raises(ValueError):
            wf.set_start_node("missing")

    def test_validate_no_start(self):
        wf = Workflow("test")
        assert wf.validate() is False

    def test_validate_success(self, simple_workflow):
        assert simple_workflow.validate() is True
        assert simple_workflow.state == WorkflowState.PENDING

    def test_execute_simple(self, simple_workflow):
        result = asyncio.run(simple_workflow.execute({"name": "World"}))
        assert result["status"] == "completed"
        assert any(h["node"] == "end" for h in result["history"])
        assert simple_workflow.state == WorkflowState.COMPLETED

    def test_execute_failure(self):
        async def bad_tool(ctx):
            raise Exception("boom")

        wf = Workflow("fail")
        node = ToolNode("bad", tool_function=bad_tool)
        wf.add_node(node)
        wf.set_start_node("bad")
        wf.add_end_node("bad")
        result = asyncio.run(wf.execute())
        assert result["status"] == "failed"
        assert wf.state == WorkflowState.FAILED

    def test_to_dict(self, simple_workflow):
        data = simple_workflow.to_dict()
        assert data["name"] == "simple"
        assert data["start_node"] == "start"
        assert data["state"] == "pending"

    def test_to_mermaid(self, simple_workflow):
        mermaid = simple_workflow.to_mermaid()
        assert "graph TD" in mermaid
        assert "start" in mermaid


# ----------------------------------------------------------------------
# WorkflowBuilder / DSL
# ----------------------------------------------------------------------


class TestWorkflowBuilder:
    def test_builder_chaining(self):
        builder = define_workflow("test").llm_node("n1").tool_node("n2", lambda ctx: None)
        assert builder.workflow is not None

    def test_builder_validate_and_build(self):
        wf = (
            define_workflow("test")
            .llm_node("n1")
            .tool_node("n2", lambda ctx: None)
            .edge("n1", "n2")
            .start("n1")
            .end("n2")
            .build()
        )
        assert isinstance(wf, Workflow)

    def test_builder_build_invalid(self):
        builder = define_workflow("test").llm_node("n1")
        with pytest.raises(ValueError):
            builder.build()

    def test_parallel_node(self):
        child = LLMNode("child")
        wf = define_workflow("test").parallel_node("p", [child]).start("p").end("p").build()
        assert "p" in wf.nodes

    def test_conditional_node(self):
        wf = (
            define_workflow("test")
            .llm_node("n1")
            .conditional_node("c", lambda ctx: True, "n2", "n3")
            .tool_node("n2", lambda ctx: None)
            .tool_node("n3", lambda ctx: None)
            .edge("n1", "c")
            .start("n1")
            .end("n2")
            .end("n3")
            .build()
        )
        assert wf.validate() is True

    def test_dsl_example(self):
        async def _run():
            async def repair(ctx):
                return {"status": "ok"}

            workflow = (
                define_workflow("incident_analysis")
                .llm_node("analyze", prompt="Incident: {incident_data}")
                .tool_node("execute_repair", tool_func=repair)
                .edge("analyze", "execute_repair")
                .start("analyze")
                .end("execute_repair")
                .build()
            )
            return await workflow.execute({"incident_data": "Server down"})

        result = asyncio.run(_run())
        assert result["status"] == "completed"


# ----------------------------------------------------------------------
# Nodes
# ----------------------------------------------------------------------


class TestLLMNode:
    def test_llm_node_initialization(self):
        node = LLMNode("n", model_name="gpt-4", prompt_template="Hi {name}")
        assert node.model_name == "gpt-4"
        assert node.prompt_template == "Hi {name}"

    def test_llm_node_format_prompt(self):
        node = LLMNode("n", prompt_template="Hi {name}")
        ctx = WorkflowContext()
        ctx.set("name", "World")
        prompt = node._format_prompt(ctx)
        assert prompt == "Hi World"

    def test_llm_node_execute(self):
        node = LLMNode("n", prompt_template="Hi {name}")
        ctx = WorkflowContext()
        ctx.set("name", "World")
        result = asyncio.run(node.execute(ctx))
        assert "World" in result


class TestToolNode:
    def test_tool_node_execute(self):
        async def fn(ctx, value=""):
            return {"value": value}

        node = ToolNode("n", tool_function=fn, tool_config={"value": "test"})
        result = asyncio.run(node.execute(WorkflowContext()))
        assert result["value"] == "test"

    def test_tool_node_execute_exception(self):
        async def fn(ctx):
            raise Exception("fail")

        node = ToolNode("n", tool_function=fn)
        with pytest.raises(Exception, match="fail"):
            asyncio.run(node.execute(WorkflowContext()))


class TestConditionalNode:
    def test_conditional_true(self):
        node = ConditionalNode("c", lambda ctx: True, "t", "f")
        result = asyncio.run(node.execute(WorkflowContext()))
        assert result == "t"

    def test_conditional_false(self):
        node = ConditionalNode("c", lambda ctx: False, "t", "f")
        result = asyncio.run(node.execute(WorkflowContext()))
        assert result == "f"


class TestParallelNode:
    def test_parallel_execute(self):
        async def fn(ctx):
            return 1

        node = ParallelNode("p", [ToolNode("a", fn), ToolNode("b", fn)])
        result = asyncio.run(node.execute(WorkflowContext()))
        assert result == {"a": 1, "b": 1}


class TestAggregatorNode:
    def test_aggregator_execute(self):
        ctx = WorkflowContext()
        ctx.set("a", 1)
        ctx.set("b", 2)
        node = AggregatorNode("agg", lambda values: sum(values), ["a", "b"])
        result = asyncio.run(node.execute(ctx))
        assert result == 3


# ----------------------------------------------------------------------
# Executor
# ----------------------------------------------------------------------


class TestWorkflowExecutor:
    def test_execute_success(self, simple_workflow):
        executor = WorkflowExecutor(max_retries=1, retry_delay=0.0)
        result = asyncio.run(executor.execute(simple_workflow))
        assert result["status"] == "completed"

    def test_execute_retry_then_success(self, simple_workflow):
        # Make the workflow fail once then succeed by toggling state
        call_count = 0
        original = simple_workflow.execute

        async def flaky_execute(self, input_data=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("flaky")
            return await original(input_data)

        simple_workflow.execute = types.MethodType(flaky_execute, simple_workflow)
        executor = WorkflowExecutor(max_retries=2, retry_delay=0.0)
        result = asyncio.run(executor.execute(simple_workflow))
        assert result["status"] == "completed"

    def test_execute_all_retries_fail(self):
        async def failing_execute(self, input_data=None):
            raise Exception("boom")

        wf = Workflow("fail")
        wf.execute = types.MethodType(failing_execute, wf)
        executor = WorkflowExecutor(max_retries=1, retry_delay=0.0)
        result = asyncio.run(executor.execute(wf))
        assert result["status"] == "failed"
        assert "last_error" in result
        assert "boom" in result["last_error"]

    def test_execute_timeout(self):
        wf = Workflow("slow")

        async def slow(ctx):
            await asyncio.sleep(5)

        node = ToolNode("slow", tool_function=slow)
        wf.add_node(node)
        wf.set_start_node("slow")
        wf.add_end_node("slow")
        executor = WorkflowExecutor(timeout=0.01)
        result = asyncio.run(executor.execute(wf))
        assert result["status"] == "failed"
        assert "timeout" in result["last_error"].lower()


class TestWorkflowOrchestrator:
    def test_register_and_get(self, simple_workflow):
        orch = WorkflowOrchestrator()
        orch.register_workflow(simple_workflow)
        assert orch.get_workflow("simple") == simple_workflow
        assert "simple" in orch.list_workflows()

    def test_execute_workflow(self, simple_workflow):
        orch = WorkflowOrchestrator()
        orch.register_workflow(simple_workflow)
        result = asyncio.run(orch.execute_workflow("simple", {"name": "x"}))
        assert result["status"] == "completed"

    def test_execute_missing_workflow(self):
        orch = WorkflowOrchestrator()
        with pytest.raises(ValueError, match="not found"):
            asyncio.run(orch.execute_workflow("missing"))


# ----------------------------------------------------------------------
# Visualizer
# ----------------------------------------------------------------------


class TestWorkflowVisualizer:
    def test_to_mermaid(self, simple_workflow):
        mermaid = WorkflowVisualizer.to_mermaid(simple_workflow)
        assert "graph TD" in mermaid

    def test_to_graphviz(self, simple_workflow):
        dot = WorkflowVisualizer.to_graphviz(simple_workflow)
        assert "digraph workflow" in dot
        assert "start" in dot
        assert "end" in dot

    def test_to_ascii(self, simple_workflow):
        ascii_art = WorkflowVisualizer.to_ascii(simple_workflow)
        assert "Workflow: simple" in ascii_art
        assert "start" in ascii_art

    def test_render_mermaid(self, simple_workflow, tmp_path):
        path = tmp_path / "diagram.mmd"
        mermaid = asyncio.run(
            WorkflowVisualizer.render_mermaid(simple_workflow, output_path=str(path))
        )
        assert path.exists()
        assert mermaid in path.read_text()

    def test_render_graphviz(self, simple_workflow, tmp_path):
        path = tmp_path / "diagram.dot"
        dot = asyncio.run(
            WorkflowVisualizer.render_graphviz(simple_workflow, output_path=str(path))
        )
        assert path.exists()
        assert dot in path.read_text()


# ----------------------------------------------------------------------
# WorkflowState
# ----------------------------------------------------------------------


class TestWorkflowState:
    def test_states(self):
        assert WorkflowState.PENDING.value == "pending"
        assert WorkflowState.RUNNING.value == "running"
        assert WorkflowState.COMPLETED.value == "completed"
        assert WorkflowState.FAILED.value == "failed"
        assert WorkflowState.PAUSED.value == "paused"
