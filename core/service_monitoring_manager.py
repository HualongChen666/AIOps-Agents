# -*- coding: utf-8 -*-
"""
Service Monitoring Manager
Enterprise-grade service monitoring with performance analysis and anomaly detection
"""

import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class AlertSeverity(Enum):
    """Alert severity"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Metric type"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class ServiceMetric:
    """Service metric"""

    metric_name: str
    service_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceAlert:
    """Service alert"""

    alert_id: str
    service_name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyDetection:
    """Anomaly detection result"""

    service_name: str
    metric_name: str
    is_anomaly: bool
    anomaly_score: float
    expected_value: float
    actual_value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceMonitoringManager:
    """
    Enterprise-grade service monitoring manager
    Provides service metrics, performance analysis, anomaly detection, and alerting
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize service monitoring manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.service_metrics: Dict[str, Dict[str, Any]] = {}

        # Alerts
        self.alerts: Dict[str, ServiceAlert] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}

        # Anomaly detection
        self.anomalies: List[AnomalyDetection] = []
        self.baseline_metrics: Dict[str, float] = {}

        # Configuration
        self.anomaly_threshold = self.config.get("anomaly_threshold", 2.0)  # Standard deviations
        self.alert_cooldown_seconds = self.config.get("alert_cooldown_seconds", 300)

        # Statistics
        self.total_metrics_collected = 0
        self.total_alerts_generated = 0
        self.total_anomalies_detected = 0

        logger.info("Service monitoring manager initialized")

    def record_metric(
        self,
        metric_name: str,
        service_name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record service metric

        Args:
            metric_name: Metric name
            service_name: Service name
            value: Metric value
            metric_type: Metric type
            labels: Metric labels
            metadata: Additional metadata
        """
        metric = ServiceMetric(
            metric_name=metric_name,
            service_name=service_name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {},
            metadata=metadata or {},
        )

        # Store metric
        metric_key = f"{service_name}:{metric_name}"
        self.metrics[metric_key].append(metric)

        # Update service metrics
        if service_name not in self.service_metrics:
            self.service_metrics[service_name] = {
                "total_metrics": 0,
                "last_updated": datetime.now(timezone.utc),
            }

        self.service_metrics[service_name]["total_metrics"] += 1
        self.service_metrics[service_name]["last_updated"] = datetime.now(timezone.utc)

        self.total_metrics_collected += 1

        logger.debug(f"Recorded metric: {metric_name}={value} for {service_name}")

    def get_service_metrics(
        self, service_name: str, time_range: Optional[timedelta] = None
    ) -> List[ServiceMetric]:
        """
        Get service metrics

        Args:
            service_name: Service name
            time_range: Time range for metrics

        Returns:
            List of metrics
        """
        metrics = []

        for metric_key, metric_deque in self.metrics.items():
            if metric_key.startswith(f"{service_name}:"):
                if time_range:
                    cutoff = datetime.now(timezone.utc) - time_range
                    metrics.extend([m for m in metric_deque if m.timestamp > cutoff])
                else:
                    metrics.extend(metric_deque)

        return sorted(metrics, key=lambda x: x.timestamp)

    def analyze_service_performance(
        self, service_name: str, time_range: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """
        Analyze service performance

        Args:
            service_name: Service name
            time_range: Time range for analysis

        Returns:
            Performance analysis
        """
        metrics = self.get_service_metrics(service_name, time_range)

        if not metrics:
            return {
                "service_name": service_name,
                "metrics_count": 0,
                "message": "No metrics available for analysis",
            }

        # Group metrics by name
        metrics_by_name = defaultdict(list)
        for metric in metrics:
            metrics_by_name[metric.metric_name].append(metric.value)

        # Calculate statistics for each metric
        analysis: Dict[str, Any] = {
            "service_name": service_name,
            "time_range_hours": time_range.total_seconds() / 3600,
            "metrics_count": len(metrics),
            "metric_analysis": {},
        }
        metric_analysis_dict: Dict[str, Dict[str, Any]] = analysis["metric_analysis"]

        for metric_name, values in metrics_by_name.items():
            if len(values) > 0:
                metric_analysis_dict[metric_name] = {
                    "count": len(values),
                    "avg": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
                    "p95": self._calculate_percentile(values, 95),
                    "p99": self._calculate_percentile(values, 99),
                }

        return analysis

    def detect_anomaly(
        self, metric_name: str, service_name: str, current_value: float
    ) -> AnomalyDetection:
        """
        Detect anomaly in metric

        Args:
            metric_name: Metric name
            service_name: Service name
            current_value: Current metric value

        Returns:
            Anomaly detection result
        """
        # Get historical values
        metric_key = f"{service_name}:{metric_name}"
        historical_values = [m.value for m in self.metrics.get(metric_key, [])]

        if len(historical_values) < 10:
            # Not enough data for anomaly detection
            return AnomalyDetection(
                service_name=service_name,
                metric_name=metric_name,
                is_anomaly=False,
                anomaly_score=0.0,
                expected_value=current_value,
                actual_value=current_value,
                timestamp=datetime.now(timezone.utc),
                metadata={"message": "Insufficient data for anomaly detection"},
            )

        # Calculate baseline
        expected_value = statistics.mean(historical_values)
        std_dev = statistics.stdev(historical_values)

        # Calculate anomaly score (z-score)
        if std_dev > 0:
            anomaly_score = abs(current_value - expected_value) / std_dev
        else:
            anomaly_score = 0.0

        # Determine if anomaly
        is_anomaly = anomaly_score > self.anomaly_threshold

        detection = AnomalyDetection(
            service_name=service_name,
            metric_name=metric_name,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            expected_value=expected_value,
            actual_value=current_value,
            timestamp=datetime.now(timezone.utc),
            metadata={
                "threshold": self.anomaly_threshold,
                "std_dev": std_dev,
                "sample_size": len(historical_values),
            },
        )

        if is_anomaly:
            self.anomalies.append(detection)
            self.total_anomalies_detected += 1
            logger.warning(
                f"Anomaly detected: {service_name}/{metric_name} (score={anomaly_score:.2f})"
            )

        return detection

    def create_alert_rule(
        self,
        rule_id: str,
        service_name: str,
        metric_name: str,
        threshold: float,
        comparison: str = "greater_than",
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> None:
        """
        Create alert rule

        Args:
            rule_id: Rule ID
            service_name: Service name
            metric_name: Metric name
            threshold: Threshold value
            comparison: Comparison operator
            severity: Alert severity
        """
        self.alert_rules[rule_id] = {
            "service_name": service_name,
            "metric_name": metric_name,
            "threshold": threshold,
            "comparison": comparison,
            "severity": severity,
            "created_at": datetime.now(timezone.utc),
        }

        logger.info(f"Created alert rule: {rule_id}")

    def check_alert_rules(self) -> List[ServiceAlert]:
        """
        Check alert rules and generate alerts

        Returns:
            List of generated alerts
        """
        generated_alerts = []

        for rule_id, rule in self.alert_rules.items():
            # Get latest metric value
            metric_key = f"{rule['service_name']}:{rule['metric_name']}"
            metric_deque: deque = self.metrics.get(metric_key, deque())

            if not metric_deque:
                continue

            latest_metric = metric_deque[-1]
            current_value = latest_metric.value
            threshold = rule["threshold"]

            # Check condition
            should_alert = False
            if rule["comparison"] == "greater_than":
                should_alert = current_value > threshold
            elif rule["comparison"] == "less_than":
                should_alert = current_value < threshold
            elif rule["comparison"] == "equals":
                should_alert = current_value == threshold

            if should_alert:
                # Check cooldown
                alert_key = f"{rule_id}:{rule['service_name']}"
                if alert_key in self.alerts:
                    last_alert = self.alerts[alert_key]
                    time_since_last = datetime.now(timezone.utc) - last_alert.timestamp
                    if time_since_last.total_seconds() < self.alert_cooldown_seconds:
                        continue

                # Generate alert
                alert = ServiceAlert(
                    alert_id=f"{rule_id}_{datetime.now(timezone.utc).timestamp()}",
                    service_name=rule["service_name"],
                    severity=rule["severity"],
                    message=(
                        f"Metric {rule['metric_name']} exceeded threshold: "
                        f"{current_value} {rule['comparison']} {threshold}"
                    ),
                    metric_name=rule["metric_name"],
                    threshold=threshold,
                    current_value=current_value,
                    timestamp=datetime.now(timezone.utc),
                )

                self.alerts[alert_key] = alert
                generated_alerts.append(alert)
                self.total_alerts_generated += 1

                logger.warning(f"Alert generated: {alert.alert_id} - {alert.message}")

        return generated_alerts

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Get monitoring summary

        Returns:
            Monitoring summary
        """
        return {
            "total_metrics_collected": self.total_metrics_collected,
            "total_services_monitored": len(self.service_metrics),
            "total_alerts_generated": self.total_alerts_generated,
            "total_anomalies_detected": self.total_anomalies_detected,
            "active_alert_rules": len(self.alert_rules),
            "active_alerts": len(
                [
                    a
                    for a in self.alerts.values()
                    if (datetime.now(timezone.utc) - a.timestamp).total_seconds() < 3600
                ]
            ),
            "services": list(self.service_metrics.keys()),
        }

    def _calculate_percentile(self, data: List[float], percentile: float) -> float:
        """
        Calculate percentile of data

        Args:
            data: Data points
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value
        """
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


# Global instance
_service_monitoring_manager: Optional[ServiceMonitoringManager] = None


def get_service_monitoring_manager() -> ServiceMonitoringManager:
    """
    Get the global service monitoring manager instance

    Returns:
        ServiceMonitoringManager instance
    """
    global _service_monitoring_manager
    if _service_monitoring_manager is None:
        _service_monitoring_manager = ServiceMonitoringManager()
    return _service_monitoring_manager
