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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["监控配置"])


# ============================================================================
# Pydantic Models
# ============================================================================


class MonitoringConfig(BaseModel):
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
# In-Memory Configuration Storage
# ============================================================================

_monitoring_config = {
    "enabled": True,
    "data_retention_days": 30,
    "sampling_rate": 1.0,
    "enable_realtime": True,
    "enable_historical": True,
    "dashboard_refresh_interval": 30,
}

_metrics_config = {
    "cpu_enabled": True,
    "memory_enabled": True,
    "disk_enabled": True,
    "network_enabled": True,
    "process_enabled": True,
    "collection_interval": 60,
    "storage_backend": "victoriametrics",
}

_logging_config = {
    "level": "INFO",
    "format": "json",
    "enable_file_logging": True,
    "enable_console_logging": True,
    "log_retention_days": 7,
    "max_file_size_mb": 100,
    "storage_backend": "loki",
}

_alert_thresholds = {
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


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/config", summary="获取监控配置")
async def get_monitoring_config() -> Dict[str, Any]:
    """获取监控配置"""
    return _monitoring_config.copy()


@router.put("/config", summary="更新监控配置")
async def update_monitoring_config(config: MonitoringConfig) -> Dict[str, Any]:
    """更新监控配置"""
    global _monitoring_config
    _monitoring_config = config.dict()
    return {"status": "success", "config": _monitoring_config}


@router.get("/metrics-config", summary="获取指标收集配置")
async def get_metrics_config() -> Dict[str, Any]:
    """获取指标收集配置"""
    return _metrics_config.copy()


@router.put("/metrics-config", summary="更新指标收集配置")
async def update_metrics_config(config: MetricsConfig) -> Dict[str, Any]:
    """更新指标收集配置"""
    global _metrics_config
    _metrics_config = config.dict()
    return {"status": "success", "config": _metrics_config}


@router.get("/logging-config", summary="获取日志配置")
async def get_logging_config() -> Dict[str, Any]:
    """获取日志配置"""
    return _logging_config.copy()


@router.put("/logging-config", summary="更新日志配置")
async def update_logging_config(config: LoggingConfig) -> Dict[str, Any]:
    """更新日志配置"""
    global _logging_config
    _logging_config = config.dict()
    return {"status": "success", "config": _logging_config}


@router.get("/alert-thresholds", summary="获取告警阈值")
async def get_alert_thresholds() -> Dict[str, Any]:
    """获取告警阈值"""
    return _alert_thresholds.copy()


@router.put("/alert-thresholds", summary="更新告警阈值")
async def update_alert_thresholds(config: AlertThresholdsConfig) -> Dict[str, Any]:
    """更新告警阈值"""
    global _alert_thresholds
    _alert_thresholds = config.dict()
    return {"status": "success", "config": _alert_thresholds}


@router.get("/status", summary="获取监控状态")
async def get_monitoring_status() -> Dict[str, Any]:
    """获取监控状态"""
    try:
        # 检查各个监控组件的状态
        status = {
            "monitoring_enabled": _monitoring_config.get("enabled", False),
            "metrics_collection": {
                "status": "running" if _metrics_config.get("cpu_enabled") else "stopped",
                "last_collection": "2026-08-26T09:00:00Z",
                "collection_interval": _metrics_config.get("collection_interval", 60),
            },
            "logging": {
                "status": "running" if _logging_config.get("enable_file_logging") else "stopped",
                "level": _logging_config.get("level", "INFO"),
                "storage_backend": _logging_config.get("storage_backend", "loki"),
            },
            "alerting": {
                "status": "active",
                "active_thresholds": len([t for t in _alert_thresholds.get("thresholds", []) if t.get("enabled")]),
                "total_thresholds": len(_alert_thresholds.get("thresholds", [])),
            },
            "storage": {
                "metrics_backend": _metrics_config.get("storage_backend", "victoriametrics"),
                "logs_backend": _logging_config.get("storage_backend", "loki"),
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
        # 模拟连接测试
        if backend == "victoriametrics":
            result = {
                "backend": "victoriametrics",
                "status": "connected",
                "latency_ms": 15,
                "version": "1.96.0",
            }
        elif backend == "loki":
            result = {
                "backend": "loki",
                "status": "connected",
                "latency_ms": 20,
                "version": "2.9.0",
            }
        elif backend == "tempo":
            result = {
                "backend": "tempo",
                "status": "connected",
                "latency_ms": 25,
                "version": "2.4.0",
            }
        else:
            result = {
                "backend": backend,
                "status": "unknown",
                "latency_ms": 0,
                "version": "unknown",
            }
        return result
    except Exception as e:
        logger.error(f"测试监控连接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"测试监控连接失败: {str(e)[:200]}")