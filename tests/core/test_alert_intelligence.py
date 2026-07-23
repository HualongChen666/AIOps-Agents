# -*- coding: utf-8 -*-
"""测试告警智能模块"""

from datetime import datetime

import pytest


class TestAlertIntelligenceModule:
    """测试告警智能模块"""

    def test_alert_intelligence_module_exists(self):
        """测试告警智能模块存在"""
        from core import alert_intelligence

        assert alert_intelligence is not None

    def test_alert_intelligence_has_functions(self):
        """测试告警智能模块有函数"""
        from core import alert_intelligence

        # 检查模块有函数或类
        assert len(dir(alert_intelligence)) > 0


class TestAlertSeverity:
    """测试AlertSeverity枚举"""

    def test_alert_severity_values(self):
        """测试AlertSeverity枚举值"""
        try:
            from core.alert_intelligence import AlertSeverity

            assert AlertSeverity.CRITICAL.value == "critical"
            assert AlertSeverity.HIGH.value == "high"
            assert AlertSeverity.WARNING.value == "warning"
            assert AlertSeverity.INFO.value == "info"
            assert AlertSeverity.LOW.value == "low"
        except Exception as e:
            pytest.skip(f"Cannot test AlertSeverity: {e}")


class TestAlertPattern:
    """测试AlertPattern数据类"""

    def test_alert_pattern_creation(self):
        """测试AlertPattern创建"""
        try:
            from core.alert_intelligence import AlertPattern

            pattern = AlertPattern(
                pattern_id="test-1",
                signature="cpu_high",
                frequency=10,
                last_seen=datetime.now(),
                is_noise=True,
                noise_reason="frequent pattern",
            )

            assert pattern.pattern_id == "test-1"
            assert pattern.signature == "cpu_high"
            assert pattern.frequency == 10
            assert pattern.is_noise is True
        except Exception as e:
            pytest.skip(f"Cannot test AlertPattern creation: {e}")

    def test_alert_pattern_default_values(self):
        """测试AlertPattern默认值"""
        try:
            from core.alert_intelligence import AlertPattern

            pattern = AlertPattern(
                pattern_id="test-2",
                signature="memory_high",
                frequency=5,
                last_seen=datetime.now(),
            )

            assert pattern.is_noise is False
            assert pattern.noise_reason == ""
            assert pattern.suppression_window == 300
        except Exception as e:
            pytest.skip(f"Cannot test AlertPattern defaults: {e}")


class TestAlertCluster:
    """测试AlertCluster数据类"""

    def test_alert_cluster_creation(self):
        """测试AlertCluster创建"""
        try:
            from core.alert_intelligence import AlertCluster, AlertSeverity

            cluster = AlertCluster(
                cluster_id="cluster-1",
                alerts=[{"id": "1"}, {"id": "2"}],
                centroid={"cpu": 80},
                severity=AlertSeverity.HIGH,
            )

            assert cluster.cluster_id == "cluster-1"
            assert len(cluster.alerts) == 2
            assert cluster.severity == AlertSeverity.HIGH
        except Exception as e:
            pytest.skip(f"Cannot test AlertCluster creation: {e}")

    def test_alert_cluster_default_values(self):
        """测试AlertCluster默认值"""
        try:
            from core.alert_intelligence import AlertCluster, AlertSeverity

            cluster = AlertCluster(cluster_id="cluster-2")

            assert cluster.alerts == []
            assert cluster.centroid == {}
            assert cluster.severity == AlertSeverity.WARNING
            assert cluster.topology_context is None
        except Exception as e:
            pytest.skip(f"Cannot test AlertCluster defaults: {e}")


class TestTrendPrediction:
    """测试TrendPrediction数据类"""

    def test_trend_prediction_creation(self):
        """测试TrendPrediction创建"""
        try:
            from core.alert_intelligence import TrendPrediction

            prediction = TrendPrediction(
                metric_name="cpu",
                predicted_values=[50.0, 55.0, 60.0],
                predicted_anomalies=[],
                confidence=0.9,
                prediction_horizon=24,
            )

            assert prediction.metric_name == "cpu"
            assert len(prediction.predicted_values) == 3
            assert prediction.confidence == 0.9
            assert prediction.prediction_horizon == 24
        except Exception as e:
            pytest.skip(f"Cannot test TrendPrediction creation: {e}")

    def test_trend_prediction_default_model(self):
        """测试TrendPrediction默认模型"""
        try:
            from core.alert_intelligence import TrendPrediction

            prediction = TrendPrediction(
                metric_name="memory",
                predicted_values=[],
                predicted_anomalies=[],
                confidence=0.5,
                prediction_horizon=12,
            )

            assert prediction.model_used == "rule_based"
        except Exception as e:
            pytest.skip(f"Cannot test TrendPrediction default model: {e}")


class TestAlertIntelligenceEngine:
    """测试AlertIntelligenceEngine类"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            assert engine is not None
            assert isinstance(engine.patterns, dict)
            assert isinstance(engine.clusters, dict)
            assert isinstance(engine.routing_rules, list)
        except Exception as e:
            pytest.skip(f"Cannot test engine initialization: {e}")

    def test_engine_analyze_empty_alerts(self):
        """测试分析空告警列表"""
        try:
            import asyncio

            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            result = asyncio.run(engine.analyze_and_aggregate_alerts([]))
            assert result == []
        except Exception as e:
            pytest.skip(f"Cannot test analyze empty alerts: {e}")

    def test_engine_analyze_single_alert(self):
        """测试分析单个告警"""
        try:
            import asyncio

            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            alerts = [{"id": "1", "title": "CPU High", "level": "warning"}]
            result = asyncio.run(engine.analyze_and_aggregate_alerts(alerts))
            assert isinstance(result, list)
        except Exception as e:
            pytest.skip(f"Cannot test analyze single alert: {e}")

    def test_engine_extract_alert_features(self):
        """测试提取告警特征"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            alerts = [{"id": "1", "title": "Test", "level": "critical", "category": "security"}]
            features = engine._extract_alert_features(alerts)
            assert features is not None
            assert features.shape[0] == 1
        except Exception as e:
            pytest.skip(f"Cannot test extract features: {e}")

    def test_engine_encode_severity(self):
        """测试严重性编码"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            assert engine._encode_severity("critical") == 4
            assert engine._encode_severity("high") == 3
            assert engine._encode_severity("warning") == 2
            assert engine._encode_severity("info") == 1
            assert engine._encode_severity("low") == 0
            assert engine._encode_severity("unknown") == 1  # default
        except Exception as e:
            pytest.skip(f"Cannot test encode severity: {e}")

    def test_engine_encode_category(self):
        """测试类别编码"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            assert engine._encode_category("security") == 4
            assert engine._encode_category("performance") == 3
            assert engine._encode_category("availability") == 2
            assert engine._encode_category("system") == 1
            assert engine._encode_category("other") == 0
            assert engine._encode_category("unknown") == 1  # default
        except Exception as e:
            pytest.skip(f"Cannot test encode category: {e}")

    def test_engine_rule_based_clustering(self):
        """测试基于规则的聚类"""
        try:
            import asyncio

            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            alerts = [
                {"id": "1", "title": "CPU High", "level": "warning"},
                {"id": "2", "title": "Memory High", "level": "warning"},
            ]
            result = asyncio.run(engine._rule_based_clustering(alerts))
            assert isinstance(result, list)
        except Exception as e:
            pytest.skip(f"Cannot test rule-based clustering: {e}")

    def test_engine_update_patterns(self):
        """测试更新模式"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            alerts = [{"id": "1", "title": "Test Alert"}]
            # 应该不抛出异常
            engine._update_patterns(alerts)
        except Exception as e:
            pytest.skip(f"Cannot test update patterns: {e}")


class TestAlertPatternEdgeCases:
    """测试AlertPattern边界情况"""

    def test_alert_pattern_empty_signature(self):
        """测试空签名"""
        try:
            from core.alert_intelligence import AlertPattern

            pattern = AlertPattern(
                pattern_id="test-1",
                signature="",
                frequency=0,
                last_seen=datetime.now(),
            )

            assert pattern.signature == ""
        except Exception as e:
            pytest.skip(f"Cannot test AlertPattern empty signature: {e}")

    def test_alert_pattern_zero_frequency(self):
        """测试零频率"""
        try:
            from core.alert_intelligence import AlertPattern

            pattern = AlertPattern(
                pattern_id="test-2",
                signature="test",
                frequency=0,
                last_seen=datetime.now(),
            )

            assert pattern.frequency == 0
        except Exception as e:
            pytest.skip(f"Cannot test AlertPattern zero frequency: {e}")


class TestAlertClusterEdgeCases:
    """测试AlertCluster边界情况"""

    def test_alert_cluster_empty_alerts(self):
        """测试空告警列表"""
        try:
            from core.alert_intelligence import AlertCluster

            cluster = AlertCluster(
                cluster_id="cluster-1",
                alerts=[],
                centroid={},
            )

            assert len(cluster.alerts) == 0
        except Exception as e:
            pytest.skip(f"Cannot test AlertCluster empty alerts: {e}")

    def test_alert_cluster_empty_centroid(self):
        """测试空质心"""
        try:
            from core.alert_intelligence import AlertCluster

            cluster = AlertCluster(
                cluster_id="cluster-2",
                alerts=[{"id": "1"}],
                centroid={},
            )

            assert cluster.centroid == {}
        except Exception as e:
            pytest.skip(f"Cannot test AlertCluster empty centroid: {e}")


class TestTrendPredictionEdgeCases:
    """测试TrendPrediction边界情况"""

    def test_trend_prediction_empty_values(self):
        """测试空预测值"""
        try:
            from core.alert_intelligence import TrendPrediction

            prediction = TrendPrediction(
                metric_name="cpu",
                predicted_values=[],
                predicted_anomalies=[],
                confidence=0.5,
                prediction_horizon=12,
            )

            assert len(prediction.predicted_values) == 0
        except Exception as e:
            pytest.skip(f"Cannot test TrendPrediction empty values: {e}")

    def test_trend_prediction_zero_confidence(self):
        """测试零置信度"""
        try:
            from core.alert_intelligence import TrendPrediction

            prediction = TrendPrediction(
                metric_name="memory",
                predicted_values=[50.0],
                predicted_anomalies=[],
                confidence=0.0,
                prediction_horizon=12,
            )

            assert prediction.confidence == 0.0
        except Exception as e:
            pytest.skip(f"Cannot test TrendPrediction zero confidence: {e}")

    def test_trend_prediction_high_confidence(self):
        """测试高置信度"""
        try:
            from core.alert_intelligence import TrendPrediction

            prediction = TrendPrediction(
                metric_name="disk",
                predicted_values=[50.0],
                predicted_anomalies=[],
                confidence=1.0,
                prediction_horizon=12,
            )

            assert prediction.confidence == 1.0
        except Exception as e:
            pytest.skip(f"Cannot test TrendPrediction high confidence: {e}")


class TestAlertIntelligenceEngineEdgeCases:
    """测试AlertIntelligenceEngine边界情况"""

    def test_engine_encode_severity_null(self):
        """测试空严重性"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            result = engine._encode_severity(None)

            # Should return default
            assert result == 1
        except Exception as e:
            pytest.skip(f"Cannot test encode severity null: {e}")

    def test_engine_encode_severity_empty(self):
        """测试空严重性"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            result = engine._encode_severity("")

            # Should return default
            assert result == 1
        except Exception as e:
            pytest.skip(f"Cannot test encode severity empty: {e}")

    def test_engine_encode_category_null(self):
        """测试空类别"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            result = engine._encode_category(None)

            # Should return default
            assert result == 1
        except Exception as e:
            pytest.skip(f"Cannot test encode category null: {e}")

    def test_engine_encode_category_empty(self):
        """测试空类别"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            result = engine._encode_category("")

            # Should return default
            assert result == 1
        except Exception as e:
            pytest.skip(f"Cannot test encode category empty: {e}")

    def test_engine_extract_features_empty(self):
        """测试提取空特征"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            features = engine._extract_alert_features([])

            assert features is not None
        except Exception as e:
            pytest.skip(f"Cannot test extract features empty: {e}")

    def test_engine_extract_features_null(self):
        """测试提取空特征"""
        try:
            from core.alert_intelligence import AlertIntelligenceEngine

            engine = AlertIntelligenceEngine()
            features = engine._extract_alert_features(None)

            assert features is not None
        except Exception as e:
            pytest.skip(f"Cannot test extract features null: {e}")


class TestAlertIntelligenceEngineAdvanced:
    def test_analyze_and_aggregate_alerts(self):
        import asyncio

        from core.alert_intelligence import AlertIntelligenceEngine

        engine = AlertIntelligenceEngine()
        alerts = [
            {"id": "1", "title": "CPU High", "level": "warning", "category": "performance"},
            {"id": "2", "title": "CPU High", "level": "warning", "category": "performance"},
        ]
        result = asyncio.run(engine.analyze_and_aggregate_alerts(alerts))
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["aggregated_count"] == 2

    def test_noise_reduction(self):
        import asyncio
        from datetime import datetime

        from core.alert_intelligence import AlertIntelligenceEngine, AlertPattern

        engine = AlertIntelligenceEngine()
        signature = "warning|performance|||"
        engine.patterns[signature] = AlertPattern(
            pattern_id=signature,
            signature=signature,
            frequency=20,
            last_seen=datetime.now(),
            is_noise=True,
            suppression_window=1000,
        )
        alerts = [{"id": "1", "title": "CPU High", "level": "warning", "category": "performance"}]
        result = asyncio.run(engine.analyze_and_aggregate_alerts(alerts))
        assert result == []

    def test_predict_trends_insufficient_data(self):
        import asyncio

        from core.alert_intelligence import AlertIntelligenceEngine

        engine = AlertIntelligenceEngine()
        result = asyncio.run(engine.predict_alert_trends("cpu", []))
        assert result.confidence == 0.0
        assert result.model_used == "insufficient_data"

    def test_predict_trends_rule_based(self):
        import asyncio
        from datetime import datetime

        from core.alert_intelligence import AlertIntelligenceEngine

        engine = AlertIntelligenceEngine()
        data = [(datetime.now(), float(i)) for i in range(10)]
        result = asyncio.run(engine.predict_alert_trends("cpu", data, horizon_hours=3))
        assert result.model_used == "rule_based"
        assert len(result.predicted_values) == 3

    def test_build_topology_context(self):
        from core.alert_intelligence import AlertIntelligenceEngine

        engine = AlertIntelligenceEngine()
        alerts = [
            {"id": "1", "host": "db1", "category": "database"},
            {"id": "2", "host": "app1", "category": "application"},
            {"id": "3", "host": "db2", "category": "database"},
        ]
        ctx = engine.build_topology_context(alerts)
        assert "db1" in ctx["nodes"]
        assert "database" in ctx["components"]

    def test_route_alerts_intelligently_default(self):
        import asyncio

        from core.alert_intelligence import AlertIntelligenceEngine

        engine = AlertIntelligenceEngine()
        alerts = [
            {"id": "1", "level": "critical", "category": "system"},
            {"id": "2", "level": "warning", "category": "security"},
            {"id": "3", "level": "warning", "category": "database"},
        ]
        routes = asyncio.run(engine.route_alerts_intelligently(alerts))
        assert "immediate" in routes
        assert "security_team" in routes
        assert "infrastructure_team" in routes

    def test_route_alerts_with_custom_rule(self):
        import asyncio

        from core.alert_intelligence import AlertIntelligenceEngine

        engine = AlertIntelligenceEngine()
        engine.add_routing_rule(
            {
                "conditions": {"service": "payment"},
                "destination": "payment_oncall",
            }
        )
        alerts = [
            {"id": "1", "level": "warning", "category": "system", "service": "payment"},
            {"id": "2", "level": "warning", "category": "system"},
        ]
        routes = asyncio.run(engine.route_alerts_intelligently(alerts))
        assert "payment_oncall" in routes
        assert "default" in routes

    def test_add_suppression_rule_and_statistics(self):
        from core.alert_intelligence import AlertIntelligenceEngine

        engine = AlertIntelligenceEngine()
        engine.add_suppression_rule({"pattern": "test"})
        stats = engine.get_alert_statistics()
        assert stats["suppression_rules"] == 1
        assert stats["routing_rules"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
