# -*- coding: utf-8 -*-
"""
Cost Router Tests
成本监控路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})
sys.modules["core.cost_monitor"] = MagicMock()

from api.cost_router import get_budget, get_collect, get_forecast


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/cost", tags=["cost"])
    test_router.add_api_route("/collect", get_collect, methods=["GET"])
    test_router.add_api_route("/forecast", get_forecast, methods=["GET"])
    test_router.add_api_route("/budget", get_budget, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestCostRouter:
    """测试成本监控路由"""

    def test_get_collect_success(self, client):
        """测试成功获取成本数据"""
        with patch("api.cost_router.collect_costs") as mock_collect:
            mock_collect.return_value = [{"date": "2026-07-01", "amount": 100.0}]

            response = client.get("/api/cost/collect")
            assert response.status_code == 200
            data = response.json()
            assert "costs" in data

    def test_get_collect_no_data(self, client):
        """测试无成本数据"""
        with patch("api.cost_router.collect_costs") as mock_collect:
            mock_collect.return_value = []

            response = client.get("/api/cost/collect")
            assert response.status_code == 404

    def test_get_forecast_success(self, client):
        """测试成功获取费用预测"""
        with patch("api.cost_router.forecast_costs") as mock_forecast:
            mock_forecast.return_value = [{"date": "2026-07-02", "predicted_amount": 105.0}]

            response = client.get("/api/cost/forecast?days=30")
            assert response.status_code == 200
            data = response.json()
            assert "forecast" in data

    def test_get_forecast_no_data(self, client):
        """测试无预测数据"""
        with patch("api.cost_router.forecast_costs") as mock_forecast:
            mock_forecast.return_value = []

            response = client.get("/api/cost/forecast?days=30")
            assert response.status_code == 404

    def test_get_forecast_default_days(self, client):
        """测试使用默认天数获取费用预测"""
        with patch("api.cost_router.forecast_costs") as mock_forecast:
            mock_forecast.return_value = [{"date": "2026-07-02", "predicted_amount": 105.0}]

            response = client.get("/api/cost/forecast")
            assert response.status_code == 200
            data = response.json()
            assert data["days"] == 30

    def test_get_budget(self, client):
        """测试获取预算状态"""
        with patch("api.cost_router.budget_status") as mock_budget:
            mock_budget.return_value = {
                "budget": 1000.0,
                "used": 500.0,
                "remaining": 500.0,
                "status": "normal",
            }

            response = client.get("/api/cost/budget")
            assert response.status_code == 200
            data = response.json()
            assert "budget" in data
            assert "used" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
