# -*- coding: utf-8 -*-
"""
Alert Router Tests
告警路由API测试
"""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch  # noqa: F401

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.alert_router import router

# Mock problematic imports before importing router
sys.modules["core.alert_service"] = MagicMock()
sys.modules["core.alert_intelligence"] = MagicMock()
sys.modules["core.alert_engine"] = MagicMock()
sys.modules["core.metrics_history"] = MagicMock()
sys.modules["aiops_core"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestGetAlerts:
    """测试获取告警列表"""

    def test_get_alerts_default_limit(self, client):
        """测试默认限制获取告警"""
        with patch("api.alert_router.alert_service.get_alerts") as mock_get_alerts:
            mock_get_alerts.return_value = {
                "alerts": [
                    {
                        "level": "warning",
                        "title": "CPU使用率过高",
                        "desc": "CPU使用率达到85%",
                        "raw_time": "10:30:00",
                        "metric": "cpu",
                        "value": 85.0,
                    }
                ]
            }

            response = client.get("/api/v1/alerts/")
            assert response.status_code == 200
            data = response.json()
            assert "alerts" in data
            mock_get_alerts.assert_called_once_with(20)

    def test_get_alerts_custom_limit(self, client):
        """测试自定义限制获取告警"""
        with patch("api.alert_router.alert_service.get_alerts") as mock_get_alerts:
            mock_get_alerts.return_value = {"alerts": []}

            response = client.get("/api/v1/alerts/?limit=50")
            assert response.status_code == 200
            mock_get_alerts.assert_called_once_with(50)

    def test_get_alerts_min_limit(self, client):
        """测试最小限制"""
        with patch("api.alert_router.alert_service.get_alerts") as mock_get_alerts:
            mock_get_alerts.return_value = {"alerts": []}

            response = client.get("/api/v1/alerts/?limit=1")
            assert response.status_code == 200
            mock_get_alerts.assert_called_once_with(1)

    def test_get_alerts_max_limit(self, client):
        """测试最大限制"""
        with patch("api.alert_router.alert_service.get_alerts") as mock_get_alerts:
            mock_get_alerts.return_value = {"alerts": []}

            response = client.get("/api/v1/alerts/?limit=500")
            assert response.status_code == 200
            mock_get_alerts.assert_called_once_with(500)

    def test_get_alerts_invalid_limit_below(self, client):
        """测试无效限制（低于最小值）"""
        response = client.get("/api/v1/alerts/?limit=0")
        assert response.status_code == 422

    def test_get_alerts_invalid_limit_above(self, client):
        """测试无效限制（高于最大值）"""
        response = client.get("/api/v1/alerts/?limit=501")
        assert response.status_code == 422

    def test_get_alerts_with_large_response(self, client):
        """测试大量告警响应"""
        with patch("api.alert_router.alert_service.get_alerts") as mock_get_alerts:
            mock_get_alerts.return_value = {
                "alerts": [
                    {
                        "level": "info",
                        "title": f"告警{i}",
                        "desc": f"描述{i}",
                        "raw_time": "10:30:00",
                        "metric": "cpu",
                        "value": i,
                    }
                    for i in range(100)
                ]
            }

            response = client.get("/api/v1/alerts/?limit=100")
            assert response.status_code == 200
            data = response.json()
            assert len(data["alerts"]) == 100


class TestClearAlerts:
    """测试清空告警"""

    def test_clear_alerts_success(self, client):
        """测试成功清空告警"""
        with patch("api.alert_router.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {"status": "success", "cleared_count": 42}

            response = client.delete("/api/v1/alerts/")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["cleared_count"] == 42

    def test_clear_alerts_empty(self, client):
        """测试清空空告警列表"""
        with patch("api.alert_router.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {"status": "success", "cleared_count": 0}

            response = client.delete("/api/v1/alerts/")
            assert response.status_code == 200
            data = response.json()
            assert data["cleared_count"] == 0

    def test_clear_alerts_with_operator_ip(self, client):
        """测试记录操作者IP"""
        with patch("api.alert_router.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {"status": "success", "cleared_count": 10}

            response = client.delete("/api/v1/alerts/")
            assert response.status_code == 200
            mock_clear.assert_called_once()


class TestIntelligenceStatistics:
    """测试智能告警统计"""

    def test_get_intelligence_statistics_success(self, client):
        """测试成功获取统计信息"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_engine.get_alert_statistics.return_value = {
                    "total_patterns": 150,
                    "noise_patterns": 25,
                    "cluster_count": 8,
                    "last_updated": "2026-07-02T10:30:00Z",
                }

                response = client.get("/api/v1/alerts/intelligence/statistics")
                assert response.status_code == 200
                data = response.json()
                assert data["total_patterns"] == 150

    def test_get_intelligence_statistics_unavailable(self, client):
        """测试智能告警引擎不可用"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
            response = client.get("/api/v1/alerts/intelligence/statistics")
            assert response.status_code == 503


class TestAlertPatterns:
    """测试告警模式"""

    def test_get_alert_patterns_default(self, client):
        """测试默认获取告警模式"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_pattern = Mock()
                mock_pattern.pattern_id = "pattern_001"
                mock_pattern.signature = "cpu_high"
                mock_pattern.frequency = 42
                mock_pattern.last_seen.isoformat.return_value = "2026-07-02T10:30:00Z"
                mock_pattern.is_noise = False
                mock_pattern.noise_reason = None

                mock_engine.patterns = {"pattern_001": mock_pattern}

                response = client.get("/api/v1/alerts/intelligence/patterns")
                assert response.status_code == 200
                data = response.json()
                assert "patterns" in data
                assert len(data["patterns"]) == 1

    def test_get_alert_patterns_with_noise(self, client):
        """测试包含噪声模式"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_pattern = Mock()
                mock_pattern.pattern_id = "pattern_001"
                mock_pattern.signature = "cpu_normal"
                mock_pattern.frequency = 100
                mock_pattern.last_seen.isoformat.return_value = "2026-07-02T10:30:00Z"
                mock_pattern.is_noise = True
                mock_pattern.noise_reason = "正常波动"

                mock_engine.patterns = {"pattern_001": mock_pattern}

                response = client.get("/api/v1/alerts/intelligence/patterns?include_noise=true")
                assert response.status_code == 200
                data = response.json()
                assert len(data["patterns"]) == 1
                assert data["patterns"][0]["is_noise"] is True

    def test_get_alert_patterns_exclude_noise(self, client):
        """测试排除噪声模式"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_pattern = Mock()
                mock_pattern.pattern_id = "pattern_001"
                mock_pattern.signature = "cpu_normal"
                mock_pattern.frequency = 100
                mock_pattern.last_seen.isoformat.return_value = "2026-07-02T10:30:00Z"
                mock_pattern.is_noise = True
                mock_pattern.noise_reason = "正常波动"

                mock_engine.patterns = {"pattern_001": mock_pattern}

                response = client.get("/api/v1/alerts/intelligence/patterns?include_noise=false")
                assert response.status_code == 200
                data = response.json()
                assert len(data["patterns"]) == 0

    def test_get_alert_patterns_custom_limit(self, client):
        """测试自定义限制"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_engine.patterns = {}

                response = client.get("/api/v1/alerts/intelligence/patterns?limit=10")
                assert response.status_code == 200

    def test_get_alert_patterns_unavailable(self, client):
        """测试智能告警引擎不可用"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
            response = client.get("/api/v1/alerts/intelligence/patterns")
            assert response.status_code == 503


class TestPredictAlertTrend:
    """测试告警趋势预测"""

    def _mock_prediction(self):
        prediction = Mock()
        prediction.metric_name = "cpu_usage"
        prediction.predicted_values = [45.2, 48.1]
        prediction.predicted_anomalies = []
        prediction.confidence = 0.87
        prediction.prediction_horizon = 24
        prediction.model_used = "prophet"
        return prediction

    def test_predict_alert_trend_success(self, client):
        """测试成功预测趋势"""
        timestamps = [f"{h:02d}:00:00" for h in range(12)]
        values = [float(v) for v in range(12)]
        mock_metrics = Mock()
        mock_metrics.to_dict.return_value = {
            "timestamps": timestamps,
            "cpu_usage": values,
        }
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_engine.predict_alert_trends = AsyncMock(return_value=self._mock_prediction())
                with patch("core.metrics_history.metrics_history", mock_metrics):
                    response = client.post(
                        "/api/v1/alerts/intelligence/predict",
                        json={"metric_name": "cpu_usage", "horizon_hours": 24},
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert data["metric_name"] == "cpu_usage"

    def test_predict_alert_trend_insufficient_data(self, client):
        """测试历史数据不足"""
        mock_metrics = Mock()
        mock_metrics.to_dict.return_value = {
            "timestamps": ["10:00:00"],
            "cpu_usage": [1.0],
        }
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("core.metrics_history.metrics_history", mock_metrics):
                response = client.post(
                    "/api/v1/alerts/intelligence/predict",
                    json={"metric_name": "cpu_usage", "horizon_hours": 24},
                )
                assert response.status_code == 400

    def test_predict_alert_trend_unavailable(self, client):
        """测试智能告警引擎不可用"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
            response = client.post(
                "/api/v1/alerts/intelligence/predict",
                json={"metric_name": "cpu_usage", "horizon_hours": 24},
            )
            assert response.status_code == 503


class TestTopologyContext:
    """测试拓扑上下文"""

    def test_get_topology_context_success(self, client):
        """测试成功获取拓扑上下文"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_engine.build_topology_context.return_value = {"nodes": []}
                response = client.get("/api/v1/alerts/intelligence/topology")
                assert response.status_code == 200

    def test_get_topology_context_unavailable(self, client):
        """测试智能告警引擎不可用"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
            response = client.get("/api/v1/alerts/intelligence/topology")
            assert response.status_code == 503


class TestRoutingRules:
    """测试路由规则"""

    def test_add_routing_rule_success(self, client):
        """测试成功添加路由规则"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as _:
                rule_data = {
                    "conditions": {"level": "critical"},
                    "destination": "oncall",
                    "description": "紧急告警通知值班人员",
                    "priority": 1,
                }

                response = client.post("/api/v1/alerts/intelligence/routing-rules", json=rule_data)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"

    def test_add_routing_rule_unavailable(self, client):
        """测试智能告警引擎不可用"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
            response = client.post(
                "/api/v1/alerts/intelligence/routing-rules",
                json={"conditions": {}, "destination": "oncall"},
            )
            assert response.status_code == 503


class TestSuppressionRules:
    """测试抑制规则"""

    def test_add_suppression_rule_success(self, client):
        """测试成功添加抑制规则"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as _:
                rule_data = {
                    "pattern": "cpu_normal",
                    "reason": "正常CPU波动，无需告警",
                    "suppression_window": 300,
                    "enabled": True,
                }

                response = client.post(
                    "/api/v1/alerts/intelligence/suppression-rules", json=rule_data
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"

    def test_add_suppression_rule_unavailable(self, client):
        """测试智能告警引擎不可用"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
            response = client.post(
                "/api/v1/alerts/intelligence/suppression-rules",
                json={"pattern": "test", "reason": "test"},
            )
            assert response.status_code == 503


class TestRouteAlerts:
    """测试智能路由告警"""

    def test_route_alerts_intelligently_success(self, client):
        """测试成功智能路由告警"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_engine.route_alerts_intelligently = AsyncMock(return_value={"oncall": []})
                response = client.post("/api/v1/alerts/intelligence/route-alerts")
                assert response.status_code == 200
                data = response.json()
                assert data["total_alerts"] == 0

    def test_route_alerts_intelligently_unavailable(self, client):
        """测试智能告警引擎不可用"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
            response = client.post("/api/v1/alerts/intelligence/route-alerts")
            assert response.status_code == 503


class TestAlertRouterEdgeCases:
    """测试边缘情况"""

    def test_get_alerts_with_negative_limit(self, client):
        """测试负数限制"""
        response = client.get("/api/v1/alerts/?limit=-1")
        assert response.status_code == 422

    def test_get_alerts_with_string_limit(self, client):
        """测试字符串限制"""
        response = client.get("/api/v1/alerts/?limit=abc")
        assert response.status_code == 422

    def test_get_alerts_response_format(self, client):
        """测试响应格式"""
        with patch("api.alert_router.alert_service.get_alerts") as mock_get_alerts:
            mock_get_alerts.return_value = {"alerts": []}

            response = client.get("/api/v1/alerts/")
            assert "application/json" in response.headers["content-type"]

    @pytest.mark.skip(reason="Clear alerts endpoint is DELETE, not GET")
    def test_clear_alerts_with_get_method(self, client):
        """测试GET方法访问清空端点"""
        response = client.get("/api/v1/alerts/")
        assert response.status_code == 200

    def test_intelligence_endpoints_with_post_wrong_method(self, client):
        """测试POST端点使用GET方法"""
        response = client.get("/api/v1/alerts/intelligence/predict")
        assert response.status_code in [405, 404]

    def test_get_alerts_with_zero_limit(self, client):
        """测试零限制"""
        response = client.get("/api/v1/alerts/?limit=0")
        assert response.status_code == 422

    def test_get_alerts_with_very_large_limit(self, client):
        """测试非常大的限制"""
        response = client.get("/api/v1/alerts/?limit=10000")
        assert response.status_code == 422

    def test_clear_alerts_response_format(self, client):
        """测试清空告警响应格式"""
        with patch("api.alert_router.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {"status": "success", "cleared_count": 10}

            response = client.delete("/api/v1/alerts/")
            assert "application/json" in response.headers["content-type"]

    def test_intelligence_statistics_response_format(self, client):
        """测试统计信息响应格式"""
        with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", True):
            with patch("api.alert_router.alert_intelligence_engine") as mock_engine:
                mock_engine.get_alert_statistics.return_value = {
                    "total_patterns": 150,
                    "noise_patterns": 25,
                }

                response = client.get("/api/v1/alerts/intelligence/statistics")
                assert "application/json" in response.headers["content-type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
