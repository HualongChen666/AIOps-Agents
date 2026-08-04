# -*- coding: utf-8 -*-
"""
Metrics Router Tests
指标路由API基础测试
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.metrics_router import (
    clear_snapshot_cache,
    get_dashboard_metrics,
    get_decision_accuracy_endpoint,
    get_feedback_accuracy,
    get_history,
    get_processes,
    get_snapshot,
    get_summary,
)

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.cache_helpers"] = MagicMock()
sys.modules["core.collector"] = MagicMock()
sys.modules["core.metrics_history"] = MagicMock()
sys.modules["core.stats_engine"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/metrics", tags=["指标采集"])
    test_router.add_api_route("/", get_dashboard_metrics, methods=["GET"])
    test_router.add_api_route("/snapshot", get_snapshot, methods=["GET"])
    test_router.add_api_route("/history", get_history, methods=["GET"])
    test_router.add_api_route("/processes", get_processes, methods=["GET"])
    test_router.add_api_route("/summary", get_summary, methods=["GET"])
    test_router.add_api_route("/cache", clear_snapshot_cache, methods=["DELETE"])
    test_router.add_api_route(
        "/feedback-accuracy", get_feedback_accuracy, methods=["GET"]
    )
    test_router.add_api_route(
        "/agent/decision-accuracy", get_decision_accuracy_endpoint, methods=["GET"]
    )
    app.include_router(test_router)
    return TestClient(app)


class TestDashboardMetrics:
    """测试仪表盘指标"""

    def test_get_dashboard_metrics_success(self, client):
        """测试成功获取仪表盘指标"""
        with patch("api.metrics_router.get_real_summary") as mock_summary:
            mock_summary.return_value = {
                "total_alerts": 42,
                "heal_rate": 85,
                "mttd_min": 15,
                "rca_accuracy": 92,
            }
            response = client.get("/api/v1/metrics/")
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert len(data["metrics"]) == 4

    def test_get_dashboard_metrics_error(self, client):
        """测试获取仪表盘指标失败"""
        with patch("api.metrics_router.get_real_summary") as mock_summary:
            mock_summary.side_effect = Exception("Database error")
            response = client.get("/api/v1/metrics/")
            assert response.status_code == 500

    def test_get_history_with_time_range(self, client):
        """测试带时间范围的历史查询"""
        with patch("api.metrics_router.metrics_history") as mock_history:
            mock_history.to_dict.return_value = {"cpu": [45.0], "memory": [60.0]}
            mock_history._maxlen = 60
            response = client.get("/api/v1/metrics/history?hours=24")
            assert response.status_code == 200


class TestGetSnapshot:
    """测试获取系统快照"""

    def test_get_snapshot_success(self, client):
        """测试成功获取系统快照"""
        with patch("api.metrics_router._snapshot_cache") as mock_cache:
            mock_cache.get.return_value = {
                "cpu": {"usage_percent": 45.2},
                "memory": {"usage_percent": 68.3},
            }

            response = client.get("/api/v1/metrics/snapshot")
            assert response.status_code == 200
            data = response.json()
            assert "cpu" in data

    def test_get_snapshot_error(self, client):
        """测试获取系统快照失败"""
        with patch("api.metrics_router._snapshot_cache") as mock_cache:
            mock_cache.get.return_value = None
            with patch("api.metrics_router._collect_system_snapshot") as mock_collect:
                mock_collect.side_effect = Exception("Collection error")

                response = client.get("/api/v1/metrics/snapshot")
                assert response.status_code == 500


class TestGetHistory:
    """测试获取历史数据"""

    def test_get_history_success(self, client):
        """测试成功获取历史数据"""
        with patch("api.metrics_router.metrics_history") as mock_history:
            mock_history.to_dict.return_value = {
                "cpu": [45.2, 48.1, 52.3],
                "memory": [68.3, 70.1, 72.5],
            }
            mock_history._maxlen = 60

            response = client.get("/api/v1/metrics/history")
            assert response.status_code == 200
            data = response.json()
            assert "cpu" in data
            assert "_meta" in data

    def test_get_history_error(self, client):
        """测试获取历史数据失败"""
        with patch("api.metrics_router.metrics_history") as mock_history:
            mock_history.to_dict.side_effect = Exception("History error")

            response = client.get("/api/v1/metrics/history")
            assert response.status_code == 500


class TestGetProcesses:
    """测试获取进程列表"""

    def test_get_processes_success(self, client):
        """测试成功获取进程列表"""
        with patch("api.metrics_router._processes_cache") as mock_cache:
            mock_cache.get.return_value = {
                "processes": [
                    {"name": "python3", "pid": 1234, "cpu_percent": 85.2},
                ]
            }

            response = client.get("/api/v1/metrics/processes")
            assert response.status_code == 200
            data = response.json()
            assert "processes" in data

    def test_get_processes_with_limit(self, client):
        """测试带limit参数获取进程列表"""
        with patch("api.metrics_router._processes_cache") as mock_cache:
            mock_cache.get.return_value = {
                "processes": [
                    {"name": "python3", "pid": 1234, "cpu_percent": 85.2},
                ]
            }

            response = client.get("/api/v1/metrics/processes?limit=20")
            assert response.status_code == 200

    def test_get_processes_error(self, client):
        """测试获取进程列表失败"""
        with patch("api.metrics_router._processes_cache") as mock_cache:
            mock_cache.get.return_value = None
            with patch("api.metrics_router._collect_top_processes") as mock_collect:
                mock_collect.side_effect = Exception("Process error")

                response = client.get("/api/v1/metrics/processes")
                assert response.status_code == 500


class TestGetSummary:
    """测试获取摘要数据"""

    def test_get_summary_success(self, client):
        """测试成功获取摘要数据"""
        with patch("api.metrics_router.get_real_summary") as mock_summary:
            mock_summary.return_value = {
                "total_alerts": 42,
                "heal_rate": 85,
                "mttd_min": 15,
                "rca_accuracy": 92,
            }

            response = client.get("/api/v1/metrics/summary")
            assert response.status_code == 200
            data = response.json()
            assert "total_alerts" in data

    def test_get_summary_error(self, client):
        """测试获取摘要数据失败"""
        with patch("api.metrics_router.get_real_summary") as mock_summary:
            mock_summary.side_effect = Exception("Summary error")

            response = client.get("/api/v1/metrics/summary")
            assert response.status_code == 500


class TestClearSnapshotCache:
    """测试清空缓存"""

    def test_clear_cache_success(self, client):
        """测试成功清空缓存"""
        with patch("api.metrics_router._snapshot_cache") as _:
            with patch("api.metrics_router._processes_cache") as _:
                response = client.delete("/api/v1/metrics/cache")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"

    def test_dashboard_metrics_critical_level(self, client):
        """测试仪表盘指标critical/警告分支"""
        with patch("api.metrics_router.get_real_summary") as mock_summary:
            mock_summary.return_value = {
                "total_alerts": 80,
                "heal_rate": 70,
                "mttd_min": 45,
                "rca_accuracy": 80,
            }
            response = client.get("/api/v1/metrics/")
            assert response.status_code == 200
            data = response.json()["metrics"]
            levels = {m["key"]: m["level"] for m in data}
            assert levels["告警数量"] == "critical"
            assert levels["自愈成功率"] == "warning"
            assert levels["MTTD"] == "warning"
            assert levels["RCA准确率"] == "warning"

    def test_get_snapshot_cache_miss(self, client):
        """测试快照缓存未命中时采集"""
        with patch("api.metrics_router._snapshot_cache") as mock_cache:
            mock_cache.get.return_value = None
            with patch(
                "api.metrics_router._collect_system_snapshot", new_callable=AsyncMock
            ) as mock_collect:
                mock_collect.return_value = {"cpu": {"usage_percent": 10}, "summary": {}}
                response = client.get("/api/v1/metrics/snapshot")
                assert response.status_code == 200
                data = response.json()
                assert "cpu" in data

    def test_get_snapshot_collection_error(self, client):
        """测试快照采集异常"""
        with patch("api.metrics_router._snapshot_cache") as mock_cache:
            mock_cache.get.return_value = None
            with patch(
                "api.metrics_router._collect_system_snapshot", new_callable=AsyncMock
            ) as mock_collect:
                mock_collect.side_effect = RuntimeError("snapshot error")
                response = client.get("/api/v1/metrics/snapshot")
                assert response.status_code == 500

    def test_collect_system_snapshot_dual_write(self, client):
        """测试快照采集触发双写分支"""
        with (
            patch("api.metrics_router.collect_all") as mock_collect,
            patch("api.metrics_router.get_real_summary") as mock_summary,
            patch("api.metrics_router._dual_write_strategy") as mock_dual,
            patch("api.metrics_router._metrics_converter") as mock_converter,  # noqa: F841
            patch("api.metrics_router._snapshot_cache") as mock_cache,
        ):
            mock_cache.get.return_value = None
            mock_collect.return_value = {"cpu": {"usage_percent": 10}}
            mock_summary.return_value = {"total_alerts": 1}
            mock_dual.write_batch_metrics = AsyncMock()
            response = client.get("/api/v1/metrics/snapshot")
            assert response.status_code == 200
            mock_dual.write_batch_metrics.assert_awaited_once()

    def test_get_processes_cache_miss(self, client):
        """测试Top进程缓存未命中时采集"""
        with patch("api.metrics_router._processes_cache") as mock_cache:
            mock_cache.get.return_value = None
            with patch(
                "api.metrics_router._collect_top_processes", new_callable=AsyncMock
            ) as mock_collect:
                mock_collect.return_value = {"processes": [{"name": "python", "pid": 1}]}
                response = client.get("/api/v1/metrics/processes")
                assert response.status_code == 200
                data = response.json()
                assert len(data["processes"]) == 1

    def test_get_processes_collection_error(self, client):
        """测试进程采集异常"""
        with patch("api.metrics_router._processes_cache") as mock_cache:
            mock_cache.get.return_value = None
            with patch(
                "api.metrics_router._collect_top_processes", new_callable=AsyncMock
            ) as mock_collect:
                mock_collect.side_effect = RuntimeError("process error")
                response = client.get("/api/v1/metrics/processes")
                assert response.status_code == 500

    def test_clear_cache_engine_exception(self, client):
        """测试清空缓存时引擎层异常被忽略"""
        with (
            patch("api.metrics_router._snapshot_cache") as _,
            patch("api.metrics_router._processes_cache") as _,
            patch.object(
                sys.modules["core.collector"],
                "invalidate_collect_cache",
                side_effect=RuntimeError("engine error"),
            ) as mock_invalidate,  # noqa: F841
        ):
            response = client.delete("/api/v1/metrics/cache")
            assert response.status_code == 200
            data = response.json()
            assert data["engine_cleared"] is False

    def test_get_history_no_data(self, client):
        """测试历史数据为空"""
        with patch("api.metrics_router.metrics_history") as mock_history:
            mock_history.to_dict.return_value = {}
            mock_history._maxlen = 60

            response = client.get("/api/v1/metrics/history")
            assert response.status_code == 200
            data = response.json()
            assert "_meta" in data

    def test_get_processes_no_limit(self, client):
        """测试不带limit参数获取进程列表"""
        with patch("api.metrics_router._processes_cache") as mock_cache:
            mock_cache.get.return_value = {
                "processes": [
                    {"name": "python3", "pid": 1234, "cpu_percent": 85.2},
                ]
            }

            response = client.get("/api/v1/metrics/processes")
            assert response.status_code == 200

    def test_get_summary_good_levels(self, client):
        """测试摘要数据良好级别"""
        with patch("api.metrics_router.get_real_summary") as mock_summary:
            mock_summary.return_value = {
                "total_alerts": 10,
                "heal_rate": 95,
                "mttd_min": 5,
                "rca_accuracy": 98,
            }

            response = client.get("/api/v1/metrics/summary")
            assert response.status_code == 200
            data = response.json()
            assert "total_alerts" in data

    def test_get_snapshot_with_summary(self, client):
        """测试快照包含摘要"""
        with patch("api.metrics_router._snapshot_cache") as mock_cache:
            mock_cache.get.return_value = {
                "cpu": {"usage_percent": 45.2},
                "summary": {"total_alerts": 5},
            }

            response = client.get("/api/v1/metrics/snapshot")
            assert response.status_code == 200
            data = response.json()
            assert "summary" in data

    def test_get_feedback_accuracy(self, client):
        """测试获取反馈准确率"""
        with patch("api.ai_feedback_router._compute_feedback_stats") as mock_stats:
            mock_stats.return_value = {
                "total": 100,
                "positive": 80,
                "negative": 20,
                "accuracy": 0.8,
            }

            response = client.get("/api/v1/metrics/feedback-accuracy")
            assert response.status_code == 200
            data = response.json()
            assert "total" in data

    def test_get_decision_accuracy(self, client):
        """测试获取决策准确率"""
        with patch("api.metrics_router.get_decision_accuracy") as mock_accuracy:
            mock_accuracy.return_value = {
                "precision": 0.85,
                "recall": 0.9,
                "f1_score": 0.87,
                "accuracy": 0.88,
            }

            response = client.get("/api/v1/metrics/agent/decision-accuracy")
            assert response.status_code == 200
            data = response.json()
            assert "precision" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
