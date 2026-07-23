# -*- coding: utf-8 -*-
"""
Integration Monitoring Enhancement (Phase 5)
Enterprise-grade integration monitoring system with comprehensive observability
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class MetricType(Enum):
    """Metric type"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MonitorStatus(Enum):
    """Monitor status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class Monitor:
    """Monitor configuration"""

    monitor_id: str
    monitor_name: str
    metric_type: MetricType
    target: str
    check_interval: int = 60
    threshold: Optional[float] = None
    comparison: str = "greater_than"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricData:
    """Metric data point"""

    metric_id: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert configuration"""

    alert_id: str
    alert_name: str
    monitor_id: str
    severity: AlertSeverity
    condition: str
    notification_channels: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertInstance:
    """Alert instance"""

    alert_instance_id: str
    alert_id: str
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    status: str = "active"
    value: float = 0.0
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntegrationMonitoringSystem:
    """Enterprise-grade integration monitoring system"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize integration monitoring system

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Monitors
        self.monitors: Dict[str, Monitor] = {}
        self._initialize_default_monitors()

        # Metrics
        self.metrics: Dict[str, List[MetricData]] = {}

        # Alerts
        self.alerts: Dict[str, Alert] = {}
        self._initialize_default_alerts()

        # Alert instances
        self.alert_instances: List[AlertInstance] = []

        # Notification handlers
        self.notification_handlers: List[Callable] = []

        # Configuration
        self.auto_monitoring = self.config.get("auto_monitoring", True)
        self.data_retention_hours = self.config.get("data_retention_hours", 168)  # 7 days

        # Statistics
        self.total_metrics = 0
        self.total_alerts = 0
        self.active_alerts = 0

        logger.info("Integration monitoring system initialized")

    def _initialize_default_monitors(self):
        """Initialize default monitors"""
        # System monitors
        self.monitors["cpu_monitor"] = Monitor(
            monitor_id="cpu_monitor",
            monitor_name="CPU Usage Monitor",
            metric_type=MetricType.GAUGE,
            target="system.cpu.usage",
            check_interval=60,
            threshold=80.0,
            comparison="greater_than",
        )

        self.monitors["memory_monitor"] = Monitor(
            monitor_id="memory_monitor",
            monitor_name="Memory Usage Monitor",
            metric_type=MetricType.GAUGE,
            target="system.memory.usage",
            check_interval=60,
            threshold=85.0,
            comparison="greater_than",
        )

        self.monitors["disk_monitor"] = Monitor(
            monitor_id="disk_monitor",
            monitor_name="Disk Usage Monitor",
            metric_type=MetricType.GAUGE,
            target="system.disk.usage",
            check_interval=300,
            threshold=90.0,
            comparison="greater_than",
        )

        # Application monitors
        self.monitors["api_latency_monitor"] = Monitor(
            monitor_id="api_latency_monitor",
            monitor_name="API Latency Monitor",
            metric_type=MetricType.HISTOGRAM,
            target="api.latency",
            check_interval=30,
            threshold=500.0,
            comparison="greater_than",
        )

        self.monitors["api_error_rate_monitor"] = Monitor(
            monitor_id="api_error_rate_monitor",
            monitor_name="API Error Rate Monitor",
            metric_type=MetricType.GAUGE,
            target="api.error_rate",
            check_interval=30,
            threshold=5.0,
            comparison="greater_than",
        )

        self.monitors["request_rate_monitor"] = Monitor(
            monitor_id="request_rate_monitor",
            monitor_name="Request Rate Monitor",
            metric_type=MetricType.COUNTER,
            target="api.requests.total",
            check_interval=30,
            threshold=None,
            comparison="none",
        )

        # Integration monitors
        self.monitors["integration_health_monitor"] = Monitor(
            monitor_id="integration_health_monitor",
            monitor_name="Integration Health Monitor",
            metric_type=MetricType.GAUGE,
            target="integration.health",
            check_interval=60,
            threshold=1.0,
            comparison="less_than",
        )

        logger.info(f"Initialized {len(self.monitors)} default monitors")

    def _initialize_default_alerts(self):
        """Initialize default alerts"""
        self.alerts["cpu_alert"] = Alert(
            alert_id="cpu_alert",
            alert_name="High CPU Usage Alert",
            monitor_id="cpu_monitor",
            severity=AlertSeverity.WARNING,
            condition="cpu_usage > 80%",
            notification_channels=["email", "slack"],
            enabled=True,
        )

        self.alerts["memory_alert"] = Alert(
            alert_id="memory_alert",
            alert_name="High Memory Usage Alert",
            monitor_id="memory_monitor",
            severity=AlertSeverity.WARNING,
            condition="memory_usage > 85%",
            notification_channels=["email", "slack"],
            enabled=True,
        )

        self.alerts["api_latency_alert"] = Alert(
            alert_id="api_latency_alert",
            alert_name="High API Latency Alert",
            monitor_id="api_latency_monitor",
            severity=AlertSeverity.ERROR,
            condition="api_latency > 500ms",
            notification_channels=["email", "slack", "pagerduty"],
            enabled=True,
        )

        self.alerts["api_error_rate_alert"] = Alert(
            alert_id="api_error_rate_alert",
            alert_name="High API Error Rate Alert",
            monitor_id="api_error_rate_monitor",
            severity=AlertSeverity.CRITICAL,
            condition="api_error_rate > 5%",
            notification_channels=["email", "slack", "pagerduty"],
            enabled=True,
        )

        self.alerts["integration_health_alert"] = Alert(
            alert_id="integration_health_alert",
            alert_name="Integration Health Alert",
            monitor_id="integration_health_monitor",
            severity=AlertSeverity.CRITICAL,
            condition="integration_health < 1",
            notification_channels=["email", "slack", "pagerduty"],
            enabled=True,
        )

        logger.info(f"Initialized {len(self.alerts)} default alerts")

    def register_monitor(self, monitor: Monitor) -> None:
        """
        Register monitor

        Args:
            monitor: Monitor configuration
        """
        self.monitors[monitor.monitor_id] = monitor
        logger.info(f"Registered monitor: {monitor.monitor_id}")

    def register_alert(self, alert: Alert) -> None:
        """
        Register alert

        Args:
            alert: Alert configuration
        """
        self.alerts[alert.alert_id] = alert
        logger.info(f"Registered alert: {alert.alert_id}")

    async def record_metric(
        self, metric_id: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record metric data

        Args:
            metric_id: Metric ID
            value: Metric value
            labels: Metric labels
        """
        metric_data = MetricData(metric_id=metric_id, value=value, labels=labels or {})

        if metric_id not in self.metrics:
            self.metrics[metric_id] = []

        self.metrics[metric_id].append(metric_data)
        self.total_metrics += 1

        # Check monitors
        await self._check_monitors(metric_id, value)

        # Prune old data
        await self._prune_old_metrics()

        logger.debug(f"Recorded metric: {metric_id} = {value}")

    async def _check_monitors(self, metric_id: str, value: float) -> None:
        """
        Check monitors for metric

        Args:
            metric_id: Metric ID
            value: Metric value
        """
        for monitor in self.monitors.values():
            if not monitor.enabled:
                continue

            if monitor.target != metric_id:
                continue

            # Check threshold condition
            should_alert = False

            if monitor.threshold is not None:
                if monitor.comparison == "greater_than" and value > monitor.threshold:
                    should_alert = True
                elif monitor.comparison == "less_than" and value < monitor.threshold:
                    should_alert = True
                elif monitor.comparison == "equal_to" and value == monitor.threshold:
                    should_alert = True

            if should_alert:
                await self._trigger_alert(monitor, value)

    async def _trigger_alert(self, monitor: Monitor, value: float) -> None:
        """
        Trigger alert for monitor

        Args:
            monitor: Monitor
            value: Metric value
        """
        # Find alerts for this monitor
        for alert in self.alerts.values():
            if alert.monitor_id == monitor.monitor_id and alert.enabled:
                # Create alert instance
                alert_instance = AlertInstance(
                    alert_instance_id=f"alert_{  # noqa: E501
                        datetime.now(
                            timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}",
                    alert_id=alert.alert_id,
                    value=value,
                    message=f"Alert triggered: {
                        alert.alert_name} - Value: {value}",
                )

                self.alert_instances.append(alert_instance)
                self.total_alerts += 1
                self.active_alerts += 1

                # Notify handlers
                await self._notify_alert(alert, alert_instance)

    async def _notify_alert(self, alert: Alert, alert_instance: AlertInstance) -> None:
        """
        Notify about alert

        Args:
            alert: Alert configuration
            alert_instance: Alert instance
        """
        for handler in self.notification_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert, alert_instance)
                else:
                    handler(alert, alert_instance)
            except Exception as e:
                logger.error(f"Alert notification handler failed: {e}")

    async def _prune_old_metrics(self) -> None:
        """Prune old metric data based on retention policy"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.data_retention_hours)

        for metric_id in self.metrics:
            self.metrics[metric_id] = [
                m for m in self.metrics[metric_id] if m.timestamp > cutoff_time
            ]

    async def start_monitoring(self) -> None:
        """Start monitoring loop"""

        async def monitoring_loop():
            while True:
                try:
                    # Simulate metric collection
                    await self._collect_metrics()

                    await asyncio.sleep(30)  # Collect every 30 seconds

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Monitoring loop error: {e}")
                    await asyncio.sleep(30)

        asyncio.create_task(monitoring_loop())
        logger.info("Monitoring loop started")

    async def _collect_metrics(self) -> None:
        """Collect metrics from all monitors"""
        import random

        # Simulate metric collection
        for monitor in self.monitors.values():
            if not monitor.enabled:
                continue

            # Simulate random values
            if "cpu" in monitor.target:
                value = random.uniform(20.0, 95.0)  # nosec B311
            elif "memory" in monitor.target:
                value = random.uniform(40.0, 90.0)  # nosec B311
            elif "disk" in monitor.target:
                value = random.uniform(30.0, 95.0)  # nosec B311
            elif "latency" in monitor.target:
                value = random.uniform(50.0, 800.0)  # nosec B311
            elif "error_rate" in monitor.target:
                value = random.uniform(0.0, 10.0)  # nosec B311
            elif "health" in monitor.target:
                value = 1.0 if random.random() > 0.1 else 0.0  # nosec B311
            else:
                value = random.uniform(0.0, 100.0)  # nosec B311

            await self.record_metric(monitor.target, value)

    def get_metrics(
        self,
        metric_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get metric data

        Args:
            metric_id: Metric ID
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of records

        Returns:
            Metric data
        """
        if metric_id not in self.metrics:
            return []

        data = self.metrics[metric_id]

        if start_time:
            data = [d for d in data if d.timestamp >= start_time]
        if end_time:
            data = [d for d in data if d.timestamp <= end_time]

        data = data[-limit:]

        return [
            {
                "metric_id": d.metric_id,
                "value": d.value,
                "timestamp": d.timestamp.isoformat(),
                "labels": d.labels,
            }
            for d in data
        ]

    def get_alerts(
        self, status: Optional[str] = None, severity: Optional[AlertSeverity] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alert instances

        Args:
            status: Filter by status
            severity: Filter by severity

        Returns:
            Alert instances
        """
        alerts = self.alert_instances

        if status:
            alerts = [a for a in alerts if a.status == status]

        if severity:
            alerts = [a for a in alerts if self.alerts[a.alert_id].severity == severity]

        return [
            {
                "alert_instance_id": a.alert_instance_id,
                "alert_id": a.alert_id,
                "alert_name": self.alerts[a.alert_id].alert_name,
                "severity": self.alerts[a.alert_id].severity.value,
                "triggered_at": a.triggered_at.isoformat(),
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "status": a.status,
                "value": a.value,
                "message": a.message,
            }
            for a in alerts
        ]

    async def resolve_alert(self, alert_instance_id: str) -> bool:
        """
        Resolve alert instance

        Args:
            alert_instance_id: Alert instance ID

        Returns:
            Success status
        """
        for alert_instance in self.alert_instances:
            if (
                alert_instance.alert_instance_id == alert_instance_id
                and alert_instance.status == "active"
            ):
                alert_instance.status = "resolved"
                alert_instance.resolved_at = datetime.now(timezone.utc)
                self.active_alerts -= 1

                logger.info(f"Resolved alert: {alert_instance_id}")
                return True

        return False

    def register_notification_handler(self, handler: Callable) -> None:
        """
        Register notification handler

        Args:
            handler: Handler function
        """
        self.notification_handlers.append(handler)
        logger.info("Registered alert notification handler")

    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        return {
            "total_monitors": len(self.monitors),
            "enabled_monitors": len([m for m in self.monitors.values() if m.enabled]),
            "total_alerts": len(self.alerts),
            "enabled_alerts": len([a for a in self.alerts.values() if a.enabled]),
            "total_metrics": self.total_metrics,
            "total_alert_instances": self.total_alerts,
            "active_alerts": self.active_alerts,
        }


def get_integration_monitoring_system(
    config: Optional[Dict[str, Any]] = None,
) -> IntegrationMonitoringSystem:
    """
    Factory function to get integration monitoring system instance

    Args:
        config: Optional configuration dictionary

    Returns:
        IntegrationMonitoringSystem: System instance
    """
    return IntegrationMonitoringSystem(config)
