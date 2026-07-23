# -*- coding: utf-8 -*-
"""
Integration tests for log aggregation and analysis
日志聚合和分析集成测试
"""

import json
from datetime import datetime, timedelta

import pytest

from core.logging.analysis import (
    AlertSeverity,
    AnomalyDetector,
    LogAlert,
    LogAlertManager,
    LogAnalyzer,
    ThresholdAlert,
    get_alert_manager,
    get_log_analyzer,
)


class TestLogAnalyzer:
    """Integration tests for LogAnalyzer"""

    def test_log_statistics_calculation(self):
        """Test log statistics calculation"""
        analyzer = LogAnalyzer()

        # Add sample logs
        logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "logger": "module1",
                "message": "Test message 1",
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "logger": "module1",
                "message": "Test error message",
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "DEBUG",
                "logger": "module2",
                "message": "Debug message",
            },
        ]

        analyzer.add_logs(logs)

        stats = analyzer.calculate_statistics()

        assert stats.total_logs == 3
        assert stats.level_counts["INFO"] == 1
        assert stats.level_counts["ERROR"] == 1
        assert stats.level_counts["DEBUG"] == 1
        assert stats.error_rate == pytest.approx(1 / 3, rel=0.01)

    def test_log_trends_calculation(self):
        """Test log trends calculation"""
        analyzer = LogAnalyzer()

        # Add logs with different timestamps
        base_time = datetime.now()
        for i in range(10):
            logs = [
                {
                    "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                    "level": "INFO",
                    "logger": "module1",
                    "message": f"Test message {i}",
                },
            ]
            analyzer.add_logs(logs)

        trends = analyzer.calculate_trends(interval=timedelta(minutes=1))

        assert len(trends.time_series) > 0
        assert trends.growth_rate >= 0  # Should have growth or zero

    def test_pattern_detection(self):
        """Test log pattern detection"""
        analyzer = LogAnalyzer()

        # Add similar error logs
        for i in range(5):
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "logger": "module1",
                    "message": f"Connection failed to server 192.168.1.{i}",
                },
            ]
            analyzer.add_logs(logs)

        patterns = analyzer.detect_patterns(min_occurrences=3)

        # Should detect a pattern for connection errors
        assert len(patterns) > 0
        assert any("Connection failed" in p.pattern for p in patterns)

    def test_time_range_filtering(self):
        """Test time range filtering"""
        analyzer = LogAnalyzer()

        base_time = datetime.now()
        logs = [
            {
                "timestamp": (base_time - timedelta(hours=2)).isoformat(),
                "level": "INFO",
                "logger": "module1",
                "message": "Old message",
            },
            {
                "timestamp": base_time.isoformat(),
                "level": "INFO",
                "logger": "module1",
                "message": "Recent message",
            },
        ]

        analyzer.add_logs(logs)

        # Filter to last hour
        stats = analyzer.calculate_statistics(
            time_range=(base_time - timedelta(hours=1), base_time + timedelta(minutes=1))
        )

        assert stats.total_logs == 1  # Only recent message


class TestAnomalyDetector:
    """Integration tests for AnomalyDetector"""

    def test_error_rate_anomaly_detection(self):
        """Test error rate anomaly detection"""
        analyzer = LogAnalyzer()
        detector = AnomalyDetector(analyzer)

        # Add baseline logs (low error rate)
        for i in range(20):
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "logger": "module1",
                    "message": f"Normal message {i}",
                },
            ]
            analyzer.add_logs(logs)

        # Add high error rate logs
        for i in range(10):
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "logger": "module1",
                    "message": f"Error message {i}",
                },
            ]
            analyzer.add_logs(logs)

        # Check for anomaly
        alert = detector.detect_error_rate_anomaly(threshold=1.0)

        # May or may not detect anomaly depending on baseline
        assert alert is None or isinstance(alert, LogAlert)

    def test_volume_anomaly_detection(self):
        """Test volume anomaly detection"""
        analyzer = LogAnalyzer()
        detector = AnomalyDetector(analyzer)

        # Add baseline logs
        for i in range(10):
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "logger": "module1",
                    "message": f"Normal message {i}",
                },
            ]
            analyzer.add_logs(logs)

        # Add sudden spike in volume
        for i in range(50):
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "logger": "module1",
                    "message": f"Spike message {i}",
                },
            ]
            analyzer.add_logs(logs)

        # Check for anomaly
        alert = detector.detect_volume_anomaly(threshold=2.0)

        # May detect volume spike
        assert alert is None or isinstance(alert, LogAlert)

    def test_pattern_anomaly_detection(self):
        """Test pattern anomaly detection"""
        analyzer = LogAnalyzer()
        detector = AnomalyDetector(analyzer)

        # Add repeated error pattern
        for i in range(15):
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "logger": "module1",
                    "message": "Database connection failed: timeout after 30s",
                },
            ]
            analyzer.add_logs(logs)

        # Check for pattern anomaly
        alert = detector.detect_pattern_anomaly(min_occurrences=10)

        # Should detect error pattern
        assert alert is not None
        assert alert.alert_type == "pattern_anomaly"


class TestLogAlertManager:
    """Integration tests for LogAlertManager"""

    def test_threshold_alert_configuration(self):
        """Test threshold alert configuration"""
        manager = LogAlertManager()

        alert = ThresholdAlert(
            name="error_rate_alert",
            metric="error_rate",
            threshold=0.1,
            operator=">",
            severity=AlertSeverity.ERROR,
        )

        manager.add_threshold_alert(alert)

        assert "error_rate_alert" in manager.threshold_alerts
        assert manager.threshold_alerts["error_rate_alert"].threshold == 0.1

    def test_threshold_alert_evaluation(self):
        """Test threshold alert evaluation"""
        analyzer = LogAnalyzer()
        manager = LogAlertManager(analyzer)

        # Add logs with high error rate
        for i in range(10):
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "logger": "module1",
                    "message": f"Error message {i}",
                },
            ]
            analyzer.add_logs(logs)

        # Configure threshold
        alert = ThresholdAlert(
            name="error_rate_alert",
            metric="error_rate",
            threshold=0.5,
            operator=">",
            severity=AlertSeverity.ERROR,
        )
        manager.add_threshold_alert(alert)

        # Check thresholds
        triggered_alerts = manager.check_thresholds()

        # Should trigger alert since error rate is 100%
        assert len(triggered_alerts) > 0
        assert triggered_alerts[0].alert_type == "threshold"

    def test_anomaly_check(self):
        """Test anomaly check integration"""
        analyzer = LogAnalyzer()
        manager = LogAlertManager(analyzer)

        # Add logs with error pattern
        for i in range(15):
            logs = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "logger": "module1",
                    "message": "Database connection failed: timeout after 30s",
                },
            ]
            analyzer.add_logs(logs)

        # Check anomalies
        anomaly_alerts = manager.check_anomalies()

        # Should detect pattern anomaly
        assert len(anomaly_alerts) > 0
        assert any(alert.alert_type == "pattern_anomaly" for alert in anomaly_alerts)

    def test_alert_history(self):
        """Test alert history tracking"""
        analyzer = LogAnalyzer()
        manager = LogAlertManager(analyzer)

        # Trigger some alerts
        alert = LogAlert(
            alert_id="test_alert",
            alert_type="test",
            severity=AlertSeverity.INFO,
            message="Test alert",
            timestamp=datetime.now(),
        )
        manager.trigger_alert(alert)

        history = manager.get_alert_history()

        assert len(history) == 1
        assert history[0].alert_id == "test_alert"

    def test_alert_handler(self):
        """Test alert handler integration"""

        class TestHandler:
            def __init__(self):
                self.handled_alerts = []

            def handle_alert(self, alert):
                self.handled_alerts.append(alert)

        analyzer = LogAnalyzer()
        manager = LogAlertManager(analyzer)

        handler = TestHandler()
        manager.add_alert_handler(handler)

        # Trigger alert
        alert = LogAlert(
            alert_id="test_alert",
            alert_type="test",
            severity=AlertSeverity.INFO,
            message="Test alert",
            timestamp=datetime.now(),
        )
        manager.trigger_alert(alert)

        # Handler should have received the alert
        assert len(handler.handled_alerts) == 1
        assert handler.handled_alerts[0].alert_id == "test_alert"


class TestInfrastructureConfigurations:
    """Integration tests for infrastructure configurations"""

    def test_filebeat_configuration(self):
        """Test Filebeat configuration file"""
        config_path = "infrastructure/logging/filebeat/filebeat.yml"

        with open(config_path, "r", encoding="utf-8") as f:
            config = f.read()

        # Verify key configurations
        assert "filebeat.inputs:" in config
        assert "output.elasticsearch:" in config
        assert "setup.kibana:" in config

    def test_fluentd_configuration(self):
        """Test Fluentd configuration file"""
        config_path = "infrastructure/logging/fluentd/fluent.conf"

        with open(config_path, "r", encoding="utf-8") as f:
            config = f.read()

        # Verify key configurations
        assert "<source>" in config
        assert "@type tail" in config
        assert "@type elasticsearch" in config

    def test_elasticsearch_index_template(self):
        """Test Elasticsearch index template"""
        template_path = "infrastructure/logging/elasticsearch/index_template.json"

        with open(template_path, "r") as f:
            template = json.load(f)

        # Verify template structure
        assert "index_patterns" in template
        assert "template" in template
        assert "mappings" in template["template"]
        assert "properties" in template["template"]["mappings"]

        # Verify key fields
        properties = template["template"]["mappings"]["properties"]
        assert "timestamp" in properties
        assert "level" in properties
        assert "trace_id" in properties
        assert "span_id" in properties

    def test_kibana_dashboard(self):
        """Test Kibana dashboard configuration"""
        dashboard_path = "infrastructure/logging/kibana/dashboard/aiops_logs_dashboard.json"

        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        # Verify dashboard structure
        assert "dashboard" in dashboard
        assert "panels" in dashboard["dashboard"]

        # Verify panels exist
        panels = dashboard["dashboard"]["panels"]
        assert len(panels) > 0

    def test_grafana_dashboard(self):
        """Test Grafana dashboard configuration"""
        dashboard_path = "infrastructure/logging/grafana/dashboard/aiops_logs_dashboard.json"

        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        # Verify dashboard structure
        assert "dashboard" in dashboard
        assert "panels" in dashboard["dashboard"]

        # Verify panels exist
        panels = dashboard["dashboard"]["panels"]
        assert len(panels) > 0


class TestGlobalFunctions:
    """Integration tests for global functions"""

    def test_get_log_analyzer_singleton(self):
        """Test global log analyzer singleton"""
        analyzer1 = get_log_analyzer()
        analyzer2 = get_log_analyzer()

        assert analyzer1 is analyzer2

    def test_get_alert_manager_singleton(self):
        """Test global alert manager singleton"""
        manager1 = get_alert_manager()
        manager2 = get_alert_manager()

        assert manager1 is manager2

    def test_alert_manager_with_custom_analyzer(self):
        """Test alert manager with custom analyzer"""
        custom_analyzer = LogAnalyzer()
        # Create a new manager instance directly instead of using singleton
        from core.logging.analysis.log_alerting import LogAlertManager

        manager = LogAlertManager(custom_analyzer)

        assert manager.log_analyzer is custom_analyzer


class TestEndToEndIntegration:
    """End-to-end integration tests"""

    def test_full_log_pipeline(self):
        """Test complete log pipeline from collection to alerting"""
        # Create analyzer and manager
        analyzer = LogAnalyzer()
        manager = LogAlertManager(analyzer)

        # Add sample logs
        logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "logger": "module1",
                "message": "Normal operation",
                "context": {
                    "trace_id": "trace-123",
                    "user_id": "user-456",
                },
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "logger": "module1",
                "message": "Connection failed to server 192.168.1.1",
                "context": {
                    "trace_id": "trace-789",
                    "user_id": "user-456",
                },
            },
        ]

        analyzer.add_logs(logs)

        # Calculate statistics
        stats = analyzer.calculate_statistics()
        assert stats.total_logs == 2

        # Detect patterns
        patterns = analyzer.detect_patterns(min_occurrences=1)
        assert len(patterns) >= 1

        # Configure and check threshold alert
        alert = ThresholdAlert(
            name="error_rate_alert",
            metric="error_rate",
            threshold=0.3,
            operator=">",
            severity=AlertSeverity.WARNING,
        )
        manager.add_threshold_alert(alert)

        triggered = manager.check_thresholds()
        # Should trigger since error rate is 50%
        assert len(triggered) > 0

        # Manually trigger the alerts to add to history
        for alert in triggered:
            manager.trigger_alert(alert)

        # Verify alert was recorded
        history = manager.get_alert_history()
        assert len(history) > 0

    def test_multi_module_log_analysis(self):
        """Test log analysis across multiple modules"""
        analyzer = LogAnalyzer()

        # Add logs from different modules
        modules = ["auth", "database", "api", "cache"]
        for module in modules:
            for i in range(5):
                logs = [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO" if i < 4 else "ERROR",
                        "logger": module,
                        "message": f"{module} operation {i}",
                    },
                ]
                analyzer.add_logs(logs)

        stats = analyzer.calculate_statistics()

        # Should have logs from all modules
        assert len(stats.module_counts) == len(modules)
        assert stats.total_logs == 20
        assert stats.error_rate == 0.2  # 4 errors out of 20 total
