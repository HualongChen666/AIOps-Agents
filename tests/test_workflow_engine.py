# -*- coding: utf-8 -*-
"""
Workflow Engine Tests
"""

import asyncio

import pytest

from core.workflow.engine import (  # noqa: F401; noqa: E501
    DAG,
    DAGNode,
    Edge,
    ExecutionContext,
    WorkflowExecutor,
)
from core.workflow.engine.dsl import WorkflowDSL, parse_json_workflow, parse_yaml_workflow
from core.workflow.engine.state_machine import WorkflowEvent, WorkflowState, WorkflowStateMachine


class TestDAG:
    """Test DAG implementation"""

    def test_add_node(self):
        """Test adding nodes to DAG"""
        dag = DAG("test")
        node = DAGNode(id="node1", name="Node 1")
        dag.add_node(node)
        assert "node1" in dag.nodes
        assert dag.nodes["node1"] == node

    def test_add_edge(self):
        """Test adding edges to DAG"""
        dag = DAG("test")
        dag.add_node(DAGNode(id="node1", name="Node 1"))
        dag.add_node(DAGNode(id="node2", name="Node 2"))
        edge = Edge(from_node="node1", to_node="node2")
        dag.add_edge(edge)
        assert len(dag.edges) == 1
        assert "node1" in dag.nodes["node2"].dependencies

    def test_topological_sort(self):
        """Test topological sorting"""
        dag = DAG("test")
        dag.add_node(DAGNode(id="node1", name="Node 1"))
        dag.add_node(DAGNode(id="node2", name="Node 2"))
        dag.add_node(DAGNode(id="node3", name="Node 3"))
        dag.add_edge(Edge(from_node="node1", to_node="node2"))
        dag.add_edge(Edge(from_node="node2", to_node="node3"))

        order = dag.topological_sort()
        assert order.index("node1") < order.index("node2")
        assert order.index("node2") < order.index("node3")

    def test_cycle_detection(self):
        """Test cycle detection"""
        dag = DAG("test")
        dag.add_node(DAGNode(id="node1", name="Node 1"))
        dag.add_node(DAGNode(id="node2", name="Node 2"))
        dag.add_edge(Edge(from_node="node1", to_node="node2"))
        dag.add_edge(Edge(from_node="node2", to_node="node1"))

        cycles = dag.detect_cycles()
        assert len(cycles) > 0


class TestWorkflowStateMachine:
    """Test workflow state machine"""

    def test_initial_state(self):
        """Test initial state"""
        sm = WorkflowStateMachine("test")
        assert sm.current_state == WorkflowState.IDLE

    def test_valid_transition(self):
        """Test valid state transition"""
        sm = WorkflowStateMachine("test")
        assert sm.can_transition(WorkflowEvent.START)
        sm.transition(WorkflowEvent.START)
        assert sm.current_state == WorkflowState.RUNNING

    def test_invalid_transition(self):
        """Test invalid state transition"""
        sm = WorkflowStateMachine("test")
        assert not sm.can_transition(WorkflowEvent.COMPLETE)
        with pytest.raises(ValueError):
            sm.transition(WorkflowEvent.COMPLETE)

    def test_terminal_states(self):
        """Test terminal state detection"""
        sm = WorkflowStateMachine("test")
        sm.transition(WorkflowEvent.START)
        sm.transition(WorkflowEvent.COMPLETE)
        assert sm.is_terminal()


class TestWorkflowExecutor:
    """Test workflow executor"""

    @pytest.mark.asyncio
    async def test_execute_simple_dag(self):
        """Test executing simple DAG"""
        dag = DAG("test")
        dag.add_node(DAGNode(id="node1", name="Node 1"))

        executor = WorkflowExecutor()

        # Register mock handler
        async def mock_handler(node, context):
            return {"result": "success"}

        executor.register_handler("task", mock_handler)

        context = await executor.execute(dag)
        assert context.status == WorkflowState.COMPLETED
        assert "node1" in context.results

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel node execution"""
        dag = DAG("test")
        dag.add_node(DAGNode(id="node1", name="Node 1"))
        dag.add_node(DAGNode(id="node2", name="Node 2"))
        dag.add_node(DAGNode(id="node3", name="Node 3", dependencies=["node1", "node2"]))

        executor = WorkflowExecutor(max_parallel_nodes=2)

        async def mock_handler(node, context):
            await asyncio.sleep(0.1)
            return {"result": f"{node.id}_success"}

        executor.register_handler("task", mock_handler)

        context = await executor.execute(dag)
        assert context.status == WorkflowState.COMPLETED


class TestWorkflowDSL:
    """Test workflow DSL"""

    def test_parse_yaml(self):
        """Test YAML parsing"""
        yaml_content = """
name: test_workflow
nodes:
  - id: node1
    name: Node 1
    type: task
    dependencies: []
  - id: node2
    name: Node 2
    type: task
    dependencies: [node1]
edges:
  - from: node1
    to: node2
"""
        dag = parse_yaml_workflow(yaml_content)
        assert dag.name == "test_workflow"
        assert len(dag.nodes) == 2
        assert len(dag.edges) == 1

    def test_parse_json(self):
        """Test JSON parsing"""
        json_content = """
{
  "name": "test_workflow",
  "nodes": [
    {"id": "node1", "name": "Node 1", "type": "task", "dependencies": []},
    {"id": "node2", "name": "Node 2", "type": "task", "dependencies": ["node1"]}
  ],
  "edges": [
    {"from": "node1", "to": "node2"}
  ]
}
"""
        dag = parse_json_workflow(json_content)
        assert dag.name == "test_workflow"
        assert len(dag.nodes) == 2

    def test_validate_dag(self):
        """Test DAG validation"""
        dsl = WorkflowDSL()
        yaml_content = """
name: test_workflow
nodes:
  - id: node1
    name: Node 1
    type: task
    dependencies: []
edges: []
"""
        dag = dsl.parse_yaml(yaml_content)
        assert dsl.validate(dag)
