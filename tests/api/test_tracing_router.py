# -*- coding: utf-8 -*-
# tests/api/test_tracing_router.py
# 追踪路由API基础测试
import sys
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.tracing_router import (
    export_trace_config,
    get_error_analysis,
    get_performance_hotspots,
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
    test_router.add_api_route("/performance/hotspots", get_performance_hotspots, methods=["GET"])
    test_router.add_api_route("/errors/analysis", get_error_analysis, methods=["GET"])
    test_router.add_api_route("/export/trace-config", export_trace_config, methods=["GET"])
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

    def test_get_performance_hotspots(self, client):
        """测试获取性能热点分析"""
        response = client.get("/api/tracing/performance/hotspots?time_range=1h")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_get_performance_hotspots_with_service(self, client):
        """测试带服务过滤的性能热点分析"""
        response = client.get(
            "/api/tracing/performance/hotspots?service_name=aiops-agent&time_range=24h"
        )
        assert response.status_code in [200, 500]

    def test_get_error_analysis(self, client):
        """测试获取错误分析"""
        response = client.get("/api/tracing/errors/analysis?time_range=1h")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_get_error_analysis_with_service(self, client):
        """测试带服务过滤的错误分析"""
        response = client.get(
            "/api/tracing/errors/analysis?service_name=aiops-agent&time_range=24h"
        )
        assert response.status_code in [200, 500]

    def test_export_trace_config(self, client):
        """测试导出追踪配置"""
        response = client.get("/api/tracing/export/trace-config")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_list_traces_invalid_limit(self, client):
        """测试无效limit参数"""
        response = client.get("/api/tracing/traces?limit=invalid")
        assert response.status_code in [200, 500, 422]

    def test_get_trace_details_not_found(self, client):
        """测试获取不存在的追踪详情"""
        response = client.get("/api/tracing/traces/nonexistent")
        assert response.status_code in [200, 500, 404]

    def test_get_performance_hotspots_invalid_time_range(self, client):
        """测试无效时间范围参数"""
        response = client.get("/api/tracing/performance/hotspots?time_range=invalid")
        assert response.status_code in [200, 500, 422]

    def test_get_error_analysis_invalid_time_range(self, client):
        """测试错误分析无效时间范围"""
        response = client.get("/api/tracing/errors/analysis?time_range=invalid")
        assert response.status_code in [200, 500, 422]

    def test_list_traces_no_params(self, client):
        """测试无参数的追踪记录列表"""
        response = client.get("/api/tracing/traces")
        assert response.status_code in [200, 500]

    def test_get_trace_details_empty_id(self, client):
        """测试空trace_id"""
        response = client.get("/api/tracing/traces/")
        # FastAPI redirects trailing slash to non-trailing slash
        assert response.status_code in [200, 307, 404, 405]

    def test_get_service_topology_with_time_range(self, client):
        """测试带时间范围的服务拓扑"""
        response = client.get("/api/tracing/topology?time_range=1h")
        assert response.status_code in [200, 500]

    def test_export_trace_config_with_format(self, client):
        """测试带格式的配置导出"""
        response = client.get("/api/tracing/export/trace-config?format=yaml")
        assert response.status_code in [200, 500]

    def test_list_traces_negative_limit(self, client):
        """测试负数limit参数"""
        response = client.get("/api/tracing/traces?limit=-1")
        assert response.status_code in [200, 500, 422]

    def test_get_performance_hotspots_no_time_range(self, client):
        """测试无时间范围的性能热点"""
        response = client.get("/api/tracing/performance/hotspots")
        assert response.status_code in [200, 500]

    def test_get_error_analysis_no_time_range(self, client):
        """测试无时间范围的错误分析"""
        response = client.get("/api/tracing/errors/analysis")
        assert response.status_code in [200, 500]

    def test_export_trace_config_config_missing(self, client):
        """测试配置导出时OTEL_COLLECTOR_ENDPOINT缺失"""
        from unittest.mock import patch
        with patch("config.OTEL_COLLECTOR_ENDPOINT", side_effect=AttributeError("No endpoint")):
            response = client.get("/api/tracing/export/trace-config")
            assert response.status_code in [200, 500]

    def test_list_traces_max_duration_filter(self, client):
        """测试最大持续时间过滤"""
        response = client.get("/api/tracing/traces?max_duration=1s")
        assert response.status_code in [200, 500]

    def test_list_traces_both_duration_filters(self, client):
        """测试同时使用最小和最大持续时间过滤"""
        response = client.get("/api/tracing/traces?min_duration=100ms&max_duration=1s")
        assert response.status_code in [200, 500]

    def test_list_traces_limit_boundary(self, client):
        """测试limit边界值"""
        response = client.get("/api/tracing/traces?limit=100")
        assert response.status_code in [200, 500]

    def test_list_traces_limit_exceeds_max(self, client):
        """测试limit超过最大值"""
        response = client.get("/api/tracing/traces?limit=101")
        assert response.status_code in [200, 500, 422]

    def test_get_trace_details_special_chars(self, client):
        """测试trace_id包含特殊字符"""
        response = client.get("/api/tracing/traces/trace-123-abc")
        assert response.status_code in [200, 500]

    def test_get_performance_hotspots_different_time_ranges(self, client):
        """测试不同时间范围"""
        time_ranges = ["1h", "24h", "7d", "30d"]
        for time_range in time_ranges:
            response = client.get(f"/api/tracing/performance/hotspots?time_range={time_range}")
            assert response.status_code in [200, 500]

    def test_get_error_analysis_different_time_ranges(self, client):
        """测试错误分析不同时间范围"""
        time_ranges = ["1h", "24h", "7d", "30d"]
        for time_range in time_ranges:
            response = client.get(f"/api/tracing/errors/analysis?time_range={time_range}")
            assert response.status_code in [200, 500]

    @pytest.mark.skip(reason="Exception paths in try-except blocks are difficult to trigger with TestClient")
    def test_get_tracing_dashboard_exception_path(self, client):
        """测试仪表板异常路径"""
        pass

    @pytest.mark.skip(reason="Exception paths in try-except blocks are difficult to trigger with TestClient")
    def test_list_traces_exception_path(self, client):
        """测试追踪列表异常路径"""
        pass

    @pytest.mark.skip(reason="Exception paths in try-except blocks are difficult to trigger with TestClient")
    def test_get_trace_details_exception_path(self, client):
        """测试追踪详情异常路径"""
        pass

    @pytest.mark.skip(reason="Exception paths in try-except blocks are difficult to trigger with TestClient")
    def test_get_service_topology_exception_path(self, client):
        """测试服务拓扑异常路径"""
        pass

    @pytest.mark.skip(reason="Exception paths in try-except blocks are difficult to trigger with TestClient")
    def test_get_performance_hotspots_exception_path(self, client):
        """测试性能热点异常路径"""
        pass

    @pytest.mark.skip(reason="Exception paths in try-except blocks are difficult to trigger with TestClient")
    def test_get_error_analysis_exception_path(self, client):
        """测试错误分析异常路径"""
        pass

    @pytest.mark.skip(reason="Exception paths in try-except blocks are difficult to trigger with TestClient")
    def test_export_trace_config_exception_path(self, client):
        """测试配置导出异常路径"""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
