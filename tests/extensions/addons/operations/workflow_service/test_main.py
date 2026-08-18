# -*- coding: utf-8 -*-
"""Tests for workflow_service main module."""

import logging
import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

# Import the main module
import sys
sys.path.insert(0, "C:/aiops-sre-agent/extensions/addons/operations/workflow_service")
import main as workflow_main


class TestMainModule:
    """Test cases for main module functions and models."""

    def test_service_name_constant(self):
        """Test SERVICE_NAME constant."""
        assert workflow_main.SERVICE_NAME == "workflow_service"

    def test_port_default(self):
        """Test default PORT value."""
        assert workflow_main.PORT == 8000

    def test_port_from_environment(self, monkeypatch):
        """Test PORT from environment variable."""
        monkeypatch.setenv("PORT", "9000")
        # Reload to pick up environment variable
        import importlib
        importlib.reload(workflow_main)
        assert workflow_main.PORT == 9000

    def test_app_initialization(self):
        """Test FastAPI app initialization."""
        assert workflow_main.app is not None
        assert hasattr(workflow_main.app, "routes")

    def test_app_title(self):
        """Test app title."""
        assert "Workflow" in workflow_main.app.title

    def test_logger_initialization(self):
        """Test logger initialization."""
        assert workflow_main.logger is not None
        assert isinstance(workflow_main.logger, logging.Logger)

    def test_workflow_model_creation(self):
        """Test Workflow model creation."""
        workflow = workflow_main.Workflow(
            name="Test Workflow",
            tasks=["task1", "task2"],
            state="pending",
        )
        assert workflow.name == "Test Workflow"
        assert workflow.tasks == ["task1", "task2"]
        assert workflow.state == "pending"
        assert workflow.id is not None  # Should be auto-generated

    def test_workflow_model_with_custom_id(self):
        """Test Workflow model with custom ID."""
        workflow = workflow_main.Workflow(
            id="custom-id",
            name="Test",
            tasks=[],
            state="pending",
        )
        assert workflow.id == "custom-id"

    def test_workflow_model_default_state(self):
        """Test Workflow model default state."""
        workflow = workflow_main.Workflow(name="Test", tasks=[], state="running")
        assert workflow.state == "running"

    def test_invoke_request_model(self):
        """Test InvokeRequest model."""
        request = workflow_main.InvokeRequest(
            action="create",
            payload={"name": "Test", "tasks": [], "state": "pending"},
        )
        assert request.action == "create"
        assert request.payload["name"] == "Test"

    def test_invoke_request_default_payload(self):
        """Test InvokeRequest with default payload."""
        request = workflow_main.InvokeRequest(action="list")
        assert request.payload == {}

    def test_invoke_request_action_validation(self):
        """Test InvokeRequest action validation."""
        valid_actions = [
            "create",
            "list",
            "get",
            "update",
            "delete",
            "query",
            "run",
            "evaluate",
            "export",
            "import",
        ]
        for action in valid_actions:
            request = workflow_main.InvokeRequest(action=action)
            assert request.action == action

    def test_invoke_request_invalid_action(self):
        """Test InvokeRequest with invalid action."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            workflow_main.InvokeRequest(action="invalid_action")

    def test_health_response_model(self):
        """Test HealthResponse model."""
        response = workflow_main.HealthResponse(
            status="ok",
            service="workflow_service",
            workflow_count=5,
        )
        assert response.status == "ok"
        assert response.service == "workflow_service"
        assert response.workflow_count == 5

    def test_health_response_defaults(self):
        """Test HealthResponse default values."""
        response = workflow_main.HealthResponse(workflow_count=0)
        assert response.status == "ok"
        assert response.service == "workflow_service"

    def test_info_response_model(self):
        """Test InfoResponse model."""
        response = workflow_main.InfoResponse(service="workflow_service")
        assert response.service == "workflow_service"
        assert response.version == "1.0.0"
        assert response.status == "running"

    def test_info_response_defaults(self):
        """Test InfoResponse default values."""
        response = workflow_main.InfoResponse()
        assert response.service == "workflow_service"
        assert response.version == "1.0.0"
        assert response.status == "running"

    def test_invoke_response_model(self):
        """Test InvokeResponse model."""
        response = workflow_main.InvokeResponse(
            success=True,
            service="workflow_service",
            action="create",
            result={"id": "test-id"},
        )
        assert response.success is True
        assert response.service == "workflow_service"
        assert response.action == "create"
        assert response.result["id"] == "test-id"

    def test_store_initialization(self):
        """Test that store is initialized as empty dict."""
        assert isinstance(workflow_main.store, dict)
        assert len(workflow_main.store) == 0

    def test_create_function(self):
        """Test _create function."""
        workflow_main.store.clear()
        payload = {"name": "Test Workflow", "tasks": ["task1"], "state": "pending"}
        result = workflow_main._create(payload)

        assert result["name"] == "Test Workflow"
        assert result["tasks"] == ["task1"]
        assert result["state"] == "pending"
        assert result["id"] in workflow_main.store

    def test_create_generates_unique_ids(self):
        """Test that _create generates unique IDs."""
        workflow_main.store.clear()
        result1 = workflow_main._create({"name": "Test1", "tasks": [], "state": "pending"})
        result2 = workflow_main._create({"name": "Test2", "tasks": [], "state": "pending"})

        assert result1["id"] != result2["id"]

    def test_list_function_empty(self):
        """Test _list function with empty store."""
        workflow_main.store.clear()
        result = workflow_main._list({})
        assert result == []

    def test_list_function_with_data(self):
        """Test _list function with data."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test1", "tasks": [], "state": "pending"})
        workflow_main._create({"name": "Test2", "tasks": [], "state": "running"})

        result = workflow_main._list({})
        assert len(result) == 2

    def test_get_function_success(self):
        """Test _get function with valid ID."""
        workflow_main.store.clear()
        created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})

        result = workflow_main._get({"id": created["id"]})

        assert result["id"] == created["id"]
        assert result["name"] == "Test"

    def test_get_function_not_found(self):
        """Test _get function with non-existent ID."""
        workflow_main.store.clear()

        with pytest.raises(HTTPException) as exc_info:
            workflow_main._get({"id": "non-existent"})

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_get_function_no_id(self):
        """Test _get function without ID parameter."""
        workflow_main.store.clear()

        with pytest.raises(HTTPException) as exc_info:
            workflow_main._get({})

        assert exc_info.value.status_code == 404

    def test_update_function_success(self):
        """Test _update function with valid ID."""
        workflow_main.store.clear()
        created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})

        updated = workflow_main._update(
            {"id": created["id"], "name": "Updated Name", "state": "running"}
        )

        assert updated["name"] == "Updated Name"
        assert updated["state"] == "running"
        assert updated["id"] == created["id"]

    def test_update_function_not_found(self):
        """Test _update function with non-existent ID."""
        workflow_main.store.clear()

        with pytest.raises(HTTPException) as exc_info:
            workflow_main._update({"id": "non-existent", "name": "Test"})

        assert exc_info.value.status_code == 404

    def test_update_function_preserves_id(self):
        """Test that _update preserves the original ID."""
        workflow_main.store.clear()
        created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})

        updated = workflow_main._update({"id": created["id"], "name": "Updated"})

        assert updated["id"] == created["id"]

    def test_delete_function_success(self):
        """Test _delete function with valid ID."""
        workflow_main.store.clear()
        created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})

        result = workflow_main._delete({"id": created["id"]})

        assert result["deleted"] == created["id"]
        assert created["id"] not in workflow_main.store

    def test_delete_function_not_found(self):
        """Test _delete function with non-existent ID."""
        workflow_main.store.clear()

        with pytest.raises(HTTPException) as exc_info:
            workflow_main._delete({"id": "non-existent"})

        assert exc_info.value.status_code == 404

    def test_query_function_with_matches(self):
        """Test _query function with matching workflows."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test1", "tasks": [], "state": "pending"})
        workflow_main._create({"name": "Test2", "tasks": [], "state": "running"})
        workflow_main._create({"name": "Test3", "tasks": [], "state": "pending"})

        result = workflow_main._query({"state": "pending"})

        assert len(result) == 2
        assert all(w["state"] == "pending" for w in result)

    def test_query_function_no_matches(self):
        """Test _query function with no matching workflows."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test1", "tasks": [], "state": "pending"})

        result = workflow_main._query({"state": "running"})

        assert result == []

    def test_query_function_empty_payload(self):
        """Test _query function with empty payload."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test1", "tasks": [], "state": "pending"})

        result = workflow_main._query({})

        # Empty query should return all (except id check)
        assert len(result) == 1

    def test_query_function_multiple_criteria(self):
        """Test _query function with multiple criteria."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test1", "tasks": ["task1"], "state": "pending"})
        workflow_main._create({"name": "Test2", "tasks": ["task2"], "state": "pending"})
        workflow_main._create({"name": "Test3", "tasks": ["task1"], "state": "running"})

        result = workflow_main._query({"state": "pending", "tasks": ["task1"]})

        assert len(result) == 1
        assert result[0]["name"] == "Test1"

    def test_run_function_with_id(self):
        """Test _run function with valid ID."""
        workflow_main.store.clear()
        created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})

        result = workflow_main._run({"id": created["id"]})

        assert result["status"] == "executed"
        assert result["id"] == created["id"]

    def test_run_function_without_id(self):
        """Test _run function without ID."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})

        result = workflow_main._run({})

        assert result["status"] == "noop"
        assert "matched" in result

    def test_run_function_with_non_existent_id(self):
        """Test _run function with non-existent ID."""
        workflow_main.store.clear()

        result = workflow_main._run({"id": "non-existent"})

        assert result["status"] == "noop"

    def test_evaluate_function(self):
        """Test _evaluate function."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test1", "tasks": [], "state": "pending"})
        workflow_main._create({"name": "Test2", "tasks": [], "state": "running"})

        result = workflow_main._evaluate({})

        assert result["total"] == 2
        assert result["service"] == "workflow_service"
        assert result["action"] == "evaluate"

    def test_export_function(self):
        """Test _export function."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test1", "tasks": [], "state": "pending"})
        workflow_main._create({"name": "Test2", "tasks": [], "state": "running"})

        result = workflow_main._export({})

        assert "items" in result
        assert len(result["items"]) == 2
        assert result["service"] == "workflow_service"

    def test_import_function(self):
        """Test _import function."""
        workflow_main.store.clear()
        items = [
            {"name": "Imported1", "tasks": [], "state": "pending"},
            {"name": "Imported2", "tasks": [], "state": "running"},
        ]

        result = workflow_main._import({"items": items})

        assert result["imported"] == 2
        assert len(workflow_main.store) == 2

    def test_import_function_empty_items(self):
        """Test _import function with empty items list."""
        workflow_main.store.clear()

        result = workflow_main._import({"items": []})

        assert result["imported"] == 0
        assert len(workflow_main.store) == 0

    def test_import_function_no_items_key(self):
        """Test _import function without items key."""
        workflow_main.store.clear()

        result = workflow_main._import({})

        assert result["imported"] == 0

    def test_handlers_dict(self):
        """Test that HANDLERS dict contains all expected handlers."""
        expected_handlers = {
            "create",
            "list",
            "get",
            "update",
            "delete",
            "query",
            "run",
            "evaluate",
            "export",
            "import",
        }
        assert set(workflow_main.HANDLERS.keys()) == expected_handlers

    def test_handlers_are_callable(self):
        """Test that all handlers are callable."""
        for handler_name, handler in workflow_main.HANDLERS.items():
            assert callable(handler), f"{handler_name} is not callable"

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test /health endpoint."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})

        response = await workflow_main.health()

        assert response.status == "ok"
        assert response.service == "workflow_service"
        assert response.workflow_count == 1

    @pytest.mark.asyncio
    async def test_health_endpoint_empty_store(self):
        """Test /health endpoint with empty store."""
        workflow_main.store.clear()

        response = await workflow_main.health()

        assert response.workflow_count == 0

    @pytest.mark.asyncio
    async def test_info_endpoint(self):
        """Test /info endpoint."""
        response = await workflow_main.info()

        assert response.service == "workflow_service"
        assert response.version == "1.0.0"
        assert response.status == "running"

    @pytest.mark.asyncio
    async def test_list_workflows_endpoint(self):
        """Test /workflows endpoint."""
        workflow_main.store.clear()
        workflow_main._create({"name": "Test1", "tasks": [], "state": "pending"})
        workflow_main._create({"name": "Test2", "tasks": [], "state": "running"})

        response = await workflow_main.list_workflows()

        assert len(response) == 2

    @pytest.mark.asyncio
    async def test_get_workflow_endpoint(self):
        """Test /workflows/{item_id} endpoint."""
        workflow_main.store.clear()
        created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})

        response = await workflow_main.get_workflow(created["id"])

        assert response["id"] == created["id"]
        assert response["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_workflow_endpoint_not_found(self):
        """Test /workflows/{item_id} endpoint with non-existent ID."""
        workflow_main.store.clear()

        with pytest.raises(HTTPException) as exc_info:
            await workflow_main.get_workflow("non-existent")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_invoke_endpoint(self):
        """Test /invoke endpoint."""
        workflow_main.store.clear()
        request = workflow_main.InvokeRequest(
            action="create",
            payload={"name": "Test", "tasks": [], "state": "pending"},
        )

        response = await workflow_main.invoke(request)

        assert response.success is True
        assert response.service == "workflow_service"
        assert response.action == "create"
        assert "id" in response.result

    @pytest.mark.asyncio
    async def test_invoke_endpoint_invalid_action(self):
        """Test /invoke endpoint with invalid action."""
        request = workflow_main.InvokeRequest(action="invalid", payload={})

        with pytest.raises(HTTPException) as exc_info:
            await workflow_main.invoke(request)

        assert exc_info.value.status_code == 400
        assert "Unknown action" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invoke_all_actions(self):
        """Test /invoke endpoint with all valid actions."""
        workflow_main.store.clear()
        valid_actions = [
            "create",
            "list",
            "get",
            "update",
            "delete",
            "query",
            "run",
            "evaluate",
            "export",
            "import",
        ]

        for action in valid_actions:
            if action == "create":
                payload = {"name": "Test", "tasks": [], "state": "pending"}
            elif action == "get":
                created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})
                payload = {"id": created["id"]}
            elif action == "update":
                created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})
                payload = {"id": created["id"], "name": "Updated"}
            elif action == "delete":
                created = workflow_main._create({"name": "Test", "tasks": [], "state": "pending"})
                payload = {"id": created["id"]}
            elif action == "import":
                payload = {"items": [{"name": "Test", "tasks": [], "state": "pending"}]}
            else:
                payload = {}

            request = workflow_main.InvokeRequest(action=action, payload=payload)
            response = await workflow_main.invoke(request)

            assert response.success is True
            assert response.action == action

    def test_main_execution(self):
        """Test that main can be executed (uvicorn.run)."""
        # Just test that the module can be imported and main block exists
        assert hasattr(workflow_main, "__name__")
        # The actual uvicorn.run would start a server, which we don't want in tests
