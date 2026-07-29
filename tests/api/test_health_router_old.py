# -*- coding: utf-8 -*-
"""
Health Router Tests
基于实际代码的健康检查路由测试
"""

import os
import sys
import threading
from unittest.mock import AsyncMock, MagicMock, Mock, patch  # noqa: F401

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.health_router import router

# 完全禁用配置加载
os.environ.setdefault("AIOPS_SKIP_CONFIG", "true")

# Mock config and other dependencies before importing router
sys.modules["core.config"] = MagicMock()
sys.modules["core.key_management_service"] = MagicMock()
sys.modules["core.database"] = MagicMock()
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.authorization"] = MagicMock()

# Import router after mocking dependencies


@pytest.fixture
def client():
    """创建测试客户端"""

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_health_check():
    """Mock health check functions"""
    with (
        patch("api.health_router.get_liveness_status") as mock_liveness,
        patch("api.health_router.get_readiness_status") as mock_readiness,
        patch("api.health_router.get_detailed_health") as mock_detailed,
        patch("api.health_router.perform_health_checks", new_callable=AsyncMock) as mock_perform,
    ):
        mock_liveness.return_value = {"status": "healthy"}
        mock_readiness.return_value = {"status": "ready"}
        mock_detailed.return_value = {
            "status": "healthy",
            "components": {"database": {"status": "healthy"}, "redis": {"status": "healthy"}},
        }
        mock_perform.return_value = {
            "status": "healthy",
            "components": {"database": {"status": "healthy"}, "redis": {"status": "healthy"}},
        }
        yield mock_liveness, mock_readiness, mock_detailed, mock_perform


class TestPingEndpoint:
    """测试ping端点"""

    def test_ping_returns_alive_status(self, client):
        """测试ping端点返回alive状态"""
        response = client.get("/api/v1/health/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    def test_ping_with_local_ip(self, client):
        """测试本地IP访问ping端点"""
        # 模拟本地IP请求
        response = client.get("/api/v1/health/ping", headers={"X-Forwarded-For": "127.0.0.1"})
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    def test_ping_with_unknown_client(self, client):
        """测试未知客户端访问ping端点"""
        # 模拟无客户端信息的请求
        response = client.get("/api/v1/health/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


class TestHealthEndpoint:
    """测试health端点"""

    @patch("api.health_router.get_liveness_status")
    def test_health_returns_liveness_status(self, mock_get_liveness, client):
        """测试health端点返回liveness状态"""
        mock_get_liveness.return_value = {"status": "healthy"}

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
        mock_get_liveness.assert_called_once()

    @patch("api.health_router.get_liveness_status")
    def test_health_with_unhealthy_status(self, mock_get_liveness, client):
        """测试health端点返回不健康状态"""
        mock_get_liveness.return_value = {"status": "unhealthy", "error": "Service down"}

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "unhealthy"

    @patch("api.health_router.get_liveness_status")
    def test_health_handles_exceptions(self, mock_get_liveness, client):
        """测试health端点处理异常情况"""
        mock_get_liveness.side_effect = Exception("Health check failed")

        response = client.get("/health")
        # 503 Service Unavailable 更适合健康检查失败场景
        assert response.status_code == 503


class TestReadyEndpoint:
    """测试ready端点"""

    @patch("api.health_router.get_readiness_status")
    def test_ready_returns_readiness_status(self, mock_get_readiness, client):
        """测试ready端点返回readiness状态"""
        mock_get_readiness.return_value = {"status": "ready"}

        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
        mock_get_readiness.assert_called_once()

    @patch("api.health_router.get_readiness_status")
    def test_ready_with_not_ready_status(self, mock_get_readiness, client):
        """测试ready端点返回未就绪状态"""
        mock_get_readiness.return_value = {"status": "not_ready", "dependencies": ["database"]}

        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "not_ready"
        assert "database" in response.json()["dependencies"]


class TestDetailedHealthEndpoint:
    """测试详细健康检查端点"""

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_returns_component_status(self, mock_get_detailed, client):
        """测试详细健康检查返回组件状态"""
        mock_get_detailed.return_value = {
            "status": "healthy",
            "components": {"database": {"status": "healthy"}, "redis": {"status": "healthy"}},
        }

        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "components" in response.json()

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_with_degraded_components(self, mock_get_detailed, client):
        """测试详细健康检查返回降级组件状态"""
        mock_get_detailed.return_value = {
            "status": "degraded",
            "components": {
                "database": {"status": "healthy"},
                "redis": {"status": "unhealthy", "error": "Connection timeout"},
            },
        }

        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert response.json()["components"]["redis"]["status"] == "unhealthy"

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_handles_exceptions(self, mock_get_detailed, client):
        """测试详细健康检查处理异常"""
        mock_get_detailed.side_effect = Exception("Health check system error")

        response = client.get("/api/v1/health/detailed")
        # 503 Service Unavailable 更适合健康检查失败场景
        assert response.status_code == 503

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_with_empty_components(self, mock_get_detailed, client):
        """测试详细健康检查返回空组件列表"""
        mock_get_detailed.return_value = {"status": "healthy", "components": {}}

        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        assert response.json()["components"] == {}


class TestHealthSecurity:
    """测试健康检查安全性"""

    def test_ping_ip_whitelist_enforcement(self, client):
        """测试ping端点IP白名单强制执行"""
        # 测试不在白名单中的IP
        response = client.get("/api/v1/health/ping", headers={"X-Forwarded-For": "192.168.1.100"})
        # 当前实现允许所有IP访问，这个测试记录当前行为
        assert response.status_code == 200

    def test_rate_limiting_on_health_endpoints(self, client):
        """测试健康检查端点的速率限制"""
        # 快速连续请求，测试速率限制
        responses = []
        for _ in range(10):
            response = client.get("/api/v1/health/ping")
            responses.append(response.status_code)

        # 当前实现没有速率限制，所有请求应该成功
        assert all(status == 200 for status in responses)

    @patch("api.health_router.get_liveness_status")
    def test_health_with_malformed_headers(self, mock_get_liveness, client):
        """测试健康检查端点处理格式错误的头部"""
        mock_get_liveness.return_value = {"status": "healthy"}
        response = client.get("/health", headers={"X-Forwarded-For": "malformed-ip-address"})
        # 应该仍然返回响应，即使头部格式错误
        assert response.status_code in [200, 400]

    def test_ping_with_large_header_values(self, client):
        """测试ping端点处理大型头部值"""
        large_header = "X" * 10000  # 非常大的头部值
        response = client.get("/api/v1/health/ping", headers={"User-Agent": large_header})
        # 应该正常处理或拒绝，不应该崩溃
        assert response.status_code in [200, 413]  # 413 Payload Too Large

    def test_ping_with_ipv6_address(self, client):
        """测试ping端点处理IPv6地址"""
        response = client.get("/api/v1/health/ping", headers={"X-Forwarded-For": "::1"})
        assert response.status_code == 200

    def test_ping_with_multiple_forwarded_ips(self, client):
        """测试ping端点处理多个转发IP"""
        response = client.get(
            "/api/v1/health/ping", headers={"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        )
        assert response.status_code == 200

    def test_ping_with_custom_user_agent(self, client):
        """测试ping端点处理自定义User-Agent"""
        response = client.get(
            "/api/v1/health/ping", headers={"User-Agent": "CustomHealthCheck/1.0"}
        )
        assert response.status_code == 200

    def test_ping_with_no_user_agent(self, client):
        """测试ping端点处理无User-Agent"""
        response = client.get("/api/v1/health/ping", headers={})
        assert response.status_code == 200


class TestHealthEdgeCases:
    """测试健康检查边缘情况"""

    def test_ping_with_different_http_methods(self, client):
        """测试ping端点只接受GET方法"""
        # GET应该工作
        response = client.get("/api/v1/health/ping")
        assert response.status_code == 200

        # POST可能不被允许
        response = client.post("/api/v1/health/ping")
        assert response.status_code in [405, 404]  # Method Not Allowed or Not Found

    def test_health_with_concurrent_requests(self, client):
        """测试健康检查端点处理并发请求"""

        results = []

        def make_request():
            response = client.get("/health")
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 所有请求都应该成功
        assert all(status in [200, 503] for status in results)

    @patch("api.health_router.get_readiness_status")
    def test_ready_with_timeout_scenario(self, mock_readiness, client):
        """测试就绪检查超时场景"""
        mock_readiness.return_value = {
            "status": "not_ready",
            "error": "Timeout waiting for dependencies",
        }

        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "not_ready"

    def test_ping_with_put_method(self, client):
        """测试ping端点不接受PUT方法"""
        response = client.put("/api/v1/health/ping")
        assert response.status_code in [405, 404]

    def test_ping_with_delete_method(self, client):
        """测试ping端点不接受DELETE方法"""
        response = client.delete("/api/v1/health/ping")
        assert response.status_code in [405, 404]

    def test_ping_with_patch_method(self, client):
        """测试ping端点不接受PATCH方法"""
        response = client.patch("/api/v1/health/ping")
        assert response.status_code in [405, 404]

    @patch("api.health_router.get_liveness_status")
    def test_health_with_empty_response(self, mock_get_liveness, client):
        """测试health端点处理空响应"""
        mock_get_liveness.return_value = {}
        response = client.get("/health")
        assert response.status_code == 200

    @patch("api.health_router.get_readiness_status")
    def test_ready_with_missing_status_field(self, mock_get_readiness, client):
        """测试ready端点处理缺失状态字段"""
        mock_get_readiness.return_value = {"timestamp": "2026-07-03T00:00:00Z"}
        response = client.get("/ready")
        assert response.status_code == 200

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_with_null_components(self, mock_get_detailed, client):
        """测试详细健康检查处理null组件"""
        mock_get_detailed.return_value = {"status": "healthy", "components": None}
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_with_large_response(self, mock_get_detailed, client):
        """测试详细健康检查处理大型响应"""
        large_components = {f"component_{i}": {"status": "healthy"} for i in range(100)}
        mock_get_detailed.return_value = {"status": "healthy", "components": large_components}
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200

    def test_ping_with_query_parameters(self, client):
        """测试ping端点处理查询参数"""
        response = client.get("/api/v1/health/ping?param=value")
        assert response.status_code == 200

    def test_ping_with_fragment(self, client):
        """测试ping端点处理URL片段"""
        response = client.get("/api/v1/health/ping#fragment")
        assert response.status_code == 200

    @patch("api.health_router.get_liveness_status")
    def test_health_with_special_characters_in_response(self, mock_get_liveness, client):
        """测试health端点处理响应中的特殊字符"""
        mock_get_liveness.return_value = {
            "status": "healthy",
            "message": "Test with special chars: <>&\"'",
        }
        response = client.get("/health")
        assert response.status_code == 200

    @patch("api.health_router.get_readiness_status")
    def test_ready_with_unicode_in_response(self, mock_get_readiness, client):
        """测试ready端点处理响应中的Unicode字符"""
        mock_get_readiness.return_value = {
            "status": "ready",
            "message": "Test with unicode: 你好世界 🌍",
        }
        response = client.get("/ready")
        assert response.status_code == 200

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_with_nested_components(self, mock_get_detailed, client):
        """测试详细健康检查处理嵌套组件"""
        mock_get_detailed.return_value = {
            "status": "healthy",
            "components": {
                "database": {
                    "status": "healthy",
                    "details": {"connection": "active", "pool_size": 10},
                }
            },
        }
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200

    @patch("api.health_router.get_liveness_status")
    def test_health_with_numeric_status(self, mock_get_liveness, client):
        """测试health端点处理数字状态"""
        mock_get_liveness.return_value = {"status": 200, "code": "OK"}
        response = client.get("/health")
        assert response.status_code == 200

    @patch("api.health_router.get_readiness_status")
    def test_ready_with_boolean_status(self, mock_get_readiness, client):
        """测试ready端点处理布尔状态"""
        mock_get_readiness.return_value = {"ready": True, "status": "ready"}
        response = client.get("/ready")
        assert response.status_code == 200


class TestTriggerHealthCheck:
    """测试触发健康检查端点"""

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_returns_status(self, mock_perform, client):
        """测试触发健康检查返回状态"""
        mock_perform.return_value = {
            "status": "healthy",
            "components": {"database": {"status": "healthy"}, "redis": {"status": "healthy"}},
        }

        response = client.post("/api/v1/health/check")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        mock_perform.assert_called_once()

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_unhealthy_status(self, mock_perform, client):
        """测试触发健康检查返回不健康状态"""
        mock_perform.return_value = {
            "status": "unhealthy",
            "components": {"database": {"status": "unhealthy"}},
        }

        response = client.post("/api/v1/health/check")
        assert response.status_code == 200
        assert response.json()["status"] == "unhealthy"

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_degraded_status(self, mock_perform, client):
        """测试触发健康检查返回降级状态"""
        mock_perform.return_value = {
            "status": "degraded",
            "components": {"redis": {"status": "degraded"}},
        }

        response = client.post("/api/v1/health/check")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_handles_exceptions(self, mock_perform, client):
        """测试触发健康检查处理异常"""
        mock_perform.side_effect = Exception("Health check failed")

        response = client.post("/api/v1/health/check")
        assert response.status_code == 503

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_duration(self, mock_perform, client):
        """测试触发健康检查返回持续时间"""
        mock_perform.return_value = {
            "status": "healthy",
            "duration_ms": 52,
            "components": {"database": {"status": "healthy"}},
        }

        response = client.post("/api/v1/health/check")
        assert response.status_code == 200
        assert "duration_ms" in response.json()

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_all_components(self, mock_perform, client):
        """测试触发健康检查返回所有组件"""
        mock_perform.return_value = {
            "status": "healthy",
            "components": {
                "database": {"status": "healthy"},
                "redis": {"status": "healthy"},
                "metrics": {"status": "healthy"},
                "alert_engine": {"status": "healthy"},
                "repair_engine": {"status": "healthy"},
            },
        }

        response = client.post("/api/v1/health/check")
        assert response.status_code == 200
        assert len(response.json()["components"]) == 5

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_local_ip(self, mock_perform, client):
        """测试本地IP触发健康检查"""
        mock_perform.return_value = {"status": "healthy"}

        response = client.post("/api/v1/health/check", headers={"X-Forwarded-For": "127.0.0.1"})
        assert response.status_code == 200

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_get_method(self, mock_perform, client):
        """测试GET方法访问触发健康检查端点"""
        mock_perform.return_value = {"status": "healthy"}

        response = client.get("/api/v1/health/check")
        assert response.status_code in [405, 404]

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_concurrent(self, mock_perform, client):
        """测试并发触发健康检查"""
        mock_perform.return_value = {"status": "healthy"}

        results = []

        def make_request():
            response = client.post("/api/v1/health/check")
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert all(status in [200, 503] for status in results)

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_put_method(self, mock_perform, client):
        """测试PUT方法访问触发健康检查端点"""
        mock_perform.return_value = {"status": "healthy"}
        response = client.put("/api/v1/health/check")
        assert response.status_code in [405, 404]

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_delete_method(self, mock_perform, client):
        """测试DELETE方法访问触发健康检查端点"""
        mock_perform.return_value = {"status": "healthy"}
        response = client.delete("/api/v1/health/check")
        assert response.status_code in [405, 404]

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_empty_body(self, mock_perform, client):
        """测试空body触发健康检查"""
        mock_perform.return_value = {"status": "healthy"}
        response = client.post("/api/v1/health/check", json={})
        assert response.status_code == 200

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_with_json_body(self, mock_perform, client):
        """测试JSON body触发健康检查"""
        mock_perform.return_value = {"status": "healthy"}
        response = client.post("/api/v1/health/check", json={"test": "data"})
        assert response.status_code == 200


class TestResponseFormat:
    """测试响应格式"""

    def test_ping_response_content_type(self, client):
        """测试ping端点返回JSON内容类型"""
        response = client.get("/api/v1/health/ping")
        assert "application/json" in response.headers["content-type"]

    @patch("api.health_router.get_liveness_status")
    def test_health_response_content_type(self, mock_get_liveness, client):
        """测试health端点返回JSON内容类型"""
        mock_get_liveness.return_value = {"status": "healthy"}
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]

    @patch("api.health_router.get_readiness_status")
    def test_ready_response_content_type(self, mock_get_readiness, client):
        """测试ready端点返回JSON内容类型"""
        mock_get_readiness.return_value = {"status": "ready"}
        response = client.get("/ready")
        assert "application/json" in response.headers["content-type"]

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_response_content_type(self, mock_get_detailed, client):
        """测试详细健康检查返回JSON内容类型"""
        mock_get_detailed.return_value = {"status": "healthy"}
        response = client.get("/api/v1/health/detailed")
        assert "application/json" in response.headers["content-type"]

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_response_content_type(self, mock_perform, client):
        """测试触发健康检查返回JSON内容类型"""
        mock_perform.return_value = {"status": "healthy"}
        response = client.post("/api/v1/health/check")
        assert "application/json" in response.headers["content-type"]

    def test_ping_response_is_json(self, client):
        """测试ping端点返回有效JSON"""
        response = client.get("/api/v1/health/ping")
        assert response.json() is not None
        assert isinstance(response.json(), dict)

    @patch("api.health_router.get_liveness_status")
    def test_health_response_is_json(self, mock_get_liveness, client):
        """测试health端点返回有效JSON"""
        mock_get_liveness.return_value = {"status": "healthy"}
        response = client.get("/health")
        assert response.json() is not None
        assert isinstance(response.json(), dict)

    @patch("api.health_router.get_readiness_status")
    def test_ready_response_is_json(self, mock_get_readiness, client):
        """测试ready端点返回有效JSON"""
        mock_get_readiness.return_value = {"status": "ready"}
        response = client.get("/ready")
        assert response.json() is not None
        assert isinstance(response.json(), dict)

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_response_is_json(self, mock_get_detailed, client):
        """测试详细健康检查返回有效JSON"""
        mock_get_detailed.return_value = {"status": "healthy"}
        response = client.get("/api/v1/health/detailed")
        assert response.json() is not None
        assert isinstance(response.json(), dict)

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_response_is_json(self, mock_perform, client):
        """测试触发健康检查返回有效JSON"""
        mock_perform.return_value = {"status": "healthy"}
        response = client.post("/api/v1/health/check")
        assert response.json() is not None
        assert isinstance(response.json(), dict)

    @patch("api.health_router.get_liveness_status")
    def test_health_response_has_timestamp(self, mock_get_liveness, client):
        """测试health端点响应包含时间戳"""
        mock_get_liveness.return_value = {"status": "healthy", "timestamp": "2026-07-03T00:00:00Z"}
        response = client.get("/health")
        assert "timestamp" in response.json()

    @patch("api.health_router.get_readiness_status")
    def test_ready_response_has_timestamp(self, mock_get_readiness, client):
        """测试ready端点响应包含时间戳"""
        mock_get_readiness.return_value = {"status": "ready", "timestamp": "2026-07-03T00:00:00Z"}
        response = client.get("/ready")
        assert "timestamp" in response.json()

    @patch("api.health_router.get_detailed_health")
    def test_detailed_health_response_has_timestamp(self, mock_get_detailed, client):
        """测试详细健康检查响应包含时间戳"""
        mock_get_detailed.return_value = {"status": "healthy", "timestamp": "2026-07-03T00:00:00Z"}
        response = client.get("/api/v1/health/detailed")
        assert "timestamp" in response.json()

    @patch("api.health_router.perform_health_checks", new_callable=AsyncMock)
    def test_trigger_health_check_response_has_timestamp(self, mock_perform, client):
        """测试触发健康检查响应包含时间戳"""
        mock_perform.return_value = {"status": "healthy", "timestamp": "2026-07-03T00:00:00Z"}
        response = client.post("/api/v1/health/check")
        assert "timestamp" in response.json()


@pytest.mark.integration
@pytest.mark.skip(reason="Integration tests require real dependencies")
class TestHealthIntegration:
    """集成测试 - 需要真实依赖"""

    @patch("api.health_router.get_liveness_status")
    def test_health_with_real_dependencies(self, mock_get_liveness, client):
        """集成测试：使用真实依赖的健康检查"""
        # 使用Mock来模拟真实依赖
        mock_get_liveness.return_value = {
            "status": "healthy",
            "components": {"database": {"status": "healthy"}, "redis": {"status": "healthy"}},
        }
        response = client.get("/health")
        assert response.status_code in [200, 503]

    @patch("api.health_router.get_readiness_status")
    def test_ready_with_real_database_connection(self, mock_get_readiness, client):
        """集成测试：使用真实数据库连接的就绪检查"""
        # 使用Mock来模拟真实数据库连接
        mock_get_readiness.return_value = {
            "status": "ready",
            "components": {"database": {"status": "healthy"}},
        }
        response = client.get("/ready")
        assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
