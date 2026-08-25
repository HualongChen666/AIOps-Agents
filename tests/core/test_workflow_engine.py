# -*- coding: utf-8 -*-
"""Tests for core/processing/l3/workflow_engine.py."""

import pytest  # noqa: F401  # Imported for test setup

import core.processing.l3.workflow_engine as wfe
from core.processing.l3.workflow_engine import (
    Workflow,
    WorkflowEngine,
    WorkflowStep,
    get_workflow_engine,
    init_workflow_engine,
)


@pytest.fixture(autouse=True)
def patch_workflow_state(monkeypatch):
    monkeypatch.setattr(wfe, "WorkflowStateClass", wfe.FallbackWorkflowState)


def test_register_and_get_workflow():
    engine = WorkflowEngine()
    wf = Workflow("wf1").add_step(WorkflowStep("s1", handler=lambda c, p: {"ok": True}))
    engine.register_workflow(wf)
    assert engine.get_workflow("wf1") == wf
    status = engine.get_status()
    assert status["workflow_count"] == 1


@pytest.mark.asyncio
async def test_execute_simple_workflow():
    engine = WorkflowEngine()

    async def step_handler(context, params):
        return {"value": params.get("x", 0) * 2}

    wf = Workflow("calc").add_step(WorkflowStep("double", handler=step_handler, params={"x": 5}))
    engine.register_workflow(wf)
    result = await engine.execute_workflow(
        "calc", {}
    )  # noqa: F841  # Variable for test verification
    assert result["context"]["double"]["value"] == 10


def test_incident_workflow():
    engine = WorkflowEngine()
    wf = engine.create_incident_response_workflow()
    assert wf.name == "incident_response"
    assert len(wf.steps) > 0


def test_factory_functions():
    init_workflow_engine({})
    engine = get_workflow_engine()
    assert isinstance(engine, WorkflowEngine)
