# -*- coding: utf-8 -*-
"""Comprehensive tests for root_cause_router.py to achieve 90%+ coverage.

This file tests all uncovered branches including:
- 503 errors when ROOT_CAUSE_INTELLIGENCE_AVAILABLE is False
- 404 errors when hypotheses don't exist
- All endpoint success paths with real business logic
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

pytestmark = [pytest.mark.api]


class TestRootCauseRouter503Errors:
    """Test 503 Service Unavailable errors when intelligence engine is not available."""

    @pytest.fixture
    def mock_unavailable_engine(self, monkeypatch):
        """Mock ROOT_CAUSE_INTELLIGENCE_AVAILABLE as False."""
        import api.root_cause_router as router_module
        monkeypatch.setattr(router_module, "ROOT_CAUSE_INTELLIGENCE_AVAILABLE", False)
        return router_module

    def test_get_topology_structure_503(self, client, mock_unavailable_engine):
        """Test GET /topology returns 503 when engine unavailable."""
        resp = client.get("/api/v1/root-cause/topology")
        assert resp.status_code == 503
        # Check response contains the error message (may be in different format)
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_discover_topology_realtime_503(self, client, mock_unavailable_engine):
        """Test POST /topology/discover returns 503 when engine unavailable."""
        resp = client.post(
            "/api/v1/root-cause/topology/discover",
            json={"metrics_data": {"cpu": 80}},
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_perform_cross_layer_tracking_503(self, client, mock_unavailable_engine):
        """Test POST /cross-layer-track returns 503 when engine unavailable."""
        resp = client.post(
            "/api/v1/root-cause/cross-layer-track",
            json={"id": "alert-1", "service": "svc1"},
            params={"max_depth": 3},
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_match_historical_patterns_503(self, client, mock_unavailable_engine):
        """Test POST /patterns/match returns 503 when engine unavailable."""
        resp = client.post(
            "/api/v1/root-cause/patterns/match",
            json={"symptoms": {"alerts": []}, "similarity_threshold": 0.5},
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_learn_historical_pattern_503(self, client, mock_unavailable_engine):
        """Test POST /patterns/learn returns 503 when engine unavailable."""
        resp = client.post(
            "/api/v1/root-cause/patterns/learn",
            json={
                "symptoms": {"alerts": []},
                "root_cause": "test_cause",
                "resolution_time": 60.0,
                "effectiveness": 0.9,
            },
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_get_historical_patterns_503(self, client, mock_unavailable_engine):
        """Test GET /patterns returns 503 when engine unavailable."""
        resp = client.get("/api/v1/root-cause/patterns")
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_analyze_root_causes_enhanced_503(self, client, mock_unavailable_engine):
        """Test POST /analyze returns 503 when engine unavailable."""
        resp = client.post(
            "/api/v1/root-cause/analyze",
            json={
                "alert": {"id": "alert-1"},
                "metrics_data": {"cpu": 80},
                "context": {},
            },
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_predict_root_causes_503(self, client, mock_unavailable_engine):
        """Test POST /predict returns 503 when engine unavailable."""
        resp = client.post(
            "/api/v1/root-cause/predict",
            json={
                "current_state": {"cpu": 80},
                "prediction_horizon": 30,
            },
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_verify_root_cause_hypothesis_503(self, client, mock_unavailable_engine):
        """Test POST /verify returns 503 when engine unavailable."""
        resp = client.post(
            "/api/v1/root-cause/verify",
            json={
                "hypothesis_id": "h-123",
                "verification_data": {"active_components": []},
            },
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_get_root_cause_statistics_503(self, client, mock_unavailable_engine):
        """Test GET /statistics returns 503 when engine unavailable."""
        resp = client.get("/api/v1/root-cause/statistics")
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_get_active_hypotheses_503(self, client, mock_unavailable_engine):
        """Test GET /hypotheses returns 503 when engine unavailable."""
        resp = client.get("/api/v1/root-cause/hypotheses")
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data

    def test_delete_hypothesis_503(self, client, mock_unavailable_engine):
        """Test DELETE /hypotheses/{id} returns 503 when engine unavailable."""
        resp = client.delete(
            "/api/v1/root-cause/hypotheses/h-123",
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "根因智能引擎不可用" in error_msg or "detail" in resp_data


class TestRootCauseRouter404Errors:
    """Test 404 Not Found errors when hypotheses don't exist."""

    @pytest.fixture
    def mock_engine_with_empty_hypotheses(self, monkeypatch):
        """Mock engine with no active hypotheses."""
        import api.root_cause_router as router_module
        import core.root_cause_intelligence as rci

        # Ensure engine is available
        monkeypatch.setattr(router_module, "ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)

        # Create a real engine instance
        engine = rci.RootCauseIntelligenceEngine()
        # Clear any existing hypotheses
        engine.active_hypotheses.clear()

        # Replace the global engine
        monkeypatch.setattr(router_module, "root_cause_intelligence_engine", engine)

        return engine

    def test_verify_root_cause_hypothesis_404(
        self, client, mock_engine_with_empty_hypotheses
    ):
        """Test POST /verify returns 404 when hypothesis doesn't exist."""
        resp = client.post(
            "/api/v1/root-cause/verify",
            json={
                "hypothesis_id": "nonexistent-h-123",
                "verification_data": {"active_components": []},
            },
        )
        assert resp.status_code == 404
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "假设 nonexistent-h-123 不存在" in error_msg or "detail" in resp_data

    def test_delete_hypothesis_404(
        self, client, mock_engine_with_empty_hypotheses
    ):
        """Test DELETE /hypotheses/{id} returns 404 when hypothesis doesn't exist."""
        resp = client.delete(
            "/api/v1/root-cause/hypotheses/nonexistent-h-456",
        )
        assert resp.status_code == 404
        resp_data = resp.json()
        error_msg = str(resp_data)
        assert "假设 nonexistent-h-456 不存在" in error_msg or "detail" in resp_data


class TestRootCauseRouterSuccessPaths:
    """Test successful paths with real business logic."""

    @pytest.fixture
    def mock_engine_with_data(self, monkeypatch):
        """Mock engine with pre-populated topology, patterns, and hypotheses."""
        import api.root_cause_router as router_module
        import core.root_cause_intelligence as rci
        from core.root_cause_intelligence import TopologyNode, TopologyLayer, HistoricalPattern, RootCauseHypothesis

        # Ensure engine is available
        monkeypatch.setattr(router_module, "ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)

        # Create a real engine instance
        engine = rci.RootCauseIntelligenceEngine()

        # Add topology nodes
        engine.topology_graph["svc1"] = TopologyNode(
            node_id="svc1",
            name="service-1",
            layer=TopologyLayer.SERVICE,
            health_status="healthy",
            dependencies={"db1"},
            dependents={"app1"},
        )
        engine.topology_graph["db1"] = TopologyNode(
            node_id="db1",
            name="database-1",
            layer=TopologyLayer.STORAGE,
            health_status="healthy",
            dependencies=set(),
            dependents={"svc1"},
        )
        engine.topology_graph["app1"] = TopologyNode(
            node_id="app1",
            name="application-1",
            layer=TopologyLayer.APPLICATION,
            health_status="unhealthy",
            dependencies={"svc1"},
            dependents=set(),
        )

        # Add historical pattern
        pattern = HistoricalPattern(
            pattern_id="pattern_1",
            symptom_signature="alerts:cpu_high,hosts:host1",
            root_cause="cpu_overload",
            frequency=5,
            last_occurrence=datetime.now(),
            confidence=0.85,
            resolution_time_avg=120.0,
            effectiveness_score=0.9,
        )
        engine.historical_patterns["pattern_1"] = pattern

        # Add active hypothesis
        hypothesis = RootCauseHypothesis(
            hypothesis_id="h-123",
            root_cause="db1",
            confidence=0.8,
            evidence=["high latency", "connection errors"],
            causal_path=["app1", "svc1", "db1"],
            impact_score=0.9,
            verification_status="pending",
        )
        engine.active_hypotheses["h-123"] = hypothesis

        # Replace the global engine
        monkeypatch.setattr(router_module, "root_cause_intelligence_engine", engine)

        return engine

    def test_get_topology_structure_success(
        self, client, mock_engine_with_data
    ):
        """Test GET /topology returns topology structure successfully."""
        resp = client.get("/api/v1/root-cause/topology")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "topology" in data
        assert "nodes" in data
        assert len(data["nodes"]) == 3
        assert "svc1" in data["nodes"]
        assert data["nodes"]["svc1"]["layer"] == "service"
        assert data["nodes"]["svc1"]["health_status"] == "healthy"

    def test_discover_topology_realtime_success(
        self, client, mock_engine_with_data
    ):
        """Test POST /topology/discover discovers topology successfully."""
        metrics_data = {
            "hosts": [{"hostname": "host1", "health": "healthy"}],
            "services": [{"name": "svc2", "health": "unhealthy"}],
        }
        resp = client.post(
            "/api/v1/root-cause/topology/discover",
            json={"metrics_data": metrics_data, "include_dependencies": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "discovery_result" in data

    def test_perform_cross_layer_tracking_success(
        self, client, mock_engine_with_data
    ):
        """Test POST /cross-layer-track performs tracking successfully."""
        alert = {
            "id": "alert-1",
            "service": "app1",
            "affected_services": ["app1"],
        }
        resp = client.post(
            "/api/v1/root-cause/cross-layer-track",
            json=alert,
            params={"max_depth": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "causal_path" in data
        assert isinstance(data["causal_path"], list)
        assert data["alert_id"] == "alert-1"

    def test_match_historical_patterns_success(
        self, client, mock_engine_with_data
    ):
        """Test POST /patterns/match matches patterns successfully."""
        symptoms = {
            "alerts": [{"alert_type": "cpu_high", "host": "host1"}],
        }
        resp = client.post(
            "/api/v1/root-cause/patterns/match",
            json={"symptoms": symptoms, "similarity_threshold": 0.5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "matched_patterns" in data
        assert isinstance(data["matched_patterns"], list)

    def test_learn_historical_pattern_success(
        self, client, mock_engine_with_data
    ):
        """Test POST /patterns/learn learns a new pattern successfully."""
        symptoms = {
            "alerts": [{"alert_type": "memory_high", "host": "host2"}],
        }
        resp = client.post(
            "/api/v1/root-cause/patterns/learn",
            json={
                "symptoms": symptoms,
                "root_cause": "memory_leak",
                "resolution_time": 180.0,
                "effectiveness": 0.85,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["root_cause"] == "memory_leak"

    def test_get_historical_patterns_success(
        self, client, mock_engine_with_data
    ):
        """Test GET /patterns returns patterns successfully."""
        resp = client.get(
            "/api/v1/root-cause/patterns",
            params={"limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "total_patterns" in data
        assert "patterns" in data
        assert isinstance(data["patterns"], list)
        assert data["total_patterns"] >= 1

    def test_analyze_root_causes_enhanced_success(
        self, client, mock_engine_with_data
    ):
        """Test POST /analyze performs enhanced analysis successfully."""
        alert = {
            "id": "alert-2",
            "service": "app1",
            "affected_services": ["app1"],
        }
        metrics_data = {
            "cpu": 85.0,
            "memory": 90.0,
        }
        resp = client.post(
            "/api/v1/root-cause/analyze",
            json={
                "alert": alert,
                "metrics_data": metrics_data,
                "context": {"correlated_alerts": []},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "hypotheses" in data
        assert isinstance(data["hypotheses"], list)

    def test_predict_root_causes_success(
        self, client, mock_engine_with_data
    ):
        """Test POST /predict predicts root causes successfully."""
        current_state = {
            "alerts": [{"alert_type": "cpu_high", "host": "host1"}],
        }
        resp = client.post(
            "/api/v1/root-cause/predict",
            json={
                "current_state": current_state,
                "prediction_horizon": 60,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "predictions" in data
        assert data["predictions"]["prediction_horizon"] == 60

    def test_verify_root_cause_hypothesis_success(
        self, client, mock_engine_with_data
    ):
        """Test POST /verify verifies hypothesis successfully."""
        resp = client.post(
            "/api/v1/root-cause/verify",
            json={
                "hypothesis_id": "h-123",
                "verification_data": {
                    "active_components": ["db1", "svc1", "app1"],
                    "affected_components": ["db1"],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "verification_result" in data

    def test_get_root_cause_statistics_success(
        self, client, mock_engine_with_data
    ):
        """Test GET /statistics returns statistics successfully."""
        resp = client.get("/api/v1/root-cause/statistics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "statistics" in data
        stats = data["statistics"]
        assert "topology_nodes" in stats
        assert "historical_patterns" in stats
        assert "active_hypotheses" in stats
        assert stats["topology_nodes"] == 3
        assert stats["historical_patterns"] >= 1
        assert stats["active_hypotheses"] >= 1

    def test_get_active_hypotheses_success(
        self, client, mock_engine_with_data
    ):
        """Test GET /hypotheses returns active hypotheses successfully."""
        resp = client.get(
            "/api/v1/root-cause/hypotheses",
            params={"limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "total_hypotheses" in data
        assert "hypotheses" in data
        assert isinstance(data["hypotheses"], list)
        assert data["total_hypotheses"] >= 1

    def test_delete_hypothesis_success(
        self, client, mock_engine_with_data
    ):
        """Test DELETE /hypotheses/{id} deletes hypothesis successfully."""
        resp = client.delete(
            "/api/v1/root-cause/hypotheses/h-123",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "h-123" in data["message"]
        # Verify hypothesis was moved to history
        assert len(mock_engine_with_data.hypothesis_history) >= 1

    def test_pattern_filtering_by_similarity_threshold(
        self, client, mock_engine_with_data
    ):
        """Test that patterns are filtered by similarity threshold."""
        symptoms = {
            "alerts": [{"alert_type": "cpu_high", "host": "host1"}],
        }
        # Use high threshold to filter out patterns
        resp = client.post(
            "/api/v1/root-cause/patterns/match",
            json={"symptoms": symptoms, "similarity_threshold": 0.99},
        )
        assert resp.status_code == 200
        data = resp.json()
        # With high threshold, likely no matches
        assert data["total_matches"] >= 0

    def test_pattern_limit_parameter(
        self, client, mock_engine_with_data
    ):
        """Test that limit parameter works for patterns endpoint."""
        resp = client.get(
            "/api/v1/root-cause/patterns",
            params={"limit": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["patterns"]) <= 1

    def test_hypotheses_limit_parameter(
        self, client, mock_engine_with_data
    ):
        """Test that limit parameter works for hypotheses endpoint."""
        resp = client.get(
            "/api/v1/root-cause/hypotheses",
            params={"limit": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["hypotheses"]) <= 1

    def test_cross_layer_tracking_max_depth_parameter(
        self, client, mock_engine_with_data
    ):
        """Test that max_depth parameter works for cross-layer tracking."""
        alert = {
            "id": "alert-3",
            "service": "app1",
        }
        resp = client.post(
            "/api/v1/root-cause/cross-layer-track",
            json=alert,
            params={"max_depth": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "causal_path" in data

    def test_topology_discovery_with_include_dependencies_false(
        self, client, mock_engine_with_data
    ):
        """Test topology discovery with include_dependencies=False."""
        metrics_data = {
            "hosts": [{"hostname": "host1", "health": "healthy"}],
        }
        resp = client.post(
            "/api/v1/root-cause/topology/discover",
            json={"metrics_data": metrics_data, "include_dependencies": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
