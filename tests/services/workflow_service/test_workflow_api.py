# -*- coding: utf-8 -*-
"""API tests for workflow microservice."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def orchestrator_client():
    from services.workflow_service.workflow_orchestrator_app import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def scheduler_client():
    from services.workflow_service.scheduler_app import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def executor_client():
    from services.workflow_service.executor_app import app

    with TestClient(app) as client:
        yield client


class TestOrchestratorAPI:
    def test_health(self, orchestrator_client):
        response = orchestrator_client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "workflow-orchestrator"

    def test_create_definition(self, orchestrator_client):
        definition = {
            "workflow_id": "wf-api",
            "name": "API Workflow",
            "nodes": [{"node_id": "n1", "name": "Node 1", "command": "echo ok"}],
        }
        response = orchestrator_client.post("/workflows/definitions", json=definition)
        assert response.status_code == 200
        assert response.json()["status"] == "created"

    def test_execute_workflow(self, orchestrator_client):
        definition = {
            "workflow_id": "wf-exec",
            "name": "Execute Workflow",
            "nodes": [{"node_id": "n1", "name": "Node 1", "command": "echo ok"}],
        }
        orchestrator_client.post("/workflows/definitions", json=definition)
        response = orchestrator_client.post("/workflows/execute", json={"workflow_id": "wf-exec"})
        assert response.status_code == 200
        assert "success" in response.json()

    def test_list_definitions(self, orchestrator_client):
        response = orchestrator_client.get("/workflows/definitions")
        assert response.status_code == 200
        assert "items" in response.json()

    def test_list_executions(self, orchestrator_client):
        response = orchestrator_client.get("/workflows/executions")
        assert response.status_code == 200
        assert "items" in response.json()

    def test_template(self, orchestrator_client):
        template = {
            "template_id": "tpl-api",
            "name": "API Template",
            "source": "Hello {{ name }}",
            "default_params": {"name": "World"},
        }
        response = orchestrator_client.post("/workflows/templates", json=template)
        assert response.status_code == 200
        response = orchestrator_client.post("/workflows/templates/tpl-api/render")
        assert response.status_code == 200
        assert "Hello World" in response.json()["rendered"]

    def test_metrics(self, orchestrator_client):
        response = orchestrator_client.get("/metrics")
        assert response.status_code == 200


class TestSchedulerAPI:
    def test_health(self, scheduler_client):
        response = scheduler_client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "workflow-scheduler"

    def test_schedule(self, scheduler_client):
        schedule = {
            "schedule_id": "sched-1",
            "workflow_id": "wf-1",
            "cron": "* * * * *",
        }
        response = scheduler_client.post("/workflows/schedule", json=schedule)
        assert response.status_code == 200
        assert "schedule_id" in response.json()

    def test_run_once(self, scheduler_client):
        response = scheduler_client.post("/workflows/run-once")
        assert response.status_code == 200


class TestExecutorAPI:
    def test_health(self, executor_client):
        response = executor_client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "workflow-executor"

    def test_metrics(self, executor_client):
        response = executor_client.get("/metrics")
        assert response.status_code == 200
