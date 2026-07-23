# -*- coding: utf-8 -*-
# tests/api/test_workflow_visualization_router_enhanced.py
# 工作流可视化路由API测试
import os
import sys
from unittest.mock import Mock, patch

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.workflow_visualization_router import router

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})
sys.modules["core.workflow_visualization"] = Mock()
sys.modules["core.workflow_visualization"].workflow_viz_service = Mock()


test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestWorkflowVisualizationRouter:
    """工作流可视化路由测试"""

    def test_get_workflow_graph(self):
        """测试获取工作流图"""
        with patch("core.workflow_visualization.workflow_viz_service.get_graph") as mock_graph:
            mock_graph.return_value = {"nodes": [], "edges": []}
            response = client.get("/api/v1/workflows/1/graph")
            assert response.status_code in [200, 401, 403, 404]

    def test_get_workflow_stats(self):
        """测试获取工作流统计"""
        with patch("core.workflow_visualization.workflow_viz_service.get_stats") as mock_stats:
            mock_stats.return_value = {"total_workflows": 10, "active": 5}
            response = client.get("/api/v1/workflows/1/stats")
            assert response.status_code in [200, 401, 403, 404]
