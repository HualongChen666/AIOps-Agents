# -*- coding: utf-8 -*-
"""
Batch Router Tests
批量API路由基础测试
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.batch_router import batch_get_alerts, batch_get_metrics

# Mock problematic imports before importing router
sys.modules["core.alert_engine"] = MagicMock()
sys.modules["core.collector"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/batch", tags=["Batch"])
    test_router.add_api_route("/alerts", batch_get_alerts, methods=["POST"])
    test_router.add_api_route("/metrics", batch_get_metrics, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestBatchRouter:
    """测试批量API路由"""

    def test_batch_get_alerts_success(self, client):
        """测试成功批量获取告警"""
        with patch("core.alert_engine.alert_history") as _:
            _ = [
                {"id": "alert-1", "title": "CPU告警", "level": "critical"},
                {"id": "alert-2", "title": "内存告警", "level": "warning"},
            ]

            response = client.post("/api/v1/batch/alerts", json=["alert-1", "alert-2"])
            assert response.status_code == 200
            data = response.json()
            assert "results" in data

    def test_batch_get_alerts_empty(self, client):
        """测试批量获取空告警列表"""
        with patch("core.alert_engine.alert_history") as _:
            pass

            response = client.post("/api/v1/batch/alerts", json=[])
            assert response.status_code == 200
            data = response.json()
            assert "results" in data

    def test_batch_get_alerts_not_found(self, client):
        """测试批量获取不存在的告警"""
        with patch("core.alert_engine.alert_history") as _:
            _ = [
                {"id": "alert-1", "title": "CPU告警", "level": "critical"},
            ]

            response = client.post("/api/v1/batch/alerts", json=["alert-999"])
            assert response.status_code == 200
            data = response.json()
            assert "results" in data

    def test_batch_get_metrics_success(self, client):
        """测试成功批量获取指标"""
        with patch("core.collector.collect_all") as mock_collect:
            mock_collect.return_value = {
                "cpu_usage": {"value": 45.2, "unit": "%"},
                "memory_usage": {"value": 68.3, "unit": "%"},
            }

            response = client.post("/api/v1/batch/metrics", json=["cpu_usage", "memory_usage"])
            assert response.status_code == 200
            data = response.json()
            assert "results" in data

    def test_batch_get_metrics_empty(self, client):
        """测试批量获取空指标列表"""
        with patch("core.collector.collect_all") as mock_collect:
            mock_collect.return_value = {}

            response = client.post("/api/v1/batch/metrics", json=[])
            assert response.status_code == 200
            data = response.json()
            assert "results" in data

    def test_batch_get_metrics_not_found(self, client):
        """测试批量获取不存在的指标"""
        with patch("core.collector.collect_all") as mock_collect:
            mock_collect.return_value = {
                "cpu_usage": {"value": 45.2, "unit": "%"},
            }

            response = client.post("/api/v1/batch/metrics", json=["nonexistent_metric"])
            assert response.status_code == 200
            data = response.json()
            assert "results" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
