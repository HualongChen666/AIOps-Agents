# -*- coding: utf-8 -*-
"""
Chaos Router Tests
混沌工程路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.api_response_standard"] = MagicMock()
sys.modules["core.api_response_standard"].create_success_response = Mock(
    return_value={"success": True, "data": {}}
)
sys.modules["core.api_response_standard"].create_error_response = Mock(
    return_value={"success": False, "error": "Error"}
)
sys.modules["core.chaos_engineering"] = MagicMock()

from api.chaos_router import (
    disable_chaos,
    enable_chaos,
    get_chaos_status,
    get_experiments,
    run_experiment,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/chaos", tags=["混沌工程"])
    test_router.add_api_route("/status", get_chaos_status, methods=["GET"])
    test_router.add_api_route("/enable", enable_chaos, methods=["POST"])
    test_router.add_api_route("/disable", disable_chaos, methods=["POST"])
    test_router.add_api_route("/experiment/{experiment_type}", run_experiment, methods=["POST"])
    test_router.add_api_route("/experiments", get_experiments, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestChaosRouter:
    """测试混沌工程路由"""

    def test_get_chaos_status(self, client):
        """测试获取混沌工程状态"""
        with patch("core.chaos_engineering.chaos_engine") as mock_engine:
            mock_engine.get_status.return_value = {
                "enabled": True,
                "stats": {"total_experiments": 10, "success_rate": 0.9},
            }
            response = client.get("/api/v1/chaos/status")
            assert response.status_code == 200

    def test_run_experiment(self, client):
        """测试运行混沌实验"""
        with patch("core.chaos_engineering.chaos_engine") as mock_engine:
            mock_engine.run_experiment.return_value = {"experiment_id": "exp1", "status": "running"}
            response = client.post("/api/v1/chaos/experiment/network_delay")
            assert response.status_code == 200

    def test_get_chaos_status_disabled(self, client):
        """测试混沌工程禁用状态"""
        with patch("core.chaos_engineering.chaos_engine") as mock_engine:
            mock_engine.get_status.return_value = {
                "enabled": False,
                "stats": {"total_experiments": 0, "success_rate": 0.0},
            }
            response = client.get("/api/v1/chaos/status")
            assert response.status_code == 200

    def test_get_experiments_empty(self, client):
        """测试空实验列表"""
        with patch("core.chaos_engineering.chaos_engine") as mock_engine:
            mock_engine.get_experiments.return_value = []
            response = client.get("/api/v1/chaos/experiments")
            assert response.status_code == 200

    def test_enable_chaos_already_enabled(self, client):
        """测试重复启用混沌工程"""
        with patch("api.chaos_router.chaos_engine") as mock_engine:
            mock_engine.enable.side_effect = ValueError("Already enabled")
            response = client.post("/api/v1/chaos/enable")
            assert response.status_code == 200
            assert response.json()["success"] is False

    def test_disable_chaos_already_disabled(self, client):
        """测试重复禁用混沌工程"""
        with patch("api.chaos_router.chaos_engine") as mock_engine:
            mock_engine.disable.side_effect = ValueError("Already disabled")
            response = client.post("/api/v1/chaos/disable")
            assert response.status_code == 200
            assert response.json()["success"] is False

    def test_run_experiment_with_params(self, client):
        """测试带参数运行实验"""
        with patch("core.chaos_engineering.chaos_engine") as mock_engine:
            mock_engine.run_experiment.return_value = {"experiment_id": "exp1", "status": "running"}
            response = client.post(
                "/api/v1/chaos/experiment/network_delay", json={"delay_ms": 100, "jitter": 10}
            )
            assert response.status_code == 200

    def test_get_experiments_with_filter(self, client):
        """测试带过滤条件的实验查询"""
        with patch("core.chaos_engineering.chaos_engine") as mock_engine:
            mock_engine.get_experiments.return_value = [
                {"id": "exp1", "type": "network_delay", "status": "completed"}
            ]
            response = client.get("/api/v1/chaos/experiments?status=completed")
            assert response.status_code == 200

    def test_get_chaos_status_success(self, client):
        """测试成功获取混沌工程状态"""
        with patch("api.chaos_router.chaos_engine") as mock_engine:
            mock_engine.is_enabled.return_value = True
            mock_engine.get_experiment_stats.return_value = {
                "total_experiments": 10,
                "success_rate": 0.9,
            }

            response = client.get("/api/v1/chaos/status")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_enable_chaos(self, client):
        """测试启用混沌工程"""
        with patch("api.chaos_router.chaos_engine") as mock_engine:
            mock_engine.enable.return_value = None

            response = client.post("/api/v1/chaos/enable")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_disable_chaos(self, client):
        """测试禁用混沌工程"""
        with patch("api.chaos_router.chaos_engine") as mock_engine:
            mock_engine.disable.return_value = None

            response = client.post("/api/v1/chaos/disable")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_run_experiment_success(self, client):
        """测试成功执行混沌实验"""
        with patch("api.chaos_router.chaos_engine") as mock_engine:
            mock_result = Mock()
            mock_result.status.value = "completed"
            mock_result.success = True
            mock_result.duration_seconds = 5.2
            mock_result.metrics = {"affected_services": 3}

            async def mock_run_func(exp, params):
                return mock_result

            mock_engine.run_experiment = mock_run_func

            response = client.post("/api/v1/chaos/experiment/latency_injection")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_run_experiment_invalid_type(self, client):
        """测试无效的实验类型"""
        with patch("api.chaos_router.ChaosExperiment") as mock_experiment:
            mock_experiment.side_effect = ValueError("Invalid type")

            response = client.post("/api/v1/chaos/experiment/invalid_type")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_get_experiments(self, client):
        """测试获取实验历史"""
        with patch("api.chaos_router.chaos_engine") as mock_engine:
            mock_exp = Mock()
            mock_exp.experiment.value = "latency_injection"
            mock_exp.status.value = "completed"
            mock_exp.success = True
            mock_exp.duration_seconds = 5.2
            mock_exp.start_time.isoformat.return_value = "2026-07-03T09:00:00Z"
            mock_exp.end_time.isoformat.return_value = "2026-07-03T09:00:05Z"
            mock_engine.get_experiment_history.return_value = [mock_exp]

            response = client.get("/api/v1/chaos/experiments")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
