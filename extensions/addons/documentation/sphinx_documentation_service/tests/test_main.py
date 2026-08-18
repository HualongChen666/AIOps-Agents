# -*- coding: utf-8 -*-
"""Tests for main.py - Real business logic for the sphinx_documentation_service."""

import pytest
from fastapi import HTTPException

from extensions.addons.documentation.sphinx_documentation_service.main import (
    _create,
    _list,
    _get,
    _update,
    _delete,
    _query,
    _run,
    _evaluate,
    _export,
    _import,
    store,
    DocPage,
    InvokeRequest,
    HealthResponse,
    InfoResponse,
    InvokeResponse,
    HANDLERS,
    SERVICE_NAME,
    PORT,
)


class TestDocPage:
    """Test suite for DocPage model."""

    def test_default_id(self):
        """Test that default ID is generated."""
        page = DocPage(title="Test", content="Content")
        assert page.id is not None
        assert len(page.id) == 8

    def test_custom_id(self):
        """Test custom ID."""
        page = DocPage(id="custom123", title="Test", content="Content")
        assert page.id == "custom123"

    def test_title(self):
        """Test title field."""
        page = DocPage(title="Test Title", content="Content")
        assert page.title == "Test Title"

    def test_content(self):
        """Test content field."""
        page = DocPage(title="Test", content="Test Content")
        assert page.content == "Test Content"

    def test_default_tags(self):
        """Test default tags is empty list."""
        page = DocPage(title="Test", content="Content")
        assert page.tags == []

    def test_custom_tags(self):
        """Test custom tags."""
        page = DocPage(title="Test", content="Content", tags=["tag1", "tag2"])
        assert page.tags == ["tag1", "tag2"]

    def test_unicode_title(self):
        """Test unicode title."""
        page = DocPage(title="测试标题", content="Content")
        assert page.title == "测试标题"

    def test_unicode_content(self):
        """Test unicode content."""
        page = DocPage(title="Test", content="测试内容")
        assert page.content == "测试内容"

    def test_unicode_tags(self):
        """Test unicode tags."""
        page = DocPage(title="Test", content="Content", tags=["标签1", "标签2"])
        assert page.tags == ["标签1", "标签2"]

    def test_empty_title(self):
        """Test empty title."""
        page = DocPage(title="", content="Content")
        assert page.title == ""

    def test_empty_content(self):
        """Test empty content."""
        page = DocPage(title="Test", content="")
        assert page.content == ""

    def test_model_dump(self):
        """Test model_dump method."""
        page = DocPage(id="test123", title="Test", content="Content", tags=["tag1"])
        data = page.model_dump()
        assert data["id"] == "test123"
        assert data["title"] == "Test"
        assert data["content"] == "Content"
        assert data["tags"] == ["tag1"]


class TestInvokeRequest:
    """Test suite for InvokeRequest model."""

    def test_valid_actions(self):
        """Test all valid actions."""
        valid_actions = ["create", "list", "get", "update", "delete", "query", "run", "evaluate", "export", "import"]
        for action in valid_actions:
            request = InvokeRequest(action=action)
            assert request.action == action

    def test_default_payload(self):
        """Test default payload is empty dict."""
        request = InvokeRequest(action="create")
        assert request.payload == {}

    def test_custom_payload(self):
        """Test custom payload."""
        request = InvokeRequest(action="create", payload={"key": "value"})
        assert request.payload == {"key": "value"}

    def test_invalid_action(self):
        """Test invalid action raises validation error."""
        with pytest.raises(Exception):  # pydantic validation error
            InvokeRequest(action="invalid_action")


class TestHandlers:
    """Test suite for handler functions."""

    def setup_method(self):
        """Clear store before each test."""
        store.clear()

    def test_create(self):
        """Test _create function."""
        payload = {"title": "Test", "content": "Content", "tags": ["tag1"]}
        result = _create(payload)
        assert result["title"] == "Test"
        assert result["content"] == "Content"
        assert result["tags"] == ["tag1"]
        assert result["id"] in store

    def test_create_with_id(self):
        """Test _create with custom ID."""
        payload = {"id": "custom123", "title": "Test", "content": "Content"}
        result = _create(payload)
        assert result["id"] == "custom123"
        assert "custom123" in store

    def test_create_without_tags(self):
        """Test _create without tags."""
        payload = {"title": "Test", "content": "Content"}
        result = _create(payload)
        assert result["tags"] == []

    def test_list_empty(self):
        """Test _list with empty store."""
        result = _list({})
        assert result == []

    def test_list_with_items(self):
        """Test _list with items in store."""
        _create({"title": "Test1", "content": "Content1"})
        _create({"title": "Test2", "content": "Content2"})
        result = _list({})
        assert len(result) == 2

    def test_get_existing(self):
        """Test _get with existing item."""
        created = _create({"title": "Test", "content": "Content"})
        result = _get({"id": created["id"]})
        assert result["id"] == created["id"]
        assert result["title"] == "Test"

    def test_get_nonexistent(self):
        """Test _get with nonexistent item raises HTTPException."""
        with pytest.raises(HTTPException, match="docpage not found"):
            _get({"id": "nonexistent"})

    def test_get_without_id(self):
        """Test _get without ID raises HTTPException."""
        with pytest.raises(HTTPException, match="docpage not found"):
            _get({})

    def test_update_existing(self):
        """Test _update with existing item."""
        created = _create({"title": "Test", "content": "Content"})
        result = _update({"id": created["id"], "title": "Updated"})
        assert result["title"] == "Updated"
        assert result["content"] == "Content"

    def test_update_nonexistent(self):
        """Test _update with nonexistent item raises HTTPException."""
        with pytest.raises(HTTPException, match="docpage not found"):
            _update({"id": "nonexistent", "title": "Updated"})

    def test_update_without_id(self):
        """Test _update without ID raises HTTPException."""
        with pytest.raises(HTTPException, match="docpage not found"):
            _update({"title": "Updated"})

    def test_update_multiple_fields(self):
        """Test _update with multiple fields."""
        created = _create({"title": "Test", "content": "Content", "tags": ["tag1"]})
        result = _update(
            {"id": created["id"], "title": "Updated", "content": "New content", "tags": ["tag2"]}
        )
        assert result["title"] == "Updated"
        assert result["content"] == "New content"
        assert result["tags"] == ["tag2"]

    def test_delete_existing(self):
        """Test _delete with existing item."""
        created = _create({"title": "Test", "content": "Content"})
        result = _delete({"id": created["id"]})
        assert result["deleted"] == created["id"]
        assert created["id"] not in store

    def test_delete_nonexistent(self):
        """Test _delete with nonexistent item raises HTTPException."""
        with pytest.raises(HTTPException, match="docpage not found"):
            _delete({"id": "nonexistent"})

    def test_delete_without_id(self):
        """Test _delete without ID raises HTTPException."""
        with pytest.raises(HTTPException, match="docpage not found"):
            _delete({})

    def test_query_matching(self):
        """Test _query with matching criteria."""
        _create({"title": "Test1", "content": "Content1", "tags": ["tag1"]})
        _create({"title": "Test2", "content": "Content2", "tags": ["tag2"]})
        result = _query({"tags": ["tag1"]})
        assert len(result) == 1
        assert result[0]["tags"] == ["tag1"]

    def test_query_no_match(self):
        """Test _query with no matching criteria."""
        _create({"title": "Test1", "content": "Content1", "tags": ["tag1"]})
        result = _query({"tags": ["nonexistent"]})
        assert result == []

    def test_query_empty_criteria(self):
        """Test _query with empty criteria returns all."""
        _create({"title": "Test1", "content": "Content1"})
        _create({"title": "Test2", "content": "Content2"})
        result = _query({})
        assert len(result) == 2

    def test_query_multiple_criteria(self):
        """Test _query with multiple criteria."""
        _create({"title": "Test1", "content": "Content1", "tags": ["tag1"]})
        _create({"title": "Test2", "content": "Content2", "tags": ["tag2"]})
        result = _query({"title": "Test1", "tags": ["tag1"]})
        assert len(result) == 1
        assert result[0]["title"] == "Test1"

    def test_run_with_id(self):
        """Test _run with valid ID."""
        created = _create({"title": "Test", "content": "Content"})
        result = _run({"id": created["id"]})
        assert result["status"] == "executed"
        assert result["id"] == created["id"]

    def test_run_without_id(self):
        """Test _run without ID."""
        result = _run({})
        assert result["status"] == "noop"
        assert "matched" in result

    def test_run_with_nonexistent_id(self):
        """Test _run with nonexistent ID."""
        result = _run({"id": "nonexistent"})
        assert result["status"] == "noop"

    def test_evaluate(self):
        """Test _evaluate function."""
        _create({"title": "Test1", "content": "Content1"})
        _create({"title": "Test2", "content": "Content2"})
        result = _evaluate({})
        assert result["total"] == 2
        assert result["service"] == SERVICE_NAME

    def test_evaluate_empty(self):
        """Test _evaluate with empty store."""
        result = _evaluate({})
        assert result["total"] == 0

    def test_export(self):
        """Test _export function."""
        _create({"title": "Test1", "content": "Content1"})
        _create({"title": "Test2", "content": "Content2"})
        result = _export({})
        assert len(result["items"]) == 2
        assert result["service"] == SERVICE_NAME

    def test_export_empty(self):
        """Test _export with empty store."""
        result = _export({})
        assert result["items"] == []

    def test_import(self):
        """Test _import function."""
        items = [
            {"id": "item1", "title": "Test1", "content": "Content1"},
            {"id": "item2", "title": "Test2", "content": "Content2"},
        ]
        result = _import({"items": items})
        assert result["imported"] == 2
        assert "item1" in store
        assert "item2" in store

    def test_import_empty(self):
        """Test _import with empty items."""
        result = _import({"items": []})
        assert result["imported"] == 0

    def test_import_without_items(self):
        """Test _import without items key."""
        result = _import({})
        assert result["imported"] == 0

    def test_import_overwrites(self):
        """Test that _import overwrites existing items."""
        _create({"id": "item1", "title": "Original", "content": "Original"})
        items = [{"id": "item1", "title": "Updated", "content": "Updated"}]
        result = _import({"items": items})
        assert result["imported"] == 1
        assert store["item1"].title == "Updated"


class TestHandlersIntegration:
    """Integration tests for handlers."""

    def setup_method(self):
        """Clear store before each test."""
        store.clear()

    def test_full_crud_cycle(self):
        """Test complete CRUD cycle."""
        # Create
        created = _create({"title": "Test", "content": "Content"})
        item_id = created["id"]

        # Read
        read = _get({"id": item_id})
        assert read["title"] == "Test"

        # Update
        updated = _update({"id": item_id, "title": "Updated"})
        assert updated["title"] == "Updated"

        # Delete
        deleted = _delete({"id": item_id})
        assert deleted["deleted"] == item_id

        # Verify deletion
        with pytest.raises(HTTPException):
            _get({"id": item_id})

    def test_query_after_multiple_creates(self):
        """Test query after creating multiple items."""
        _create({"title": "Test1", "content": "Content1", "tags": ["tag1"]})
        _create({"title": "Test2", "content": "Content2", "tags": ["tag2"]})
        _create({"title": "Test3", "content": "Content3", "tags": ["tag1"]})

        result = _query({"tags": ["tag1"]})
        assert len(result) == 2

    def test_export_import_roundtrip(self):
        """Test export and import roundtrip."""
        _create({"title": "Test1", "content": "Content1"})
        _create({"title": "Test2", "content": "Content2"})

        exported = _export({})
        store.clear()

        imported = _import({"items": exported["items"]})
        assert imported["imported"] == 2

        result = _list({})
        assert len(result) == 2


class TestConstants:
    """Test suite for constants."""

    def test_service_name(self):
        """Test SERVICE_NAME constant."""
        assert SERVICE_NAME == "sphinx_documentation_service"

    def test_port_default(self):
        """Test PORT default value."""
        assert PORT == 8000

    def test_handlers_dict(self):
        """Test HANDLERS dict contains all handlers."""
        expected_handlers = [
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
        for handler in expected_handlers:
            assert handler in HANDLERS
            assert callable(HANDLERS[handler])


class TestStore:
    """Test suite for store."""

    def setup_method(self):
        """Clear store before each test."""
        store.clear()

    def test_store_is_dict(self):
        """Test that store is a dict."""
        assert isinstance(store, dict)

    def test_store_persistence_across_handlers(self):
        """Test that store persists across handler calls."""
        created = _create({"title": "Test", "content": "Content"})
        item_id = created["id"]
        read = _get({"id": item_id})
        assert read["id"] == item_id

    def test_store_clear(self):
        """Test clearing store."""
        _create({"title": "Test", "content": "Content"})
        assert len(store) > 0
        store.clear()
        assert len(store) == 0


class TestResponseModels:
    """Test suite for response models."""

    def test_health_response(self):
        """Test HealthResponse model."""
        response = HealthResponse(status="ok", service=SERVICE_NAME, docpage_count=5)
        assert response.status == "ok"
        assert response.service == SERVICE_NAME
        assert response.docpage_count == 5

    def test_info_response(self):
        """Test InfoResponse model."""
        response = InfoResponse(service=SERVICE_NAME)
        assert response.service == SERVICE_NAME
        assert response.version == "1.0.0"
        assert response.status == "running"

    def test_invoke_response(self):
        """Test InvokeResponse model."""
        response = InvokeResponse(
            success=True, service=SERVICE_NAME, action="create", result={"id": "123"}
        )
        assert response.success is True
        assert response.service == SERVICE_NAME
        assert response.action == "create"
        assert response.result == {"id": "123"}

    def test_health_response_defaults(self):
        """Test HealthResponse default values."""
        response = HealthResponse(service=SERVICE_NAME, docpage_count=0)
        assert response.status == "ok"
        assert response.service == SERVICE_NAME
        assert response.docpage_count == 0

    def test_info_response_custom_version(self):
        """Test InfoResponse with custom version."""
        response = InfoResponse(service=SERVICE_NAME, version="2.0.0")
        assert response.version == "2.0.0"

    def test_invoke_response_false(self):
        """Test InvokeResponse with success=False."""
        response = InvokeResponse(
            success=False, service=SERVICE_NAME, action="create", result={}
        )
        assert response.success is False
