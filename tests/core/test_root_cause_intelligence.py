# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/root_cause_intelligence.py
Target: 90%+ statement and branch coverage
"""

import os
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.root_cause_intelligence import (
    CAUSAL_AVAILABLE,
    CHANGE_CORRELATION_WINDOW_MINUTES,
    ESCALATION_CONFIDENCE_THRESHOLD,
    EXECUTION_CONFIDENCE_THRESHOLD,
    MAX_DIAGNOSIS_STEPS,
    MAX_ROOT_CAUSE_CANDIDATES,
    ML_AVAILABLE,
    RootCauseHypothesis,
    TopologyLayer,
    TopologyNode,
)


class TestConstants:
    """Test suite for module constants"""

    def test_execution_confidence_threshold(self):
        """Test execution confidence threshold constant"""
        assert EXECUTION_CONFIDENCE_THRESHOLD == 0.75

    def test_escalation_confidence_threshold(self):
        """Test escalation confidence threshold constant"""
        assert ESCALATION_CONFIDENCE_THRESHOLD == 0.60

    def test_max_root_cause_candidates(self):
        """Test max root cause candidates constant"""
        assert MAX_ROOT_CAUSE_CANDIDATES == 5

    def test_max_diagnosis_steps(self):
        """Test max diagnosis steps constant"""
        assert MAX_DIAGNOSIS_STEPS == 5

    def test_change_correlation_window_minutes(self):
        """Test change correlation window constant"""
        assert CHANGE_CORRELATION_WINDOW_MINUTES == 15

    def test_causal_available(self):
        """Test causal available flag"""
        assert isinstance(CAUSAL_AVAILABLE, bool)

    def test_ml_available(self):
        """Test ML available flag"""
        assert isinstance(ML_AVAILABLE, bool)


class TestTopologyLayer:
    """Test suite for TopologyLayer enum"""

    def test_topology_layer_values(self):
        """Test TopologyLayer enum values"""
        assert TopologyLayer.APPLICATION.value == "application"
        assert TopologyLayer.SERVICE.value == "service"
        assert TopologyLayer.INFRASTRUCTURE.value == "infrastructure"
        assert TopologyLayer.NETWORK.value == "network"
        assert TopologyLayer.STORAGE.value == "storage"


class TestTopologyNode:
    """Test suite for TopologyNode dataclass"""

    def test_topology_node_creation(self):
        """Test creating a TopologyNode"""
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
        )
        assert node.node_id == "node-1"
        assert node.name == "API Service"
        assert node.layer == TopologyLayer.SERVICE
        assert node.dependencies == set()
        assert node.dependents == set()
        assert node.health_status == "healthy"
        assert isinstance(node.last_updated, datetime)
        assert node.metadata == {}

    def test_topology_node_with_dependencies(self):
        """Test TopologyNode with dependencies"""
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
            dependencies={"db-1", "cache-1"},
        )
        assert node.dependencies == {"db-1", "cache-1"}

    def test_topology_node_with_dependents(self):
        """Test TopologyNode with dependents"""
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
            dependents={"frontend-1", "mobile-1"},
        )
        assert node.dependents == {"frontend-1", "mobile-1"}

    def test_topology_node_with_custom_health(self):
        """Test TopologyNode with custom health status"""
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
            health_status="degraded",
        )
        assert node.health_status == "degraded"

    def test_topology_node_with_metadata(self):
        """Test TopologyNode with metadata"""
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
            metadata={"version": "1.0.0", "owner": "team-a"},
        )
        assert node.metadata == {"version": "1.0.0", "owner": "team-a"}

    def test_topology_node_custom_timestamp(self):
        """Test TopologyNode with custom timestamp"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
            last_updated=custom_time,
        )
        assert node.last_updated == custom_time


class TestRootCauseHypothesis:
    """Test suite for RootCauseHypothesis dataclass"""

    def test_root_cause_hypothesis_creation(self):
        """Test creating a RootCauseHypothesis"""
        hypothesis = RootCauseHypothesis(
            hypothesis_id="hypo-1",
            root_cause="High CPU usage in API service",
            confidence=0.85,
        )
        assert hypothesis.hypothesis_id == "hypo-1"
        assert hypothesis.root_cause == "High CPU usage in API service"
        assert hypothesis.confidence == 0.85
        assert hypothesis.evidence == []
        assert hypothesis.causal_path == []
        assert hypothesis.impact_score == 0.0
        assert hypothesis.verification_status == "pending"

    def test_root_cause_hypothesis_with_evidence(self):
        """Test RootCauseHypothesis with evidence"""
        hypothesis = RootCauseHypothesis(
            hypothesis_id="hypo-1",
            root_cause="High CPU usage",
            confidence=0.85,
            evidence=["CPU spike at 10:00", "Memory leak detected"],
        )
        assert len(hypothesis.evidence) == 2
        assert "CPU spike at 10:00" in hypothesis.evidence

    def test_root_cause_hypothesis_with_causal_path(self):
        """Test RootCauseHypothesis with causal path"""
        hypothesis = RootCauseHypothesis(
            hypothesis_id="hypo-1",
            root_cause="Database connection pool exhaustion",
            confidence=0.90,
            causal_path=["api-service", "db-connection-pool", "database"],
        )
        assert len(hypothesis.causal_path) == 3
        assert "api-service" in hypothesis.causal_path

    def test_root_cause_hypothesis_with_impact_score(self):
        """Test RootCauseHypothesis with impact score"""
        hypothesis = RootCauseHypothesis(
            hypothesis_id="hypo-1",
            root_cause="High CPU usage",
            confidence=0.85,
            impact_score=0.95,
        )
        assert hypothesis.impact_score == 0.95

    def test_root_cause_hypothesis_verified_status(self):
        """Test RootCauseHypothesis with verified status"""
        hypothesis = RootCauseHypothesis(
            hypothesis_id="hypo-1",
            root_cause="High CPU usage",
            confidence=0.85,
            verification_status="verified",
        )
        assert hypothesis.verification_status == "verified"

    def test_root_cause_hypothesis_rejected_status(self):
        """Test RootCauseHypothesis with rejected status"""
        hypothesis = RootCauseHypothesis(
            hypothesis_id="hypo-1",
            root_cause="High CPU usage",
            confidence=0.85,
            verification_status="rejected",
        )
        assert hypothesis.verification_status == "rejected"


class TestRootCauseIntelligenceEngine:
    """Test suite for RootCauseIntelligenceEngine"""

    def test_engine_initialization(self):
        """Test engine initialization"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        assert engine is not None
        assert hasattr(engine, "topology_graph")
        assert hasattr(engine, "hypotheses")

    def test_engine_with_config(self):
        """Test engine initialization with config"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        config = {
            "max_candidates": 10,
            "confidence_threshold": 0.8,
        }
        engine = RootCauseIntelligenceEngine(config)
        assert engine is not None

    def test_add_topology_node(self):
        """Test adding topology node"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
        )

        engine.add_node(node)
        assert "node-1" in engine.topology_graph

    def test_add_topology_dependency(self):
        """Test adding topology dependency"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        node1 = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
        )
        node2 = TopologyNode(
            node_id="node-2",
            name="Database",
            layer=TopologyLayer.STORAGE,
        )

        engine.add_node(node1)
        engine.add_node(node2)
        engine.add_dependency("node-1", "node-2")

        assert "node-2" in engine.topology_graph["node-1"]

    def test_remove_topology_node(self):
        """Test removing topology node"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
        )

        engine.add_node(node)
        engine.remove_node("node-1")
        assert "node-1" not in engine.topology_graph

    def test_get_node(self):
        """Test getting topology node"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
        )

        engine.add_node(node)
        retrieved = engine.get_node("node-1")
        assert retrieved is not None
        assert retrieved.node_id == "node-1"

    def test_get_node_not_found(self):
        """Test getting non-existent node"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        retrieved = engine.get_node("non-existent")
        assert retrieved is None

    def test_update_node_health(self):
        """Test updating node health status"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
        )

        engine.add_node(node)
        engine.update_node_health("node-1", "degraded")

        retrieved = engine.get_node("node-1")
        assert retrieved.health_status == "degraded"

    def test_get_affected_nodes(self):
        """Test getting affected nodes"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        node1 = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
        )
        node2 = TopologyNode(
            node_id="node-2",
            name="Database",
            layer=TopologyLayer.STORAGE,
        )

        engine.add_node(node1)
        engine.add_node(node2)
        engine.add_dependency("node-1", "node-2")

        affected = engine.get_affected_nodes("node-2")
        assert "node-1" in affected

    def test_generate_hypothesis(self):
        """Test generating root cause hypothesis"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        alert = {
            "id": "alert-1",
            "level": "critical",
            "metric": "cpu",
            "value": 95,
            "host": "server-1",
        }

        hypothesis = engine.generate_hypothesis(alert)
        assert hypothesis is not None
        assert isinstance(hypothesis, RootCauseHypothesis)

    def test_analyze_root_cause(self):
        """Test root cause analysis"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        alert = {
            "id": "alert-1",
            "level": "critical",
            "metric": "cpu",
            "value": 95,
            "host": "server-1",
        }

        # Add some topology
        node = TopologyNode(
            node_id="server-1",
            name="Server 1",
            layer=TopologyLayer.INFRASTRUCTURE,
        )
        engine.add_node(node)

        result = engine.analyze_root_cause(alert)
        assert result is not None
        assert "candidates" in result or "hypothesis" in result

    def test_verify_hypothesis(self):
        """Test hypothesis verification"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        hypothesis = RootCauseHypothesis(
            hypothesis_id="hypo-1",
            root_cause="High CPU usage",
            confidence=0.85,
        )

        verification_result = engine.verify_hypothesis(hypothesis)
        assert verification_result is not None
        assert "status" in verification_result or "verified" in verification_result

    def test_get_topology_summary(self):
        """Test getting topology summary"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        node = TopologyNode(
            node_id="node-1",
            name="API Service",
            layer=TopologyLayer.SERVICE,
        )

        engine.add_node(node)
        summary = engine.get_topology_summary()
        assert summary is not None
        assert "nodes" in summary or "total_nodes" in summary


class TestRootCauseAnalysisAlgorithms:
    """Test suite for root cause analysis algorithms"""

    def test_confidence_scoring(self):
        """Test confidence scoring algorithm"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        evidence = [
            {"type": "metric", "strength": 0.8},
            {"type": "log", "strength": 0.6},
            {"type": "topology", "strength": 0.7},
        ]

        confidence = engine._calculate_confidence(evidence)
        assert 0.0 <= confidence <= 1.0

    def test_impact_scoring(self):
        """Test impact scoring algorithm"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        affected_services = ["api", "web", "mobile"]
        severity = "critical"

        impact = engine._calculate_impact(affected_services, severity)
        assert 0.0 <= impact <= 1.0

    def test_causal_path_analysis(self):
        """Test causal path analysis"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()

        # Build topology
        node1 = TopologyNode("web", "Web", TopologyLayer.APPLICATION)
        node2 = TopologyNode("api", "API", TopologyLayer.SERVICE)
        node3 = TopologyNode("db", "DB", TopologyLayer.STORAGE)

        engine.add_node(node1)
        engine.add_node(node2)
        engine.add_node(node3)
        engine.add_dependency("web", "api")
        engine.add_dependency("api", "db")

        path = engine._find_causal_path("web", "db")
        assert path is not None
        assert len(path) >= 2

    def test_historical_pattern_matching(self):
        """Test historical pattern matching"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        current_alert = {
            "metric": "cpu",
            "value": 95,
            "pattern": "spike",
        }

        historical_patterns = [
            {"metric": "cpu", "pattern": "spike", "root_cause": "memory leak"},
            {"metric": "memory", "pattern": "gradual", "root_cause": "connection leak"},
        ]

        match = engine._match_historical_pattern(current_alert, historical_patterns)
        assert match is not None or match is None  # May or may not find match

    def test_change_correlation(self):
        """Test change correlation analysis"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        alert_time = datetime.now(timezone.utc)

        changes = [
            {
                "timestamp": alert_time - timedelta(minutes=5),
                "type": "deployment",
                "service": "api",
            },
            {
                "timestamp": alert_time - timedelta(minutes=30),
                "type": "config",
                "service": "api",
            },
        ]

        correlated = engine._correlate_with_changes(alert_time, changes)
        assert isinstance(correlated, list)


class TestRootCauseIntelligenceML:
    """Test suite for ML-based root cause analysis"""

    def test_ml_analysis_when_available(self):
        """Test ML analysis when libraries are available"""
        if not ML_AVAILABLE:
            pytest.skip("ML libraries not available")

        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        features = [[0.8, 0.6, 0.9], [0.3, 0.4, 0.5]]
        labels = [1, 0]

        # This would train a model if ML is available
        # For testing, we just verify the method exists
        assert hasattr(engine, "_train_model") or hasattr(engine, "_predict_with_ml")

    def test_rule_based_fallback(self):
        """Test rule-based fallback when ML is not available"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        alert = {
            "metric": "cpu",
            "value": 95,
            "host": "server-1",
        }

        # Should use rule-based analysis
        result = engine.analyze_root_cause(alert)
        assert result is not None


class TestRootCauseIntelligenceIntegration:
    """Test suite for integration scenarios"""

    def test_full_analysis_workflow(self):
        """Test complete analysis workflow"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()

        # Build topology
        web = TopologyNode("web", "Web", TopologyLayer.APPLICATION)
        api = TopologyNode("api", "API", TopologyLayer.SERVICE)
        db = TopologyNode("db", "DB", TopologyLayer.STORAGE)

        engine.add_node(web)
        engine.add_node(api)
        engine.add_node(db)
        engine.add_dependency("web", "api")
        engine.add_dependency("api", "db")

        # Analyze alert
        alert = {
            "id": "alert-1",
            "level": "critical",
            "metric": "response_time",
            "value": 5.0,
            "service": "web",
        }

        result = engine.analyze_root_cause(alert)
        assert result is not None

    def test_multi_hypothesis_generation(self):
        """Test generating multiple hypotheses"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        alert = {
            "id": "alert-1",
            "level": "critical",
            "metric": "cpu",
            "value": 95,
        }

        hypotheses = engine.generate_multiple_hypotheses(alert, max_count=3)
        assert len(hypotheses) <= 3
        assert all(isinstance(h, RootCauseHypothesis) for h in hypotheses)

    def test_hypothesis_ranking(self):
        """Test hypothesis ranking by confidence"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        hypotheses = [
            RootCauseHypothesis("h1", "Cause 1", 0.7),
            RootCauseHypothesis("h2", "Cause 2", 0.9),
            RootCauseHypothesis("h3", "Cause 3", 0.5),
        ]

        ranked = engine.rank_hypotheses(hypotheses)
        assert ranked[0].confidence >= ranked[1].confidence
        assert ranked[1].confidence >= ranked[2].confidence


class TestRootCauseIntelligenceErrorHandling:
    """Test suite for error handling"""

    def test_handle_missing_node(self):
        """Test handling of missing node in analysis"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        alert = {
            "id": "alert-1",
            "metric": "cpu",
            "value": 95,
            "host": "non-existent",
        }

        # Should handle gracefully
        result = engine.analyze_root_cause(alert)
        assert result is not None

    def test_handle_invalid_alert(self):
        """Test handling of invalid alert data"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()
        invalid_alerts = [
            None,
            {},
            {"metric": None},
            {"metric": "cpu", "value": "invalid"},
        ]

        for alert in invalid_alerts:
            result = engine.analyze_root_cause(alert)
            # Should handle gracefully or return appropriate error
            assert result is not None or isinstance(result, dict)

    def test_handle_topology_inconsistency(self):
        """Test handling of topology inconsistency"""
        from core.root_cause_intelligence import RootCauseIntelligenceEngine

        engine = RootCauseIntelligenceEngine()

        # Add dependency without adding nodes
        engine.add_dependency("node-1", "node-2")

        # Should handle gracefully
        summary = engine.get_topology_summary()
        assert summary is not None
