# -*- coding: utf-8 -*-
"""Tests for Group 6 workflow & operations addons."""

from unittest.mock import MagicMock

import pytest

from extensions.addons.operations.capacity_planning_service.service import (
    Service as CapacityPlanningService,
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


class _MockResponse:
    status_code = 200
    text = "ok"
    headers = {}


class _MockCompleted:
    returncode = 0
    stdout = "hello"
    stderr = ""


@pytest.fixture(autouse=True)
def _enable_real_execute(monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")


@pytest.fixture
def mock_request(monkeypatch):
    m = MagicMock(return_value=_MockResponse())
    monkeypatch.setattr("requests.request", m)
    return m


@pytest.fixture
def mock_run(monkeypatch):
    m = MagicMock(return_value=_MockCompleted())
    monkeypatch.setattr("subprocess.run", m)
    return m


def test_workflow_engine_service(mock_request):
    params = {"workflow_def": [{"type": "http", "method": "GET", "url": "http://example.com"}]}
    result = WorkflowEngineService.execute_operation("execute_workflow", params)
    assert result["success"] is True
    mock_request.assert_called_once()


def test_workflow_service(mock_run):
    params = {"workflow_def": [{"type": "cli", "command": ["echo", "hello"]}]}
    result = WorkflowService.execute_operation("run_workflow", params)
    assert result["success"] is True
    mock_run.assert_called_once()


def test_incident_runbook_service():
    params = {
        "runbook": [{"type": "decision", "condition": "severity == 'high'", "true": "escalate"}],
        "inputs": {"severity": "high"},
    }
    result = IncidentRunbookService.execute_operation("run_runbook", params)
    assert result["success"] is True
    assert result["results"]["results"][0]["result"]["decision"] is True


def test_capacity_planning_service():
    params = {"metrics": {"cpu": 80}, "forecasts": {"cpu": 95}}
    result = CapacityPlanningService.execute_operation("capacity_analysis", params)
    assert result["success"] is True
    assert any(r["resource"] == "cpu" for r in result["recommendations"])


def test_scenario_memory_service():
    result = ScenarioMemoryService.execute_operation(
        "get_scenario_memory", {"query": "network outage"}
    )
    assert "query" in result
