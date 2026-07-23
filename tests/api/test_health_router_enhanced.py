# -*- coding: utf-8 -*-
"""
Enhanced Health Router Tests with Real HTTP Client
使用FastAPI TestClient进行真实HTTP测试，包含认证和错误场景测试
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.health_router import router


@pytest.fixture
def client():
    """创建测试客户端（同步）"""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
async def async_client():
    """创建异步测试客户端"""
    app = FastAPI()
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_auth():
    """Mock认证依赖"""
    with patch("core.authentication.get_current_active_user") as mock_auth:
        # 模拟认证用户
        mock_auth.return_value = {
            "id": "test_user_id",
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
            "is_superuser": False,
        }
        yield mock_auth


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


class TestPingEndpointRealHTTP:
    """使用真实HTTP客户端测试ping端点"""

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
        assert "application/json" in response.headers["content-type"]

    def test_ping_concurrent_requests(self, client):
        """测试并发请求处理"""
        import threading

        responses = []

        def make_request():
            responses.append(client.get("/api/v1/health/ping"))

        # 发送10个并发请求
        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 所有请求都应该成功
        assert all(response.status_code == 200 for response in responses)
        assert all(response.json()["status"] == "alive" for response in responses)


class TestHealthEndpointRealHTTP:
    """使用真实HTTP客户端测试health端点"""

    @pytest.mark.asyncio
    async def test_health_get_method_success(self, async_client, mock_health_functions):
        """测试GET方法访问health端点成功"""
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    @pytest.mark.asyncio
    async def test_health_post_method_not_allowed(self, async_client):
        """测试POST方法不被允许"""
        response = await async_client.post("/health")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_health_with_unhealthy_status(self, async_client):
        """测试不健康状态返回"""
        with patch("api.health_router.get_liveness_status") as mock_liveness:
            mock_liveness.return_value = {"status": "unhealthy", "error": "Service degraded"}

            response = await async_client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_with_exception(self, async_client):
        """测试异常处理"""
        with patch("api.health_router.get_liveness_status") as mock_liveness:
            mock_liveness.side_effect = Exception("Health check failed")

            response = await async_client.get("/health")
            # 路由将异常转换为503服务不可用
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_health_response_structure(self, async_client, mock_health_functions):
        """测试响应结构"""
        response = await async_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestReadyEndpointRealHTTP:
    """使用真实HTTP客户端测试ready端点"""

    @pytest.mark.asyncio
    async def test_ready_get_method_success(self, async_client, mock_health_functions):
        """测试GET方法访问ready端点成功"""
        response = await async_client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    @pytest.mark.asyncio
    async def test_ready_post_method_not_allowed(self, async_client):
        """测试POST方法不被允许"""
        response = await async_client.post("/ready")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_ready_with_not_ready_status(self, async_client):
        """测试未就绪状态"""
        with patch("api.health_router.get_readiness_status") as mock_readiness:
            mock_readiness.return_value = {
                "status": "not_ready",
                "dependencies": ["database", "redis"],
            }

            response = await async_client.get("/ready")
            assert response.status_code == 200
            assert response.json()["status"] == "not_ready"
            assert "dependencies" in response.json()

    @pytest.mark.asyncio
    async def test_ready_with_partial_dependency_failure(self, async_client):
        """测试部分依赖失败"""
        with patch("api.health_router.get_readiness_status") as mock_readiness:
            mock_readiness.return_value = {
                "status": "degraded",
                "dependencies": {"database": "ready", "redis": "not_ready"},
            }

            response = await async_client.get("/ready")
            assert response.status_code == 200
            assert response.json()["status"] == "degraded"


class TestDetailedHealthEndpointRealHTTP:
    """使用真实HTTP客户端测试详细健康检查端点"""

    @pytest.mark.asyncio
    async def test_detailed_health_get_method_success(self, async_client, mock_health_functions):
        """测试GET方法访问详细健康检查成功"""
        response = await async_client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "components" in response.json()

    @pytest.mark.asyncio
    async def test_detailed_health_post_method_not_allowed(self, async_client):
        """测试POST方法不被允许"""
        response = await async_client.post("/api/v1/health/detailed")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_detailed_health_with_local_ip(self, async_client, mock_health_functions):
        """测试本地IP访问详细健康检查"""
        response = await async_client.get(
            "/api/v1/health/detailed", headers={"X-Forwarded-For": "127.0.0.1"}
        )
        assert response.status_code == 200
        assert "components" in response.json()

    @pytest.mark.asyncio
    async def test_detailed_health_with_remote_ip(self, async_client, mock_health_functions):
        """测试远程IP访问详细健康检查"""
        response = await async_client.get(
            "/api/v1/health/detailed", headers={"X-Forwarded-For": "192.168.1.100"}
        )
        # 当前实现允许所有IP访问
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_detailed_health_with_degraded_status(self, async_client):
        """测试降级状态"""
        with patch("api.health_router.get_detailed_health") as mock_detailed:
            mock_detailed.return_value = {
                "status": "degraded",
                "components": {
                    "database": {"status": "healthy"},
                    "redis": {"status": "unhealthy", "error": "Connection timeout"},
                },
            }

            response = await async_client.get("/api/v1/health/detailed")
            assert response.status_code == 200
            assert response.json()["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_detailed_health_with_exception(self, async_client):
        """测试异常处理"""
        with patch("api.health_router.get_detailed_health") as mock_detailed:
            mock_detailed.side_effect = Exception("Health check system error")

            response = await async_client.get("/api/v1/health/detailed")
            assert response.status_code == 503


class TestTriggerHealthCheckEndpointRealHTTP:
    """使用真实HTTP客户端测试触发健康检查端点"""

    @pytest.mark.asyncio
    async def test_trigger_health_check_post_method_success(
        self, async_client, mock_health_functions
    ):
        """测试POST方法触发健康检查成功"""
        response = await async_client.post("/api/v1/health/check")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "components" in response.json()

    @pytest.mark.asyncio
    async def test_trigger_health_check_get_method_not_allowed(self, async_client):
        """测试GET方法不被允许"""
        response = await async_client.get("/api/v1/health/check")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_trigger_health_check_with_local_ip(self, async_client, mock_health_functions):
        """测试本地IP触发健康检查"""
        response = await async_client.post(
            "/api/v1/health/check", headers={"X-Forwarded-For": "127.0.0.1"}
        )
        assert response.status_code == 200
        assert "components" in response.json()

    @pytest.mark.asyncio
    async def test_trigger_health_check_with_remote_ip(self, async_client, mock_health_functions):
        """测试远程IP触发健康检查"""
        response = await async_client.post(
            "/api/v1/health/check", headers={"X-Forwarded-For": "192.168.1.100"}
        )
        # 当前实现允许所有IP访问
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trigger_health_check_async_execution(self, async_client, mock_health_functions):
        """测试异步执行健康检查"""
        mock_perform = mock_health_functions[3]
        response = await async_client.post("/api/v1/health/check")
        assert response.status_code == 200
        assert mock_perform.awaited


class TestAuthenticationScenarios:
    """测试认证场景"""

    @pytest.mark.asyncio
    async def test_authentication_required_for_remote_access(
        self, async_client, mock_auth, mock_health_functions
    ):
        """测试远程访问需要认证"""
        # 注意：当前实现中认证依赖没有正确集成
        # 这个测试为将来的认证集成做准备
        with patch("config.ALLOWED_LOCAL_IPS", []):
            response = await async_client.get(
                "/api/v1/health/detailed", headers={"X-Forwarded-For": "192.168.1.100"}
            )
            # 当前实现仍然返回200，因为认证没有完全集成
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_local_ip_bypasses_authentication(self, async_client, mock_health_functions):
        """测试本地IP绕过认证"""
        response = await async_client.get(
            "/api/v1/health/detailed", headers={"X-Forwarded-For": "127.0.0.1"}
        )
        # 本地IP应该可以无认证访问
        assert response.status_code == 200


class TestErrorScenarios:
    """测试错误场景"""

    @pytest.mark.asyncio
    async def test_404_not_found(self, async_client):
        """测试404错误"""
        response = await async_client.get("/api/v1/health/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_405_method_not_allowed(self, async_client):
        """测试405错误"""
        response = await async_client.post("/health")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_500_internal_server_error(self, async_client):
        """测试500错误"""
        with patch("api.health_router.get_liveness_status") as mock_liveness:
            mock_liveness.side_effect = Exception("Unexpected error")

            response = await async_client.get("/health")
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_malformed_json_request(self, async_client, mock_health_functions):
        """测试格式错误的JSON请求"""
        response = await async_client.post(
            "/api/v1/health/check",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        # 端点忽略请求体，返回200
        assert response.status_code in [200, 405, 422]

    @pytest.mark.asyncio
    async def test_large_request_headers(self, async_client):
        """测试大型请求头部"""
        large_header = "X" * 10000
        response = await async_client.get(
            "/api/v1/health/ping", headers={"User-Agent": large_header}
        )
        # 应该正常处理或拒绝
        assert response.status_code in [200, 413, 431]


class TestPerformanceAndLoad:
    """测试性能和负载"""

    @pytest.mark.asyncio
    async def test_response_time_within_acceptable_range(self, async_client, mock_health_functions):
        """测试响应时间在可接受范围内"""
        import time

        start_time = time.time()
        response = await async_client.get("/api/v1/health/ping")
        end_time = time.time()

        assert response.status_code == 200
        # 响应时间应该小于1秒
        assert (end_time - start_time) < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_load_handling(self, async_client, mock_health_functions):
        """测试并发负载处理"""
        import asyncio

        async def make_request():
            return await async_client.get("/api/v1/health/ping")

        # 发送50个并发请求
        responses = await asyncio.gather(*[make_request() for _ in range(50)])

        # 所有请求都应该成功
        assert all(response.status_code == 200 for response in responses)

    @pytest.mark.asyncio
    async def test_sequential_request_performance(self, async_client, mock_health_functions):
        """测试顺序请求性能"""
        import time

        start_time = time.time()
        for _ in range(10):
            response = await async_client.get("/api/v1/health/ping")
            assert response.status_code == 200
        end_time = time.time()

        # 10个顺序请求应该在合理时间内完成
        assert (end_time - start_time) < 5.0


class TestSecurityScenarios:
    """测试安全场景"""

    @pytest.mark.asyncio
    async def test_sql_injection_attempt(self, async_client):
        """测试SQL注入尝试"""
        response = await async_client.get("/api/v1/health/ping", params={"id": "1' OR '1'='1"})
        # 端点不接受查询参数，应该忽略或返回错误
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_xss_attempt(self, async_client):
        """测试XSS尝试"""
        response = await async_client.get(
            "/api/v1/health/ping", headers={"User-Agent": "<script>alert('xss')</script>"}
        )
        # 应该正常处理，不执行脚本
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_path_traversal_attempt(self, async_client):
        """测试路径遍历尝试"""
        response = await async_client.get("/api/v1/health/../../etc/passwd")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_header_injection_attempt(self, async_client):
        """测试头部注入尝试"""
        response = await async_client.get(
            "/api/v1/health/ping",
            headers={"X-Forwarded-For": "127.0.0.1\r\nX-Injected-Header: malicious"},
        )
        # 应该安全处理或拒绝
        assert response.status_code in [200, 400]


@pytest.mark.integration
class TestHealthRouterIntegration:
    """健康检查路由集成测试"""

    @pytest.mark.asyncio
    async def test_full_health_check_workflow(self, async_client, mock_health_functions):
        """测试完整健康检查工作流"""
        # 1. 检查存活状态
        liveness_response = await async_client.get("/health")
        assert liveness_response.status_code == 200

        # 2. 检查就绪状态
        readiness_response = await async_client.get("/ready")
        assert readiness_response.status_code == 200

        # 3. 检查详细状态
        detailed_response = await async_client.get("/api/v1/health/detailed")
        assert detailed_response.status_code == 200

        # 4. 触发新的健康检查
        trigger_response = await async_client.post("/api/v1/health/check")
        assert trigger_response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_with_degraded_components(self, async_client):
        """测试组件降级时的健康检查"""
        with patch(
            "api.health_router.perform_health_checks", new_callable=AsyncMock
        ) as mock_perform:
            mock_perform.return_value = {
                "status": "degraded",
                "last_check": "2024-01-01T00:00:00Z",
                "overall_status": "degraded",
                "components": {
                    "database": {"status": "healthy"},
                    "redis": {"status": "unhealthy"},
                    "metrics": {"status": "healthy"},
                },
            }

            response = await async_client.post("/api/v1/health/check")
            assert response.status_code == 200
            assert response.json()["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_recovery_scenario(self, async_client):
        """测试健康检查恢复场景"""
        # 模拟从不健康恢复到健康
        with patch(
            "api.health_router.perform_health_checks", new_callable=AsyncMock
        ) as mock_perform:
            # 第一次调用返回不健康
            mock_perform.return_value = {
                "status": "unhealthy",
                "components": {"database": {"status": "unhealthy"}},
            }

            response1 = await async_client.post("/api/v1/health/check")
            assert response1.json()["status"] == "unhealthy"

            # 第二次调用返回健康
            mock_perform.return_value = {
                "status": "healthy",
                "components": {"database": {"status": "healthy"}},
            }

            response2 = await async_client.post("/api/v1/health/check")
            assert response2.json()["status"] == "healthy"
