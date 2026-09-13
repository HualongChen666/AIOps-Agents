# -*- coding: utf-8 -*-
"""
Monitoring Configuration Router Module
======================================

Provides API endpoints for monitoring and observability configuration.
Supports metric collection, logging configuration, alert thresholds, and dashboard settings.

Endpoints:
- GET /api/v1/monitoring/config - Get monitoring configuration
- PUT /api/v1/monitoring/config - Update monitoring configuration
- GET /api/v1/monitoring/metrics-config - Get metrics collection configuration
- PUT /api/v1/monitoring/metrics-config - Update metrics collection configuration
- GET /api/v1/monitoring/logging-config - Get logging configuration
- PUT /api/v1/monitoring/logging-config - Update logging configuration
- GET /api/v1/monitoring/alert-thresholds - Get alert thresholds
- PUT /api/v1/monitoring/alert-thresholds - Update alert thresholds
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.backend_requirements import requires_backend
from core.metrics_history import get_metrics_history
from core.persistent_store import PersistentStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["监控配置"])


# ============================================================================
# Pydantic Models
# ============================================================================


class MonitoringConfigMonitoringConfig(BaseModel):
    """监控配置模型"""

    enabled: bool = Field(True, description="监控是否启用")
    data_retention_days: int = Field(30, description="数据保留天数")
    sampling_rate: float = Field(1.0, description="采样率")
    enable_realtime: bool = Field(True, description="是否启用实时监控")
    enable_historical: bool = Field(True, description="是否启用历史数据")
    dashboard_refresh_interval: int = Field(30, description="仪表板刷新间隔（秒）")


class MetricsConfig(BaseModel):
    """指标收集配置模型"""

    cpu_enabled: bool = Field(True, description="CPU指标收集")
    memory_enabled: bool = Field(True, description="内存指标收集")
    disk_enabled: bool = Field(True, description="磁盘指标收集")
    network_enabled: bool = Field(True, description="网络指标收集")
    process_enabled: bool = Field(True, description="进程指标收集")
    collection_interval: int = Field(60, description="收集间隔（秒）")
    storage_backend: str = Field("victoriametrics", description="存储后端")


class LoggingConfig(BaseModel):
    """日志配置模型"""

    level: str = Field("INFO", description="日志级别")
    format: str = Field("json", description="日志格式")
    enable_file_logging: bool = Field(True, description="是否启用文件日志")
    enable_console_logging: bool = Field(True, description="是否启用控制台日志")
    log_retention_days: int = Field(7, description="日志保留天数")
    max_file_size_mb: int = Field(100, description="最大文件大小（MB）")
    storage_backend: str = Field("loki", description="日志存储后端")


class AlertThreshold(BaseModel):
    """告警阈值模型"""

    metric_name: str = Field(..., description="指标名称")
    warning_threshold: float = Field(..., description="警告阈值")
    critical_threshold: float = Field(..., description="严重阈值")
    comparison: str = Field("greater", description="比较方式")
    enabled: bool = Field(True, description="是否启用")


class AlertThresholdsConfig(BaseModel):
    """告警阈值配置模型"""

    thresholds: List[AlertThreshold] = Field([], description="告警阈值列表")
    notification_channels: List[str] = Field([], description="通知通道")
    cooldown_seconds: int = Field(300, description="冷却时间（秒）")


# ============================================================================
# Configuration Storage (durable)
# ============================================================================
#
# The four configuration documents are persisted through ``PersistentStore``
# (the ``persistent_records`` table) so they survive process restarts and are
# shared across workers, instead of living only in module-level dicts.

_CONFIG_STORE: PersistentStore = PersistentStore("monitoring", "config")

_MONITORING_CONFIG_KEY = "monitoring"
_METRICS_CONFIG_KEY = "metrics"
_LOGGING_CONFIG_KEY = "logging"
_ALERT_THRESHOLDS_KEY = "alert_thresholds"

_DEFAULT_MONITORING_CONFIG = {
    "enabled": True,
    "data_retention_days": 30,
    "sampling_rate": 1.0,
    "enable_realtime": True,
    "enable_historical": True,
    "dashboard_refresh_interval": 30,
}

_DEFAULT_METRICS_CONFIG = {
    "cpu_enabled": True,
    "memory_enabled": True,
    "disk_enabled": True,
    "network_enabled": True,
    "process_enabled": True,
    "collection_interval": 60,
    "storage_backend": "victoriametrics",
}

_DEFAULT_LOGGING_CONFIG = {
    "level": "INFO",
    "format": "json",
    "enable_file_logging": True,
    "enable_console_logging": True,
    "log_retention_days": 7,
    "max_file_size_mb": 100,
    "storage_backend": "loki",
}

_DEFAULT_ALERT_THRESHOLDS = {
    "thresholds": [
        {
            "metric_name": "cpu_usage",
            "warning_threshold": 80.0,
            "critical_threshold": 90.0,
            "comparison": "greater",
            "enabled": True,
        },
        {
            "metric_name": "memory_usage",
            "warning_threshold": 85.0,
            "critical_threshold": 95.0,
            "comparison": "greater",
            "enabled": True,
        },
        {
            "metric_name": "disk_usage",
            "warning_threshold": 85.0,
            "critical_threshold": 95.0,
            "comparison": "greater",
            "enabled": True,
        },
        {
            "metric_name": "error_rate",
            "warning_threshold": 1.0,
            "critical_threshold": 5.0,
            "comparison": "greater",
            "enabled": True,
        },
    ],
    "notification_channels": ["email", "slack"],
    "cooldown_seconds": 300,
}


def _load_config(key: str, default: Dict[str, Any]) -> Dict[str, Any]:
    """Return the persisted config for *key*, seeding it on first access."""
    stored = _CONFIG_STORE.get(key)
    if stored is None:
        _CONFIG_STORE[key] = dict(default)
        return dict(default)
    return dict(stored)


def _save_config(key: str, value: Dict[str, Any]) -> Dict[str, Any]:
    """Persist *value* under *key* and return a plain copy."""
    _CONFIG_STORE[key] = dict(value)
    return dict(value)


def _last_metrics_collection() -> Optional[str]:
    """Timestamp of the most recent real metrics sample, or ``None``.

    Derived from the live ``METRICS_HISTORY`` ring buffer — never a fixed
    constant.  Returns ``None`` when no metric has been collected yet.
    """
    history = get_metrics_history(1)
    if not history:
        return None
    timestamp = history[-1].get("timestamp")
    return str(timestamp) if timestamp else None


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/config", summary="获取监控配置")
async def get_monitoring_config() -> Dict[str, Any]:
    """获取监控配置"""
    return _load_config(_MONITORING_CONFIG_KEY, _DEFAULT_MONITORING_CONFIG)


@router.put("/config", summary="更新监控配置")
async def update_monitoring_config(config: MonitoringConfigMonitoringConfig) -> Dict[str, Any]:
    """更新监控配置"""
    saved = _save_config(_MONITORING_CONFIG_KEY, config.model_dump())
    return {"status": "success", "config": saved}


@router.get("/metrics-config", summary="获取指标收集配置")
async def get_metrics_config() -> Dict[str, Any]:
    """获取指标收集配置"""
    return _load_config(_METRICS_CONFIG_KEY, _DEFAULT_METRICS_CONFIG)


@router.put("/metrics-config", summary="更新指标收集配置")
async def update_metrics_config(config: MetricsConfig) -> Dict[str, Any]:
    """更新指标收集配置"""
    saved = _save_config(_METRICS_CONFIG_KEY, config.model_dump())
    return {"status": "success", "config": saved}


@router.get("/logging-config", summary="获取日志配置")
async def get_logging_config() -> Dict[str, Any]:
    """获取日志配置"""
    return _load_config(_LOGGING_CONFIG_KEY, _DEFAULT_LOGGING_CONFIG)


@router.put("/logging-config", summary="更新日志配置")
async def update_logging_config(config: LoggingConfig) -> Dict[str, Any]:
    """更新日志配置"""
    saved = _save_config(_LOGGING_CONFIG_KEY, config.model_dump())
    return {"status": "success", "config": saved}


@router.get("/alert-thresholds", summary="获取告警阈值")
async def get_alert_thresholds() -> Dict[str, Any]:
    """获取告警阈值"""
    return _load_config(_ALERT_THRESHOLDS_KEY, _DEFAULT_ALERT_THRESHOLDS)


@router.put("/alert-thresholds", summary="更新告警阈值")
async def update_alert_thresholds(config: AlertThresholdsConfig) -> Dict[str, Any]:
    """更新告警阈值"""
    saved = _save_config(_ALERT_THRESHOLDS_KEY, config.model_dump())
    return {"status": "success", "config": saved}


@router.get("/status", summary="获取监控状态")
async def get_monitoring_status() -> Dict[str, Any]:
    """获取监控状态"""
    try:
        monitoring_config = _load_config(_MONITORING_CONFIG_KEY, _DEFAULT_MONITORING_CONFIG)
        metrics_config = _load_config(_METRICS_CONFIG_KEY, _DEFAULT_METRICS_CONFIG)
        logging_config = _load_config(_LOGGING_CONFIG_KEY, _DEFAULT_LOGGING_CONFIG)
        alert_thresholds = _load_config(_ALERT_THRESHOLDS_KEY, _DEFAULT_ALERT_THRESHOLDS)

        # 检查各个监控组件的状态
        status = {
            "monitoring_enabled": monitoring_config.get("enabled", False),
            "metrics_collection": {
                "status": "running" if metrics_config.get("cpu_enabled") else "stopped",
                "last_collection": _last_metrics_collection(),
                "collection_interval": metrics_config.get("collection_interval", 60),
            },
            "logging": {
                "status": "running" if logging_config.get("enable_file_logging") else "stopped",
                "level": logging_config.get("level", "INFO"),
                "storage_backend": logging_config.get("storage_backend", "loki"),
            },
            "alerting": {
                "status": "active",
                "active_thresholds": len([t for t in alert_thresholds.get("thresholds", []) if t.get("enabled")]),
                "total_thresholds": len(alert_thresholds.get("thresholds", [])),
            },
            "storage": {
                "metrics_backend": metrics_config.get("storage_backend", "victoriametrics"),
                "logs_backend": logging_config.get("storage_backend", "loki"),
                "traces_backend": "tempo",
            },
        }
        return status
    except Exception as e:
        logger.error(f"获取监控状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取监控状态失败: {str(e)[:200]}")


@router.post("/test-connection", summary="测试监控连接")
async def test_monitoring_connection(backend: str = Query(..., description="存储后端")) -> Dict[str, Any]:
    """测试监控存储后端连接"""
    try:
        import time as _time

        start = _time.perf_counter()

        if backend == "victoriametrics":
            import httpx

            from config import VICTORIAMETRICS_URL

            base = str(VICTORIAMETRICS_URL).rstrip("/")
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{base}/-/healthy")
                connected = response.status_code < 500
            except Exception as e:  # noqa: BLE001 - surfaced as requires-backend
                requires_backend(
                    "victoriametrics",
                    capability="monitoring connection test",
                    reason=f"VictoriaMetrics unreachable: {e}",
                )
        elif backend == "loki":
            from core.loki_client import get_loki_client

            connected = await get_loki_client().health_check()
            if not connected:
                requires_backend(
                    "loki",
                    capability="monitoring connection test",
                    reason="Loki is not reachable or not configured",
                )
        elif backend == "tempo":
            from core.tempo_client import get_tempo_client

            connected = await get_tempo_client().health_check()
            if not connected:
                requires_backend(
                    "tempo",
                    capability="monitoring connection test",
                    reason="Tempo is not reachable or not configured",
                )
        else:
            requires_backend(
                backend,
                capability="monitoring connection test",
                reason=f"Unsupported monitoring backend '{backend}'",
            )

        return {
            "backend": backend,
            "status": "connected" if connected else "degraded",
            "latency_ms": round((_time.perf_counter() - start) * 1000, 1),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试监控连接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"测试监控连接失败: {str(e)[:200]}")
