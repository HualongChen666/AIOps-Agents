# -*- coding: utf-8 -*-
"""
Test suite for Chaos Engineering Router (Basic)
混沌工程基础路由测试套件
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock


@pytest.fixture
def client():
    """Create a test client for the router"""
    from api.chaos_router import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_chaos_engine():
    """Mock the chaos engine"""
    engine = Mock()
    engine.is_enabled = Mock(return_value=True)
    engine.get_experiment_stats = Mock(
        return_value={
            "total_experiments": 10,
            "successful_experiments": 8,
            "failed_experiments": 2,
            "success_rate": 80.0,
        }
    )
    engine.get_experiment_history = Mock(return_value=[])
    engine.run_experiment = AsyncMock()
    return engine


class TestChaosStatus:
    """Test chaos status endpoints"""

    def test_get_chaos_status(self, client, mock_chaos_engine):
        """Test GET /api/v1/chaos/status"""
        with patch("api.chaos_router.chaos_engine", mock_chaos_engine):
            response = client.get("/api/v1/chaos/status")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "enabled" in data["data"]
            assert "stats" in data["data"]

    def test_enable_chaos(self, client, mock_chaos_engine):
        """Test POST /api/v1/chaos/enable"""
        with patch("api.chaos_router.chaos_engine", mock_chaos_engine):
            response = client.post("/api/v1/chaos/enable")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["enabled"] is True

    def test_disable_chaos(self, client, mock_chaos_engine):
        """Test POST /api/v1/chaos/disable"""
        with patch("api.chaos_router.chaos_engine", mock_chaos_engine):
            response = client.post("/api/v1/chaos/disable")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["enabled"] is False


class TestChaosExperiments:
    """Test chaos experiment endpoints"""

    def test_run_experiment_valid_type(self, client, mock_chaos_engine):
        """Test POST /api/v1/chaos/experiment/{type} with valid type"""
        from core.chaos_engineering import ExperimentResult, ExperimentStatus, ChaosExperiment
        from datetime import datetime, timezone

        mock_result = ExperimentResult(
            experiment=ChaosExperiment.LATENCY_INJECTION,
            status=ExperimentStatus.COMPLETED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=5.0,
            success=True,
            metrics={"affected_services": 3},
        )
        mock_chaos_engine.run_experiment.return_value = mock_result

        with patch("api.chaos_router.chaos_engine", mock_chaos_engine):
            response = client.post(
                "/api/v1/chaos/experiment/latency_injection",
                json={"delay_ms": 500, "target": "api-service"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["experiment"] == "latency_injection"
            assert data["data"]["success"] is True

    def test_run_experiment_invalid_type(self, client, mock_chaos_engine):
        """Test POST /api/v1/chaos/experiment/{type} with invalid type"""
        with patch("api.chaos_router.chaos_engine", mock_chaos_engine):
            response = client.post(
                "/api/v1/chaos/experiment/invalid_type",
                json={}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_get_experiments(self, client, mock_chaos_engine):
        """Test GET /api/v1/chaos/experiments"""
        with patch("api.chaos_router.chaos_engine", mock_chaos_engine):
            response = client.get("/api/v1/chaos/experiments")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "experiments" in data["data"]
            assert "total" in data["data"]


class TestChaosTemplates:
    """Test chaos template endpoints"""

    def test_get_chaos_templates(self, client):
        """Test GET /api/v1/chaos/templates"""
        response = client.get("/api/v1/chaos/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "templates" in data["data"]
        assert len(data["data"]["templates"]) > 0

        # Verify template structure
        template = data["data"]["templates"][0]
        assert "id" in template
        assert "name" in template
        assert "type" in template
        assert "description" in template
        assert "severity" in template
        assert "parameters" in template


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
