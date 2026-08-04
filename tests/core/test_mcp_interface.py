# -*- coding: utf-8 -*-
"""MCP L5 Interface Router Tests"""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.interface.l5.mcp_interface import MCPInterface


@pytest.fixture
def client():
    interface = MCPInterface({})
    interface._tools = {
        "get_host_health": {
            "name": "get_host_health",
            "description": "Get health status of a specific host",
            "handler": AsyncMock(return_value={"status": "healthy"}),
            "parameters": {"host_id": {"type": "string", "required": True}},
        },
        "echo": {
            "name": "echo",
            "description": "Echo tool",
            "handler": AsyncMock(return_value={"echo": "ok"}),
            "parameters": {"message": {"type": "string", "required": True}},
        },
    }
    app = FastAPI()
    app.include_router(interface.get_router())
    return TestClient(app)


class TestMcpInterface:
    def test_list_tools(self, client):
        response = client.get("/mcp/tools")
        assert response.status_code == 200
        assert response.json()["count"] == 2

    def test_execute_known_tool(self, client):
        response = client.post("/mcp/tools/get_host_health", json={"host_id": "host-1"})
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_execute_unknown_tool(self, client):
        response = client.post("/mcp/tools/unknown", json={})
        assert response.status_code == 404

    def test_execute_tool_missing_param(self, client):
        response = client.post("/mcp/tools/get_host_health", json={})
        assert response.status_code == 422

    def test_execute_tool_unexpected_param(self, client):
        response = client.post("/mcp/tools/get_host_health", json={"host_id": "1", "extra": "x"})
        assert response.status_code == 422

    def test_get_capabilities(self, client):
        response = client.get("/mcp/capabilities")
        assert response.status_code == 200
        assert response.json()["protocol"] == "MCP"

    def test_get_status(self):
        interface = MCPInterface({})
        interface._tools = {"a": {}}
        status = interface.get_status()
        assert status["initialized"] is True
        assert status["tool_count"] == 1

    def test_register_tool(self):
        interface = MCPInterface({})
        interface.register_tool("new_tool", "New tool", AsyncMock(), {})
        assert "new_tool" in interface._tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
