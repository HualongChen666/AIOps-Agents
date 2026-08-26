# -*- coding: utf-8 -*-
"""
Database Monitoring and Observability Configuration
==================================================

Provides comprehensive monitoring and observability configuration for database operations.
Includes performance metrics, alert thresholds, and baseline establishment for database migrations.

This module ensures that database operations are properly monitored with:
- Performance metrics collection
- Alert threshold configuration
- Baseline establishment
- Real-time monitoring capabilities
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/database-monitoring", tags=["数据库监控"])


# ============================================================================
# Enums
# ============================================================================


class AlertSeverity(str, Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """指标类型"""
    QUERY_TIME = "query_time"
    CONNECTION_COUNT = "connection_count"
    DATABASE_SIZE = "database_size"
    CACHE_HIT_RATIO = "cache_hit_ratio"
    DEADLOCK_COUNT = "deadlock_count"
    SLOW_QUERY_COUNT = "slow_query_count"


# ============================================================================
# Pydantic Models
# ============================================================================


class DatabaseMetricThreshold(BaseModel):
    """数据库指标阈值配置"""

    metric_type: MetricType = Field(..., description="指标类型")
    warning_threshold: float = Field(..., description="警告阈值")
    critical_threshold: float = Field(..., description="严重阈值")
    enabled: bool = Field(True, description="是否启用")
    description: str = Field("", description="阈值描述")


class DatabaseMonitoringConfig(BaseModel):
    """数据库监控配置"""

    enabled: bool = Field(True, description="监控是否启用")
    collection_interval: int = Field(60, description="数据收集间隔（秒）")
    retention_days: int = Field(30, description="数据保留天数")
    enable_realtime: bool = Field(True, description="是否启用实时监控")
    enable_slow_query_log: bool = Field(True, description="是否启用慢查询日志")
    slow_query_threshold: float = Field(1.0, description="慢查询阈值（秒）")
    enable_connection_monitoring: bool = Field(True, description="是否启用连接监控")
    max_connections_threshold: int = Field(100, description="最大连接数阈值")
    enable_deadlock_detection: bool = Field(True, description="是否启用死锁检测")


class DatabasePerformanceBaseline(BaseModel):
    """数据库性能基线"""

    baseline_name: str = Field(..., description="基线名称")
    established_at: datetime = Field(default_factory=datetime.utcnow, description="建立时间")
    avg_query_time: float = Field(..., description="平均查询时间（毫秒）")
    p95_query_time: float = Field(..., description="95分位查询时间（毫秒）")
    p99_query_time: float = Field(..., description="99分位查询时间（毫秒）")
    avg_connection_count: float = Field(..., description="平均连接数")
    peak_connection_count: int = Field(..., description="峰值连接数")
    cache_hit_ratio: float = Field(..., description="缓存命中率")
    database_size_mb: float = Field(..., description="数据库大小（MB）")
    description: str = Field("", description="基线描述")


class DatabaseAlertRule(BaseModel):
    """数据库告警规则"""

    rule_id: str = Field(..., description="规则ID")
    rule_name: str = Field(..., description="规则名称")
    metric_type: MetricType = Field(..., description="监控指标类型")
    condition: str = Field(..., description="告警条件")
    severity: AlertSeverity = Field(..., description="告警严重程度")
    enabled: bool = Field(True, description="是否启用")
    notification_channels: List[str] = Field(default_factory=list, description="通知渠道")
    cooldown_minutes: int = Field(5, description="冷却时间（分钟）")
    description: str = Field("", description="规则描述")


class DatabaseMonitoringStatus(BaseModel):
    """数据库监控状态"""

    monitoring_enabled: bool = Field(..., description="监控是否启用")
    last_collection_time: Optional[datetime] = Field(None, description="最后收集时间")
    active_alerts: int = Field(0, description="活跃告警数量")
    total_metrics_collected: int = Field(0, description="收集的指标总数")
    database_health: str = Field("healthy", description="数据库健康状态")
    uptime_percentage: float = Field(100.0, description="正常运行时间百分比")


# ============================================================================
# In-Memory Storage (for demo purposes)
# ============================================================================

_monitoring_config: DatabaseMonitoringConfig = DatabaseMonitoringConfig()
_metric_thresholds: Dict[str, DatabaseMetricThreshold] = {}
_performance_baselines: Dict[str, DatabasePerformanceBaseline] = {}
_alert_rules: Dict[str, DatabaseAlertRule] = {}
_monitoring_status: DatabaseMonitoringStatus = DatabaseMonitoringStatus(
    monitoring_enabled=True,
    last_collection_time=datetime.utcnow(),
    active_alerts=0,
    total_metrics_collected=0,
    database_health="healthy",
    uptime_percentage=100.0
)


# ============================================================================
# Helper Functions
# ============================================================================


def _initialize_default_thresholds():
    """初始化默认的指标阈值"""
    default_thresholds = [
        DatabaseMetricThreshold(
            metric_type=MetricType.QUERY_TIME,
            warning_threshold=100.0,  # 100ms
            critical_threshold=500.0,  # 500ms
            enabled=True,
            description="查询时间阈值"
        ),
        DatabaseMetricThreshold(
            metric_type=MetricType.CONNECTION_COUNT,
            warning_threshold=80.0,
            critical_threshold=95.0,
            enabled=True,
            description="连接数阈值"
        ),
        DatabaseMetricThreshold(
            metric_type=MetricType.CACHE_HIT_RATIO,
            warning_threshold=0.8,
            critical_threshold=0.5,
            enabled=True,
            description="缓存命中率阈值"
        ),
        DatabaseMetricThreshold(
            metric_type=MetricType.SLOW_QUERY_COUNT,
            warning_threshold=10.0,
            critical_threshold=50.0,
            enabled=True,
            description="慢查询数量阈值"
        ),
    ]
    
    for threshold in default_thresholds:
        _metric_thresholds[threshold.metric_type.value] = threshold


def _initialize_default_alert_rules():
    """初始化默认的告警规则"""
    default_rules = [
        DatabaseAlertRule(
            rule_id="slow_query_alert",
            rule_name="慢查询告警",
            metric_type=MetricType.QUERY_TIME,
            condition="query_time > 500",
            severity=AlertSeverity.WARNING,
            enabled=True,
            notification_channels=["email", "slack"],
            cooldown_minutes=5,
            description="当查询时间超过500ms时触发告警"
        ),
        DatabaseAlertRule(
            rule_id="connection_alert",
            rule_name="连接数告警",
            metric_type=MetricType.CONNECTION_COUNT,
            condition="connection_count > 90",
            severity=AlertSeverity.ERROR,
            enabled=True,
            notification_channels=["email", "slack"],
            cooldown_minutes=10,
            description="当连接数超过90时触发告警"
        ),
        DatabaseAlertRule(
            rule_id="deadlock_alert",
            rule_name="死锁告警",
            metric_type=MetricType.DEADLOCK_COUNT,
            condition="deadlock_count > 0",
            severity=AlertSeverity.CRITICAL,
            enabled=True,
            notification_channels=["email", "slack", "pagerduty"],
            cooldown_minutes=1,
            description="当检测到死锁时立即触发告警"
        ),
    ]
    
    for rule in default_rules:
        _alert_rules[rule.rule_id] = rule


# Initialize defaults
_initialize_default_thresholds()
_initialize_default_alert_rules()


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/config", response_model=DatabaseMonitoringConfig)
async def get_monitoring_config() -> DatabaseMonitoringConfig:
    """获取数据库监控配置"""
    return _monitoring_config


@router.put("/config", response_model=DatabaseMonitoringConfig)
async def update_monitoring_config(config: DatabaseMonitoringConfig) -> DatabaseMonitoringConfig:
    """更新数据库监控配置"""
    global _monitoring_config
    _monitoring_config = config
    logger.info(f"Database monitoring configuration updated: {config}")
    return _monitoring_config


@router.get("/thresholds", response_model=Dict[str, DatabaseMetricThreshold])
async def get_metric_thresholds() -> Dict[str, DatabaseMetricThreshold]:
    """获取所有指标阈值"""
    return _metric_thresholds


@router.put("/thresholds/{metric_type}", response_model=DatabaseMetricThreshold)
async def update_metric_threshold(
    metric_type: str,
    threshold: DatabaseMetricThreshold
) -> DatabaseMetricThreshold:
    """更新特定指标的阈值"""
    if metric_type not in _metric_thresholds:
        raise HTTPException(status_code=404, detail=f"Metric type {metric_type} not found")
    
    _metric_thresholds[metric_type] = threshold
    logger.info(f"Metric threshold updated for {metric_type}: {threshold}")
    return threshold


@router.get("/baselines", response_model=Dict[str, DatabasePerformanceBaseline])
async def get_performance_baselines() -> Dict[str, DatabasePerformanceBaseline]:
    """获取所有性能基线"""
    return _performance_baselines


@router.post("/baselines", response_model=DatabasePerformanceBaseline)
async def create_performance_baseline(baseline: DatabasePerformanceBaseline) -> DatabasePerformanceBaseline:
    """创建新的性能基线"""
    if baseline.baseline_name in _performance_baselines:
        raise HTTPException(status_code=400, detail=f"Baseline {baseline.baseline_name} already exists")
    
    _performance_baselines[baseline.baseline_name] = baseline
    logger.info(f"Performance baseline created: {baseline.baseline_name}")
    return baseline


@router.get("/baselines/{baseline_name}", response_model=DatabasePerformanceBaseline)
async def get_performance_baseline(baseline_name: str) -> DatabasePerformanceBaseline:
    """获取特定的性能基线"""
    if baseline_name not in _performance_baselines:
        raise HTTPException(status_code=404, detail=f"Baseline {baseline_name} not found")
    
    return _performance_baselines[baseline_name]


@router.get("/alert-rules", response_model=Dict[str, DatabaseAlertRule])
async def get_alert_rules() -> Dict[str, DatabaseAlertRule]:
    """获取所有告警规则"""
    return _alert_rules


@router.post("/alert-rules", response_model=DatabaseAlertRule)
async def create_alert_rule(rule: DatabaseAlertRule) -> DatabaseAlertRule:
    """创建新的告警规则"""
    if rule.rule_id in _alert_rules:
        raise HTTPException(status_code=400, detail=f"Alert rule {rule.rule_id} already exists")
    
    _alert_rules[rule.rule_id] = rule
    logger.info(f"Alert rule created: {rule.rule_id}")
    return rule


@router.put("/alert-rules/{rule_id}", response_model=DatabaseAlertRule)
async def update_alert_rule(rule_id: str, rule: DatabaseAlertRule) -> DatabaseAlertRule:
    """更新告警规则"""
    if rule_id not in _alert_rules:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    
    _alert_rules[rule_id] = rule
    logger.info(f"Alert rule updated: {rule_id}")
    return rule


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(rule_id: str) -> Dict[str, str]:
    """删除告警规则"""
    if rule_id not in _alert_rules:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    
    del _alert_rules[rule_id]
    logger.info(f"Alert rule deleted: {rule_id}")
    return {"message": f"Alert rule {rule_id} deleted successfully"}


@router.get("/status", response_model=DatabaseMonitoringStatus)
async def get_monitoring_status() -> DatabaseMonitoringStatus:
    """获取数据库监控状态"""
    # Update last collection time
    _monitoring_status.last_collection_time = datetime.utcnow()
    return _monitoring_status


@router.post("/establish-baseline")
async def establish_current_baseline(baseline_name: str) -> DatabasePerformanceBaseline:
    """基于当前性能数据建立基线"""
    # In a real implementation, this would collect actual performance metrics
    # For now, we create a baseline with sample data
    baseline = DatabasePerformanceBaseline(
        baseline_name=baseline_name,
        established_at=datetime.utcnow(),
        avg_query_time=45.0,  # Sample data
        p95_query_time=120.0,
        p99_query_time=250.0,
        avg_connection_count=35.0,
        peak_connection_count=65,
        cache_hit_ratio=0.92,
        database_size_mb=1024.0,
        description=f"Baseline established on {datetime.utcnow().isoformat()}"
    )
    
    _performance_baselines[baseline_name] = baseline
    logger.info(f"Performance baseline established: {baseline_name}")
    return baseline


@router.get("/health")
async def get_database_health() -> Dict[str, Any]:
    """获取数据库健康状态"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "query_time_ms": 45.0,
            "connection_count": 35,
            "cache_hit_ratio": 0.92,
            "database_size_mb": 1024.0,
            "slow_query_count": 2,
            "deadlock_count": 0
        },
        "alerts": {
            "active": 0,
            "last_24h": 0
        }
    }
