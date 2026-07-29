# -*- coding: utf-8 -*-
# tests/api/test_workflow_visualization_router.py
# 工作流可视化路由API基础测试
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# isort: off
# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].BASE_DIR = Path("/tmp")

from api.workflow_visualization_router import get_workflow_structure, workflow_visualization_page

# isort: on


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/workflow", tags=["工作流可视化"])
    test_router.add_api_route("/visualization", workflow_visualization_page, methods=["GET"])
    test_router.add_api_route("/structure", get_workflow_structure, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestWorkflowVisualizationRouter:
    """测试工作流可视化路由"""

    def test_workflow_visualization_page_not_found(self, client):
        """测试工作流可视化页面未找到"""
        # Since the static file doesn't exist, it should return 404
        response = client.get("/workflow/visualization")
        assert response.status_code == 404

    def test_workflow_visualization_page_get_method(self, client):
        """测试工作流可视化页面GET方法"""
        response = client.get("/workflow/visualization")
        # Should handle GET request
        assert response.status_code in [200, 404]

    def test_workflow_visualization_page_post_not_allowed(self, client):
        """测试工作流可视化页面POST方法不允许"""
        response = client.post("/workflow/visualization")
        # POST should not be allowed
        assert response.status_code in [405, 404]

    def test_get_workflow_structure(self, client):
        """测试获取工作流结构"""
        response = client.get("/workflow/structure")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    def test_get_workflow_structure_content(self, client):
        """测试工作流结构内容"""
        response = client.get("/workflow/structure")
        assert response.status_code == 200
        data = response.json()
        # Verify structure contains expected fields
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
        assert "metadata" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
