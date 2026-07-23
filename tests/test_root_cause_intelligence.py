# -*- coding: utf-8 -*-
"""
Unit Tests for Root Cause Intelligence
======================================

Comprehensive unit tests for the root cause intelligence module.
"""

import asyncio
from datetime import datetime, timedelta  # noqa: F401
from typing import Any, Dict, List  # noqa: F401

import pytest

try:
    from core.root_cause_intelligence import (
        CausalEdge,
        CausalGraph,
        CausalNode,
        HistoricalPattern,
        RootCauseIntelligence,
        RootCausePrediction,
    )

    ROOT_CAUSE_AVAILABLE = True
except ImportError:
    ROOT_CAUSE_AVAILABLE = False


@pytest.mark.skipif(not ROOT_CAUSE_AVAILABLE, reason="Root cause intelligence not available")
class TestRootCauseIntelligence:
    """Test suite for RootCauseIntelligence"""

    @pytest.fixture
    def root_cause_intel(self):
        """Fixture for RootCauseIntelligence instance"""
        return RootCauseIntelligence()

    @pytest.fixture
    def sample_topology(self):
        """Fixture for sample topology data"""
        return {
            "nodes": [
                {"id": "service_a", "type": "service", "name": "Service A"},
                {"id": "service_b", "type": "service", "name": "Service B"},
                {"id": "database", "type": "database", "name": "Database"},
                {"id": "cache", "type": "cache", "name": "Cache"},
            ],
            "edges": [
                {"source": "service_a", "target": "database", "relation": "depends_on"},
                {"source": "service_b", "target": "database", "relation": "depends_on"},
                {"source": "service_a", "target": "cache", "relation": "uses"},
            ],
        }

    @pytest.fixture
    def sample_alerts(self):
        """Fixture for sample alerts"""
        return [
            {
                "alert_id": "alert_1",
                "component": "service_a",
                "severity": "critical",
                "message": "Service A is down",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "alert_id": "alert_2",
                "component": "database",
                "severity": "critical",
                "message": "Database connection failed",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "alert_id": "alert_3",
                "component": "service_b",
                "severity": "warning",
                "message": "Service B degraded",
                "timestamp": datetime.now().isoformat(),
            },
        ]

    def test_initialization(self, root_cause_intel):
        """Test that RootCauseIntelligence initializes correctly"""
        assert root_cause_intel is not None
        assert hasattr(root_cause_intel, "causal_graph")
        assert hasattr(root_cause_intel, "historical_patterns")
        assert hasattr(root_cause_intel, "root_cause_predictions")

    @pytest.mark.asyncio
    async def test_build_causal_graph(self, root_cause_intel, sample_topology):
        """Test building causal graph from topology"""
        graph = await root_cause_intel.build_causal_graph(sample_topology)

        assert graph is not None
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    @pytest.mark.asyncio
    async def test_analyze_root_cause(self, root_cause_intel, sample_alerts):
        """Test root cause analysis"""
        result = await root_cause_intel.analyze_root_cause(
            alerts=sample_alerts, context={"topology": "test"}
        )

        assert result is not None
        assert "root_cause" in result
        assert "confidence" in result
        assert "evidence" in result
        assert result["confidence"] >= 0

    @pytest.mark.asyncio
    async def test_correlate_alerts(self, root_cause_intel, sample_alerts):
        """Test alert correlation"""
        correlations = await root_cause_intel.correlate_alerts(sample_alerts)

        assert correlations is not None
        assert isinstance(correlations, list)
        # Check that correlations have the expected structure
        if correlations:
            assert "alert_group" in correlations[0]
            assert "correlation_score" in correlations[0]

    @pytest.mark.asyncio
    async def test_match_historical_pattern(self, root_cause_intel):
        """Test historical pattern matching"""
        current_alerts = [
            {
                "component": "database",
                "severity": "critical",
                "message": "Database connection failed",
            }
        ]

        pattern = await root_cause_intel.match_historical_pattern(current_alerts)

        assert pattern is not None
        assert "pattern_id" in pattern
        assert "similarity_score" in pattern
        assert pattern["similarity_score"] >= 0

    @pytest.mark.asyncio
    async def test_predict_root_cause(self, root_cause_intel, sample_alerts):
        """Test root cause prediction"""
        prediction = await root_cause_intel.predict_root_cause(
            current_alerts=sample_alerts, historical_data={"past_incidents": []}
        )

        assert prediction is not None
        assert "predicted_root_cause" in prediction
        assert "confidence" in prediction
        assert "prediction_timestamp" in prediction

    @pytest.mark.asyncio
    async def test_verify_root_cause(self, root_cause_intel):
        """Test root cause verification"""
        verification = await root_cause_intel.verify_root_cause(
            root_cause_hypothesis="Database failure", verification_data={"database_status": "down"}
        )

        assert verification is not None
        assert "verified" in verification
        assert "confidence" in verification
        assert "evidence" in verification

    def test_add_historical_pattern(self, root_cause_intel):
        """Test adding historical pattern"""
        pattern_data = {
            "pattern_id": "pattern_1",
            "alert_sequence": ["alert_a", "alert_b"],
            "root_cause": "component_c",
            "frequency": 5,
        }

        root_cause_intel.add_historical_pattern(pattern_data)

        assert len(root_cause_intel.historical_patterns) > 0
        assert root_cause_intel.historical_patterns[0].pattern_id == "pattern_1"

    def test_get_causal_path(self, root_cause_intel, sample_topology):
        """Test getting causal path between components"""
        # Build graph first
        asyncio.run(root_cause_intel.build_causal_graph(sample_topology))

        path = root_cause_intel.get_causal_path("service_a", "database")

        assert path is not None
        assert isinstance(path, list)


@pytest.mark.skipif(not ROOT_CAUSE_AVAILABLE, reason="Root cause intelligence not available")
class TestCausalGraph:
    """Test suite for CausalGraph"""

    def test_causal_graph_creation(self):
        """Test CausalGraph creation"""
        graph = CausalGraph()

        assert graph is not None
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self):
        """Test adding node to causal graph"""
        graph = CausalGraph()
        node = CausalNode(node_id="node_1", node_type="service", name="Test Service")

        graph.add_node(node)

        assert len(graph.nodes) == 1
        assert graph.nodes[0].node_id == "node_1"

    def test_add_edge(self):
        """Test adding edge to causal graph"""
        graph = CausalGraph()

        node_a = CausalNode(node_id="node_a", node_type="service", name="Service A")
        node_b = CausalNode(node_id="node_b", node_type="service", name="Service B")

        graph.add_node(node_a)
        graph.add_node(node_b)

        edge = CausalEdge(source="node_a", target="node_b", relation="depends_on", strength=0.8)

        graph.add_edge(edge)

        assert len(graph.edges) == 1
        assert graph.edges[0].source == "node_a"
        assert graph.edges[0].target == "node_b"


@pytest.mark.skipif(not ROOT_CAUSE_AVAILABLE, reason="Root cause intelligence not available")
class TestHistoricalPattern:
    """Test suite for HistoricalPattern"""

    def test_historical_pattern_creation(self):
        """Test HistoricalPattern creation"""
        pattern = HistoricalPattern(
            pattern_id="pattern_1",
            alert_sequence=["alert_a", "alert_b"],
            root_cause="component_c",
            frequency=10,
            last_seen=datetime.now(),
        )

        assert pattern.pattern_id == "pattern_1"
        assert len(pattern.alert_sequence) == 2
        assert pattern.root_cause == "component_c"
        assert pattern.frequency == 10


@pytest.mark.skipif(not ROOT_CAUSE_AVAILABLE, reason="Root cause intelligence not available")
class TestRootCausePrediction:
    """Test suite for RootCausePrediction"""

    def test_root_cause_prediction_creation(self):
        """Test RootCausePrediction creation"""
        prediction = RootCausePrediction(
            prediction_id="pred_1",
            predicted_root_cause="database_failure",
            confidence=0.85,
            prediction_timestamp=datetime.now(),
        )

        assert prediction.prediction_id == "pred_1"
        assert prediction.predicted_root_cause == "database_failure"
        assert prediction.confidence == 0.85
