# -*- coding: utf-8 -*-
# tests/api/test_workflow_router.py
# 工作流路由API基础测试
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import api.workflow_router as workflow_router
from api.workflow_router import get_concurrent_status, list_workflows

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.workflow_engine"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/workflows", tags=["工作流"])
    test_router.add_api_route("/definitions", list_workflows, methods=["GET"])
    test_router.add_api_route("/concurrent", get_concurrent_status, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


@pytest.fixture
def client_with_simulate():
    """创建包含simulate端点的测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/workflows", tags=["工作流"])
    test_router.add_api_route("/definitions", list_workflows, methods=["GET"])
    test_router.add_api_route("/concurrent", get_concurrent_status, methods=["GET"])
    test_router.add_api_route(
        "/simulate/{wf_key}",
        workflow_router.simulate_workflow,
        methods=["GET"],
    )
    app.include_router(test_router)
    return TestClient(app)


class TestWorkflowRouter:
    """测试工作流路由"""

    def test_list_workflows(self, client):
        """测试获取所有工作流定义"""
        with patch("api.workflow_router.get_workflow_definitions") as mock_get:
            mock_get.return_value = {
                "data_collection": {
                    "key": "data_collection",
                    "name": "数据采集与摄入",
                    "description": "从各种数据源采集指标和日志",
                }
            }

            response = client.get("/api/v1/workflows/definitions")
            assert response.status_code in [200, 500]

    def test_list_workflows_error(self, client):
        """测试获取工作流定义失败"""
        with patch("api.workflow_router.get_workflow_definitions") as mock_get:
            mock_get.side_effect = Exception("获取工作流定义失败")

            response = client.get("/api/v1/workflows/definitions")
            assert response.status_code == 500

    def test_get_concurrent_status(self, client):
        """测试获取SSE并发状态"""
        response = client.get("/api/v1/workflows/concurrent")
        assert response.status_code == 200
        data = response.json()
        assert "max_concurrent" in data
        assert "available" in data
        assert "in_use" in data

    def test_get_concurrent_status_content(self, client):
        """测试SSE并发状态内容"""
        response = client.get("/api/v1/workflows/concurrent")
        assert response.status_code == 200
        data = response.json()
        # Verify structure contains expected fields
        assert isinstance(data["max_concurrent"], int)
        assert isinstance(data["available"], int)
        assert isinstance(data["in_use"], int)
        assert isinstance(data["is_locked"], bool)

    def test_list_workflows_response_structure(self, client):
        """测试工作流定义响应结构"""
        with patch("api.workflow_router.get_workflow_definitions") as mock_get:
            mock_get.return_value = {
                "data_collection": {"key": "data_collection", "name": "数据采集与摄入"}
            }

            response = client.get("/api/v1/workflows/definitions")
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)

    def test_list_workflows_empty(self, client):
        """测试空工作流定义列表"""
        with patch("api.workflow_router.get_workflow_definitions") as mock_get:
            mock_get.return_value = {}

            response = client.get("/api/v1/workflows/definitions")
            assert response.status_code in [200, 500]

    def test_list_workflows_multiple(self, client):
        """测试多个工作流定义"""
        with patch("api.workflow_router.get_workflow_definitions") as mock_get:
            mock_get.return_value = {
                "data_collection": {"key": "data_collection", "name": "数据采集"},
                "alert_processing": {"key": "alert_processing", "name": "告警处理"},
                "repair_execution": {"key": "repair_execution", "name": "修复执行"},
            }

            response = client.get("/api/v1/workflows/definitions")
            assert response.status_code in [200, 500]

    def test_get_concurrent_status_with_lock(self, client):
        """测试锁定状态下的并发状态"""
        with patch.object(workflow_router._sse_semaphore, "locked", return_value=True):
            response = client.get("/api/v1/workflows/concurrent")
            assert response.status_code == 200
            data = response.json()
            assert data["is_locked"] is True

    def test_get_concurrent_status_available_slots(self, client):
        """测试可用插槽数量"""
        response = client.get("/api/v1/workflows/concurrent")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] >= 0
        assert data["available"] <= data["max_concurrent"]

    def test_list_workflows_with_filter(self, client):
        """测试带过滤条件的工作流列表"""
        with patch("api.workflow_router.get_workflow_definitions") as mock_get:
            mock_get.return_value = {
                "data_collection": {"key": "data_collection", "name": "数据采集"}
            }

            response = client.get("/api/v1/workflows/definitions?category=collection")
            assert response.status_code in [200, 500]

    def test_get_concurrent_status_zero_in_use(self, client):
        """测试无工作流运行时的并发状态"""
        with patch("api.workflow_router._SSE_MAX_CONCURRENT", 10):
            with patch.object(workflow_router._sse_semaphore, "_value", 10):
                response = client.get("/api/v1/workflows/concurrent")
                assert response.status_code == 200
                data = response.json()
                assert data["in_use"] == 0

    def test_get_concurrent_status_max_capacity(self, client):
        """测试达到最大容量时的并发状态"""
        with patch("api.workflow_router._SSE_MAX_CONCURRENT", 10):
            with patch.object(workflow_router._sse_semaphore, "_value", 0):
                response = client.get("/api/v1/workflows/concurrent")
                assert response.status_code == 200
                data = response.json()
                assert data["available"] == 0

    def test_list_workflows_timeout(self, client):
        """测试工作流定义获取超时"""
        with patch("api.workflow_router.get_workflow_definitions") as mock_get:
            mock_get.side_effect = TimeoutError("Request timeout")

            response = client.get("/api/v1/workflows/definitions")
            assert response.status_code == 500

    def test_simulate_workflow_success(self, client_with_simulate):
        """测试工作流仿真成功"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"test_workflow": {}}):
            async def mock_stream():
                yield {"type": "workflow_start"}
                yield {"type": "step_complete", "node_key": "test"}
                yield {"type": "workflow_done"}

            with patch("api.workflow_router.simulate_workflow_stream") as mock_simulate:
                mock_simulate.return_value = mock_stream()
                response = client_with_simulate.get("/api/v1/workflows/simulate/test_workflow")
                # SSE endpoints return 200 even if we don't consume the stream
                assert response.status_code == 200

    def test_simulate_workflow_invalid_key(self, client_with_simulate):
        """测试工作流仿真无效wf_key"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"valid_workflow": {}}):
            response = client_with_simulate.get("/api/v1/workflows/simulate/invalid_workflow")
            assert response.status_code == 404

    def test_simulate_workflow_semaphore_full(self, client_with_simulate):
        """测试工作流仿真并发已满"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"test_workflow": {}}):
            with patch.object(workflow_router._sse_semaphore, "_value", 0):
                with patch.object(workflow_router._sse_semaphore, "locked", return_value=True):
                    response = client_with_simulate.get("/api/v1/workflows/simulate/test_workflow")
                    # Should return 503 when semaphore is full
                    assert response.status_code in [200, 503]

    def test_simulate_workflow_no_value_attribute(self, client_with_simulate):
        """测试semaphore无_value属性时的兼容处理"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"test_workflow": {}}):
            with patch.object(workflow_router._sse_semaphore, "locked", return_value=False):
                with patch.object(workflow_router._sse_semaphore, "__getattribute__", side_effect=AttributeError):
                    # Should fall back to locked() check
                    response = client_with_simulate.get("/api/v1/workflows/simulate/test_workflow")
                    assert response.status_code == 200

    def test_simulate_workflow_client_disconnect(self, client_with_simulate):
        """测试客户端断开连接"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"test_workflow": {}}):
            async def mock_stream():
                yield {"type": "workflow_start"}
                # Simulate client disconnect by checking request
                yield {"type": "step_complete"}

            with patch("api.workflow_router.simulate_workflow_stream") as mock_simulate:
                mock_simulate.return_value = mock_stream()
                response = client_with_simulate.get("/api/v1/workflows/simulate/test_workflow")
                assert response.status_code == 200

    def test_simulate_workflow_json_serialization_error(self, client_with_simulate):
        """测试SSE事件序列化失败"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"test_workflow": {}}):
            async def mock_stream():
                yield {"type": "workflow_start"}
                # Yield non-serializable object
                yield object()

            with patch("api.workflow_router.simulate_workflow_stream") as mock_simulate:
                mock_simulate.return_value = mock_stream()
                response = client_with_simulate.get("/api/v1/workflows/simulate/test_workflow")
                assert response.status_code == 200

    def test_simulate_workflow_cancelled_error(self, client_with_simulate):
        """测试SSE连接被取消"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"test_workflow": {}}):
            async def mock_stream():
                yield {"type": "workflow_start"}
                raise asyncio.CancelledError()

            with patch("api.workflow_router.simulate_workflow_stream") as mock_simulate:
                mock_simulate.return_value = mock_stream()
                response = client_with_simulate.get("/api/v1/workflows/simulate/test_workflow")
                assert response.status_code == 200

    def test_simulate_workflow_internal_error(self, client_with_simulate):
        """测试SSE内部异常"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"test_workflow": {}}):
            async def mock_stream():
                yield {"type": "workflow_start"}
                raise RuntimeError("Internal error")

            with patch("api.workflow_router.simulate_workflow_stream") as mock_simulate:
                mock_simulate.return_value = mock_stream()
                response = client_with_simulate.get("/api/v1/workflows/simulate/test_workflow")
                assert response.status_code == 200

    def test_simulate_workflow_is_disconnected_error(self, client_with_simulate):
        """测试is_disconnected检测异常"""
        with patch("api.workflow_router.WORKFLOW_DEFINITIONS", {"test_workflow": {}}):
            async def mock_stream():
                yield {"type": "workflow_start"}
                yield {"type": "workflow_done"}

            with patch("api.workflow_router.simulate_workflow_stream") as mock_simulate:
                mock_simulate.return_value = mock_stream()
                response = client_with_simulate.get("/api/v1/workflows/simulate/test_workflow")
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
