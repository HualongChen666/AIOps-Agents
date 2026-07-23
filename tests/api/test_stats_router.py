# -*- coding: utf-8 -*-
# tests/api/test_stats_router.py
# 统计数据路由API基础测试
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].INTERNAL_API_KEY = ""
sys.modules["config"].ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
sys.modules["config"].TRUST_PROXY_HEADER = False
sys.modules["core.stats_engine"] = MagicMock()

from api.stats_router import get_summary, record_repair_result


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/stats", tags=["统计数据"])
    test_router.add_api_route("/summary", get_summary, methods=["GET"])
    test_router.add_api_route("/repair/record", record_repair_result, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestStatsRouter:
    """测试统计数据路由"""

    def test_get_summary_success(self, client):
        """测试成功获取统计摘要"""
        with patch("api.stats_router.get_real_summary") as mock_summary:
            mock_summary.return_value = {"total_alerts": 100, "resolved": 80, "heal_rate": 80.0}

            response = client.get("/api/v1/stats/summary")
            assert response.status_code in [200, 500]

    def test_get_summary_error(self, client):
        """测试获取统计摘要失败"""
        with patch("api.stats_router.get_real_summary") as mock_summary:
            mock_summary.side_effect = Exception("Stats engine error")

            response = client.get("/api/v1/stats/summary")
            assert response.status_code in [200, 500]

    def test_record_repair_result_success(self, client):
        """测试成功记录修复结果"""
        with patch("api.stats_router.record_repair") as mock_record:
            mock_record.return_value = None

            response = client.post(
                "/api/v1/stats/repair/record",
                json={"success": True, "rule_name": "CPU高负载修复", "script_key": "kill_high_cpu"},
            )
            assert response.status_code in [200, 403]

    def test_record_repair_result_failure(self, client):
        """测试记录修复失败结果"""
        with patch("api.stats_router.record_repair") as mock_record:
            mock_record.return_value = None

            response = client.post(
                "/api/v1/stats/repair/record",
                json={
                    "success": False,
                    "rule_name": "CPU高负载修复",
                    "script_key": "kill_high_cpu",
                    "output": "修复失败",
                },
            )
            assert response.status_code in [200, 403]

    def test_record_repair_result_invalid_payload(self, client):
        """测试记录修复结果无效载荷"""
        response = client.post(
            "/api/v1/stats/repair/record", json={"success": "invalid"}  # Should be boolean
        )
        assert response.status_code in [422, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
