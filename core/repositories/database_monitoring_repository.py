# -*- coding: utf-8 -*-
"""
database_monitoring_repository.py
----------------------------------
Database Monitoring Data Repository

Provides database access layer for database monitoring configurations,
thresholds, baselines, alert rules, and status tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    DatabaseMetricThresholdDB,
    DatabaseMonitoringConfigDB,
    DatabasePerformanceBaselineDB,
    DatabaseAlertRuleDB,
    DatabaseMonitoringStatusDB,
)

logger = logging.getLogger(__name__)


class DatabaseMonitoringRepository:
    """Repository for database monitoring data access"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================================
    # Monitoring Config Operations
    # ============================================================================

    async def get_config(self) -> Optional[DatabaseMonitoringConfigDB]:
        """Get the current monitoring configuration"""
        result = await self.db.execute(
            select(DatabaseMonitoringConfigDB).order_by(DatabaseMonitoringConfigDB.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def create_config(
        self,
        enabled: bool,
        collection_interval: int,
        retention_days: int,
        enable_realtime: bool,
        enable_slow_query_log: bool,
        slow_query_threshold: float,
        enable_connection_monitoring: bool,
        max_connections_threshold: int,
        enable_deadlock_detection: bool,
        updated_by: Optional[str] = None,
    ) -> DatabaseMonitoringConfigDB:
        """Create a new monitoring configuration"""
        config = DatabaseMonitoringConfigDB(
            enabled=enabled,
            collection_interval=collection_interval,
            retention_days=retention_days,
            enable_realtime=enable_realtime,
            enable_slow_query_log=enable_slow_query_log,
            slow_query_threshold=slow_query_threshold,
            enable_connection_monitoring=enable_connection_monitoring,
            max_connections_threshold=max_connections_threshold,
            enable_deadlock_detection=enable_deadlock_detection,
            updated_by=updated_by,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        logger.info(f"Created database monitoring config: id={config.id}")
        return config

    async def update_config(
        self,
        config_id: int,
        enabled: Optional[bool] = None,
        collection_interval: Optional[int] = None,
        retention_days: Optional[int] = None,
        enable_realtime: Optional[bool] = None,
        enable_slow_query_log: Optional[bool] = None,
        slow_query_threshold: Optional[float] = None,
        enable_connection_monitoring: Optional[bool] = None,
        max_connections_threshold: Optional[int] = None,
        enable_deadlock_detection: Optional[bool] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[DatabaseMonitoringConfigDB]:
        """Update monitoring configuration"""
        update_data: Dict[str, Any] = {}
        if enabled is not None:
            update_data["enabled"] = enabled
        if collection_interval is not None:
            update_data["collection_interval"] = collection_interval
        if retention_days is not None:
            update_data["retention_days"] = retention_days
        if enable_realtime is not None:
            update_data["enable_realtime"] = enable_realtime
        if enable_slow_query_log is not None:
            update_data["enable_slow_query_log"] = enable_slow_query_log
        if slow_query_threshold is not None:
            update_data["slow_query_threshold"] = slow_query_threshold
        if enable_connection_monitoring is not None:
            update_data["enable_connection_monitoring"] = enable_connection_monitoring
        if max_connections_threshold is not None:
            update_data["max_connections_threshold"] = max_connections_threshold
        if enable_deadlock_detection is not None:
            update_data["enable_deadlock_detection"] = enable_deadlock_detection
        if updated_by is not None:
            update_data["updated_by"] = updated_by

        if not update_data:
            return None

        result = await self.db.execute(
            update(DatabaseMonitoringConfigDB)
            .where(DatabaseMonitoringConfigDB.id == config_id)
            .values(**update_data)
            .returning(DatabaseMonitoringConfigDB)
        )
        await self.db.commit()
        return result.scalar_one_or_none()

    # ============================================================================
    # Metric Threshold Operations
    # ============================================================================

    async def get_all_thresholds(self) -> List[DatabaseMetricThresholdDB]:
        """Get all metric thresholds"""
        result = await self.db.execute(select(DatabaseMetricThresholdDB))
        return result.scalars().all()

    async def get_threshold_by_metric_type(self, metric_type: str) -> Optional[DatabaseMetricThresholdDB]:
        """Get threshold by metric type"""
        result = await self.db.execute(
            select(DatabaseMetricThresholdDB).where(DatabaseMetricThresholdDB.metric_type == metric_type)
        )
        return result.scalar_one_or_none()

    async def create_threshold(
        self,
        metric_type: str,
        warning_threshold: float,
        critical_threshold: float,
        enabled: bool = True,
        description: str = "",
        created_by: Optional[str] = None,
    ) -> DatabaseMetricThresholdDB:
        """Create a new metric threshold"""
        threshold = DatabaseMetricThresholdDB(
            metric_type=metric_type,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            enabled=enabled,
            description=description,
            created_by=created_by,
        )
        self.db.add(threshold)
        await self.db.commit()
        await self.db.refresh(threshold)
        logger.info(f"Created metric threshold: metric_type={metric_type}, id={threshold.id}")
        return threshold

    async def update_threshold(
        self,
        threshold_id: int,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        enabled: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> Optional[DatabaseMetricThresholdDB]:
        """Update metric threshold"""
        update_data: Dict[str, Any] = {}
        if warning_threshold is not None:
            update_data["warning_threshold"] = warning_threshold
        if critical_threshold is not None:
            update_data["critical_threshold"] = critical_threshold
        if enabled is not None:
            update_data["enabled"] = enabled
        if description is not None:
            update_data["description"] = description

        if not update_data:
            return None

        result = await self.db.execute(
            update(DatabaseMetricThresholdDB)
            .where(DatabaseMetricThresholdDB.id == threshold_id)
            .values(**update_data)
            .returning(DatabaseMetricThresholdDB)
        )
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete_threshold(self, threshold_id: int) -> bool:
        """Delete metric threshold"""
        result = await self.db.execute(
            delete(DatabaseMetricThresholdDB).where(DatabaseMetricThresholdDB.id == threshold_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ============================================================================
    # Performance Baseline Operations
    # ============================================================================

    async def get_all_baselines(self) -> List[DatabasePerformanceBaselineDB]:
        """Get all performance baselines"""
        result = await self.db.execute(select(DatabasePerformanceBaselineDB))
        return result.scalars().all()

    async def get_baseline_by_name(self, baseline_name: str) -> Optional[DatabasePerformanceBaselineDB]:
        """Get baseline by name"""
        result = await self.db.execute(
            select(DatabasePerformanceBaselineDB).where(
                DatabasePerformanceBaselineDB.baseline_name == baseline_name
            )
        )
        return result.scalar_one_or_none()

    async def create_baseline(
        self,
        baseline_name: str,
        avg_query_time: float,
        p95_query_time: float,
        p99_query_time: float,
        avg_connection_count: float,
        peak_connection_count: int,
        cache_hit_ratio: float,
        database_size_mb: float,
        description: str = "",
        created_by: Optional[str] = None,
    ) -> DatabasePerformanceBaselineDB:
        """Create a new performance baseline"""
        baseline = DatabasePerformanceBaselineDB(
            baseline_name=baseline_name,
            established_at=datetime.utcnow(),
            avg_query_time=avg_query_time,
            p95_query_time=p95_query_time,
            p99_query_time=p99_query_time,
            avg_connection_count=avg_connection_count,
            peak_connection_count=peak_connection_count,
            cache_hit_ratio=cache_hit_ratio,
            database_size_mb=database_size_mb,
            description=description,
            created_by=created_by,
        )
        self.db.add(baseline)
        await self.db.commit()
        await self.db.refresh(baseline)
        logger.info(f"Created performance baseline: baseline_name={baseline_name}, id={baseline.id}")
        return baseline

    async def delete_baseline(self, baseline_name: str) -> bool:
        """Delete performance baseline by name"""
        result = await self.db.execute(
            delete(DatabasePerformanceBaselineDB).where(
                DatabasePerformanceBaselineDB.baseline_name == baseline_name
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    # ============================================================================
    # Alert Rule Operations
    # ============================================================================

    async def get_all_alert_rules(self) -> List[DatabaseAlertRuleDB]:
        """Get all alert rules"""
        result = await self.db.execute(select(DatabaseAlertRuleDB))
        return result.scalars().all()

    async def get_alert_rule_by_id(self, rule_id: str) -> Optional[DatabaseAlertRuleDB]:
        """Get alert rule by ID"""
        result = await self.db.execute(
            select(DatabaseAlertRuleDB).where(DatabaseAlertRuleDB.rule_id == rule_id)
        )
        return result.scalar_one_or_none()

    async def create_alert_rule(
        self,
        rule_id: str,
        rule_name: str,
        metric_type: str,
        condition: str,
        severity: str,
        enabled: bool = True,
        notification_channels: Optional[List[str]] = None,
        cooldown_minutes: int = 5,
        description: str = "",
        created_by: Optional[str] = None,
    ) -> DatabaseAlertRuleDB:
        """Create a new alert rule"""
        rule = DatabaseAlertRuleDB(
            rule_id=rule_id,
            rule_name=rule_name,
            metric_type=metric_type,
            condition=condition,
            severity=severity,
            enabled=enabled,
            notification_channels=notification_channels,
            cooldown_minutes=cooldown_minutes,
            description=description,
            created_by=created_by,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        logger.info(f"Created alert rule: rule_id={rule_id}, id={rule.id}")
        return rule

    async def update_alert_rule(
        self,
        rule_id: str,
        rule_name: Optional[str] = None,
        metric_type: Optional[str] = None,
        condition: Optional[str] = None,
        severity: Optional[str] = None,
        enabled: Optional[bool] = None,
        notification_channels: Optional[List[str]] = None,
        cooldown_minutes: Optional[int] = None,
        description: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[DatabaseAlertRuleDB]:
        """Update alert rule"""
        update_data: Dict[str, Any] = {}
        if rule_name is not None:
            update_data["rule_name"] = rule_name
        if metric_type is not None:
            update_data["metric_type"] = metric_type
        if condition is not None:
            update_data["condition"] = condition
        if severity is not None:
            update_data["severity"] = severity
        if enabled is not None:
            update_data["enabled"] = enabled
        if notification_channels is not None:
            update_data["notification_channels"] = notification_channels
        if cooldown_minutes is not None:
            update_data["cooldown_minutes"] = cooldown_minutes
        if description is not None:
            update_data["description"] = description
        if updated_by is not None:
            update_data["updated_by"] = updated_by

        if not update_data:
            return None

        result = await self.db.execute(
            update(DatabaseAlertRuleDB)
            .where(DatabaseAlertRuleDB.rule_id == rule_id)
            .values(**update_data)
            .returning(DatabaseAlertRuleDB)
        )
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete alert rule by ID"""
        result = await self.db.execute(
            delete(DatabaseAlertRuleDB).where(DatabaseAlertRuleDB.rule_id == rule_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ============================================================================
    # Monitoring Status Operations
    # ============================================================================

    async def get_status(self) -> Optional[DatabaseMonitoringStatusDB]:
        """Get the current monitoring status"""
        result = await self.db.execute(
            select(DatabaseMonitoringStatusDB).order_by(DatabaseMonitoringStatusDB.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def create_status(
        self,
        monitoring_enabled: bool = True,
        active_alerts: int = 0,
        total_metrics_collected: int = 0,
        database_health: str = "healthy",
        uptime_percentage: float = 100.0,
    ) -> DatabaseMonitoringStatusDB:
        """Create a new monitoring status"""
        status = DatabaseMonitoringStatusDB(
            monitoring_enabled=monitoring_enabled,
            last_collection_time=datetime.utcnow(),
            active_alerts=active_alerts,
            total_metrics_collected=total_metrics_collected,
            database_health=database_health,
            uptime_percentage=uptime_percentage,
        )
        self.db.add(status)
        await self.db.commit()
        await self.db.refresh(status)
        logger.info(f"Created monitoring status: id={status.id}")
        return status

    async def update_status(
        self,
        status_id: int,
        monitoring_enabled: Optional[bool] = None,
        last_collection_time: Optional[datetime] = None,
        active_alerts: Optional[int] = None,
        total_metrics_collected: Optional[int] = None,
        database_health: Optional[str] = None,
        uptime_percentage: Optional[float] = None,
    ) -> Optional[DatabaseMonitoringStatusDB]:
        """Update monitoring status"""
        update_data: Dict[str, Any] = {}
        if monitoring_enabled is not None:
            update_data["monitoring_enabled"] = monitoring_enabled
        if last_collection_time is not None:
            update_data["last_collection_time"] = last_collection_time
        if active_alerts is not None:
            update_data["active_alerts"] = active_alerts
        if total_metrics_collected is not None:
            update_data["total_metrics_collected"] = total_metrics_collected
        if database_health is not None:
            update_data["database_health"] = database_health
        if uptime_percentage is not None:
            update_data["uptime_percentage"] = uptime_percentage

        if not update_data:
            return None

        result = await self.db.execute(
            update(DatabaseMonitoringStatusDB)
            .where(DatabaseMonitoringStatusDB.id == status_id)
            .values(**update_data)
            .returning(DatabaseMonitoringStatusDB)
        )
        await self.db.commit()
        return result.scalar_one_or_none()
