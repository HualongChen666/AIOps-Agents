# -*- coding: utf-8 -*-
"""
LangGraph Workflow Tests
Tests for workflow execution and node types
"""

import asyncio  # noqa: F401

import pytest

from core.ai.langgraph import (
    ConditionalNode,
    LLMNode,
    ToolNode,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    define_workflow,
)


class TestWorkflow:
    """Test basic workflow functionality"""

    def test_workflow_creation(self):
        """Test workflow creation"""
        workflow = Workflow("test_workflow")
        assert workflow.name == "test_workflow"
        assert workflow.state.value == "pending"

    def test_add_node(self):
        """Test adding nodes to workflow"""
        workflow = Workflow("test")
        node = ToolNode("test_node", lambda ctx: "result")
        workflow.add_node(node)
        assert "test_node" in workflow.nodes

    def test_add_edge(self):
        """Test adding edges to workflow"""
        workflow = Workflow("test")
        node1 = ToolNode("node1", lambda ctx: "result1")
        node2 = ToolNode("node2", lambda ctx: "result2")
        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_edge("node1", "node2")
        assert len(workflow.edges) == 1

    def test_workflow_validation(self):
        """Test workflow validation"""
        workflow = Workflow("test")
        node = ToolNode("node", lambda ctx: "result")
        workflow.add_node(node)
        workflow.set_start_node("node")
        assert workflow.validate()

    def test_workflow_validation_no_start(self):
        """Test workflow validation without start node"""
        workflow = Workflow("test")
        node = ToolNode("node", lambda ctx: "result")
        workflow.add_node(node)
        assert workflow.validate() is False


class TestLLMNode:
    """Test LLM node functionality"""

    def test_llm_node_creation(self):
        """Test LLM node creation"""
        node = LLMNode("test_llm", model_name="gpt-4", prompt_template="Test prompt")
        assert node.name == "test_llm"
        assert node.model_name == "gpt-4"
        assert node.node_type == "llm"

    @pytest.mark.asyncio
    async def test_llm_node_execute(self):
        """Test LLM node execution"""
        node = LLMNode("test_llm", prompt_template="Test {var}")
        context = WorkflowContext()
        context.set("var", "value")
        result = await node.execute(context)
        assert result is not None


class TestToolNode:
    """Test tool node functionality"""

    def test_tool_node_creation(self):
        """Test tool node creation"""

        async def test_tool(ctx, **kwargs):
            return "tool_result"

        node = ToolNode("test_tool", test_tool)
        assert node.name == "test_tool"
        assert node.node_type == "tool"

    @pytest.mark.asyncio
    async def test_tool_node_execute(self):
        """Test tool node execution"""

        async def test_tool(ctx, **kwargs):
            return "tool_result"

        node = ToolNode("test_tool", test_tool)
        context = WorkflowContext()
        result = await node.execute(context)
        assert result == "tool_result"


class TestConditionalNode:
    """Test conditional node functionality"""

    def test_conditional_node_creation(self):
        """Test conditional node creation"""

        def condition(ctx):
            return True

        node = ConditionalNode("test_cond", condition, "true_branch", "false_branch")
        assert node.name == "test_cond"
        assert node.node_type == "conditional"

    @pytest.mark.asyncio
    async def test_conditional_node_true(self):
        """Test conditional node with true condition"""

        def condition(ctx):
            return True

        node = ConditionalNode("test_cond", condition, "true_branch", "false_branch")
        context = WorkflowContext()
        result = await node.execute(context)
        assert result == "true_branch"

    @pytest.mark.asyncio
    async def test_conditional_node_false(self):
        """Test conditional node with false condition"""

        def condition(ctx):
            return False

        node = ConditionalNode("test_cond", condition, "true_branch", "false_branch")
        context = WorkflowContext()
        result = await node.execute(context)
        assert result == "false_branch"


class TestWorkflowBuilder:
    """Test workflow builder DSL"""

    def test_builder_creation(self):
        """Test builder creation"""
        builder = WorkflowBuilder("test", "Test workflow")
        assert builder.workflow.name == "test"

    def test_builder_llm_node(self):
        """Test builder with LLM node"""
        builder = WorkflowBuilder("test")
        builder.llm_node("llm_node", model="gpt-4")
        assert "llm_node" in builder.workflow.nodes

    def test_builder_tool_node(self):
        """Test builder with tool node"""

        async def tool_func(ctx, **kwargs):
            return "result"

        builder = WorkflowBuilder("test")
        builder.tool_node("tool_node", tool_func)
        assert "tool_node" in builder.workflow.nodes

    def test_builder_edge(self):
        """Test builder with edge"""

        async def tool_func(ctx, **kwargs):
            return "result"

        builder = WorkflowBuilder("test")
        builder.tool_node("node1", tool_func)
        builder.tool_node("node2", tool_func)
        builder.edge("node1", "node2")
        assert len(builder.workflow.edges) == 1

    def test_builder_build(self):
        """Test building workflow"""

        async def tool_func(ctx, **kwargs):
            return "result"

        builder = WorkflowBuilder("test")
        builder.tool_node("node", tool_func)
        builder.start("node")
        workflow = builder.build()
        assert workflow.start_node == "node"


class TestDefineWorkflow:
    """Test define_workflow DSL function"""

    def test_define_workflow(self):
        """Test define_workflow function"""
        builder = define_workflow("test", "Test description")
        assert isinstance(builder, WorkflowBuilder)
        assert builder.workflow.name == "test"


class TestWorkflowExecution:
    """Test workflow execution"""

    @pytest.mark.asyncio
    async def test_simple_workflow_execution(self):
        """Test simple workflow execution"""
        workflow = Workflow("simple")

        async def tool_func(ctx, **kwargs):
            return "executed"

        node = ToolNode("node1", tool_func)
        workflow.add_node(node)
        workflow.set_start_node("node1")
        workflow.add_end_node("node1")

        result = await workflow.execute()
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_with_context(self):
        """Test workflow with context data"""
        workflow = Workflow("context_test")

        async def tool_func(ctx, **kwargs):
            return ctx.get("test_key")

        node = ToolNode("node1", tool_func)
        workflow.add_node(node)
        workflow.set_start_node("node1")
        workflow.add_end_node("node1")

        result = await workflow.execute({"test_key": "test_value"})
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_with_edges(self):
        """Test workflow with edges"""
        workflow = Workflow("edge_test")

        async def tool_func(ctx, **kwargs):
            return "executed"

        node1 = ToolNode("node1", tool_func)
        node2 = ToolNode("node2", tool_func)
        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_edge("node1", "node2")
        workflow.set_start_node("node1")
        workflow.add_end_node("node2")

        result = await workflow.execute()
        assert result["status"] == "completed"
        assert len(result["history"]) == 2
