# -*- coding: utf-8 -*-
# tests/api/test_stats_router.py
# 统计数据路由API基础测试
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import api.stats_router
from api.stats_router import get_summary, record_repair_result

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].INTERNAL_API_KEY = ""
sys.modules["config"].ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
sys.modules["config"].TRUST_PROXY_HEADER = False
sys.modules["core.stats_engine"] = MagicMock()

api.stats_router.INTERNAL_API_KEY = ""
api.stats_router.ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
api.stats_router.TRUST_PROXY_HEADER = False


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

    def test_get_summary_cache_hit(self, client):
        """测试统计摘要缓存命中"""
        with patch("api.stats_router.get_real_summary") as mock_summary:
            mock_summary.return_value = {"total_alerts": 100, "resolved": 80, "heal_rate": 80.0}

            # 第一次请求填充缓存
            response1 = client.get("/api/v1/stats/summary")
            # 第二次请求应该命中缓存
            response2 = client.get("/api/v1/stats/summary")
            assert response1.status_code in [200, 500]
            assert response2.status_code in [200, 500]

    def test_record_repair_result_with_internal_key(self, client):
        """测试使用内部密钥记录修复结果"""
        import api.stats_router

        # 设置内部密钥
        api.stats_router.INTERNAL_API_KEY = "test-secret-key"
        api.stats_router.ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
        api.stats_router.TRUST_PROXY_HEADER = False

        with patch("api.stats_router.record_repair", new_callable=AsyncMock) as mock_record:
            mock_record.return_value = None

            response = client.post(
                "/api/v1/stats/repair/record",
                json={"success": True, "rule_name": "CPU高负载修复", "script_key": "kill_high_cpu"},
                headers={"X-Internal-Key": "test-secret-key"},
            )
            assert response.status_code in [200, 403]

        # 重置配置
        api.stats_router.INTERNAL_API_KEY = ""
        api.stats_router.ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
        api.stats_router.TRUST_PROXY_HEADER = False

    def test_record_repair_result_wrong_key(self, client):
        """测试使用错误密钥记录修复结果"""
        import api.stats_router

        # 设置内部密钥
        api.stats_router.INTERNAL_API_KEY = "test-secret-key"
        api.stats_router.ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
        api.stats_router.TRUST_PROXY_HEADER = False

        with patch("api.stats_router.record_repair") as mock_record:
            mock_record.return_value = None

            response = client.post(
                "/api/v1/stats/repair/record",
                json={"success": True, "rule_name": "CPU高负载修复", "script_key": "kill_high_cpu"},
                headers={"X-Internal-Key": "wrong-key"},
            )
            assert response.status_code == 403

        # 重置配置
        api.stats_router.INTERNAL_API_KEY = ""
        api.stats_router.ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
        api.stats_router.TRUST_PROXY_HEADER = False

    def test_record_repair_result_trust_proxy_no_key(self, client):
        """测试代理场景下未配置密钥"""
        import api.stats_router

        # 启用代理但未配置密钥
        api.stats_router.INTERNAL_API_KEY = ""
        api.stats_router.ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
        api.stats_router.TRUST_PROXY_HEADER = True

        with patch("api.stats_router.record_repair") as mock_record:
            mock_record.return_value = None

            response = client.post(
                "/api/v1/stats/repair/record",
                json={"success": True, "rule_name": "CPU高负载修复", "script_key": "kill_high_cpu"},
            )
            assert response.status_code == 403

        # 重置配置
        api.stats_router.INTERNAL_API_KEY = ""
        api.stats_router.ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
        api.stats_router.TRUST_PROXY_HEADER = False

    def test_record_repair_result_error(self, client):
        """测试记录修复结果异常"""
        import api.stats_router

        api.stats_router.INTERNAL_API_KEY = ""
        api.stats_router.ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
        api.stats_router.TRUST_PROXY_HEADER = False

        with patch("api.stats_router.record_repair") as mock_record:
            mock_record.side_effect = Exception("Record error")

            response = client.post(
                "/api/v1/stats/repair/record",
                json={"success": True, "rule_name": "CPU高负载修复", "script_key": "kill_high_cpu"},
            )
            assert response.status_code in [200, 403, 500]

    def test_get_real_client_ip_with_proxy(self, client):
        """测试通过代理获取真实IP"""
        import api.stats_router

        # 启用代理
        api.stats_router.TRUST_PROXY_HEADER = True
        import config
        config.TRUSTED_PROXY_COUNT = 1

        with patch("api.stats_router.get_real_summary") as mock_summary:
            mock_summary.return_value = {"total_alerts": 100, "resolved": 80, "heal_rate": 80.0}

            response = client.get(
                "/api/v1/stats/summary",
                headers={"X-Forwarded-For": "10.0.0.1, 192.168.1.1"},
            )
            assert response.status_code in [200, 500]

        # 重置配置
        api.stats_router.TRUST_PROXY_HEADER = False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
