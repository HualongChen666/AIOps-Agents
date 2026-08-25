# -*- coding: utf-8 -*-
"""
Simple comprehensive test suite for low coverage modules
Tests for 10 files with <90% coverage without database dependencies
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from modules.analyze.anomaly.isolation_forest import (
    IsolationForestDetector,
)
from modules.apm.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyDiscoverer,
    DependencyEdge,
    DependencyHealthAssessor,
    DependencyTopology,
    DependencyType,
    HealthStatus,
    ServiceNode,
    TopologyVisualizer,
)
from modules.execute.saga.participants import (
    APICallParticipant,
    CompensationAction,
    DatabaseParticipant,
    MessageQueueParticipant,
    NotificationParticipant,
    Participant,
    ResourceAllocationParticipant,
    create_compensation_action,
)

# Import modules under test
from modules.high_availability.self_healing import (
    FailureEvent,
    FailureType,
    RemediationAction,
    RemediationResult,
    SelfHealingEngine,
    SelfHealingPolicy,
    create_self_healing_engine,
)
from modules.observability.smart_alerting import (
    Alert,
    AlertAggregator,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    AlertSuppressor,
    DynamicThresholdCalculator,
    SmartAlertingEngine,
    create_smart_alerting_engine,
)
from modules.optimization.storage_optimizer import (
    DataCompressor,
    DataLifecycleManager,
    DataObject,
    StorageManager,
    StorageOptimizer,
    StorageStatistics,
    StorageType,
    create_data_compressor,
    create_data_lifecycle_manager,
    create_storage_manager,
    create_storage_optimizer,
)

# =============================================================================
# Tests for modules/high_availability/self_healing.py
# =============================================================================


class TestSelfHealingEngine:
    """Test SelfHealingEngine"""

    def test_engine_initialization(self):
        """Test engine initialization"""
        engine = SelfHealingEngine()
        assert len(engine.policies) > 0
        assert len(engine.action_handlers) > 0

    def test_add_policy(self):
        """Test adding policy"""
        engine = SelfHealingEngine()
        policy = SelfHealingPolicy(
            id="test-policy",
            name="Test Policy",
            failure_type=FailureType.SERVICE_DOWN,
            remediation_actions=[RemediationAction.RESTART_SERVICE],
        )
        engine.add_policy(policy)
        assert "test-policy" in engine.policies

    def test_remove_policy(self):
        """Test removing policy"""
        engine = SelfHealingEngine()
        engine.remove_policy("service-down-restart")
        assert "service-down-restart" not in engine.policies

    def test_detect_failure(self):
        """Test failure detection"""
        engine = SelfHealingEngine()
        event = engine.detect_failure(
            failure_type=FailureType.SERVICE_DOWN,
            component="web-service",
            severity="high",
            description="Service is down",
            metadata={"auto_restart": True},
        )
        assert isinstance(event, FailureEvent)
        assert event.failure_type == FailureType.SERVICE_DOWN
        assert len(engine.failure_history) > 0

    def test_trigger_self_healing_no_policy(self):
        """Test self-healing with no matching policy"""
        engine = SelfHealingEngine()
        event = FailureEvent(
            id="test-1",
            failure_type=FailureType.NETWORK_PARTITION,
            component="network",
            severity="critical",
            description="Network partition",
        )
        results = engine.trigger_self_healing(event)
        assert len(results) == 0

    def test_trigger_self_healing_with_policy(self):
        """Test self-healing with matching policy"""
        engine = SelfHealingEngine()
        event = engine.detect_failure(
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Service down",
            metadata={"auto_restart": True},
        )
        results = engine.trigger_self_healing(event)
        assert len(results) > 0
        assert isinstance(results[0], RemediationResult)

    def test_trigger_self_healing_cooldown(self):
        """Test self-healing cooldown period"""
        engine = SelfHealingEngine()
        event = engine.detect_failure(
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Service down",
            metadata={"auto_restart": True},
        )
        # First trigger
        engine.trigger_self_healing(event)
        # Immediate second trigger (should be in cooldown)
        results = engine.trigger_self_healing(event)
        assert len(results) == 0

    def test_sanitize_component_valid(self):
        """Test component name sanitization with valid name"""
        engine = SelfHealingEngine()
        result = engine._sanitize_component("valid-service_123")
        assert result == "valid-service_123"

    def test_sanitize_component_invalid(self):
        """Test component name sanitization with invalid name"""
        engine = SelfHealingEngine()
        with pytest.raises(ValueError):
            engine._sanitize_component("invalid;name")

    def test_verify_remediation(self):
        """Test remediation verification"""
        engine = SelfHealingEngine()
        event = FailureEvent(
            id="test-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test",
            severity="high",
            description="Test",
        )
        result = engine.verify_remediation(event)
        assert result is True

    def test_get_statistics(self):
        """Test statistics retrieval"""
        engine = SelfHealingEngine()
        engine.detect_failure(FailureType.SERVICE_DOWN, "test", "high", "Test")
        stats = engine.get_statistics()
        assert stats["total_failures"] > 0
        assert "success_rate" in stats

    def test_failure_event_to_dict(self):
        """Test FailureEvent serialization"""
        event = FailureEvent(
            id="test-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test",
            severity="high",
            description="Test",
        )
        data = event.to_dict()
        assert data["id"] == "test-1"
        assert data["failure_type"] == "service_down"

    def test_remediation_result_to_dict(self):
        """Test RemediationResult serialization"""
        result = RemediationResult(
            policy_id="test",
            action=RemediationAction.RESTART_SERVICE,
            success=True,
            message="Success",
        )
        data = result.to_dict()
        assert data["policy_id"] == "test"
        assert data["action"] == "restart_service"

    def test_policy_matches(self):
        """Test policy matching logic"""
        policy = SelfHealingPolicy(
            id="test",
            name="Test",
            failure_type=FailureType.SERVICE_DOWN,
            remediation_actions=[RemediationAction.RESTART_SERVICE],
            conditions={"auto_restart": True},
        )
        event = FailureEvent(
            id="test",
            failure_type=FailureType.SERVICE_DOWN,
            component="test",
            severity="high",
            description="Test",
            metadata={"auto_restart": True},
        )
        assert policy.matches(event) is True

    def test_policy_disabled(self):
        """Test disabled policy doesn't match"""
        policy = SelfHealingPolicy(
            id="test",
            name="Test",
            failure_type=FailureType.SERVICE_DOWN,
            remediation_actions=[RemediationAction.RESTART_SERVICE],
            enabled=False,
        )
        event = FailureEvent(
            id="test",
            failure_type=FailureType.SERVICE_DOWN,
            component="test",
            severity="high",
            description="Test",
        )
        assert policy.matches(event) is False

    def test_create_self_healing_engine(self):
        """Test factory function"""
        engine = create_self_healing_engine()
        assert isinstance(engine, SelfHealingEngine)


# =============================================================================
# Tests for modules/optimization/storage_optimizer.py
# =============================================================================


class TestStorageOptimizer:
    """Test StorageOptimizer and related classes"""

    def test_data_object_properties(self):
        """Test DataObject property calculations"""
        obj = DataObject(
            id="test-1",
            name="test.dat",
            size=1024,
            created_at=datetime.now() - timedelta(days=10),
            last_accessed=datetime.now() - timedelta(days=5),
            access_count=20,
        )
        assert obj.age_days >= 10
        assert obj.days_since_last_access >= 5

    def test_data_object_to_dict(self):
        """Test DataObject serialization"""
        obj = DataObject(id="test", name="test.dat", size=1024)
        data = obj.to_dict()
        assert data["id"] == "test"
        assert data["size"] == 1024

    def test_storage_manager_add_remove(self):
        """Test adding and removing objects"""
        manager = StorageManager()
        obj = DataObject(id="test", name="test.dat", size=1024)
        manager.add_object(obj)
        assert manager.get_object("test") is not None
        manager.remove_object("test")
        assert manager.get_object("test") is None

    def test_storage_manager_access(self):
        """Test object access tracking"""
        manager = StorageManager()
        obj = DataObject(id="test", name="test.dat", size=1024, access_count=5)
        manager.add_object(obj)
        manager.access_object("test")
        retrieved = manager.get_object("test")
        assert retrieved.access_count == 6

    def test_storage_manager_statistics(self):
        """Test storage statistics"""
        manager = StorageManager()
        manager.add_object(DataObject(id="1", name="a", size=1024, storage_type=StorageType.HOT))
        manager.add_object(DataObject(id="2", name="b", size=2048, storage_type=StorageType.COLD))
        stats = manager.get_statistics()
        assert stats.total_objects == 2
        assert stats.total_size == 3072

    def test_storage_manager_cost_estimation(self):
        """Test monthly cost estimation"""
        manager = StorageManager()
        # Add 1GB of hot storage
        manager.add_object(DataObject(id="1", name="a", size=1024**3, storage_type=StorageType.HOT))
        cost = manager.estimate_monthly_cost()
        assert cost > 0

    def test_storage_optimizer_tiering_analysis(self):
        """Test storage tiering analysis"""
        manager = StorageManager()
        optimizer = StorageOptimizer(manager)

        # Add objects with different access patterns
        manager.add_object(
            DataObject(
                id="hot",
                name="hot.dat",
                size=1024,
                created_at=datetime.now() - timedelta(days=1),
                last_accessed=datetime.now() - timedelta(hours=1),
                access_count=50,
            )
        )
        manager.add_object(
            DataObject(
                id="cold",
                name="cold.dat",
                size=1024,
                created_at=datetime.now() - timedelta(days=100),
                last_accessed=datetime.now() - timedelta(days=90),
                access_count=1,
            )
        )

        recommendations = optimizer.analyze_storage_tiering()
        assert isinstance(recommendations, dict)
        assert "hot" in recommendations or "cold" in recommendations

    def test_storage_optimizer_apply_tiering(self):
        """Test applying tiering recommendations"""
        manager = StorageManager()
        optimizer = StorageOptimizer(manager)

        obj = DataObject(id="test", name="test.dat", size=1024, storage_type=StorageType.HOT)
        manager.add_object(obj)

        recommendations = {"cold": ["test"]}
        results = optimizer.apply_tiering(recommendations)
        assert results["cold"] == 1
        assert manager.get_object("test").storage_type == StorageType.COLD

    def test_storage_optimizer_identify_unused(self):
        """Test identifying unused data"""
        manager = StorageManager()
        optimizer = StorageOptimizer(manager)

        manager.add_object(
            DataObject(
                id="unused",
                name="unused.dat",
                size=1024,
                last_accessed=datetime.now() - timedelta(days=100),
            )
        )

        unused = optimizer.identify_unused_data(days_threshold=90)
        assert len(unused) > 0
        assert unused[0].id == "unused"

    def test_storage_optimizer_suggest_deletion(self):
        """Test deletion suggestions"""
        manager = StorageManager()
        optimizer = StorageOptimizer(manager)

        manager.add_object(
            DataObject(
                id="large_old",
                name="large.dat",
                size=2 * 1024**3,  # 2GB
                last_accessed=datetime.now() - timedelta(days=200),
            )
        )

        candidates = optimizer.suggest_deletion(
            size_threshold=1024**3,  # 1GB
            days_threshold=180,
        )
        assert len(candidates) > 0

    def test_storage_optimizer_estimate_savings(self):
        """Test savings estimation"""
        manager = StorageManager()
        optimizer = StorageOptimizer(manager)

        manager.add_object(
            DataObject(
                id="test",
                name="test.dat",
                size=1024**3,  # 1GB
                storage_type=StorageType.HOT,
            )
        )

        recommendations = {"cold": ["test"]}
        savings = optimizer.estimate_savings(recommendations)
        assert "test" in savings
        assert savings["test"] > 0

    def test_data_compressor_gzip(self):
        """Test gzip compression"""
        compressor = DataCompressor()
        data = b"Hello, World! " * 1000
        compressed, ratio = compressor.compress_data(data, algorithm="gzip")
        assert len(compressed) < len(data)
        assert ratio > 1.0

    def test_data_compressor_zlib(self):
        """Test zlib compression"""
        compressor = DataCompressor()
        data = b"Test data" * 500
        compressed, ratio = compressor.compress_data(data, algorithm="zlib")
        assert len(compressed) < len(data)

    def test_data_compressor_estimate_savings(self):
        """Test compression savings estimation"""
        compressor = DataCompressor()
        objects = [
            DataObject(id="1", name="a", size=1024),
            DataObject(id="2", name="b", size=2048),
        ]
        savings = compressor.estimate_compression_savings(objects, estimated_ratio=2.0)
        assert savings["savings"] > 0

    def test_lifecycle_manager_add_policy(self):
        """Test adding lifecycle policy"""
        manager = StorageManager()
        lifecycle = DataLifecycleManager(manager)

        lifecycle.add_lifecycle_policy(
            policy_id="test-policy",
            pattern="log-",
            rules={"transition_after_days": 30, "transition_to": "cold"},
        )
        assert "test-policy" in lifecycle.lifecycle_policies

    def test_lifecycle_manager_apply_policies(self):
        """Test applying lifecycle policies"""
        manager = StorageManager()
        lifecycle = DataLifecycleManager(manager)

        lifecycle.add_lifecycle_policy(
            policy_id="test-policy",
            pattern="old-",
            rules={"transition_after_days": 30, "transition_to": "cold"},
        )

        manager.add_object(
            DataObject(
                id="old-file",
                name="old-data.dat",
                size=1024,
                created_at=datetime.now() - timedelta(days=40),
            )
        )

        actions = lifecycle.apply_lifecycle_policies()
        assert len(actions) > 0

    def test_storage_statistics_to_dict(self):
        """Test StorageStatistics serialization"""
        stats = StorageStatistics(total_objects=10, total_size=1024)
        data = stats.to_dict()
        assert data["total_objects"] == 10
        assert "total_size_gb" in data

    def test_factory_functions(self):
        """Test factory functions"""
        manager = create_storage_manager()
        assert isinstance(manager, StorageManager)

        optimizer = create_storage_optimizer(manager)
        assert isinstance(optimizer, StorageOptimizer)

        compressor = create_data_compressor()
        assert isinstance(compressor, DataCompressor)

        lifecycle = create_data_lifecycle_manager(manager)
        assert isinstance(lifecycle, DataLifecycleManager)


# =============================================================================
# Tests for modules/observability/smart_alerting.py
# =============================================================================


class TestSmartAlerting:
    """Test SmartAlertingEngine and related classes"""

    def test_alert_fingerprint(self):
        """Test alert fingerprint generation"""
        alert = Alert(
            id="test-1",
            title="CPU High",
            description="CPU usage is high",
            severity=AlertSeverity.WARNING,
            source="prometheus",
            labels={"host": "server1"},
        )
        fingerprint = alert.generate_fingerprint()
        assert len(fingerprint) == 64  # SHA256 hash length
        assert alert.fingerprint == fingerprint

    def test_alert_to_dict(self):
        """Test Alert serialization"""
        alert = Alert(
            id="test",
            title="Test",
            description="Test alert",
            severity=AlertSeverity.INFO,
        )
        data = alert.to_dict()
        assert data["id"] == "test"
        assert data["severity"] == "info"

    def test_alert_rule_evaluate_simple(self):
        """Test simple rule evaluation"""
        rule = AlertRule(
            id="cpu-high",
            name="CPU High",
            condition="cpu_usage > 80",
            severity=AlertSeverity.WARNING,
        )
        metrics = {"cpu_usage": 85.0}
        assert rule.evaluate(metrics) is True

        metrics = {"cpu_usage": 75.0}
        assert rule.evaluate(metrics) is False

    def test_alert_rule_evaluate_complex(self):
        """Test complex rule evaluation with AND/OR"""
        rule = AlertRule(
            id="complex",
            name="Complex",
            condition="cpu_usage > 80 and memory_usage > 90",
            severity=AlertSeverity.CRITICAL,
        )
        metrics = {"cpu_usage": 85.0, "memory_usage": 95.0}
        assert rule.evaluate(metrics) is True

        metrics = {"cpu_usage": 85.0, "memory_usage": 85.0}
        assert rule.evaluate(metrics) is False

    def test_alert_rule_evaluate_or(self):
        """Test OR condition"""
        rule = AlertRule(
            id="or-test",
            name="OR Test",
            condition="cpu_usage > 90 or memory_usage > 90",
            severity=AlertSeverity.WARNING,
        )
        metrics = {"cpu_usage": 95.0, "memory_usage": 80.0}
        assert rule.evaluate(metrics) is True

    def test_alert_rule_evaluate_not(self):
        """Test NOT condition"""
        rule = AlertRule(
            id="not-test",
            name="NOT Test",
            condition="not cpu_usage > 90",
            severity=AlertSeverity.INFO,
        )
        metrics = {"cpu_usage": 80.0}
        assert rule.evaluate(metrics) is True

    def test_alert_rule_evaluate_operators(self):
        """Test various comparison operators"""
        rule = AlertRule(
            id="ops-test",
            name="Operators Test",
            condition="value >= 10",
            severity=AlertSeverity.WARNING,
        )
        assert rule.evaluate({"value": 10}) is True
        assert rule.evaluate({"value": 15}) is True
        assert rule.evaluate({"value": 5}) is False

    def test_alert_rule_unsafe_condition(self):
        """Test unsafe condition rejection"""
        rule = AlertRule(
            id="unsafe",
            name="Unsafe",
            condition="__import__('os').system('ls')",
            severity=AlertSeverity.WARNING,
        )
        metrics = {"value": 10}
        assert rule.evaluate(metrics) is False

    def test_dynamic_threshold_calculator(self):
        """Test dynamic threshold calculation"""
        calculator = DynamicThresholdCalculator(window_size=50)

        # Add some metric values
        for i in range(20):
            calculator.add_metric("cpu", 50 + i)

        threshold = calculator.calculate_threshold("cpu", method="percentile", percentile=90)
        assert threshold > 0

    def test_dynamic_threshold_stddev(self):
        """Test stddev threshold method"""
        calculator = DynamicThresholdCalculator()
        for i in range(20):
            calculator.add_metric("cpu", 50 + np.random.randn())

        threshold = calculator.calculate_threshold("cpu", method="stddev", multiplier=2)
        assert threshold > 0

    def test_dynamic_threshold_moving_avg(self):
        """Test moving average threshold method"""
        calculator = DynamicThresholdCalculator()
        for i in range(20):
            calculator.add_metric("cpu", 50 + i)

        threshold = calculator.calculate_threshold("cpu", method="moving_avg", window=10)
        assert threshold > 0

    def test_dynamic_threshold_insufficient_data(self):
        """Test threshold with insufficient data"""
        calculator = DynamicThresholdCalculator()
        threshold = calculator.calculate_threshold("cpu", method="percentile")
        assert threshold == 0.0

    def test_alert_aggregator(self):
        """Test alert aggregation"""
        aggregator = AlertAggregator()

        alert1 = Alert(
            id="1",
            title="CPU High",
            description="CPU high",
            severity=AlertSeverity.WARNING,
            source="prometheus",
            labels={"host": "server1"},
        )
        alert2 = Alert(
            id="2",
            title="CPU High",
            description="CPU high",
            severity=AlertSeverity.WARNING,
            source="prometheus",
            labels={"host": "server1"},
        )

        aggregator.add_alert(alert1)
        aggregator.add_alert(alert2)

        aggregated = aggregator.aggregate()
        assert len(aggregated) == 1
        assert "Aggregated from 2 alerts" in aggregated[0].description

    def test_alert_suppressor(self):
        """Test alert suppression"""
        suppressor = AlertSuppressor()

        suppressor.add_suppression_rule(
            match_labels={"host": "server1"},
            duration=3600,
        )

        alert = Alert(
            id="test",
            title="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            labels={"host": "server1"},
        )

        assert suppressor.should_suppress(alert) is True

    def test_alert_suppressor_no_match(self):
        """Test alert suppression with no matching rule"""
        suppressor = AlertSuppressor()

        suppressor.add_suppression_rule(
            match_labels={"host": "server1"},
            duration=3600,
        )

        alert = Alert(
            id="test",
            title="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            labels={"host": "server2"},  # Different host
        )

        # Should not suppress because labels don't match
        assert suppressor.should_suppress(alert) is False

    def test_smart_alerting_engine(self):
        """Test smart alerting engine"""
        engine = SmartAlertingEngine()

        engine.add_rule(
            AlertRule(
                id="cpu-high",
                name="CPU High",
                condition="cpu_usage > 80",
                severity=AlertSeverity.WARNING,
            )
        )

        metrics = {"cpu_usage": 85.0}
        alerts = engine.evaluate_metrics(metrics)
        assert len(alerts) > 0
        assert alerts[0].title == "CPU High"

    def test_smart_alerting_acknowledge(self):
        """Test alert acknowledgment"""
        engine = SmartAlertingEngine()

        engine.add_rule(
            AlertRule(
                id="test",
                name="Test",
                condition="value > 10",
                severity=AlertSeverity.WARNING,
            )
        )

        alerts = engine.evaluate_metrics({"value": 15})
        alert_id = alerts[0].id

        result = engine.acknowledge_alert(alert_id)
        assert result is True
        assert engine.active_alerts[alerts[0].fingerprint].status == AlertStatus.ACKNOWLEDGED

    def test_smart_alerting_resolve(self):
        """Test alert resolution"""
        engine = SmartAlertingEngine()

        engine.add_rule(
            AlertRule(
                id="test",
                name="Test",
                condition="value > 10",
                severity=AlertSeverity.WARNING,
            )
        )

        alerts = engine.evaluate_metrics({"value": 15})
        alert_id = alerts[0].id

        result = engine.resolve_alert(alert_id)
        assert result is True
        assert engine.active_alerts[alerts[0].fingerprint].status == AlertStatus.RESOLVED

    def test_smart_alerting_statistics(self):
        """Test alert statistics"""
        engine = SmartAlertingEngine()

        engine.add_rule(
            AlertRule(
                id="test",
                name="Test",
                condition="value > 10",
                severity=AlertSeverity.WARNING,
            )
        )

        engine.evaluate_metrics({"value": 15})
        stats = engine.get_alert_statistics()
        assert stats["total_active"] > 0
        assert "by_severity" in stats

    def test_create_smart_alerting_engine(self):
        """Test factory function"""
        engine = create_smart_alerting_engine()
        assert isinstance(engine, SmartAlertingEngine)


# =============================================================================
# Tests for modules/apm/dependency_analyzer.py
# =============================================================================


class TestDependencyAnalyzer:
    """Test DependencyAnalyzer and related classes"""

    def test_service_node_to_dict(self):
        """Test ServiceNode serialization"""
        node = ServiceNode(
            id="service-1",
            name="Service 1",
            type="microservice",
            health=HealthStatus.HEALTHY,
        )
        data = node.to_dict()
        assert data["id"] == "service-1"
        assert data["health"] == "healthy"

    def test_dependency_edge_to_dict(self):
        """Test DependencyEdge serialization"""
        edge = DependencyEdge(
            source="service-1",
            target="service-2",
            dependency_type=DependencyType.SYNC,
            weight=1.5,
            latency=100.0,
        )
        data = edge.to_dict()
        assert data["source"] == "service-1"
        assert data["dependency_type"] == "sync"

    def test_dependency_topology(self):
        """Test DependencyTopology operations"""
        topology = DependencyTopology()

        node1 = ServiceNode(id="1", name="Service 1")
        node2 = ServiceNode(id="2", name="Service 2")

        topology.add_node(node1)
        topology.add_node(node2)

        edge = DependencyEdge(
            source="1",
            target="2",
            dependency_type=DependencyType.SYNC,
        )
        topology.add_edge(edge)

        assert "1" in topology.nodes
        assert "2" in topology.get_dependencies("1")
        assert "1" in topology.get_dependents("2")

    def test_dependency_topology_recursive(self):
        """Test recursive dependency traversal"""
        topology = DependencyTopology()

        topology.add_node(ServiceNode(id="1", name="S1"))
        topology.add_node(ServiceNode(id="2", name="S2"))
        topology.add_node(ServiceNode(id="3", name="S3"))

        topology.add_edge(
            DependencyEdge(source="1", target="2", dependency_type=DependencyType.SYNC)
        )
        topology.add_edge(
            DependencyEdge(source="2", target="3", dependency_type=DependencyType.SYNC)
        )

        all_deps = topology.get_all_dependencies("1")
        assert "2" in all_deps
        assert "3" in all_deps

    def test_dependency_topology_critical_path(self):
        """Test critical path finding"""
        topology = DependencyTopology()

        topology.add_node(ServiceNode(id="1", name="S1"))
        topology.add_node(ServiceNode(id="2", name="S2"))
        topology.add_node(ServiceNode(id="3", name="S3"))

        topology.add_edge(
            DependencyEdge(source="1", target="2", dependency_type=DependencyType.SYNC, weight=1.0)
        )
        topology.add_edge(
            DependencyEdge(source="2", target="3", dependency_type=DependencyType.SYNC, weight=2.0)
        )

        path = topology.find_critical_path("1", "3")
        assert len(path) == 3
        assert path[0] == "1"
        assert path[-1] == "3"

    def test_dependency_topology_to_dict(self):
        """Test topology serialization"""
        topology = DependencyTopology()
        topology.add_node(ServiceNode(id="1", name="S1"))
        topology.add_edge(
            DependencyEdge(source="1", target="2", dependency_type=DependencyType.SYNC)
        )

        data = topology.to_dict()
        assert "nodes" in data
        assert "edges" in data

    def test_dependency_discoverer_from_traces(self):
        """Test dependency discovery from traces"""
        discoverer = DependencyDiscoverer()

        trace_data = [
            {
                "spans": [
                    {"service_id": "svc1", "service_name": "Service 1", "kind": "server"},
                    {"service_id": "svc2", "service_name": "Service 2", "kind": "client"},
                ]
            }
        ]

        topology = discoverer.discover(method="trace", trace_data=trace_data)
        assert len(topology.nodes) > 0

    def test_dependency_discoverer_from_config(self):
        """Test dependency discovery from config"""
        discoverer = DependencyDiscoverer()

        config_data = {
            "services": [
                {
                    "id": "svc1",
                    "name": "Service 1",
                    "dependencies": [
                        {"id": "svc2", "name": "Service 2", "type": "sync"},
                    ],
                }
            ]
        }

        topology = discoverer.discover(method="config", config_data=config_data)
        assert len(topology.nodes) > 0

    def test_dependency_discoverer_from_metrics(self):
        """Test dependency discovery from metrics"""
        discoverer = DependencyDiscoverer()

        metrics_data = {
            "call_relationships": [
                {"source": "svc1", "target": "svc2", "call_count": 100},
            ]
        }

        topology = discoverer.discover(method="metrics", metrics_data=metrics_data)
        assert len(topology.nodes) > 0

    def test_dependency_discoverer_unknown_method(self):
        """Test unknown discovery method"""
        discoverer = DependencyDiscoverer()
        with pytest.raises(ValueError):
            discoverer.discover(method="unknown")

    def test_dependency_health_assessor(self):
        """Test dependency health assessment"""
        topology = DependencyTopology()
        topology.add_node(ServiceNode(id="1", name="S1"))

        assessor = DependencyHealthAssessor(topology)

        metrics = {"error_rate": 0.01, "latency": 500, "availability": 0.99}
        health = assessor.assess_node_health("1", metrics)
        assert health == HealthStatus.HEALTHY

    def test_dependency_health_assessor_unhealthy(self):
        """Test unhealthy node assessment"""
        topology = DependencyTopology()
        topology.add_node(ServiceNode(id="1", name="S1"))

        assessor = DependencyHealthAssessor(topology)

        metrics = {"error_rate": 0.10, "latency": 2000, "availability": 0.90}
        health = assessor.assess_node_health("1", metrics)
        assert health == HealthStatus.UNHEALTHY

    def test_dependency_health_assessor_edge(self):
        """Test edge health assessment"""
        topology = DependencyTopology()
        assessor = DependencyHealthAssessor(topology)

        edge = DependencyEdge(
            source="1",
            target="2",
            dependency_type=DependencyType.SYNC,
            error_rate=0.02,
            latency=2000,
        )
        health = assessor.assess_dependency_health(edge)
        assert health == HealthStatus.DEGRADED

    def test_dependency_health_assessor_critical_nodes(self):
        """Test critical node identification"""
        topology = DependencyTopology()

        topology.add_node(ServiceNode(id="1", name="S1"))
        topology.add_node(ServiceNode(id="2", name="S2"))
        topology.add_node(ServiceNode(id="3", name="S3"))

        topology.add_edge(
            DependencyEdge(source="2", target="1", dependency_type=DependencyType.SYNC)
        )
        topology.add_edge(
            DependencyEdge(source="3", target="1", dependency_type=DependencyType.SYNC)
        )

        assessor = DependencyHealthAssessor(topology)
        critical = assessor.identify_critical_nodes()
        assert len(critical) > 0

    def test_topology_visualizer_to_json(self):
        """Test topology JSON serialization"""
        topology = DependencyTopology()
        topology.add_node(ServiceNode(id="1", name="S1"))
        topology.add_edge(
            DependencyEdge(source="1", target="2", dependency_type=DependencyType.SYNC)
        )

        json_str = TopologyVisualizer.to_json(topology)
        data = json.loads(json_str)
        assert "nodes" in data
        assert "edges" in data

    def test_topology_visualizer_from_json(self):
        """Test topology JSON deserialization"""
        json_str = '{"nodes": [{"id": "1", "name": "S1"}], "edges": []}'
        topology = TopologyVisualizer.from_json(json_str)
        assert "1" in topology.nodes

    def test_dependency_analyzer(self):
        """Test comprehensive dependency analyzer"""
        analyzer = DependencyAnalyzer()

        config_data = {
            "services": [
                {
                    "id": "svc1",
                    "name": "Service 1",
                    "dependencies": [{"id": "svc2", "name": "Service 2", "type": "sync"}],
                }
            ]
        }

        topology = analyzer.discover_topology(method="config", config_data=config_data)
        assert topology is not None
        assert analyzer.topology is not None


# =============================================================================
# Tests for modules/execute/saga/participants.py
# =============================================================================


class TestSagaParticipants:
    """Test Saga participants"""

    @pytest.mark.asyncio
    async def test_participant_base_class(self):
        """Test participant base class is abstract"""
        with pytest.raises(TypeError):
            Participant(name="test")

    @pytest.mark.asyncio
    async def test_database_participant(self):
        """Test database participant"""
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin = AsyncMock(return_value=mock_transaction)

        participant = DatabaseParticipant(name="db-test", db_session=mock_session)

        context = {"db-test_operation": AsyncMock(return_value={"result": "success"})}
        result = await participant.execute(context)
        assert result is not None

    @pytest.mark.asyncio
    async def test_database_participant_compensate(self):
        """Test database participant compensation"""
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin = AsyncMock(return_value=mock_transaction)

        participant = DatabaseParticipant(name="db-test", db_session=mock_session)
        await participant.execute({})
        await participant.compensate({})

        mock_transaction.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_call_participant(self):
        """Test API call participant"""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json = Mock(return_value={"transaction_id": "tx-123"})
        mock_client.post = AsyncMock(return_value=mock_response)

        participant = APICallParticipant(
            name="api-test",
            execute_url="http://api.example.com/execute",
            compensate_url="http://api.example.com/compensate",
            http_client=mock_client,
        )

        context = {"api-test_payload": {"data": "test"}}
        result = await participant.execute(context)
        assert result["transaction_id"] == "tx-123"

    @pytest.mark.asyncio
    async def test_api_call_participant_compensate(self):
        """Test API call participant compensation"""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json = Mock(return_value={"transaction_id": "tx-123"})
        mock_client.post = AsyncMock(return_value=mock_response)

        participant = APICallParticipant(
            name="api-test",
            execute_url="http://api.example.com/execute",
            compensate_url="http://api.example.com/compensate",
            http_client=mock_client,
        )

        await participant.execute({"api-test_payload": {}})
        await participant.compensate({})

        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_message_queue_participant(self):
        """Test message queue participant"""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(return_value="msg-123")

        participant = MessageQueueParticipant(
            name="mq-test",
            queue_client=mock_client,
            topic="test-topic",
        )

        context = {"mq-test_message": {"data": "test"}}
        result = await participant.execute(context)
        assert result["message_id"] == "msg-123"

    @pytest.mark.asyncio
    async def test_message_queue_participant_compensate(self):
        """Test message queue participant compensation"""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(return_value="msg-123")

        participant = MessageQueueParticipant(
            name="mq-test",
            queue_client=mock_client,
            topic="test-topic",
        )

        await participant.execute({"mq-test_message": {}})
        await participant.compensate({})

        assert mock_client.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_resource_allocation_participant(self):
        """Test resource allocation participant"""
        mock_manager = AsyncMock()
        mock_manager.allocate = AsyncMock(return_value=["res-1", "res-2"])

        participant = ResourceAllocationParticipant(
            name="resource-test",
            resource_manager=mock_manager,
        )

        context = {"resource-test_spec": {"cpu": 4}}
        result = await participant.execute(context)
        assert "allocated" in result

    @pytest.mark.asyncio
    async def test_resource_allocation_participant_compensate(self):
        """Test resource allocation participant compensation"""
        mock_manager = AsyncMock()
        mock_manager.allocate = AsyncMock(return_value=["res-1"])
        mock_manager.release = AsyncMock()

        participant = ResourceAllocationParticipant(
            name="resource-test",
            resource_manager=mock_manager,
        )

        await participant.execute({"resource-test_spec": {}})
        await participant.compensate({})

        mock_manager.release.assert_called_once_with("res-1")

    @pytest.mark.asyncio
    async def test_notification_participant(self):
        """Test notification participant"""
        mock_service = AsyncMock()
        mock_service.send = AsyncMock(return_value="notif-123")

        participant = NotificationParticipant(
            name="notif-test",
            notification_service=mock_service,
        )

        context = {"notif-test_notification": {"message": "test"}}
        result = await participant.execute(context)
        assert result["notification_id"] == "notif-123"

    @pytest.mark.asyncio
    async def test_notification_participant_compensate(self):
        """Test notification participant compensation"""
        mock_service = AsyncMock()
        mock_service.send = AsyncMock(return_value="notif-123")
        mock_service.cancel = AsyncMock()

        participant = NotificationParticipant(
            name="notif-test",
            notification_service=mock_service,
        )

        await participant.execute({"notif-test_notification": {}})
        await participant.compensate({})

        mock_service.cancel.assert_called_once_with("notif-123")

    def test_notification_participant_should_compensate(self):
        """Test notification participant should not compensate"""
        mock_service = Mock()
        participant = NotificationParticipant(
            name="notif-test",
            notification_service=mock_service,
        )
        assert participant.should_compensate({}) is False

    def test_compensation_action(self):
        """Test compensation action"""
        execute_func = Mock(return_value="executed")
        compensate_func = Mock(return_value="compensated")

        action = CompensationAction(
            name="test-action",
            execute=execute_func,
            compensate=compensate_func,
        )

        assert action.name == "test-action"
        assert action.execute == execute_func
        assert action.compensate == compensate_func

    def test_create_compensation_action(self):
        """Test factory function"""
        execute_func = Mock()
        compensate_func = Mock()

        action = create_compensation_action(
            name="test",
            execute_func=execute_func,
            compensate_func=compensate_func,
        )

        assert isinstance(action, CompensationAction)


# =============================================================================
# Tests for modules/analyze/anomaly/isolation_forest.py
# =============================================================================


class TestIsolationForest:
    """Test IsolationForestDetector"""

    def test_isolation_forest_initialization(self):
        """Test detector initialization"""
        detector = IsolationForestDetector(
            contamination=0.1,
            n_estimators=100,
            random_state=42,
        )
        assert detector.contamination == 0.1
        assert detector.n_estimators == 100
        assert not detector.is_fitted

    def test_isolation_forest_fit(self):
        """Test model fitting"""
        detector = IsolationForestDetector(contamination=0.1, random_state=42)

        data = [{"value": i, "timestamp": f"2024-01-{i:02d}"} for i in range(1, 101)]

        detector.fit(data)
        assert detector.is_fitted
        assert detector.model is not None

    def test_isolation_forest_fit_insufficient_data(self):
        """Test fitting with insufficient data"""
        detector = IsolationForestDetector()

        data = [{"value": 1}, {"value": 2}]

        with pytest.raises(ValueError):
            detector.fit(data)

    def test_isolation_forest_predict(self):
        """Test prediction"""
        detector = IsolationForestDetector(contamination=0.1, random_state=42)

        train_data = [{"value": i, "timestamp": f"2024-01-{i:02d}"} for i in range(1, 101)]
        detector.fit(train_data)

        test_data = [
            {"value": 50, "timestamp": "2024-01-15"},
            {"value": 1000, "timestamp": "2024-01-20"},  # Anomaly
        ]

        result = detector.predict(test_data, return_scores=True)
        assert "predictions" in result
        assert "anomalies" in result
        assert "scores" in result

    def test_isolation_forest_predict_not_fitted(self):
        """Test prediction without fitting"""
        detector = IsolationForestDetector()

        with pytest.raises(RuntimeError):
            detector.predict([{"value": 1}])

    def test_isolation_forest_detect_anomalies(self):
        """Test anomaly detection"""
        detector = IsolationForestDetector(contamination=0.1, random_state=42)

        train_data = [{"value": i, "timestamp": f"2024-01-{i:02d}"} for i in range(1, 101)]
        detector.fit(train_data)

        test_data = [{"value": i, "timestamp": f"2024-01-{i:02d}"} for i in range(1, 51)]

        anomalies = detector.detect_anomalies(test_data, threshold=0.5)
        assert isinstance(anomalies, list)

    def test_isolation_forest_feature_importance(self):
        """Test feature importance"""
        detector = IsolationForestDetector(contamination=0.1, random_state=42)

        data = [
            {"value1": i, "value2": i * 2, "timestamp": f"2024-01-{i:02d}"} for i in range(1, 101)
        ]
        detector.fit(data)

        importance = detector.get_feature_importance()
        assert isinstance(importance, dict)
        assert len(importance) > 0

    def test_isolation_forest_feature_importance_not_fitted(self):
        """Test feature importance without fitting"""
        detector = IsolationForestDetector()

        with pytest.raises(RuntimeError):
            detector.get_feature_importance()

    def test_isolation_forest_save_load(self, tmp_path):
        """Test model save and load"""
        detector = IsolationForestDetector(contamination=0.1, random_state=42)

        data = [{"value": i, "timestamp": f"2024-01-{i:02d}"} for i in range(1, 101)]
        detector.fit(data)

        model_path = tmp_path / "isolation_forest_model.joblib"
        detector.save_model(str(model_path))

        assert model_path.exists()

        detector2 = IsolationForestDetector()
        detector2.load_model(str(model_path))

        assert detector2.is_fitted
        assert detector2.contamination == 0.1

    def test_isolation_forest_save_not_fitted(self, tmp_path):
        """Test saving without fitting"""
        detector = IsolationForestDetector()

        with pytest.raises(RuntimeError):
            detector.save_model(str(tmp_path / "model.joblib"))

    def test_isolation_forest_with_pca(self):
        """Test with PCA dimensionality reduction"""
        detector = IsolationForestDetector(
            contamination=0.1,
            use_pca=True,
            pca_components=0.95,
            random_state=42,
        )

        data = [
            {"value1": i, "value2": i * 2, "value3": i * 3, "timestamp": f"2024-01-{i:02d}"}
            for i in range(1, 101)
        ]
        detector.fit(data)

        assert detector.pca is not None
        assert detector.is_fitted

    def test_isolation_forest_no_numeric_features(self):
        """Test with no numeric features"""
        detector = IsolationForestDetector()

        data = [{"text": "hello"}, {"text": "world"}]

        with pytest.raises(ValueError):
            detector.fit(data)

    def test_isolation_forest_custom_feature_cols(self):
        """Test with custom feature columns"""
        detector = IsolationForestDetector(random_state=42)

        data = [{"value1": i, "value2": i * 2, "label": f"cat{i%2}"} for i in range(1, 101)]
        detector.fit(data, feature_cols=["value1", "value2"])

        assert detector.feature_names == ["value1", "value2"]


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto", "--tb=short"])
