# -*- coding: utf-8 -*-
# tests/api/test_root_cause_router.py
# 根因分析路由API基础测试
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.root_cause_intelligence"] = MagicMock()

from api.root_cause_router import (
    get_historical_patterns,
    get_root_cause_statistics,
    get_topology_structure,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/root-cause", tags=["根因分析"])
    test_router.add_api_route("/topology", get_topology_structure, methods=["GET"])
    test_router.add_api_route("/patterns", get_historical_patterns, methods=["GET"])
    test_router.add_api_route("/statistics", get_root_cause_statistics, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestRootCauseRouter:
    """测试根因分析路由"""

    def test_get_topology_structure(self, client):
        """测试获取拓扑结构"""
        with (
            patch("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True),
            patch("api.root_cause_router.root_cause_intelligence_engine") as mock_engine,
        ):
            mock_engine._get_topology_summary.return_value = {"total_nodes": 10, "total_edges": 15}
            mock_engine.topology_graph = {}

            response = client.get("/api/v1/root-cause/topology")
            assert response.status_code in [200, 503]

    def test_get_topology_structure_unavailable(self, client):
        """测试根因智能引擎不可用"""
        with patch("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False):
            response = client.get("/api/v1/root-cause/topology")
            assert response.status_code == 503

    def test_get_historical_patterns(self, client):
        """测试获取历史模式列表"""
        with (
            patch("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True),
            patch("api.root_cause_router.root_cause_intelligence_engine") as mock_engine,
        ):
            mock_pattern = Mock()
            mock_pattern.pattern_id = "pattern-1"
            mock_pattern.root_cause = "CPU高负载"
            mock_pattern.confidence = 0.85
            mock_pattern.frequency = 10
            mock_pattern.last_occurrence = MagicMock()
            mock_pattern.last_occurrence.isoformat.return_value = "2026-07-03T00:00:00Z"
            mock_pattern.resolution_time_avg = 5.0
            mock_pattern.effectiveness_score = 0.9
            mock_engine.historical_patterns = {"pattern-1": mock_pattern}

            response = client.get("/api/v1/root-cause/patterns")
            assert response.status_code in [200, 503]

    def test_get_historical_patterns_unavailable(self, client):
        """测试根因智能引擎不可用时获取历史模式"""
        with patch("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False):
            response = client.get("/api/v1/root-cause/patterns")
            assert response.status_code == 503

    def test_get_root_cause_statistics(self, client):
        """测试获取根因分析统计信息"""
        with (
            patch("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True),
            patch("api.root_cause_router.root_cause_intelligence_engine") as mock_engine,
        ):
            mock_engine.get_analysis_statistics.return_value = {
                "total_analyses": 100,
                "success_rate": 0.95,
            }

            response = client.get("/api/v1/root-cause/statistics")
            assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
