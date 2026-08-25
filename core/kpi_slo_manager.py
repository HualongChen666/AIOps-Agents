# -*- coding: utf-8 -*-
"""
core/kpi_slo_manager.py
=======================

KPI and SLO Management System

This module provides comprehensive Key Performance Indicator (KPI) and
Service Level Objective (SLO) management capabilities including:
- KPI definition and management
- SLO calculation and tracking
- SLA compliance checking
- Alert threshold management
- Historical data tracking
- Trend analysis
- Report generation
"""

from __future__ import annotations

import datetime
import json
import logging
import math
import statistics
import threading
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AggregationMethod(Enum):
    """SLO aggregation methods."""

    GOOD_RATIO = "good_ratio"
    UPTIME = "uptime"
    P99_LT = "p99_lt"
    MEAN_LT = "mean_lt"
    P95_LT = "p95_lt"
    P50_LT = "p50_lt"


class ComplianceStatus(Enum):
    """SLA compliance status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    UNKNOWN = "unknown"


@dataclass
class KPITarget:
    """KPI target configuration."""

    target: float
    warning: float
    critical: float
    unit: str


@dataclass
class KPIDefinition:
    """KPI definition."""

    name: str
    description: str
    enabled: bool
    unit: str
    targets: Dict[str, KPITarget] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLODefinition:
    """SLO definition."""

    name: str
    description: str
    enabled: bool
    target: float
    window: str
    alert_threshold: float
    metric: str
    aggregation: str
    service: str = "default"


@dataclass
class KPIDataPoint:
    """KPI data point with timestamp."""

    timestamp: datetime.datetime
    value: float
    metric: str
    service: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLOEvaluationResult:
    """SLO evaluation result."""

    slo_id: str
    slo_name: str
    current: float
    target: float
    error_budget_remaining_percent: float
    burn_rate: float
    status: str
    alert: bool
    window: str
    timestamp: datetime.datetime


@dataclass
class SLAComplianceReport:
    """SLA compliance report."""

    report_id: str
    period: str
    generated_at: datetime.datetime
    slo_results: List[SLOEvaluationResult]
    overall_compliance: ComplianceStatus
    total_slos: int
    compliant_slos: int
    non_compliant_slos: int
    warning_slos: int


@dataclass
class TrendAnalysis:
    """Trend analysis result."""

    metric: str
    service: str
    period: str
    trend: str  # "increasing", "decreasing", "stable"
    slope: float
    r_squared: float
    forecast: List[Tuple[datetime.datetime, float]]
    confidence_interval: float


@dataclass
class Alert:
    """Alert definition."""

    alert_id: str
    severity: SeverityLevel
    kpi_slo_id: str
    message: str
    timestamp: datetime.datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class KPISLOManager:
    """
    KPI and SLO Management System

    Manages KPI definitions, SLO calculations, SLA compliance checking,
    alert threshold management, historical data tracking, trend analysis,
    and report generation.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the KPI/SLO manager.

        Args:
            config_path: Path to the KPI/SLO configuration file.
                        Defaults to config/kpi_slo_config.yaml
        """
        if config_path is None:
            config_path = "config/kpi_slo_config.yaml"

        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.kpis: Dict[str, KPIDefinition] = {}
        self.slos: Dict[str, SLODefinition] = {}
        self.historical_data: Dict[str, deque] = {}
        self.alerts: List[Alert] = []
        self.reports: List[SLAComplianceReport] = []

        self._lock = threading.Lock()
        self._max_history_points = 10000

        self._load_config()
        self._initialize_kpis()
        self._initialize_slos()

    def _load_config(self) -> None:
        """Load KPI/SLO configuration from YAML file."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded KPI/SLO configuration from {self.config_path}")
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {self.config_path}, using defaults")
            self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}, using defaults")
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "kpi": {},
            "slo": {},
            "alerts": {"enabled": True},
            "error_budget": {"enabled": True},
            "reporting": {"enabled": True},
            "historical_tracking": {"enabled": True},
            "predictive_analysis": {"enabled": True},
        }

    def _initialize_kpis(self) -> None:
        """Initialize KPI definitions from configuration."""
        kpi_config = self.config.get("kpi", {})
        for kpi_key, kpi_data in kpi_config.items():
            if not isinstance(kpi_data, dict) or not kpi_data.get("enabled", True):
                continue

            targets = {}
            if "percentiles" in kpi_data:
                if not isinstance(kpi_data["percentiles"], dict):
                    logger.warning(f"Invalid percentiles structure in KPI {kpi_key}")
                    continue
                for percentile, values in kpi_data["percentiles"].items():
                    targets[percentile] = KPITarget(
                        target=values.get("target", 0.0),
                        warning=values.get("warning", 0.0),
                        critical=values.get("critical", 0.0),
                        unit=kpi_data.get("unit", ""),
                    )

            self.kpis[kpi_key] = KPIDefinition(
                name=kpi_data.get("name", kpi_key),
                description=kpi_data.get("description", ""),
                enabled=kpi_data.get("enabled", True),
                unit=kpi_data.get("unit", ""),
                targets=targets,
                metadata=kpi_data,
            )

        logger.info(f"Initialized {len(self.kpis)} KPI definitions")

    def _initialize_slos(self) -> None:
        """Initialize SLO definitions from configuration."""
        slo_config = self.config.get("slo", {})
        slo_counter = 0

        for slo_category, slo_data in slo_config.items():
            if not isinstance(slo_data, dict) or not slo_data.get("enabled", True):
                continue

            targets = slo_data.get("targets", {})
            if not isinstance(targets, dict):
                logger.warning(f"Invalid targets structure in SLO category {slo_category}")
                continue

            for target_key, target_values in targets.items():
                if not isinstance(target_values, dict):
                    continue

                slo_id = f"SLO-{slo_counter:03d}"
                self.slos[slo_id] = SLODefinition(
                    name=f"{slo_data.get('name', slo_category)} - {target_key}",
                    description=slo_data.get("description", ""),
                    enabled=target_values.get("enabled", True),
                    target=target_values.get("target", 0.0),
                    window=target_values.get("window", "24h"),
                    alert_threshold=target_values.get("alert_threshold", 0.0),
                    metric=target_values.get("metric", ""),
                    aggregation=target_values.get("aggregation", "good_ratio"),
                    service=target_values.get("service", "default"),
                )
                slo_counter += 1

        logger.info(f"Initialized {len(self.slos)} SLO definitions")

    # KPI Management Methods

    def get_kpi(self, kpi_id: str) -> Optional[KPIDefinition]:
        """Get KPI definition by ID."""
        return self.kpis.get(kpi_id)

    def list_kpis(self) -> Dict[str, KPIDefinition]:
        """List all KPI definitions."""
        return self.kpis.copy()

    def add_kpi(self, kpi_id: str, kpi: KPIDefinition) -> bool:
        """Add a new KPI definition."""
        with self._lock:
            if kpi_id in self.kpis:
                logger.warning(f"KPI {kpi_id} already exists")
                return False
            self.kpis[kpi_id] = kpi
            logger.info(f"Added KPI {kpi_id}")
            return True

    def update_kpi(self, kpi_id: str, **kwargs) -> bool:
        """Update an existing KPI definition."""
        with self._lock:
            if kpi_id not in self.kpis:
                logger.warning(f"KPI {kpi_id} not found")
                return False

            kpi = self.kpis[kpi_id]
            for key, value in kwargs.items():
                if hasattr(kpi, key):
                    setattr(kpi, key, value)

            logger.info(f"Updated KPI {kpi_id}")
            return True

    def delete_kpi(self, kpi_id: str) -> bool:
        """Delete a KPI definition."""
        with self._lock:
            if kpi_id not in self.kpis:
                logger.warning(f"KPI {kpi_id} not found")
                return False

            del self.kpis[kpi_id]
            logger.info(f"Deleted KPI {kpi_id}")
            return True

    def record_kpi_value(
        self,
        metric: str,
        value: float,
        service: str = "default",
        timestamp: Optional[datetime.datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a KPI data point.

        Args:
            metric: Metric name
            value: Metric value
            service: Service name
            timestamp: Timestamp (defaults to now)
            metadata: Additional metadata
        """
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()

        data_point = KPIDataPoint(
            timestamp=timestamp,
            value=value,
            metric=metric,
            service=service,
            metadata=metadata or {},
        )

        key = f"{metric}:{service}"
        with self._lock:
            if key not in self.historical_data:
                self.historical_data[key] = deque(maxlen=self._max_history_points)

            self.historical_data[key].append(data_point)

    def get_kpi_history(
        self,
        metric: str,
        service: str = "default",
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
    ) -> List[KPIDataPoint]:
        """
        Get historical KPI data.

        Args:
            metric: Metric name
            service: Service name
            start: Start timestamp (optional)
            end: End timestamp (optional)

        Returns:
            List of KPI data points
        """
        key = f"{metric}:{service}"
        if key not in self.historical_data:
            return []

        with self._lock:
            data = list(self.historical_data[key])

        if start is not None:
            data = [d for d in data if d.timestamp >= start]
        if end is not None:
            data = [d for d in data if d.timestamp <= end]

        return data

    def get_latest(self, metric: str, service: str = "default") -> Optional[float]:
        """
        Get the latest value for a metric.

        Args:
            metric: Metric name
            service: Service name

        Returns:
            Latest value or None if not found
        """
        history = self.get_kpi_history(metric, service)
        if not history:
            return None
        return history[-1].value

    def calculate_kpi(
        self, kpi_id: str, service: str = "default", percentile: Optional[str] = None
    ) -> Optional[float]:
        """
        Calculate current KPI value.

        Args:
            kpi_id: KPI identifier
            service: Service name
            percentile: Percentile to calculate (p50, p95, p99)

        Returns:
            Calculated KPI value or None
        """
        kpi = self.get_kpi(kpi_id)
        if kpi is None:
            logger.warning(f"KPI {kpi_id} not found")
            return None

        history = self.get_kpi_history(kpi_id, service)
        if not history:
            return None

        values = [d.value for d in history]

        if percentile == "p50":
            return self._percentile(values, 0.50)
        elif percentile == "p95":
            return self._percentile(values, 0.95)
        elif percentile == "p99":
            return self._percentile(values, 0.99)
        else:
            return statistics.mean(values) if values else None

    def _percentile(self, values: List[float], q: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        index = max(0, min(n - 1, math.ceil((n - 1) * q)))
        return sorted_values[index]

    # SLO Management Methods

    def get_slo(self, slo_id: str) -> Optional[SLODefinition]:
        """Get SLO definition by ID."""
        return self.slos.get(slo_id)

    def list_slos(self) -> Dict[str, SLODefinition]:
        """List all SLO definitions."""
        return self.slos.copy()

    def add_slo(self, slo_id: str, slo: SLODefinition) -> bool:
        """Add a new SLO definition."""
        with self._lock:
            if slo_id in self.slos:
                logger.warning(f"SLO {slo_id} already exists")
                return False

            # Clamp values to valid ranges
            slo.target = max(0.0, min(1.0, float(slo.target)))
            slo.alert_threshold = max(0.0, min(1.0, float(slo.alert_threshold)))

            # Handle window - if it's a string, parse it first
            if isinstance(slo.window, str):
                slo.window = self._parse_window(slo.window)
            else:
                slo.window = max(1, int(slo.window))

            self.slos[slo_id] = slo
            logger.info(f"Added SLO {slo_id}")
            return True

    def update_slo(self, slo_id: str, **kwargs) -> bool:
        """Update an existing SLO definition."""
        with self._lock:
            if slo_id not in self.slos:
                logger.warning(f"SLO {slo_id} not found")
                return False

            slo = self.slos[slo_id]
            for key, value in kwargs.items():
                if hasattr(slo, key):
                    # Special handling for window to parse string values
                    if key == "window" and isinstance(value, str):
                        value = self._parse_window(value)
                    setattr(slo, key, value)

            logger.info(f"Updated SLO {slo_id}")
            return True

    def delete_slo(self, slo_id: str) -> bool:
        """Delete an SLO definition."""
        with self._lock:
            if slo_id not in self.slos:
                logger.warning(f"SLO {slo_id} not found")
                return False

            del self.slos[slo_id]
            logger.info(f"Deleted SLO {slo_id}")
            return True

    def evaluate_slo(self, slo_id: str) -> Optional[SLOEvaluationResult]:
        """
        Evaluate an SLO against current metrics.

        Args:
            slo_id: SLO identifier

        Returns:
            SLO evaluation result or None
        """
        slo = self.get_slo(slo_id)
        if slo is None:
            logger.warning(f"SLO {slo_id} not found")
            return None

        # Get historical data for the SLO window
        window_hours = self._parse_window(slo.window)
        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(hours=window_hours)

        history = self.get_kpi_history(slo.metric, slo.service, start_time, end_time)

        if not history:
            # No data available, assume healthy
            return SLOEvaluationResult(
                slo_id=slo_id,
                slo_name=slo.name,
                current=1.0,
                target=slo.target,
                error_budget_remaining_percent=100.0,
                burn_rate=0.0,
                status="healthy",
                alert=False,
                window=slo.window,
                timestamp=datetime.datetime.utcnow(),
            )

        # Calculate current value based on aggregation method
        current = self._calculate_aggregation(history, slo)

        # Calculate error budget
        error_budget_remaining = self._calculate_error_budget(current, slo.target)
        burn_rate = self._calculate_burn_rate(current, slo.target)

        # Determine status
        if current >= slo.target:
            status = "healthy"
            alert = False
        elif current >= slo.alert_threshold:
            status = "warning"
            alert = False
        else:
            status = "critical"
            alert = True

        return SLOEvaluationResult(
            slo_id=slo_id,
            slo_name=slo.name,
            current=current,
            target=slo.target,
            error_budget_remaining_percent=error_budget_remaining,
            burn_rate=burn_rate,
            status=status,
            alert=alert,
            window=slo.window,
            timestamp=datetime.datetime.utcnow(),
        )

    def _parse_window(self, window) -> int:
        """Parse window string or integer to hours."""
        # If already an integer, return it
        if isinstance(window, int):
            return max(1, window)

        # If it's a string, parse it
        if isinstance(window, str):
            window = window.lower()
            if window.endswith("h"):
                try:
                    return max(1, int(window[:-1]))
                except ValueError:
                    return 24
            elif window.endswith("d"):
                try:
                    return max(1, int(window[:-1]) * 24)
                except ValueError:
                    return 24
            elif window.endswith("w"):
                try:
                    return max(1, int(window[:-1]) * 24 * 7)
                except ValueError:
                    return 24
            elif window.endswith("m"):
                try:
                    return max(1, int(window[:-1]) * 24 * 30)
                except ValueError:
                    return 24
            else:
                try:
                    return max(1, int(window))
                except ValueError:
                    return 24  # Default to 24 hours

        # Default fallback
        return 24

    def _calculate_aggregation(self, history: List[KPIDataPoint], slo: SLODefinition) -> float:
        """Calculate aggregated value based on SLO aggregation method."""
        values = [d.value for d in history]

        if not values:
            return 1.0

        aggregation = slo.aggregation.lower()

        if aggregation == "good_ratio":
            # Count values that meet the target
            good_count = sum(1 for v in values if v >= slo.target)
            return good_count / len(values)
        elif aggregation == "uptime":
            # Calculate uptime ratio based on timestamps
            if len(history) < 2:
                return 1.0
            total_duration = (history[-1].timestamp - history[0].timestamp).total_seconds()
            if total_duration <= 0:
                return 1.0
            good_duration = 0.0
            for i in range(len(history) - 1):
                duration = (history[i + 1].timestamp - history[i].timestamp).total_seconds()
                if history[i].value >= slo.target:
                    good_duration += duration
            return good_duration / total_duration
        elif aggregation == "p99_lt":
            p99 = self._percentile(values, 0.99)
            return 1.0 if p99 <= slo.target else 0.0
        elif aggregation == "p95_lt":
            p95 = self._percentile(values, 0.95)
            return 1.0 if p95 <= slo.target else 0.0
        elif aggregation == "p50_lt":
            p50 = self._percentile(values, 0.50)
            return 1.0 if p50 <= slo.target else 0.0
        elif aggregation == "mean_lt":
            mean = statistics.mean(values)
            return 1.0 if mean <= slo.target else 0.0
        else:
            # Default to good_ratio
            good_count = sum(1 for v in values if v >= slo.target)
            return good_count / len(values)

    def _calculate_error_budget(self, current: float, target: float) -> float:
        """Calculate remaining error budget percentage."""
        if target >= 1.0:
            return 100.0 if current >= 1.0 else 0.0

        bad_ratio = 1.0 - current
        allowed_bad = 1.0 - target
        if allowed_bad <= 0:
            return 0.0

        consumed_percent = (bad_ratio / allowed_bad) * 100.0
        return max(0.0, 100.0 - consumed_percent)

    def _calculate_burn_rate(self, current: float, target: float) -> float:
        """Calculate error budget burn rate."""
        if target >= 1.0:
            return 0.0 if current >= 1.0 else 100.0

        bad_ratio = 1.0 - current
        allowed_bad = 1.0 - target
        if allowed_bad <= 0:
            return 100.0

        return bad_ratio / allowed_bad

    def evaluate_all_slos(self) -> List[SLOEvaluationResult]:
        """Evaluate all SLOs."""
        results = []
        for slo_id in self.slos:
            result = self.evaluate_slo(slo_id)
            if result:
                results.append(result)
        return results

    # SLA Compliance Checking

    def check_sla_compliance(self, period: str = "30d") -> SLAComplianceReport:
        """
        Check SLA compliance for all SLOs over a period.

        Args:
            period: Time period (e.g., "30d", "7d", "24h")

        Returns:
            SLA compliance report
        """
        results = self.evaluate_all_slos()

        compliant_count = sum(1 for r in results if r.status == "healthy")
        non_compliant_count = sum(1 for r in results if r.status == "critical")
        warning_count = sum(1 for r in results if r.status == "warning")

        # Determine overall compliance
        if non_compliant_count > 0:
            overall_compliance = ComplianceStatus.NON_COMPLIANT
        elif warning_count > 0:
            overall_compliance = ComplianceStatus.WARNING
        else:
            overall_compliance = ComplianceStatus.COMPLIANT

        report_id = f"SLA-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        report = SLAComplianceReport(
            report_id=report_id,
            period=period,
            generated_at=datetime.datetime.utcnow(),
            slo_results=results,
            overall_compliance=overall_compliance,
            total_slos=len(results),
            compliant_slos=compliant_count,
            non_compliant_slos=non_compliant_count,
            warning_slos=warning_count,
        )

        with self._lock:
            self.reports.append(report)

        return report

    # Alert Threshold Management

    def check_alert_thresholds(self) -> List[Alert]:
        """
        Check all KPIs and SLOs against alert thresholds.

        Returns:
            List of generated alerts
        """
        alerts = []
        alert_config = self.config.get("alerts", {})

        if not alert_config.get("enabled", True):
            return alerts

        # Check KPI thresholds
        for kpi_id, kpi in self.kpis.items():
            if not kpi.enabled:
                continue

            for target_name, target in kpi.targets.items():
                current = self.calculate_kpi(kpi_id, percentile=target_name)
                if current is None:
                    continue

                if current >= target.critical:
                    severity = SeverityLevel.CRITICAL
                    message = f"KPI {kpi.name} ({target_name}) critical: {current}{target.unit} >= {target.critical}{target.unit}"
                elif current >= target.warning:
                    severity = SeverityLevel.WARNING
                    message = f"KPI {kpi.name} ({target_name}) warning: {current}{target.unit} >= {target.warning}{target.unit}"
                else:
                    continue

                alert = Alert(
                    alert_id=f"ALERT-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}",
                    severity=severity,
                    kpi_slo_id=kpi_id,
                    message=message,
                    timestamp=datetime.datetime.utcnow(),
                )
                alerts.append(alert)

        # Check SLO thresholds
        slo_results = self.evaluate_all_slos()
        for result in slo_results:
            if result.alert:
                severity = SeverityLevel.CRITICAL
                message = f"SLO {result.slo_name} critical: current={result.current:.2%}, target={result.target:.2%}"
            elif result.status == "warning":
                severity = SeverityLevel.WARNING
                message = f"SLO {result.slo_name} warning: current={result.current:.2%}, target={result.target:.2%}"
            else:
                continue

            alert = Alert(
                alert_id=f"ALERT-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}",
                severity=severity,
                kpi_slo_id=result.slo_id,
                message=message,
                timestamp=datetime.datetime.utcnow(),
            )
            alerts.append(alert)

        with self._lock:
            self.alerts.extend(alerts)

        return alerts

    def get_alerts(
        self, severity: Optional[SeverityLevel] = None, since: Optional[datetime.datetime] = None
    ) -> List[Alert]:
        """
        Get alerts, optionally filtered by severity and time.

        Args:
            severity: Filter by severity level
            since: Filter by timestamp

        Returns:
            List of alerts
        """
        with self._lock:
            alerts = self.alerts.copy()

        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]

        if since is not None:
            alerts = [a for a in alerts if a.timestamp >= since]

        return alerts

    def clear_alerts(self, before: Optional[datetime.datetime] = None) -> int:
        """
        Clear alerts, optionally those before a timestamp.

        Args:
            before: Clear alerts before this timestamp

        Returns:
            Number of alerts cleared
        """
        with self._lock:
            if before is None:
                count = len(self.alerts)
                self.alerts.clear()
            else:
                old_count = len(self.alerts)
                self.alerts = [a for a in self.alerts if a.timestamp >= before]
                count = old_count - len(self.alerts)

        logger.info(f"Cleared {count} alerts")
        return count

    # Trend Analysis

    def analyze_trend(
        self, metric: str, service: str = "default", period: str = "7d"
    ) -> Optional[TrendAnalysis]:
        """
        Analyze trend for a metric over a period.

        Args:
            metric: Metric name
            service: Service name
            period: Time period

        Returns:
            Trend analysis result or None
        """
        window_hours = self._parse_window(period)
        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(hours=window_hours)

        history = self.get_kpi_history(metric, service, start_time, end_time)

        if len(history) < 2:
            logger.warning(f"Insufficient data for trend analysis: {len(history)} points")
            return None

        # Extract values and timestamps
        values = [d.value for d in history]
        timestamps = [(d.timestamp - start_time).total_seconds() / 3600.0 for d in history]

        # Simple linear regression
        n = len(values)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values))
        sum_x2 = sum(x * x for x in timestamps)
        sum_y2 = sum(y * y for y in values)  # noqa: F841 - Reserved for correlation calculation

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            slope = 0.0
            r_squared = 0.0
            intercept = sum_y / n if n > 0 else 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n

            # Calculate R-squared
            y_mean = sum_y / n
            ss_tot = sum((y - y_mean) ** 2 for y in values)
            ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(timestamps, values))
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Determine trend direction
        if abs(slope) < 0.01:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        # Generate forecast
        forecast_horizon = 7 * 24  # 7 days in hours  # noqa: F841 - Reserved for future use
        forecast = []
        for hours in range(1, 8):
            future_time = end_time + datetime.timedelta(hours=hours * 24)
            future_x = window_hours + hours * 24
            future_value = slope * future_x + intercept
            forecast.append((future_time, future_value))

        predictive_config = self.config.get("predictive_analysis", {})
        confidence_interval = predictive_config.get("confidence_interval", 0.95)

        return TrendAnalysis(
            metric=metric,
            service=service,
            period=period,
            trend=trend,
            slope=slope,
            r_squared=r_squared,
            forecast=forecast,
            confidence_interval=confidence_interval,
        )

    # Report Generation

    def generate_report(self, period: str = "30d", format: str = "json") -> Dict[str, Any]:
        """
        Generate a comprehensive KPI/SLO report.

        Args:
            period: Time period for the report
            format: Report format (json, html, pdf)

        Returns:
            Report data as dictionary
        """
        sla_report = self.check_sla_compliance(period)
        slo_results = sla_report.slo_results

        # KPI summary
        kpi_summary = {}
        for kpi_id, kpi in self.kpis.items():
            if not kpi.enabled:
                continue

            kpi_summary[kpi_id] = {
                "name": kpi.name,
                "description": kpi.description,
                "unit": kpi.unit,
                "current_values": {},
            }

            for target_name in kpi.targets:
                current = self.calculate_kpi(kpi_id, percentile=target_name)
                if current is not None:
                    kpi_summary[kpi_id]["current_values"][target_name] = current

        # Trend analysis
        trends = []
        for kpi_id in self.kpis:
            if not self.kpis[kpi_id].enabled:
                continue
            trend = self.analyze_trend(kpi_id, period=period)
            if trend:
                trends.append(
                    {
                        "metric": trend.metric,
                        "service": trend.service,
                        "trend": trend.trend,
                        "slope": trend.slope,
                        "r_squared": trend.r_squared,
                    }
                )

        # Error budget summary
        error_budget_summary = {
            "total_slos": len(slo_results),
            "healthy_slos": sum(1 for r in slo_results if r.status == "healthy"),
            "warning_slos": sum(1 for r in slo_results if r.status == "warning"),
            "critical_slos": sum(1 for r in slo_results if r.status == "critical"),
            "average_error_budget": (
                statistics.mean([r.error_budget_remaining_percent for r in slo_results])
                if slo_results
                else 100.0
            ),
        }

        # Recent alerts
        recent_alerts = self.get_alerts(
            since=datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        )

        report = {
            "report_id": sla_report.report_id,
            "period": period,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "executive_summary": {
                "overall_compliance": sla_report.overall_compliance.value,
                "total_slos": sla_report.total_slos,
                "compliant_slos": sla_report.compliant_slos,
                "non_compliant_slos": sla_report.non_compliant_slos,
                "warning_slos": sla_report.warning_slos,
            },
            "kpi_summary": kpi_summary,
            "slo_results": [
                {
                    "slo_id": r.slo_id,
                    "slo_name": r.slo_name,
                    "current": r.current,
                    "target": r.target,
                    "error_budget_remaining_percent": r.error_budget_remaining_percent,
                    "burn_rate": r.burn_rate,
                    "status": r.status,
                    "window": r.window,
                }
                for r in slo_results
            ],
            "error_budget_summary": error_budget_summary,
            "trends": trends,
            "recent_alerts": [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity.value,
                    "kpi_slo_id": a.kpi_slo_id,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in recent_alerts
            ],
            "recommendations": self._generate_recommendations(slo_results, trends),
        }

        return report

    def _generate_recommendations(
        self, slo_results: List[SLOEvaluationResult], trends: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on SLO results and trends."""
        recommendations = []

        # Check for critical SLOs
        critical_slos = [r for r in slo_results if r.status == "critical"]
        if critical_slos:
            recommendations.append(
                f"Immediate action required: {len(critical_slos)} SLO(s) in critical state"
            )

        # Check for warning SLOs
        warning_slos = [r for r in slo_results if r.status == "warning"]
        if warning_slos:
            recommendations.append(f"Attention needed: {len(warning_slos)} SLO(s) in warning state")

        # Check for high burn rates
        high_burn_rate = [r for r in slo_results if r.burn_rate > 2.0]
        if high_burn_rate:
            recommendations.append(
                f"High error budget burn rate detected for {len(high_burn_rate)} SLO(s)"
            )

        # Check for concerning trends
        increasing_trends = [t for t in trends if t.get("trend") == "increasing"]
        if increasing_trends:
            recommendations.append(
                f"Increasing trends detected for {len(increasing_trends)} metric(s)"
            )

        if not recommendations:
            recommendations.append("All systems operating within normal parameters")

        return recommendations

    def save_report(self, report: Dict[str, Any], filepath: str) -> bool:
        """
        Save report to file.

        Args:
            report: Report data
            filepath: Output file path

        Returns:
            True if successful
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)

            # Set restrictive permissions for report file (644 - owner read/write, group/others read)
            try:
                import os
                import stat

                os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            except (OSError, AttributeError):
                # chmod may fail on Windows or non-Unix systems
                pass

            logger.info(f"Saved report to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            return False

    # Error Budget Tracking

    def get_error_budget_status(self, slo_id: str) -> Optional[Dict[str, Any]]:
        """
        Get error budget status for an SLO.

        Args:
            slo_id: SLO identifier

        Returns:
            Error budget status or None
        """
        result = self.evaluate_slo(slo_id)
        if result is None:
            return None

        error_budget_config = self.config.get("error_budget", {})

        return {
            "slo_id": slo_id,
            "slo_name": result.slo_name,
            "error_budget_remaining_percent": result.error_budget_remaining_percent,
            "burn_rate": result.burn_rate,
            "status": result.status,
            "time_to_exhaustion": self._calculate_time_to_exhaustion(result),
            "burn_rate_status": self._evaluate_burn_rate_status(
                result.burn_rate, error_budget_config
            ),
        }

    def _calculate_time_to_exhaustion(self, result: SLOEvaluationResult) -> Optional[str]:
        """Calculate estimated time until error budget exhaustion."""
        if result.burn_rate <= 0:
            return "Never"

        window_hours = self._parse_window(result.window)
        remaining_fraction = result.error_budget_remaining_percent / 100.0

        if remaining_fraction <= 0:
            return "Exhausted"

        hours_remaining = (remaining_fraction / result.burn_rate) * window_hours

        if hours_remaining < 1:
            return f"{int(hours_remaining * 60)} minutes"
        elif hours_remaining < 24:
            return f"{int(hours_remaining)} hours"
        elif hours_remaining < 24 * 7:
            return f"{int(hours_remaining / 24)} days"
        else:
            return f"{int(hours_remaining / (24 * 7))} weeks"

    def _evaluate_burn_rate_status(self, burn_rate: float, config: Dict[str, Any]) -> str:
        """Evaluate burn rate status against thresholds."""
        warning_threshold = config.get("burn_rate_thresholds", {}).get("warning", 2.0)
        critical_threshold = config.get("burn_rate_thresholds", {}).get("critical", 10.0)

        if burn_rate >= critical_threshold:
            return "critical"
        elif burn_rate >= warning_threshold:
            return "warning"
        else:
            return "normal"

    # Real-time Monitoring

    def start_realtime_monitoring(self, interval_seconds: int = 60) -> None:
        """
        Start real-time monitoring (placeholder for future implementation).

        Args:
            interval_seconds: Monitoring interval
        """
        logger.info(f"Real-time monitoring would start with {interval_seconds}s interval")
        # This would be implemented with a background thread or async task
        # For now, it's a placeholder

    def stop_realtime_monitoring(self) -> None:
        """Stop real-time monitoring (placeholder)."""
        logger.info("Real-time monitoring would stop")
        # This would be implemented with a background thread or async task
        # For now, it's a placeholder

    @property
    def size(self) -> int:
        """Get the total number of historical data points across all metrics."""
        with self._lock:
            total = sum(len(data) for data in self.historical_data.values())
        return total

    @property
    def sample_count(self) -> int:
        """Get the total number of sample points."""
        return self.size

    def __repr__(self) -> str:
        """String representation of the manager."""
        return f"KPISLOManager(kpis={len(self.kpis)}, slos={len(self.slos)}, history_points={self.size})"


# Global instance
kpi_slo_manager = KPISLOManager()
