# -*- coding: utf-8 -*-
"""Tests for main.py module."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from extensions.addons.ai_plus.knowledge_graph_service.main import (
    _create,
    _delete,
    _evaluate,
    _export,
    _get,
    _import,
    _list,
    _query,
    _run,
    _update,
    app,
    store,
)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the store before each test."""
    store.clear()
    yield
    store.clear()


class TestMainModule:
    """Test cases for main.py module functions."""

    def test_create(self):
        """Test _create function."""
        payload = {"id": "test1", "label": "Test Node", "properties": {"key": "value"}}
        result = _create(payload)

        assert result["id"] == "test1"
        assert result["label"] == "Test Node"
        assert result["properties"] == {"key": "value"}
        assert "test1" in store

    def test_create_with_generated_id(self):
        """Test _create with auto-generated ID."""
        payload = {"label": "Test Node", "properties": {}}
        result = _create(payload)

        assert "id" in result
        assert result["label"] == "Test Node"
        assert result["id"] in store

    def test_list_empty(self):
        """Test _list with empty store."""
        result = _list({})

        assert result == []

    def test_list_with_items(self):
        """Test _list with items in store."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})
        _create({"id": "node2", "label": "Node 2", "properties": {}})

        result = _list({})

        assert len(result) == 2
        assert result[0]["id"] == "node1"
        assert result[1]["id"] == "node2"

    def test_get_existing(self):
        """Test _get with existing node."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        result = _get({"id": "node1"})

        assert result["id"] == "node1"
        assert result["label"] == "Node 1"

    def test_get_nonexistent(self):
        """Test _get with nonexistent node."""
        with pytest.raises(Exception) as exc_info:
            _get({"id": "nonexistent"})
        assert "node not found" in str(exc_info.value)

    def test_get_without_id(self):
        """Test _get without providing ID."""
        with pytest.raises(Exception) as exc_info:
            _get({})
        assert "node not found" in str(exc_info.value)

    def test_update_existing(self):
        """Test _update with existing node."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        result = _update({"id": "node1", "label": "Updated Node", "new_field": "value"})

        assert result["id"] == "node1"
        assert result["label"] == "Updated Node"
        assert result["new_field"] == "value"
        assert store["node1"].label == "Updated Node"

    def test_update_nonexistent(self):
        """Test _update with nonexistent node."""
        with pytest.raises(Exception) as exc_info:
            _update({"id": "nonexistent", "label": "Updated"})
        assert "node not found" in str(exc_info.value)

    def test_update_without_id(self):
        """Test _update without providing ID."""
        with pytest.raises(Exception) as exc_info:
            _update({"label": "Updated"})
        assert "node not found" in str(exc_info.value)

    def test_delete_existing(self):
        """Test _delete with existing node."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        result = _delete({"id": "node1"})

        assert result["deleted"] == "node1"
        assert "node1" not in store

    def test_delete_nonexistent(self):
        """Test _delete with nonexistent node."""
        with pytest.raises(Exception) as exc_info:
            _delete({"id": "nonexistent"})
        assert "node not found" in str(exc_info.value)

    def test_delete_without_id(self):
        """Test _delete without providing ID."""
        with pytest.raises(Exception) as exc_info:
            _delete({})
        assert "node not found" in str(exc_info.value)

    def test_query_with_filters(self):
        """Test _query with filters."""
        _create({"id": "node1", "label": "Node 1", "properties": {"type": "A"}})
        _create({"id": "node2", "label": "Node 2", "properties": {"type": "B"}})
        _create({"id": "node3", "label": "Node 3", "properties": {"type": "A"}})

        result = _query({"properties": {"type": "A"}})

        assert len(result) == 2
        assert all(item["properties"]["type"] == "A" for item in result)

    def test_query_without_filters(self):
        """Test _query without filters."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})
        _create({"id": "node2", "label": "Node 2", "properties": {}})

        result = _query({})

        assert len(result) == 2

    def test_query_no_matches(self):
        """Test _query with no matches."""
        _create({"id": "node1", "label": "Node 1", "properties": {"type": "A"}})

        result = _query({"properties": {"type": "B"}})

        assert len(result) == 0

    def test_run_with_existing_id(self):
        """Test _run with existing node ID."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        result = _run({"id": "node1"})

        assert result["status"] == "executed"
        assert result["id"] == "node1"

    def test_run_without_id(self):
        """Test _run without node ID."""
        result = _run({})

        assert result["status"] == "noop"
        assert "matched" in result

    def test_run_with_nonexistent_id(self):
        """Test _run with nonexistent node ID."""
        result = _run({"id": "nonexistent"})

        assert result["status"] == "noop"

    def test_evaluate(self):
        """Test _evaluate function."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})
        _create({"id": "node2", "label": "Node 2", "properties": {}})

        result = _evaluate({})

        assert result["total"] == 2
        assert result["action"] == "evaluate"

    def test_export(self):
        """Test _export function."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})
        _create({"id": "node2", "label": "Node 2", "properties": {}})

        result = _export({})

        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == "node1"
        assert result["items"][1]["id"] == "node2"

    def test_export_empty(self):
        """Test _export with empty store."""
        result = _export({})

        assert result["items"] == []

    def test_import(self):
        """Test _import function."""
        items = [
            {"id": "node1", "label": "Node 1", "properties": {}},
            {"id": "node2", "label": "Node 2", "properties": {}},
        ]

        result = _import({"items": items})

        assert result["imported"] == 2
        assert "node1" in store
        assert "node2" in store

    def test_import_empty(self):
        """Test _import with empty items."""
        result = _import({"items": []})

        assert result["imported"] == 0

    def test_import_without_items(self):
        """Test _import without items key."""
        result = _import({})

        assert result["imported"] == 0


class TestMainAPI:
    """Test cases for main.py FastAPI endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "node_count" in data

    def test_info_endpoint(self, client):
        """Test /info endpoint."""
        response = client.get("/info")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "knowledge_graph_service"
        assert data["status"] == "running"

    def test_list_nodes_endpoint(self, client):
        """Test /nodes endpoint."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        response = client.get("/nodes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "node1"

    def test_get_node_endpoint(self, client):
        """Test /nodes/{item_id} endpoint."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        response = client.get("/nodes/node1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "node1"

    def test_get_node_endpoint_not_found(self, client):
        """Test /nodes/{item_id} endpoint with nonexistent node."""
        response = client.get("/nodes/nonexistent")

        assert response.status_code == 404

    def test_invoke_endpoint_create(self, client):
        """Test /invoke endpoint with create action."""
        payload = {
            "action": "create",
            "payload": {"id": "node1", "label": "Node 1", "properties": {}},
        }

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "create"
        assert data["result"]["id"] == "node1"

    def test_invoke_endpoint_list(self, client):
        """Test /invoke endpoint with list action."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        payload = {"action": "list", "payload": {}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["result"]) == 1

    def test_invoke_endpoint_invalid_action(self, client):
        """Test /invoke endpoint with invalid action."""
        payload = {"action": "invalid", "payload": {}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 400

    def test_invoke_endpoint_get(self, client):
        """Test /invoke endpoint with get action."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        payload = {"action": "get", "payload": {"id": "node1"}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["id"] == "node1"

    def test_invoke_endpoint_update(self, client):
        """Test /invoke endpoint with update action."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        payload = {
            "action": "update",
            "payload": {"id": "node1", "label": "Updated Node"},
        }

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["label"] == "Updated Node"

    def test_invoke_endpoint_delete(self, client):
        """Test /invoke endpoint with delete action."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        payload = {"action": "delete", "payload": {"id": "node1"}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["deleted"] == "node1"

    def test_invoke_endpoint_query(self, client):
        """Test /invoke endpoint with query action."""
        _create({"id": "node1", "label": "Node 1", "properties": {"type": "A"}})
        _create({"id": "node2", "label": "Node 2", "properties": {"type": "B"}})

        payload = {"action": "query", "payload": {"properties": {"type": "A"}}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["result"]) == 1

    def test_invoke_endpoint_run(self, client):
        """Test /invoke endpoint with run action."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        payload = {"action": "run", "payload": {"id": "node1"}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["status"] == "executed"

    def test_invoke_endpoint_evaluate(self, client):
        """Test /invoke endpoint with evaluate action."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        payload = {"action": "evaluate", "payload": {}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["total"] == 1

    def test_invoke_endpoint_export(self, client):
        """Test /invoke endpoint with export action."""
        _create({"id": "node1", "label": "Node 1", "properties": {}})

        payload = {"action": "export", "payload": {}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["result"]["items"]) == 1

    def test_invoke_endpoint_import(self, client):
        """Test /invoke endpoint with import action."""
        items = [{"id": "node1", "label": "Node 1", "properties": {}}]

        payload = {"action": "import", "payload": {"items": items}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["imported"] == 1
