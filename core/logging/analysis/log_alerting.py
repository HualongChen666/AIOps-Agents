# -*- coding: utf-8 -*-
"""
Log Alerting Module
日志告警模块

Provides log alerting capabilities including anomaly detection and threshold alerts.
"""

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from .log_analyzer import LogAnalyzer


class AlertSeverity(Enum):
    """Alert severity enumeration"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogAlert:
    """Log alert data class"""

    alert_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    triggered_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "triggered_by": self.triggered_by,
        }


class AlertHandler(ABC):
    """Abstract base class for alert handlers"""

    @abstractmethod
    def handle_alert(self, alert: LogAlert) -> None:
        """
        Handle an alert

        Args:
            alert: Alert to handle
        """


@dataclass
class ThresholdAlert:
    """Threshold alert configuration"""

    name: str
    metric: str
    threshold: float
    operator: str = ">"  # ">", "<", ">=", "<=", "=="
    severity: AlertSeverity = AlertSeverity.WARNING
    window: timedelta = timedelta(minutes=5)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self, value: float) -> bool:
        """
        Evaluate threshold condition

        Args:
            value: Current metric value

        Returns:
            True if threshold is triggered
        """
        if self.operator == ">":
            return value > self.threshold
        elif self.operator == "<":
            return value < self.threshold
        elif self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == "==":
            return value == self.threshold
        return False


class AnomalyDetector:
    """
    Anomaly detector for logs
    日志异常检测器

    Detects anomalies in log patterns and metrics.
    """

    def __init__(self, log_analyzer: LogAnalyzer):
        """
        Initialize anomaly detector

        Args:
            log_analyzer: Log analyzer instance
        """
        self.log_analyzer = log_analyzer
        self._baseline_metrics: Dict[str, List[float]] = {}
        self._baseline_window = 100

    def detect_error_rate_anomaly(self, threshold: float = 2.0) -> Optional[LogAlert]:
        """
        Detect error rate anomaly

        Args:
            threshold: Standard deviation threshold

        Returns:
            LogAlert if anomaly detected, None otherwise
        """
        stats = self.log_analyzer.calculate_statistics()

        if stats.total_logs == 0:
            return None

        current_error_rate = stats.error_rate

        # Update baseline
        if "error_rate" not in self._baseline_metrics:
            self._baseline_metrics["error_rate"] = []
        self._baseline_metrics["error_rate"].append(current_error_rate)

        # Maintain baseline window
        if len(self._baseline_metrics["error_rate"]) > self._baseline_window:
            self._baseline_metrics["error_rate"].pop(0)

        # Calculate anomaly if we have enough baseline
        if len(self._baseline_metrics["error_rate"]) >= 10:
            baseline = self._baseline_metrics["error_rate"][:-1]
            import statistics

            mean = statistics.mean(baseline)
            stdev = statistics.stdev(baseline) if len(baseline) > 1 else 0.0

            if stdev > 0:
                z_score = abs(current_error_rate - mean) / stdev
                if z_score > threshold:
                    return LogAlert(
                        alert_id=f"error_rate_anomaly_{int(time.time())}",
                        alert_type="error_rate_anomaly",
                        severity=AlertSeverity.ERROR,
                        message=(
                            f"Error rate anomaly detected: {current_error_rate:.2%} "
                            f"(baseline: {mean:.2%}, z-score: {z_score:.2f})"
                        ),
                        timestamp=datetime.now(),
                        metadata={
                            "current_error_rate": current_error_rate,
                            "baseline_error_rate": mean,
                            "z_score": z_score,
                        },
                        triggered_by="anomaly_detector",
                    )

        return None

    def detect_volume_anomaly(self, threshold: float = 2.0) -> Optional[LogAlert]:
        """
        Detect log volume anomaly

        Args:
            threshold: Standard deviation threshold

        Returns:
            LogAlert if anomaly detected, None otherwise
        """
        trends = self.log_analyzer.calculate_trends()

        if not trends.time_series:
            return None

        current_volume = trends.time_series[-1][1]

        # Update baseline
        if "log_volume" not in self._baseline_metrics:
            self._baseline_metrics["log_volume"] = []
        self._baseline_metrics["log_volume"].append(current_volume)

        # Maintain baseline window
        if len(self._baseline_metrics["log_volume"]) > self._baseline_window:
            self._baseline_metrics["log_volume"].pop(0)

        # Calculate anomaly if we have enough baseline
        if len(self._baseline_metrics["log_volume"]) >= 10:
            baseline = self._baseline_metrics["log_volume"][:-1]
            import statistics

            mean = statistics.mean(baseline)
            stdev = statistics.stdev(baseline) if len(baseline) > 1 else 0.0

            if stdev > 0:
                z_score = abs(current_volume - mean) / stdev
                if z_score > threshold:
                    return LogAlert(
                        alert_id=f"volume_anomaly_{int(time.time())}",
                        alert_type="volume_anomaly",
                        severity=AlertSeverity.WARNING,
                        message=(
                            f"Log volume anomaly detected: {current_volume} "
                            f"(baseline: {mean:.2f}, z-score: {z_score:.2f})"
                        ),
                        timestamp=datetime.now(),
                        metadata={
                            "current_volume": current_volume,
                            "baseline_volume": mean,
                            "z_score": z_score,
                        },
                        triggered_by="anomaly_detector",
                    )

        return None

    def detect_pattern_anomaly(self, min_occurrences: int = 10) -> Optional[LogAlert]:
        """
        Detect new or unusual log patterns

        Args:
            min_occurrences: Minimum pattern occurrences to consider

        Returns:
            LogAlert if anomaly detected, None otherwise
        """
        patterns = self.log_analyzer.detect_patterns(min_occurrences)

        # Check for error patterns
        error_patterns = [p for p in patterns if p.severity == "error"]

        if error_patterns:
            # Find the most frequent error pattern
            top_error = max(error_patterns, key=lambda p: p.count)

            return LogAlert(
                alert_id=f"pattern_anomaly_{int(time.time())}",
                alert_type="pattern_anomaly",
                severity=AlertSeverity.ERROR,
                message=(
                    f"Frequent error pattern detected: '{top_error.pattern}' "
                    f"(occurrences: {top_error.count})"
                ),
                timestamp=datetime.now(),
                metadata={
                    "pattern": top_error.pattern,
                    "count": top_error.count,
                    "examples": top_error.examples[:3],
                },
                triggered_by="anomaly_detector",
            )

        return None


class LogAlertManager:
    """
    Log alert manager
    日志告警管理器

    Manages log alerts including threshold alerts and anomaly detection.
    """

    def __init__(self, log_analyzer: Optional[LogAnalyzer] = None):
        """
        Initialize log alert manager

        Args:
            log_analyzer: Optional log analyzer instance
        """
        self.log_analyzer = log_analyzer or LogAnalyzer()
        self.anomaly_detector = AnomalyDetector(self.log_analyzer)
        self.threshold_alerts: Dict[str, ThresholdAlert] = {}
        self.alert_handlers: List[AlertHandler] = []
        self._alert_history: List[LogAlert] = []
        self._lock = threading.RLock()
        self._running = False
        self._check_interval = 30  # seconds

        logger.info("Log alert manager initialized")

    def add_threshold_alert(self, alert: ThresholdAlert) -> None:
        """
        Add a threshold alert

        Args:
            alert: Threshold alert configuration
        """
        with self._lock:
            self.threshold_alerts[alert.name] = alert
            logger.info(f"Threshold alert added: {alert.name}")

    def remove_threshold_alert(self, name: str) -> None:
        """
        Remove a threshold alert

        Args:
            name: Alert name
        """
        with self._lock:
            if name in self.threshold_alerts:
                del self.threshold_alerts[name]
                logger.info(f"Threshold alert removed: {name}")

    def add_alert_handler(self, handler: AlertHandler) -> None:
        """
        Add an alert handler

        Args:
            handler: Alert handler instance
        """
        self.alert_handlers.append(handler)
        logger.info(f"Alert handler added: {handler.__class__.__name__}")

    def remove_alert_handler(self, handler: AlertHandler) -> None:
        """
        Remove an alert handler

        Args:
            handler: Alert handler instance
        """
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)
            logger.info(f"Alert handler removed: {handler.__class__.__name__}")

    def check_thresholds(self) -> List[LogAlert]:
        """
        Check all threshold alerts

        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        stats = self.log_analyzer.calculate_statistics()
        trends = self.log_analyzer.calculate_trends()

        with self._lock:
            for name, alert_config in self.threshold_alerts.items():
                if not alert_config.enabled:
                    continue

                # Get metric value
                value = self._get_metric_value(alert_config.metric, stats, trends)

                if value is not None and alert_config.evaluate(value):
                    alert = LogAlert(
                        alert_id=f"threshold_{name}_{
                            int(
                                time.time())}",
                        alert_type="threshold",
                        severity=alert_config.severity,
                        message=f"Threshold alert '{name}' triggered: {
                            alert_config.metric} = {value} {
                            alert_config.operator} {
                            alert_config.threshold}",
                        timestamp=datetime.now(),
                        metadata={
                            "alert_name": name,
                            "metric": alert_config.metric,
                            "value": value,
                            "threshold": alert_config.threshold,
                            "operator": alert_config.operator,
                        },
                        triggered_by="threshold_alert",
                    )
                    triggered_alerts.append(alert)

        return triggered_alerts

    def check_anomalies(self) -> List[LogAlert]:
        """
        Check for anomalies

        Returns:
            List of anomaly alerts
        """
        anomaly_alerts = []

        # Check error rate anomaly
        error_alert = self.anomaly_detector.detect_error_rate_anomaly()
        if error_alert:
            anomaly_alerts.append(error_alert)

        # Check volume anomaly
        volume_alert = self.anomaly_detector.detect_volume_anomaly()
        if volume_alert:
            anomaly_alerts.append(volume_alert)

        # Check pattern anomaly
        pattern_alert = self.anomaly_detector.detect_pattern_anomaly()
        if pattern_alert:
            anomaly_alerts.append(pattern_alert)

        return anomaly_alerts

    def _get_metric_value(self, metric: str, stats, trends) -> Optional[float]:
        """
        Get metric value

        Args:
            metric: Metric name
            stats: Log statistics
            trends: Log trends

        Returns:
            Metric value or None
        """
        if metric == "error_rate":
            return stats.error_rate  # type: ignore[no-any-return]
        elif metric == "total_logs":
            return stats.total_logs  # type: ignore[no-any-return]
        elif metric == "avg_response_time":
            return stats.avg_response_time  # type: ignore[no-any-return]
        elif metric == "unique_users":
            return stats.unique_users  # type: ignore[no-any-return]
        elif metric == "growth_rate":
            return trends.growth_rate  # type: ignore[no-any-return]
        elif metric == "peak_value":
            return trends.peak_value  # type: ignore[no-any-return]
        return None

    def trigger_alert(self, alert: LogAlert) -> None:
        """
        Trigger an alert

        Args:
            alert: Alert to trigger
        """
        with self._lock:
            self._alert_history.append(alert)
            logger.warning(f"Alert triggered: {alert.message}")

        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler.handle_alert(alert)
            except Exception as e:
                logger.error(f"Error in alert handler {handler.__class__.__name__}: {e}")

    def run_check(self) -> None:
        """Run a single alert check"""
        # Check thresholds
        threshold_alerts = self.check_thresholds()
        for alert in threshold_alerts:
            self.trigger_alert(alert)

        # Check anomalies
        anomaly_alerts = self.check_anomalies()
        for alert in anomaly_alerts:
            self.trigger_alert(alert)

    def start_monitoring(self) -> None:
        """Start continuous monitoring"""
        if self._running:
            logger.warning("Alert monitoring is already running")
            return

        self._running = True
        logger.info("Starting alert monitoring")

        def monitoring_loop():
            while self._running:
                try:
                    self.run_check()
                except Exception as e:
                    logger.error(f"Error in alert monitoring: {e}")
                time.sleep(self._check_interval)

        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()

    def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        self._running = False
        logger.info("Stopping alert monitoring")

    def get_alert_history(self, limit: int = 100) -> List[LogAlert]:
        """
        Get alert history

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alerts
        """
        with self._lock:
            return self._alert_history[-limit:]

    def clear_alert_history(self) -> None:
        """Clear alert history"""
        with self._lock:
            self._alert_history.clear()
            logger.info("Alert history cleared")


# Global alert manager instance
_global_alert_manager: Optional[LogAlertManager] = None


def get_alert_manager(log_analyzer: Optional[LogAnalyzer] = None) -> LogAlertManager:
    """
    Get global alert manager instance

    Args:
        log_analyzer: Optional log analyzer instance

    Returns:
        LogAlertManager instance
    """
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = LogAlertManager(log_analyzer)
    return _global_alert_manager
