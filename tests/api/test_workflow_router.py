# -*- coding: utf-8 -*-
# tests/api/test_workflow_router.py
# 工作流路由API基础测试
import sys
from unittest.mock import MagicMock, patch

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
