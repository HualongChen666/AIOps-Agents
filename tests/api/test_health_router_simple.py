# -*- coding: utf-8 -*-
"""
Simplified Health Router Tests
简化的健康检查路由测试，使用同步TestClient
"""

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.health_router import router


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_health_functions():
    """Mock健康检查函数"""
    with (
        patch("api.health_router.get_liveness_status") as mock_liveness,
        patch("api.health_router.get_readiness_status") as mock_readiness,
        patch("api.health_router.get_detailed_health") as mock_detailed,
        patch("api.health_router.perform_health_checks", new_callable=AsyncMock) as mock_perform,
    ):

        mock_liveness.return_value = {"status": "alive", "timestamp": "2024-01-01T00:00:00Z"}
        mock_readiness.return_value = {"status": "ready", "timestamp": "2024-01-01T00:00:00Z"}
        mock_detailed.return_value = {
            "status": "healthy",
            "last_check": "2024-01-01T00:00:00Z",
            "components": {
                "database": {"status": "healthy", "response_time": 0.001},
                "redis": {"status": "healthy", "response_time": 0.001},
                "metrics": {"status": "healthy", "response_time": 0.001},
            },
        }
        mock_perform.return_value = {
            "status": "healthy",
            "last_check": "2024-01-01T00:00:00Z",
            "overall_status": "healthy",
            "components": {
                "database": {"status": "healthy", "response_time": 0.001},
                "redis": {"status": "healthy", "response_time": 0.001},
                "metrics": {"status": "healthy", "response_time": 0.001},
            },
        }
        yield mock_liveness, mock_readiness, mock_detailed, mock_perform


class TestPingEndpoint:
    """测试ping端点"""

    def test_ping_get_method_success(self, client):
        """测试GET方法访问ping端点成功"""
        response = client.get("/api/v1/health/ping")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_ping_post_method_not_allowed(self, client):
        """测试POST方法不被允许"""
        response = client.post("/api/v1/health/ping")
        assert response.status_code == 405  # Method Not Allowed

    def test_ping_put_method_not_allowed(self, client):
        """测试PUT方法不被允许"""
        response = client.put("/api/v1/health/ping")
        assert response.status_code == 405

    def test_ping_delete_method_not_allowed(self, client):
        """测试DELETE方法不被允许"""
        response = client.delete("/api/v1/health/ping")
        assert response.status_code == 405

    def test_ping_with_local_ip_header(self, client):
        """测试本地IP头部访问"""
        response = client.get("/api/v1/health/ping", headers={"X-Forwarded-For": "127.0.0.1"})
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_ping_with_remote_ip_header(self, client):
        """测试远程IP头部访问"""
        response = client.get("/api/v1/health/ping", headers={"X-Forwarded-For": "192.168.1.100"})
        # 当前实现允许所有IP访问
        assert response.status_code == 200

    def test_ping_response_headers(self, client):
        """测试响应头部"""
        response = client.get("/api/v1/health/ping")
        assert response.status_code == 200
        assert "content-type" in response.headers


class TestHealthEndpoint:
    """测试health端点"""

    def test_health_get_method_success(self, client, mock_health_functions):
        """测试GET方法访问health端点成功"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_health_post_method_not_allowed(self, client):
        """测试POST方法不被允许"""
        response = client.post("/health")
        assert response.status_code == 405

    def test_health_with_unhealthy_status(self, client):
        """测试不健康状态返回"""
        with patch("api.health_router.get_liveness_status") as mock_liveness:
            mock_liveness.return_value = {"status": "unhealthy", "error": "Service degraded"}

            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "unhealthy"


class TestReadyEndpoint:
    """测试ready端点"""

    def test_ready_get_method_success(self, client, mock_health_functions):
        """测试GET方法访问ready端点成功"""
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_ready_post_method_not_allowed(self, client):
        """测试POST方法不被允许"""
        response = client.post("/ready")
        assert response.status_code == 405

    def test_ready_with_not_ready_status(self, client):
        """测试未就绪状态"""
        with patch("api.health_router.get_readiness_status") as mock_readiness:
            mock_readiness.return_value = {
                "status": "not_ready",
                "dependencies": ["database", "redis"],
            }

            response = client.get("/ready")
            assert response.status_code == 200
            assert response.json()["status"] == "not_ready"


class TestDetailedHealthEndpoint:
    """测试详细健康检查端点"""

    def test_detailed_health_get_method_success(self, client, mock_health_functions):
        """测试GET方法访问详细健康检查成功"""
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "components" in response.json()

    def test_detailed_health_post_method_not_allowed(self, client):
        """测试POST方法不被允许"""
        response = client.post("/api/v1/health/detailed")
        assert response.status_code == 405

    def test_detailed_health_with_local_ip(self, client, mock_health_functions):
        """测试本地IP访问详细健康检查"""
        response = client.get("/api/v1/health/detailed", headers={"X-Forwarded-For": "127.0.0.1"})
        assert response.status_code == 200
        assert "components" in response.json()


class TestTriggerHealthCheckEndpoint:
    """测试触发健康检查端点"""

    def test_trigger_health_check_post_method_success(self, client, mock_health_functions):
        """测试POST方法触发健康检查成功"""
        response = client.post("/api/v1/health/check")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "components" in response.json()

    def test_trigger_health_check_get_method_not_allowed(self, client):
        """测试GET方法不被允许"""
        response = client.get("/api/v1/health/check")
        assert response.status_code == 405


class TestErrorScenarios:
    """测试错误场景"""

    def test_404_not_found(self, client):
        """测试404错误"""
        response = client.get("/api/v1/health/nonexistent")
        assert response.status_code == 404

    def test_405_method_not_allowed(self, client):
        """测试405错误"""
        response = client.post("/health")
        assert response.status_code == 405

    def test_500_internal_server_error(self, client):
        """测试500错误"""
        with patch("api.health_router.get_liveness_status") as mock_liveness:
            mock_liveness.side_effect = Exception("Unexpected error")

            response = client.get("/health")
            assert response.status_code == 503


class TestSecurityScenarios:
    """测试安全场景"""

    def test_sql_injection_attempt(self, client):
        """测试SQL注入尝试"""
        response = client.get("/api/v1/health/ping", params={"id": "1' OR '1'='1"})
        # 端点不接受查询参数，应该忽略或返回错误
        assert response.status_code == 200

    def test_xss_attempt(self, client):
        """测试XSS尝试"""
        response = client.get(
            "/api/v1/health/ping", headers={"User-Agent": "<script>alert('xss')</script>"}
        )
        # 应该正常处理，不执行脚本
        assert response.status_code == 200

    def test_path_traversal_attempt(self, client):
        """测试路径遍历尝试"""
        response = client.get("/api/v1/health/../../etc/passwd")
        assert response.status_code == 404


@pytest.mark.integration
class TestHealthRouterIntegration:
    """健康检查路由集成测试"""

    def test_full_health_check_workflow(self, client, mock_health_functions):
        """测试完整健康检查工作流"""
        # 1. 检查存活状态
        liveness_response = client.get("/health")
        assert liveness_response.status_code == 200

        # 2. 检查就绪状态
        readiness_response = client.get("/ready")
        assert readiness_response.status_code == 200

        # 3. 检查详细状态
        detailed_response = client.get("/api/v1/health/detailed")
        assert detailed_response.status_code == 200

        # 4. 触发新的健康检查
        trigger_response = client.post("/api/v1/health/check")
        assert trigger_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
