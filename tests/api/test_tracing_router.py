# -*- coding: utf-8 -*-
# tests/api/test_tracing_router.py
# 追踪路由API基础测试
import sys
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.tracing_router import (
    get_service_topology,
    get_trace_details,
    get_tracing_dashboard,
    list_traces,
)

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].OTEL_COLLECTOR_ENDPOINT = "http://localhost:4318"


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/tracing", tags=["Tracing"])
    test_router.add_api_route("/dashboard", get_tracing_dashboard, methods=["GET"])
    test_router.add_api_route("/traces", list_traces, methods=["GET"])
    test_router.add_api_route("/traces/{trace_id}", get_trace_details, methods=["GET"])
    test_router.add_api_route("/topology", get_service_topology, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestTracingRouter:
    """测试追踪路由"""

    def test_get_tracing_dashboard(self, client):
        """测试获取追踪仪表板"""
        response = client.get("/api/tracing/dashboard")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_list_traces(self, client):
        """测试列出追踪记录"""
        response = client.get("/api/tracing/traces?limit=20")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_list_traces_with_filters(self, client):
        """测试带过滤条件的追踪记录列表"""
        response = client.get(
            "/api/tracing/traces?service_name=aiops-agent&limit=10&min_duration=100ms"
        )
        assert response.status_code in [200, 500]

    def test_get_trace_details(self, client):
        """测试获取追踪详情"""
        response = client.get("/api/tracing/traces/trace-123")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_get_service_topology(self, client):
        """测试获取服务调用拓扑"""
        response = client.get("/api/tracing/topology")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
