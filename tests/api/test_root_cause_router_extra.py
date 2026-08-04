# -*- coding: utf-8 -*-
"""补充测试：覆盖 api/root_cause_router.py 的遗漏分支与端点。"""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.modules["core.root_cause_intelligence"] = MagicMock()

from api.root_cause_router import router  # noqa: E402


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _hypothesis_obj():
    return SimpleNamespace(
        hypothesis_id="h1",
        root_cause="rc",
        confidence=0.9,
        evidence=[],
        causal_path=[],
        impact_score=0.8,
        verification_status="pending",
        verification_timestamp=None,
    )


def _pattern_obj():
    return SimpleNamespace(
        pattern_id="p1",
        root_cause="rc",
        confidence=0.9,
        frequency=1,
        last_occurrence=SimpleNamespace(isoformat=lambda: "2026-08-04T00:00:00Z"),
        resolution_time_avg=1.0,
        effectiveness_score=0.9,
    )


class TestRootCauseRouterExtra:
    """覆盖缺失的 503 分支与 verify/delete/active 等端点。"""

    def test_discover_topology_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.post(
            "/api/v1/root-cause/topology/discover",
            json={"metrics_data": {}, "include_dependencies": True},
        )
        assert response.status_code == 503

    def test_cross_layer_tracking_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.post(
            "/api/v1/root-cause/cross-layer-track", json={"id": "a1"}, params={"max_depth": 3}
        )
        assert response.status_code == 503

    def test_match_patterns_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.post("/api/v1/root-cause/patterns/match", json={"symptoms": {}})
        assert response.status_code == 503

    def test_learn_pattern_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.post(
            "/api/v1/root-cause/patterns/learn",
            json={
                "symptoms": {},
                "root_cause": "rc",
                "resolution_time": 1.0,
                "effectiveness": 0.9,
            },
        )
        assert response.status_code == 503

    def test_analyze_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.post(
            "/api/v1/root-cause/analyze",
            json={"alert": {"id": "a1"}, "metrics_data": {}},
        )
        assert response.status_code == 503

    def test_predict_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.post(
            "/api/v1/root-cause/predict",
            json={"current_state": {}, "prediction_horizon": 60},
        )
        assert response.status_code == 503

    def test_statistics_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.get("/api/v1/root-cause/statistics")
        assert response.status_code == 503

    def test_verify_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.post(
            "/api/v1/root-cause/verify",
            json={"hypothesis_id": "h1", "verification_data": {}},
        )
        assert response.status_code == 503

    def test_active_hypotheses_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.get("/api/v1/root-cause/hypotheses")
        assert response.status_code == 503

    def test_delete_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False, raising=False
        )
        response = client.delete("/api/v1/root-cause/hypotheses/h1")
        assert response.status_code == 503

    def test_verify_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.active_hypotheses = {"h1": _hypothesis_obj()}
        mock_engine.verify_root_cause = AsyncMock(return_value={"verified": True})
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.post(
            "/api/v1/root-cause/verify",
            json={"hypothesis_id": "h1", "verification_data": {}},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_verify_not_found(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.active_hypotheses = {}
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.post(
            "/api/v1/root-cause/verify",
            json={"hypothesis_id": "h1", "verification_data": {}},
        )
        assert response.status_code == 404

    def test_get_active_hypotheses_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.active_hypotheses = {"h1": _hypothesis_obj()}
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.get("/api/v1/root-cause/hypotheses")
        assert response.status_code == 200
        assert response.json()["total_hypotheses"] == 1

    def test_delete_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.active_hypotheses = {"h1": _hypothesis_obj()}
        mock_engine.hypothesis_history = []
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.delete("/api/v1/root-cause/hypotheses/h1")
        assert response.status_code == 200
        assert "h1" in response.json()["message"]

    def test_delete_not_found(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.active_hypotheses = {}
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.delete("/api/v1/root-cause/hypotheses/h1")
        assert response.status_code == 404

    def test_learn_pattern_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.learn_historical_pattern.return_value = None
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.post(
            "/api/v1/root-cause/patterns/learn",
            json={
                "symptoms": {"cpu": 90},
                "root_cause": "CPU",
                "resolution_time": 5.0,
                "effectiveness": 0.9,
            },
        )
        assert response.status_code == 200

    def test_get_historical_patterns_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.historical_patterns = {"p1": _pattern_obj()}
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.get("/api/v1/root-cause/patterns")
        assert response.status_code == 200
        assert response.json()["total_patterns"] == 1

    def test_get_root_cause_statistics_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.get_analysis_statistics.return_value = {"total": 1}
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.get("/api/v1/root-cause/statistics")
        assert response.status_code == 200

    def test_match_historical_patterns_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.match_historical_patterns = AsyncMock(return_value=[_pattern_obj()])
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.post(
            "/api/v1/root-cause/patterns/match",
            json={"symptoms": {"cpu": 90}, "similarity_threshold": 0.5},
        )
        assert response.status_code == 200

    def test_discover_topology_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.discover_topology_realtime = AsyncMock(return_value={"nodes": 1})
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.post(
            "/api/v1/root-cause/topology/discover",
            json={"metrics_data": {"cpu": 90}, "include_dependencies": True},
        )
        assert response.status_code == 200

    def test_cross_layer_tracking_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.perform_cross_layer_tracking = AsyncMock(return_value=["n1", "n2"])
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.post(
            "/api/v1/root-cause/cross-layer-track",
            json={"id": "a1"},
            params={"max_depth": 3},
        )
        assert response.status_code == 200

    def test_analyze_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.analyze_root_causes_enhanced = AsyncMock(return_value=[_hypothesis_obj()])
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.post(
            "/api/v1/root-cause/analyze",
            json={"alert": {"id": "a1"}, "metrics_data": {"cpu": 90}, "context": {}},
        )
        assert response.status_code == 200

    def test_predict_success(self, client, monkeypatch):
        mock_engine = MagicMock()
        mock_engine.predict_root_causes = AsyncMock(return_value={"trend": "up"})
        monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
        monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", mock_engine)
        response = client.post(
            "/api/v1/root-cause/predict",
            json={"current_state": {"cpu": 90}, "prediction_horizon": 60},
        )
        assert response.status_code == 200
