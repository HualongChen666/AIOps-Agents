# -*- coding: utf-8 -*-
"""Tests for core/workflow/engine/executor.py."""

import pytest

from core.workflow.engine.dag import DAG, DAGNode
from core.workflow.engine.executor import ExecutionContext, WorkflowExecutor
from core.workflow.engine.state_machine import WorkflowState


def test_execution_context_dict():
    ctx = ExecutionContext(workflow_id="wf", run_id="run1")
    assert ctx.to_dict()["workflow_id"] == "wf"


@pytest.mark.asyncio
async def test_workflow_executor():
    executor = WorkflowExecutor(default_timeout=1, default_max_retries=0)

    async def handler(node, context):
        return {"node": node.id}

    executor.register_handler("noop", handler)

    dag = DAG("test")
    dag.add_node(DAGNode(id="n1", name="N1", type="noop", config={}))
    ctx = await executor.execute(dag)
    assert ctx.status == WorkflowState.COMPLETED
    assert ctx.results["n1"] == {"node": "n1"}


@pytest.mark.asyncio
async def test_workflow_executor_failure():
    executor = WorkflowExecutor(default_timeout=1, default_max_retries=0)

    async def bad_handler(node, context):
        raise RuntimeError("boom")

    executor.register_handler("fail", bad_handler)

    dag = DAG("test_fail")
    dag.add_node(DAGNode(id="f1", name="F1", type="fail", config={}))
    ctx = await executor.execute(dag)
    assert "f1" in ctx.errors
    assert ctx.errors["f1"].startswith("Node f1 failed")
