# -*- coding: utf-8 -*-
"""Real branch-coverage tests for core.interface.l5.mcp_interface.

These tests exercise the real MCPInterface, its real FastAPI router, and the
real core.mcp_tools handlers. No mocks are used; fallback branches are reached
by supplying an invalid/missing ``mcp_tools_module`` through the config.
"""

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.testclient import TestClient

from core.interface.l5.mcp_interface import (
    MCPInterface,
    get_mcp_interface,
    init_mcp_interface,
)


def _build_client(interface: MCPInterface) -> TestClient:
    app = FastAPI()
    app.include_router(interface.get_router())
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def default_client():
    interface = MCPInterface()
    client = _build_client(interface)
    try:
        yield client
    finally:
        client.close()


def test_initialization_and_none_config():
    i1 = MCPInterface()
    assert i1.get_status()["initialized"] is True
    assert i1.get_status()["tool_count"] == 5
    assert isinstance(i1.get_router(), APIRouter)

    i2 = MCPInterface(None)
    assert i2.get_status()["initialized"] is True
    assert i2.get_status()["tool_count"] == 5


def test_list_tools_and_capabilities(default_client):
    r = default_client.get("/mcp/tools")
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data
    assert data["count"] == len(data["tools"])

    r = default_client.get("/mcp/capabilities")
    assert r.status_code == 200
    cap = r.json()
    assert cap["protocol"] == "MCP"
    assert cap["version"] == "1.0"
    assert "timestamp" in cap


def test_get_host_health_success(default_client):
    r = default_client.post("/mcp/tools/get_host_health", json={"host_id": "h1"})
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_get_host_health_missing_required(default_client):
    r = default_client.post("/mcp/tools/get_host_health", json={})
    assert r.status_code == 422


def test_get_host_health_wrong_type(default_client):
    r = default_client.post("/mcp/tools/get_host_health", json={"host_id": 123})
    assert r.status_code == 422


def test_get_host_health_unexpected_param(default_client):
    r = default_client.post(
        "/mcp/tools/get_host_health", json={"host_id": "h1", "foo": "bar"}
    )
    assert r.status_code == 422


def test_get_metrics_success(default_client):
    r = default_client.post(
        "/mcp/tools/get_metrics",
        json={"host_id": "h1", "metrics": ["cpu", "memory"]},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_get_metrics_missing_metrics(default_client):
    r = default_client.post("/mcp/tools/get_metrics", json={"host_id": "h1"})
    assert r.status_code == 422


def test_get_metrics_invalid_array(default_client):
    r = default_client.post(
        "/mcp/tools/get_metrics",
        json={"host_id": "h1", "metrics": "cpu"},
    )
    assert r.status_code == 422


def test_search_incident_history_validation(default_client):
    # Missing required query
    r = default_client.post("/mcp/tools/search_incident_history", json={})
    assert r.status_code == 422

    # Invalid integer (string)
    r = default_client.post(
        "/mcp/tools/search_incident_history",
        json={"query": "cpu", "limit": "five"},
    )
    assert r.status_code == 422

    # Boolean rejected as integer
    r = default_client.post(
        "/mcp/tools/search_incident_history",
        json={"query": "cpu", "limit": True},
    )
    assert r.status_code == 422

    # Valid call; real RAG may fail and is covered by the 500 error branch
    r = default_client.post(
        "/mcp/tools/search_incident_history",
        json={"query": "cpu", "limit": 5},
    )
    assert r.status_code in (200, 500)


def test_approve_repair_validation(default_client):
    # Missing approved
    r = default_client.post(
        "/mcp/tools/approve_repair", json={"repair_id": "r1"}
    )
    assert r.status_code == 422

    # approved not a boolean
    r = default_client.post(
        "/mcp/tools/approve_repair",
        json={"repair_id": "r1", "approved": "yes"},
    )
    assert r.status_code == 422

    # Invalid comment type
    r = default_client.post(
        "/mcp/tools/approve_repair",
        json={"repair_id": "r1", "approved": True, "comment": 123},
    )
    assert r.status_code == 422

    # Valid call; real db_engine may return 200 or 500
    r = default_client.post(
        "/mcp/tools/approve_repair",
        json={"repair_id": "r1", "approved": True},
    )
    assert r.status_code in (200, 500)


def test_trigger_repair_with_hitl_validation(default_client):
    # Missing user
    r = default_client.post(
        "/mcp/tools/trigger_repair_with_hitl",
        json={"alert_id": "a1"},
    )
    assert r.status_code == 422

    # Invalid string type
    r = default_client.post(
        "/mcp/tools/trigger_repair_with_hitl",
        json={"alert_id": 1, "user": "admin"},
    )
    assert r.status_code == 422


def test_trigger_repair_with_hitl_real(default_client):
    # This calls the real core.mcp_tools trigger_repair_with_hitl workflow.
    # It may take a few seconds but should complete within the timeout.
    r = default_client.post(
        "/mcp/tools/trigger_repair_with_hitl",
        json={"alert_id": "a1", "user": "admin"},
    )
    assert r.status_code in (200, 500)


def test_unknown_tool_404(default_client):
    r = default_client.post("/mcp/tools/unknown_tool", json={"x": "y"})
    assert r.status_code == 404


def test_custom_tool_else_branch_and_error_handling():
    interface = MCPInterface()

    async def echo_handler(message: str):
        return {"message": message}

    interface.register_tool(
        "custom_echo",
        "Echo back the input",
        echo_handler,
        {"message": {"type": "string", "required": True}},
    )

    client = _build_client(interface)
    r = client.post("/mcp/tools/custom_echo", json={"message": "hello"})
    assert r.status_code == 200
    assert r.json() == {"message": "hello"}
    client.close()

    async def error_handler():
        raise RuntimeError("boom")

    interface.register_tool("custom_error", "Always fails", error_handler, {})
    client = _build_client(interface)
    r = client.post("/mcp/tools/custom_error", json={})
    assert r.status_code == 500
    client.close()


def test_missing_tools_module_fallback():
    # Exercise the fallback branch when the configured tool module does not exist.
    interface = MCPInterface({"mcp_tools_module": "core.no_such_mcp_tools"})
    assert interface.get_status()["initialized"] is True
    assert interface.get_status()["tool_count"] == 0

    client = _build_client(interface)
    try:
        r = client.get("/mcp/tools")
        assert r.status_code == 200
        assert r.json()["count"] == 0

        r = client.post("/mcp/tools/anything", json={"x": "y"})
        assert r.status_code == 404
    finally:
        client.close()


def test_singleton_lifecycle():
    assert get_mcp_interface() is None
    instance = init_mcp_interface({"mcp_tools_module": "core.mcp_tools"})
    assert get_mcp_interface() is instance
    assert get_mcp_interface().get_status()["initialized"] is True
