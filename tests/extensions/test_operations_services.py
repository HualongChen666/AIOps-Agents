# -*- coding: utf-8 -*-
"""Happy-path tests for operations addon Service classes."""

import asyncio
from unittest.mock import MagicMock

import pytest

from extensions.addons.engines.workflow_engine import WorkflowEngine
from extensions.addons.operations.capacity_planning_service.service import (
    Service as CapacityPlanningService,
)
from extensions.addons.operations.incident_response_service.service import (
    Service as IncidentResponseService,
)
from extensions.addons.operations.incident_runbook_service.service import (
    Service as IncidentRunbookService,
)
from extensions.addons.operations.scenario_memory_service.service import (
    Service as ScenarioMemoryService,
)
from extensions.addons.operations.workflow_engine_service.service import (
    Service as WorkflowEngineService,
)
from extensions.addons.operations.workflow_service.service import Service as WorkflowService


class _FakeCache:
    """In-memory cache stand-in for incident response tests."""

    async def set(self, *args, **kwargs):
        return None

    async def get(self, *args, **kwargs):
        return None


def test_capacity_planning_service(monkeypatch):
    """Capacity planning analysis returns recommendations."""
    monkeypatch.setattr(CapacityPlanningService, "_engine", WorkflowEngine(dry_run=True))
    result = CapacityPlanningService.execute_operation(
        "capacity_analysis",
        {"metrics": {"cpu": 80}, "forecasts": {"cpu": 95}},
    )
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "recommendations" in result
    assert any(r.get("resource") == "cpu" for r in result["recommendations"])


def test_incident_response_service(monkeypatch):
    """Incident Response service lists its supported operations."""
    service = IncidentResponseService(cache=_FakeCache())
    # This service exposes ``call`` as its dispatch method.
    service.execute_operation = service.call
    result = asyncio.run(service.execute_operation("list_methods", request={}))
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("status") == "ok"
    assert result.get("feature") == "list_methods"
    assert "result" in result
    assert "methods" in result["result"]


def test_incident_runbook_service(monkeypatch):
    """Incident Runbook service dispatches a runbook and returns a result."""
    fake_engine = MagicMock()
    fake_engine.run_runbook.return_value = {
        "success": True,
        "runbook": [],
        "results": {"results": [{"step": "decision", "result": {"decision": True}}]},
    }
    monkeypatch.setattr(IncidentRunbookService, "_engine", fake_engine)
    result = IncidentRunbookService.execute_operation(
        "run_runbook",
        {
            "runbook": [
                {
                    "type": "decision",
                    "condition": "severity == 'high'",
                    "true": "escalate",
                }
            ],
            "inputs": {"severity": "high"},
        },
    )
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "results" in result
    fake_engine.run_runbook.assert_called_once()


def test_scenario_memory_service(monkeypatch):
    """Scenario Memory service returns synthetic memory matches."""
    monkeypatch.setattr(ScenarioMemoryService, "_engine", WorkflowEngine(dry_run=True))
    result = ScenarioMemoryService.execute_operation(
        "get_scenario_memory",
        {"query": "network outage"},
    )
    assert isinstance(result, dict)
    assert result.get("query") == "network outage"
    assert "matches" in result


def test_workflow_engine_service(monkeypatch):
    """Workflow Engine service executes a workflow definition."""
    monkeypatch.setattr(WorkflowEngineService, "_engine", WorkflowEngine(dry_run=True))
    result = WorkflowEngineService.execute_operation(
        "execute_workflow",
        {"workflow_def": [{"type": "http", "method": "GET", "url": "http://example.com"}]},
    )
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "results" in result


def test_workflow_service(monkeypatch):
    """Workflow service runs a workflow and returns step results."""
    monkeypatch.setattr(WorkflowService, "_engine", WorkflowEngine(dry_run=True))
    result = WorkflowService.execute_operation(
        "run_workflow",
        {"workflow_def": [{"type": "cli", "command": ["echo", "hello"]}]},
    )
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "results" in result
