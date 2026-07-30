# -*- coding: utf-8 -*-
"""
Priority Router Tests
业务影响优先级路由API基础测试
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.priority_router import assess_impact, get_sla_status, priority_health, rank_alerts


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/priority", tags=["priority"])
    test_router.add_api_route("/health", priority_health, methods=["GET"])
    test_router.add_api_route("/assess", assess_impact, methods=["POST"])
    test_router.add_api_route("/rank", rank_alerts, methods=["POST"])
    test_router.add_api_route("/sla/status", get_sla_status, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestPriorityRouter:
    """测试业务影响优先级路由"""

    def test_priority_health(self, client):
        """测试优先级服务健康检查"""
        response = client.get("/priority/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "priority_available" in data

    def test_assess_impact(self, client):
        """测试评估告警业务影响"""
        with patch("api.priority_router.PRIORITY_AVAILABLE", True):
            with patch("api.priority_router._assessor") as mock_assessor:
                mock_impact = Mock()
                mock_impact.to_dict.return_value = {
                    "service": "api-service",
                    "impact_level": "high",
                    "affected_users": 1000,
                }
                mock_assessor.assess.return_value = mock_impact
                response = client.post(
                    "/priority/assess", json={"service": "api-service", "affected_users": 1000}
                )
                assert response.status_code == 200

    def test_assess_impact_not_available(self, client):
        """测试优先级服务不可用时的评估"""
        with patch("api.priority_router.PRIORITY_AVAILABLE", False):
            response = client.post("/priority/assess", json={"service": "api-service"})
            assert response.status_code == 503

    def test_rank_alerts(self, client):
        """测试按优先级排序告警"""
        with patch("api.priority_router.PRIORITY_AVAILABLE", True):
            with patch("api.priority_router._ranker") as mock_ranker:
                mock_rank = Mock()
                mock_rank.__dict__ = {"alert_id": "1", "priority": 1, "score": 0.95}
                mock_ranker.rank_alerts.return_value = [mock_rank]
                response = client.post("/priority/rank", json=[{"alert_id": "1"}])
                assert response.status_code == 200

    def test_rank_alerts_not_available(self, client):
        """测试优先级服务不可用时的排序"""
        with patch("api.priority_router.PRIORITY_AVAILABLE", False):
            response = client.post("/priority/rank", json=[{"alert_id": "1"}])
            assert response.status_code == 503

    def test_get_sla_status(self, client):
        """测试获取服务SLA状态"""
        with patch("api.priority_router.PRIORITY_AVAILABLE", True):
            with patch("api.priority_router._sla_scheduler") as mock_scheduler:
                mock_scheduler.get_sla_status.return_value = {
                    "service": "api-service",
                    "sla_compliance": 0.98,
                }
                response = client.get("/priority/sla/status?service=api-service")
                assert response.status_code == 200

    def test_get_sla_status_not_available(self, client):
        """测试优先级服务不可用时的SLA状态"""
        with patch("api.priority_router.PRIORITY_AVAILABLE", False):
            response = client.get("/priority/sla/status?service=api-service")
            assert response.status_code == 503


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
