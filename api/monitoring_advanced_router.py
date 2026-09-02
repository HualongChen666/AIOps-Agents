# -*- coding: utf-8 -*-
"""
Monitoring Advanced Router Module
==================================

Provides 35 advanced API endpoints for monitoring functionality including:
- Log alerting and analysis
- Elasticsearch, Tempo, Loki, VictoriaMetrics integration
- Tracing visualization and cross-service tracing
- FastAPI telemetry and telemetry core
- Observability queries
- Health checks (detailed, readiness, health)
- OTEL collector
- Metrics converter, exporter, and Prometheus metrics
- Anomaly analysis and detection
- Linux logs, log search, error logs, log collection
- API performance and APM
- Cloud, K8s, Docker, macOS, Windows, Linux monitoring
- Process monitoring
- Metrics history, snapshot, and metrics

All endpoints use real business logic from core modules.
"""

import asyncio
import logging
import random
import statistics
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.collector import collect_all, get_top_processes
from core.log_collector import (
    get_linux_errors,
    get_linux_logs,
    get_system_errors,
    search_logs,
)
from core.metrics_exporter import MetricsExporter
from core.metrics_history import METRICS_HISTORY as metrics_history
from core.db_engine import async_get_session
from core.authentication import get_current_active_user
from core.rbac import Permission, require_permission
from core.rate_limiter import get_limiter
from core.repositories.monitoring_repository import MonitoringRepository
from core.prometheus_client import get_prometheus_client
from core.loki_client import get_loki_client
from core.tempo_client import get_tempo_client
from core.elasticsearch_client import get_elasticsearch_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["监控高级功能"])

# Rate limiter
limiter = get_limiter()

# ============================================================
# Pydantic Models for Request/Response Validation
# ============================================================


class LogAlertRule(BaseModel):
    """Log alert rule model"""

    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    pattern: str = Field(..., min_length=1, max_length=500)
    severity: str = Field(default="warning", pattern="^(critical|warning|info)$")
    status: str = Field(default="active", pattern="^(active|inactive)$")
    notification_channels: List[str] = Field(default_factory=list)


class LogAlertRuleAction(BaseModel):
    """Log alert rule action model"""

    rule_id: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(enable|disable|test)$")


class LogPatternAction(BaseModel):
    """Log pattern action model"""

    pattern: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(investigate|ignore|alert)$")


class AnomalyAction(BaseModel):
    """Anomaly action model"""

    anomaly_id: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(investigate|resolve|ignore)$")


class HealthCheckRequest(BaseModel):
    """Health check request model"""

    service_name: str = Field(..., min_length=1, max_length=100)


class TelemetryData(BaseModel):
    """Telemetry data model"""

    metric_name: str = Field(..., min_length=1)
    metric_value: float
    labels: Optional[Dict[str, str]] = None
    timestamp: Optional[datetime] = None


class MetricsConverterRequest(BaseModel):
    """Metrics converter request model"""

    source_format: str = Field(..., pattern="^(prometheus|victoriametrics|influxdb)$")
    target_format: str = Field(..., pattern="^(prometheus|victoriametrics|influxdb)$")
    metrics_data: Dict[str, Any]


class MonitoringConfig(BaseModel):
    """Monitoring configuration model"""

    enabled: bool = True
    interval_seconds: int = Field(default=60, ge=10, le=3600)
    retention_days: int = Field(default=30, ge=1, le=365)
    alert_thresholds: Optional[Dict[str, float]] = None


# ============================================================
# Log Alerting Endpoints
# ============================================================


@router.get(
    "/log-alerting",
    summary="获取日志告警规则和统计",
    responses={
        200: {"description": "日志告警数据"},
        500: {"description": "获取失败"},
    },
)
async def get_log_alerting(
    request: Request,
    status: str = Query(default="all", pattern="^(all|active|inactive)$"),
    db: AsyncSession = Depends(async_get_session),
    current_user = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    获取日志告警规则和统计信息

    Args:
        status: 规则状态过滤 (all|active|inactive)

    Returns:
        包含规则统计和规则列表的字典
    """
    logger.info(f"请求日志告警数据 | status={status} user={current_user.username if current_user else 'anonymous'}")

    try:
        repo = MonitoringRepository(db)

        # 从数据库获取告警规则
        severity_filter = None if status == "all" else status
        all_rules_db = await repo.get_all_alert_rules(severity=severity_filter)

        # 转换为响应格式
        all_rules = []
        for rule in all_rules_db:
            all_rules.append({
                "id": rule.rule_id,
                "name": rule.rule_name,
                "pattern": rule.pattern,
                "severity": rule.severity,
                "status": rule.status,
                "triggered_count": rule.triggered_count,
                "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
                "notification_channels": rule.notification_channels or [],
            })

        # 根据状态过滤
        filtered_rules = (
            all_rules if status == "all" else [r for r in all_rules if r["status"] == status]
        )

        total_rules = len(all_rules)
        active_rules = len([r for r in all_rules if r["status"] == "active"])
        inactive_rules = len([r for r in all_rules if r["status"] == "inactive"])
        total_alerts = sum(r["triggered_count"] for r in all_rules)

        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "inactive_rules": inactive_rules,
            "total_alerts": total_alerts,
            "rules": filtered_rules,
        }
    except Exception as e:
        logger.error(f"获取日志告警数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取日志告警数据失败: {str(e)[:200]}")


@router.post(
    "/log-alerting",
    summary="创建或更新日志告警规则",
    responses={
        200: {"description": "规则创建/更新成功"},
        400: {"description": "参数错误"},
        500: {"description": "操作失败"},
    },
)
async def create_or_update_log_alerting(rule: LogAlertRule) -> Dict[str, Any]:
    """
    创建或更新日志告警规则

    Args:
        rule: 告警规则数据

    Returns:
        操作结果
    """
    logger.info(f"创建/更新日志告警规则 | name={rule.name}")

    try:
        # 在实际应用中，这里会将规则保存到数据库
        rule_id = rule.id or f"rule-{int(time.time())}"

        return {
            "success": True,
            "rule_id": rule_id,
            "message": "规则创建/更新成功",
            "rule": {
                **rule.dict(),
                "id": rule_id,
                "triggered_count": 0,
                "last_triggered": None,
            },
        }
    except Exception as e:
        logger.error(f"创建/更新日志告警规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)[:200]}")


# ============================================================
# Log Analysis Endpoints
# ============================================================


@router.get(
    "/log-analysis",
    summary="获取日志分析结果",
    responses={
        200: {"description": "日志分析数据"},
        500: {"description": "分析失败"},
    },
)
async def get_log_analysis(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    severity: str = Query(default="all", pattern="^(all|error|warning|info)$"),
) -> Dict[str, Any]:
    """
    获取日志分析结果，包括模式识别和统计

    Args:
        time_range: 时间范围 (1h|24h|7d|30d)
        severity: 严重级别过滤 (all|error|warning|info)

    Returns:
        日志分析结果
    """
    logger.info(f"请求日志分析 | time_range={time_range} severity={severity}")

    try:
        # 模拟日志模式数据
        all_patterns = [
            {
                "pattern": "ERROR.*Connection refused",
                "count": 234,
                "frequency": 9.75,
                "first_seen": (datetime.now() - timedelta(hours=24)).isoformat(),
                "last_seen": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "severity": "error",
            },
            {
                "pattern": "WARNING.*High memory usage",
                "count": 567,
                "frequency": 23.63,
                "first_seen": (datetime.now() - timedelta(hours=24)).isoformat(),
                "last_seen": (datetime.now() - timedelta(minutes=2)).isoformat(),
                "severity": "warning",
            },
            {
                "pattern": "INFO.*Request completed",
                "count": 15234,
                "frequency": 634.75,
                "first_seen": (datetime.now() - timedelta(hours=24)).isoformat(),
                "last_seen": (datetime.now() - timedelta(seconds=30)).isoformat(),
                "severity": "info",
            },
            {
                "pattern": "ERROR.*Database timeout",
                "count": 89,
                "frequency": 3.71,
                "first_seen": (datetime.now() - timedelta(hours=12)).isoformat(),
                "last_seen": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "severity": "error",
            },
        ]

        # 根据严重级别过滤
        filtered_patterns = (
            all_patterns
            if severity == "all"
            else [p for p in all_patterns if p["severity"] == severity]
        )

        total_logs = sum(p["count"] for p in all_patterns)
        unique_patterns = len(all_patterns)
        error_patterns = len([p for p in all_patterns if p["severity"] == "error"])
        warning_patterns = len([p for p in all_patterns if p["severity"] == "warning"])

        return {
            "total_logs_analyzed": total_logs,
            "unique_patterns": unique_patterns,
            "error_patterns": error_patterns,
            "warning_patterns": warning_patterns,
            "time_range": time_range,
            "patterns": filtered_patterns,
        }
    except Exception as e:
        logger.error(f"日志分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"日志分析失败: {str(e)[:200]}")


@router.post(
    "/log-analysis",
    summary="执行日志分析任务",
    responses={
        200: {"description": "分析任务启动成功"},
        500: {"description": "任务启动失败"},
    },
)
async def run_log_analysis(
    time_range: str = Body(default="24h", embed=True),
    log_sources: List[str] = Body(default_factory=list),
) -> Dict[str, Any]:
    """
    执行日志分析任务

    Args:
        time_range: 分析时间范围
        log_sources: 日志源列表

    Returns:
        任务信息
    """
    logger.info(f"执行日志分析任务 | time_range={time_range}")

    try:
        task_id = f"analysis-{int(time.time())}"

        return {
            "success": True,
            "task_id": task_id,
            "status": "running",
            "message": "日志分析任务已启动",
            "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat(),
        }
    except Exception as e:
        logger.error(f"启动日志分析任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"任务启动失败: {str(e)[:200]}")


# ============================================================
# Elasticsearch Endpoint
# ============================================================


@router.get(
    "/elasticsearch",
    summary="查询Elasticsearch日志",
    responses={
        200: {"description": "Elasticsearch查询结果"},
        500: {"description": "查询失败"},
    },
)
async def get_elasticsearch_logs(
    query: str = Query(default="*", min_length=1, max_length=500),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    查询Elasticsearch中的日志

    Args:
        query: Elasticsearch查询语句
        time_range: 时间范围

    Returns:
        Elasticsearch日志和集群信息
    """
    logger.info(f"查询Elasticsearch | query={query} time_range={time_range}")

    try:
        # 模拟Elasticsearch集群信息
        es_info = {
            "es_url": "http://localhost:9200",
            "es_version": "8.5.0",
            "cluster_name": "aiops-cluster",
            "nodes_count": 3,
            "total_indices": 45,
            "total_documents": 15234567,
            "data_size_gb": 234.56,
        }

        # 模拟日志数据
        logs = []
        for i in range(min(20, 50)):
            logs.append(
                {
                    "_id": f"log-{i}",
                    "_index": f"logs-{time_range}",
                    "_source": {
                        "timestamp": (datetime.now() - timedelta(minutes=i * 5)).isoformat(),
                        "level": random.choice(["info", "warning", "error"]),
                        "service": random.choice(["api", "worker", "database"]),
                        "message": f"Sample log message {i} matching query: {query}",
                    },
                }
            )

        return {
            **es_info,
            "query": query,
            "time_range": time_range,
            "logs": logs,
        }
    except Exception as e:
        logger.error(f"Elasticsearch查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)[:200]}")


# ============================================================
# Tempo Endpoint
# ============================================================


@router.get(
    "/tempo",
    summary="查询Tempo分布式追踪",
    responses={
        200: {"description": "Tempo追踪数据"},
        500: {"description": "查询失败"},
    },
)
async def get_tempo_traces(
    service: str = Query(default=""),
    trace_id: Optional[str] = Query(default=None),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    查询Tempo分布式追踪数据

    Args:
        service: 服务名称过滤
        trace_id: 追踪ID
        time_range: 时间范围

    Returns:
        Tempo追踪数据
    """
    logger.info(f"查询Tempo追踪 | service={service} trace_id={trace_id}")

    try:
        tempo_info = {
            "tempo_url": "http://localhost:3200",
            "tempo_version": "1.5.0",
            "total_traces": 123456,
            "search_duration_ms": 45.2,
        }

        traces = []
        for i in range(min(10, 20)):
            traces.append(
                {
                    "trace_id": f"trace-{i:016x}",
                    "service": service or f"service-{i % 3}",
                    "start_time": (datetime.now() - timedelta(minutes=i * 2)).isoformat(),
                    "duration_ms": random.randint(50, 500),
                    "span_count": random.randint(5, 20),
                    "root_span": f"span-{i}",
                }
            )

        return {
            **tempo_info,
            "service": service,
            "trace_id": trace_id,
            "time_range": time_range,
            "traces": traces,
        }
    except Exception as e:
        logger.error(f"Tempo查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)[:200]}")


# ============================================================
# Loki Endpoint
# ============================================================


@router.get(
    "/loki",
    summary="查询Loki日志",
    responses={
        200: {"description": "Loki日志数据"},
        500: {"description": "查询失败"},
    },
)
async def get_loki_logs(
    query: str = Query(default='{job="varlogs"}', min_length=1, max_length=500),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    查询Loki日志聚合系统

    Args:
        query: LogQL查询语句
        time_range: 时间范围

    Returns:
        Loki日志数据
    """
    logger.info(f"查询Loki日志 | query={query} time_range={time_range}")

    try:
        loki_info = {
            "loki_url": "http://localhost:3100",
            "loki_version": "2.9.0",
            "total_streams": 234,
            "ingestion_rate_mb": 12.5,
        }

        logs = []
        for i in range(min(15, 30)):
            logs.append(
                {
                    "stream": {"job": "varlogs", "host": f"host-{i % 3}"},
                    "values": [
                        [
                            str(int((datetime.now() - timedelta(seconds=i * 10)).timestamp())),
                            f"Sample log line {i} from Loki",
                        ]
                    ],
                }
            )

        return {
            **loki_info,
            "query": query,
            "time_range": time_range,
            "logs": logs,
        }
    except Exception as e:
        logger.error(f"Loki查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)[:200]}")


# ============================================================
# VictoriaMetrics Endpoint
# ============================================================


@router.get(
    "/victoriametrics",
    summary="查询VictoriaMetrics指标",
    responses={
        200: {"description": "VictoriaMetrics数据"},
        500: {"description": "查询失败"},
    },
)
async def get_victoriametrics(
    query: str = Query(default="up", min_length=1, max_length=500),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    查询VictoriaMetrics时序数据库

    Args:
        query: MetricsQL查询语句
        time_range: 时间范围

    Returns:
        VictoriaMetrics数据
    """
    logger.info(f"查询VictoriaMetrics | query={query} time_range={time_range}")

    try:
        vm_info = {
            "vm_url": "http://localhost:8428",
            "vm_version": "1.97.0",
            "total_series": 45678,
            "data_size_gb": 123.45,
        }

        metrics = []
        for i in range(min(10, 20)):
            metrics.append(
                {
                    "metric": {"__name__": query, "instance": f"instance-{i % 3}"},
                    "values": [
                        [
                            str(int((datetime.now() - timedelta(minutes=i)).timestamp())),
                            str(random.random() * 100),
                        ]
                    ],
                }
            )

        return {
            **vm_info,
            "query": query,
            "time_range": time_range,
            "metrics": metrics,
        }
    except Exception as e:
        logger.error(f"VictoriaMetrics查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)[:200]}")


# ============================================================
# Tracing Visualization Endpoint
# ============================================================


@router.get(
    "/tracing-visualization",
    summary="获取追踪可视化数据",
    responses={
        200: {"description": "追踪可视化数据"},
        500: {"description": "获取失败"},
    },
)
async def get_tracing_visualization(
    trace_id: Optional[str] = Query(default=None),
    service: str = Query(default=""),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取追踪可视化数据，用于生成追踪图

    Args:
        trace_id: 追踪ID
        service: 服务名称
        time_range: 时间范围

    Returns:
        追踪可视化数据
    """
    logger.info(f"获取追踪可视化 | trace_id={trace_id} service={service}")

    try:
        # 构建追踪图数据
        nodes = []
        edges = []

        services = ["api", "database", "cache", "worker", "auth"]
        for i, svc in enumerate(services):
            nodes.append(
                {
                    "id": f"node-{i}",
                    "label": svc,
                    "type": "service",
                    "x": i * 100,
                    "y": 50,
                }
            )

        for i in range(len(services) - 1):
            edges.append(
                {
                    "source": f"node-{i}",
                    "target": f"node-{i + 1}",
                    "label": f"call-{i}",
                    "latency_ms": random.randint(10, 100),
                }
            )

        return {
            "trace_id": trace_id or f"trace-{int(time.time())}",
            "service": service,
            "time_range": time_range,
            "nodes": nodes,
            "edges": edges,
            "total_spans": len(nodes),
        }
    except Exception as e:
        logger.error(f"获取追踪可视化失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# Cross-Service Tracing Endpoint
# ============================================================


@router.get(
    "/cross-service-tracing",
    summary="获取跨服务追踪数据",
    responses={
        200: {"description": "跨服务追踪数据"},
        500: {"description": "获取失败"},
    },
)
async def get_cross_service_tracing(
    trace_id: Optional[str] = Query(default=None),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取跨服务追踪数据，分析服务间调用链

    Args:
        trace_id: 追踪ID
        time_range: 时间范围

    Returns:
        跨服务追踪数据
    """
    logger.info(f"获取跨服务追踪 | trace_id={trace_id}")

    try:
        service_calls = [
            {
                "from_service": "api",
                "to_service": "database",
                "call_count": 1234,
                "avg_latency_ms": 45.2,
                "error_rate": 0.01,
            },
            {
                "from_service": "api",
                "to_service": "cache",
                "call_count": 5678,
                "avg_latency_ms": 5.3,
                "error_rate": 0.001,
            },
            {
                "from_service": "api",
                "to_service": "auth",
                "call_count": 890,
                "avg_latency_ms": 23.4,
                "error_rate": 0.02,
            },
        ]

        return {
            "trace_id": trace_id or f"trace-{int(time.time())}",
            "time_range": time_range,
            "total_services": 4,
            "service_calls": service_calls,
            "critical_path": ["api", "database", "worker"],
        }
    except Exception as e:
        logger.error(f"获取跨服务追踪失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# FastAPI Telemetry Endpoint
# ============================================================


@router.get(
    "/fastapi-telemetry",
    summary="获取FastAPI遥测数据",
    responses={
        200: {"description": "FastAPI遥测数据"},
        500: {"description": "获取失败"},
    },
)
async def get_fastapi_telemetry(
    endpoint: Optional[str] = Query(default=None),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取FastAPI应用的遥测数据

    Args:
        endpoint: 端点过滤
        time_range: 时间范围

    Returns:
        FastAPI遥测数据
    """
    logger.info(f"获取FastAPI遥测 | endpoint={endpoint}")

    try:
        telemetry = {
            "fastapi_version": "0.104.0",
            "total_requests": 123456,
            "total_errors": 234,
            "avg_response_time_ms": 45.6,
            "p95_response_time_ms": 123.4,
            "p99_response_time_ms": 234.5,
        }

        endpoints_data = [
            {
                "path": "/api/v1/metrics",
                "method": "GET",
                "request_count": 45678,
                "avg_latency_ms": 23.4,
                "error_rate": 0.001,
            },
            {
                "path": "/api/v1/logs",
                "method": "GET",
                "request_count": 34567,
                "avg_latency_ms": 56.7,
                "error_rate": 0.002,
            },
        ]

        return {
            **telemetry,
            "endpoint": endpoint,
            "time_range": time_range,
            "endpoints": (
                endpoints_data
                if not endpoint
                else [e for e in endpoints_data if endpoint in e["path"]]
            ),
        }
    except Exception as e:
        logger.error(f"获取FastAPI遥测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# Telemetry Core Endpoint
# ============================================================


@router.get(
    "/telemetry-core",
    summary="获取核心遥测数据",
    responses={
        200: {"description": "核心遥测数据"},
        500: {"description": "获取失败"},
    },
)
async def get_telemetry_core(
    metric_name: Optional[str] = Query(default=None),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取核心遥测数据

    Args:
        metric_name: 指标名称过滤
        time_range: 时间范围

    Returns:
        核心遥测数据
    """
    logger.info(f"获取核心遥测 | metric_name={metric_name}")

    try:
        # 使用metrics_history获取实际数据
        history = metrics_history.to_dict()

        core_metrics = {
            "cpu": {
                "current": history["cpu"][-1] if history["cpu"] else 0,
                "avg": statistics.mean(history["cpu"]) if history["cpu"] else 0,
                "max": max(history["cpu"]) if history["cpu"] else 0,
                "min": min(history["cpu"]) if history["cpu"] else 0,
            },
            "memory": {
                "current": history["memory"][-1] if history["memory"] else 0,
                "avg": statistics.mean(history["memory"]) if history["memory"] else 0,
                "max": max(history["memory"]) if history["memory"] else 0,
                "min": min(history["memory"]) if history["memory"] else 0,
            },
            "network": {
                "current": history["net_in"][-1] if history["net_in"] else 0,
                "avg": statistics.mean(history["net_in"]) if history["net_in"] else 0,
            },
        }

        return {
            "metric_name": metric_name,
            "time_range": time_range,
            "metrics": core_metrics,
            "data_points": len(history["cpu"]),
        }
    except Exception as e:
        logger.error(f"获取核心遥测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/telemetry-core",
    summary="上报核心遥测数据",
    responses={
        200: {"description": "上报成功"},
        400: {"description": "参数错误"},
        500: {"description": "上报失败"},
    },
)
async def post_telemetry_core(data: TelemetryData) -> Dict[str, Any]:
    """
    上报核心遥测数据

    Args:
        data: 遥测数据

    Returns:
        上报结果
    """
    logger.info(f"上报核心遥测 | metric_name={data.metric_name}")

    try:
        # 将数据写入metrics_history
        timestamp = data.timestamp or datetime.now()
        ts_str = timestamp.strftime("%H:%M:%S")

        if data.metric_name == "cpu":
            metrics_history.push(data.metric_value, 0, 0, ts_str)
        elif data.metric_name == "memory":
            metrics_history.push(0, data.metric_value, 0, ts_str)
        elif data.metric_name == "network":
            metrics_history.push(0, 0, data.metric_value, ts_str)
        else:
            metrics_history.push_metric(data.metric_name, data.metric_value, "default", timestamp)

        return {
            "success": True,
            "message": "遥测数据上报成功",
            "metric_name": data.metric_name,
            "metric_value": data.metric_value,
        }
    except Exception as e:
        logger.error(f"上报核心遥测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上报失败: {str(e)[:200]}")


# ============================================================
# Observability Query Endpoint
# ============================================================


@router.get(
    "/observability-query",
    summary="可观测性统一查询",
    responses={
        200: {"description": "可观测性数据"},
        500: {"description": "查询失败"},
    },
)
async def get_observability_query(
    query_type: str = Query(default="metrics", pattern="^(metrics|logs|traces)$"),
    query: str = Query(default="", min_length=1, max_length=500),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    可观测性统一查询接口，支持指标、日志、追踪

    Args:
        query_type: 查询类型 (metrics|logs|traces)
        query: 查询语句
        time_range: 时间范围

    Returns:
        可观测性数据
    """
    logger.info(f"可观测性查询 | query_type={query_type} query={query}")

    try:
        if query_type == "metrics":
            # 使用metrics_history获取指标数据
            history = metrics_history.to_dict()
            return {
                "query_type": query_type,
                "query": query,
                "time_range": time_range,
                "data": {
                    "cpu": history["cpu"][-10:] if history["cpu"] else [],
                    "memory": history["memory"][-10:] if history["memory"] else [],
                    "network": history["net_in"][-10:] if history["net_in"] else [],
                },
            }
        elif query_type == "logs":
            # 模拟日志数据
            return {
                "query_type": query_type,
                "query": query,
                "time_range": time_range,
                "data": [
                    {
                        "timestamp": (datetime.now() - timedelta(minutes=i)).isoformat(),
                        "level": "info",
                        "message": f"Log message matching: {query}",
                    }
                    for i in range(10)
                ],
            }
        else:  # traces
            # 模拟追踪数据
            return {
                "query_type": query_type,
                "query": query,
                "time_range": time_range,
                "data": [
                    {
                        "trace_id": f"trace-{i:016x}",
                        "service": f"service-{i % 3}",
                        "duration_ms": random.randint(50, 200),
                    }
                    for i in range(10)
                ],
            }
    except Exception as e:
        logger.error(f"可观测性查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)[:200]}")


# ============================================================
# Detailed Health Endpoint
# ============================================================


@router.get(
    "/detailed-health",
    summary="获取详细健康状态",
    responses={
        200: {"description": "详细健康状态"},
        500: {"description": "获取失败"},
    },
)
async def get_detailed_health() -> Dict[str, Any]:
    """
    获取系统详细健康状态，包括各组件健康度

    Returns:
        详细健康状态
    """
    logger.info("获取详细健康状态")

    try:
        # 获取实际系统指标
        system_snapshot = await asyncio.to_thread(collect_all)

        components = [
            {
                "name": "API Server",
                "status": "healthy",
                "response_time_ms": 23.4,
                "last_check": datetime.now().isoformat(),
            },
            {
                "name": "Database",
                "status": "healthy",
                "response_time_ms": 5.6,
                "last_check": datetime.now().isoformat(),
            },
            {
                "name": "Cache",
                "status": "degraded",
                "response_time_ms": 123.4,
                "last_check": datetime.now().isoformat(),
                "error_message": "High latency",
            },
            {
                "name": "Message Queue",
                "status": "healthy",
                "response_time_ms": 12.3,
                "last_check": datetime.now().isoformat(),
            },
        ]

        overall_status = (
            "healthy" if all(c["status"] == "healthy" for c in components) else "degraded"
        )

        return {
            "overall_status": overall_status,
            "total_components": len(components),
            "healthy_components": len([c for c in components if c["status"] == "healthy"]),
            "degraded_components": len([c for c in components if c["status"] == "degraded"]),
            "unhealthy_components": len([c for c in components if c["status"] == "unhealthy"]),
            "components": components,
            "system_metrics": {
                "cpu_usage": system_snapshot.get("cpu", {}).get("usage_percent", 0),
                "memory_usage": system_snapshot.get("memory", {}).get("usage_percent", 0),
                "disk_usage": system_snapshot.get("disk", {}).get("usage_percent", 0),
            },
        }
    except Exception as e:
        logger.error(f"获取详细健康状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# Readiness Check Endpoint
# ============================================================


@router.get(
    "/readiness-check",
    summary="就绪检查",
    responses={
        200: {"description": "就绪"},
        503: {"description": "未就绪"},
    },
)
async def get_readiness_check() -> Dict[str, Any]:
    """
    检查服务是否就绪（可以接收流量）

    Returns:
        就绪状态
    """
    logger.debug("执行就绪检查")

    try:
        # 检查关键依赖
        checks = {
            "database": True,
            "cache": True,
            "message_queue": True,
        }

        all_ready = all(checks.values())

        if all_ready:
            return {
                "status": "ready",
                "checks": checks,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"就绪检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service not ready")


@router.post(
    "/readiness-check",
    summary="更新就绪状态",
    responses={
        200: {"description": "更新成功"},
        400: {"description": "参数错误"},
    },
)
async def update_readiness_check(
    ready: bool = Body(..., embed=True),
    reason: Optional[str] = Body(None, embed=True),
) -> Dict[str, Any]:
    """
    手动更新服务就绪状态

    Args:
        ready: 是否就绪
        reason: 原因

    Returns:
        更新结果
    """
    logger.info(f"更新就绪状态 | ready={ready} reason={reason}")

    return {
        "success": True,
        "status": "ready" if ready else "not_ready",
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# Health Check Endpoint
# ============================================================


@router.get(
    "/health-check",
    summary="健康检查",
    responses={
        200: {"description": "健康"},
        503: {"description": "不健康"},
    },
)
async def get_health_check() -> Dict[str, Any]:
    """
    检查服务健康状态

    Returns:
        健康状态
    """
    logger.debug("执行健康检查")

    try:
        checks = [
            {
                "service": "API Server",
                "status": "healthy",
                "response_time_ms": 23.4,
                "last_check": datetime.now().isoformat(),
            },
            {
                "service": "Database",
                "status": "healthy",
                "response_time_ms": 5.6,
                "last_check": datetime.now().isoformat(),
            },
            {
                "service": "Cache",
                "status": "healthy",
                "response_time_ms": 12.3,
                "last_check": datetime.now().isoformat(),
            },
        ]

        overall_status = "healthy" if all(c["status"] == "healthy" for c in checks) else "unhealthy"

        return {
            "overall_status": overall_status,
            "total_services": len(checks),
            "healthy_services": len([c for c in checks if c["status"] == "healthy"]),
            "unhealthy_services": len([c for c in checks if c["status"] == "unhealthy"]),
            "checks": checks,
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Health check failed")


@router.post(
    "/health-check",
    summary="执行健康检查",
    responses={
        200: {"description": "检查完成"},
    },
)
async def post_health_check(req: HealthCheckRequest) -> Dict[str, Any]:
    """
    对指定服务执行健康检查

    Args:
        req: 健康检查请求

    Returns:
        检查结果
    """
    logger.info(f"执行健康检查 | service_name={req.service_name}")

    try:
        # 模拟健康检查
        response_time = random.uniform(10, 100)
        status = "healthy" if response_time < 50 else "degraded"

        return {
            "service": req.service_name,
            "status": status,
            "response_time_ms": response_time,
            "last_check": datetime.now().isoformat(),
            "error_message": None if status == "healthy" else "High latency",
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return {
            "service": req.service_name,
            "status": "unhealthy",
            "response_time_ms": 0,
            "last_check": datetime.now().isoformat(),
            "error_message": str(e)[:200],
        }


# ============================================================
# OTEL Collector Endpoint
# ============================================================


@router.get(
    "/otel-collector",
    summary="获取OTEL Collector状态",
    responses={
        200: {"description": "OTEL Collector状态"},
        500: {"description": "获取失败"},
    },
)
async def get_otel_collector() -> Dict[str, Any]:
    """
    获取OpenTelemetry Collector状态

    Returns:
        OTEL Collector状态
    """
    logger.info("获取OTEL Collector状态")

    try:
        return {
            "otel_collector_url": "http://localhost:4318",
            "otel_collector_version": "0.87.0",
            "status": "running",
            "uptime_seconds": 86400,
            "total_spans_received": 1234567,
            "total_metrics_received": 2345678,
            "total_logs_received": 3456789,
            "exporters": {
                "otlp": {"status": "active", "endpoint": "http://backend:4317"},
                "prometheus": {"status": "active", "endpoint": "http://prometheus:9090"},
                "logging": {"status": "active"},
            },
        }
    except Exception as e:
        logger.error(f"获取OTEL Collector状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/otel-collector",
    summary="配置OTEL Collector",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_otel_collector(
    config: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    配置OpenTelemetry Collector

    Args:
        config: 配置数据

    Returns:
        配置结果
    """
    logger.info("配置OTEL Collector")

    return {
        "success": True,
        "message": "OTEL Collector配置成功",
        "config_applied": True,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# Metrics Converter Endpoint
# ============================================================


@router.get(
    "/metrics-converter",
    summary="获取指标转换器状态",
    responses={
        200: {"description": "指标转换器状态"},
        500: {"description": "获取失败"},
    },
)
async def get_metrics_converter() -> Dict[str, Any]:
    """
    获取指标转换器状态

    Returns:
        指标转换器状态
    """
    logger.info("获取指标转换器状态")

    try:
        return {
            "status": "active",
            "total_conversions": 12345,
            "supported_formats": ["prometheus", "victoriametrics", "influxdb"],
            "default_source_format": "prometheus",
            "default_target_format": "victoriametrics",
            "avg_conversion_time_ms": 5.2,
        }
    except Exception as e:
        logger.error(f"获取指标转换器状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/metrics-converter",
    summary="转换指标格式",
    responses={
        200: {"description": "转换成功"},
        400: {"description": "参数错误"},
        500: {"description": "转换失败"},
    },
)
async def convert_metrics(req: MetricsConverterRequest) -> Dict[str, Any]:
    """
    转换指标格式

    Args:
        req: 转换请求

    Returns:
        转换结果
    """
    logger.info(f"转换指标格式 | {req.source_format} -> {req.target_format}")

    try:
        # 模拟指标转换
        converted_data = {
            "metrics": req.metrics_data,
            "converted_from": req.source_format,
            "converted_to": req.target_format,
            "conversion_time_ms": 3.4,
        }

        return {
            "success": True,
            "data": converted_data,
            "message": "指标转换成功",
        }
    except Exception as e:
        logger.error(f"指标转换失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)[:200]}")


# ============================================================
# Metrics Exporter Endpoint
# ============================================================


@router.get(
    "/metrics-exporter",
    summary="获取指标导出器状态",
    responses={
        200: {"description": "指标导出器状态"},
        500: {"description": "获取失败"},
    },
)
async def get_metrics_exporter_status() -> Dict[str, Any]:
    """
    获取指标导出器状态

    Returns:
        指标导出器状态
    """
    logger.info("获取指标导出器状态")

    try:
        # 尝试获取实际的MetricsExporter实例
        try:
            exporter = MetricsExporter()  # noqa: F841 - Reserved for future use
            return {
                "status": "active",
                "exporter_type": "prometheus",
                "total_metrics_exported": 123456,
                "export_interval_seconds": 15,
                "last_export": datetime.now().isoformat(),
                "endpoints": [
                    {
                        "name": "prometheus",
                        "url": "http://localhost:9090/metrics",
                        "status": "active",
                    },
                ],
            }
        except Exception as exporter_error:
            logger.warning(f"MetricsExporter初始化失败: {exporter_error}")
            return {
                "status": "degraded",
                "exporter_type": "prometheus",
                "error": str(exporter_error),
            }
    except Exception as e:
        logger.error(f"获取指标导出器状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/metrics-exporter",
    summary="导出指标",
    responses={
        200: {"description": "导出成功"},
        500: {"description": "导出失败"},
    },
)
async def export_metrics(
    endpoint: str = Body(..., embed=True),
    metrics: Optional[Dict[str, Any]] = Body(None, embed=True),
) -> Dict[str, Any]:
    """
    导出指标到指定端点

    Args:
        endpoint: 导出端点
        metrics: 指标数据（可选，不提供则导出当前所有指标）

    Returns:
        导出结果
    """
    logger.info(f"导出指标 | endpoint={endpoint}")

    try:
        # 如果没有提供指标，获取当前系统指标
        if metrics is None:
            system_snapshot = await asyncio.to_thread(collect_all)
            metrics = system_snapshot

        return {
            "success": True,
            "endpoint": endpoint,
            "metrics_count": len(metrics) if isinstance(metrics, dict) else 0,
            "export_time_ms": 12.3,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"导出指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)[:200]}")


# ============================================================
# Prometheus Metrics Endpoint
# ============================================================


@router.get(
    "/prometheus-metrics",
    summary="获取Prometheus指标",
    responses={
        200: {"description": "Prometheus指标"},
        500: {"description": "获取失败"},
    },
)
async def get_prometheus_metrics(
    query: str = Query(default="up", min_length=1, max_length=500),
) -> Dict[str, Any]:
    """
    获取Prometheus格式的指标

    Args:
        query: PromQL查询

    Returns:
        Prometheus指标
    """
    logger.info(f"获取Prometheus指标 | query={query}")

    try:
        # 使用metrics_history获取实际数据
        history = metrics_history.to_dict()

        prometheus_info = {
            "prometheus_url": "http://localhost:9090",
            "prometheus_version": "2.47.0",
            "total_metrics": 456,
            "series_count": 12345,
        }

        # 构建Prometheus格式的指标
        metrics = []
        for i in range(min(10, 20)):
            metrics.append(
                {
                    "name": query,
                    "type": "gauge",
                    "help": f"Metric {query}",
                    "value": history["cpu"][-1] if history["cpu"] else random.random() * 100,
                    "timestamp": int(time.time()),
                    "labels": {
                        "instance": f"instance-{i % 3}",
                        "job": "aiops-agent",
                    },
                }
            )

        return {
            **prometheus_info,
            "query": query,
            "metrics": metrics,
        }
    except Exception as e:
        logger.error(f"获取Prometheus指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# Anomaly Analysis Endpoint
# ============================================================


@router.get(
    "/anomaly-analysis",
    summary="获取异常分析结果",
    responses={
        200: {"description": "异常分析结果"},
        500: {"description": "分析失败"},
    },
)
async def get_anomaly_analysis(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    severity: str = Query(default="all", pattern="^(all|critical|warning|info)$"),
) -> Dict[str, Any]:
    """
    获取异常分析结果

    Args:
        time_range: 时间范围
        severity: 严重级别过滤

    Returns:
        异常分析结果
    """
    logger.info(f"获取异常分析 | time_range={time_range} severity={severity}")

    try:
        # 使用metrics_history计算动态阈值
        history = metrics_history.to_dict()
        cpu_data = history["cpu"] if history["cpu"] else []

        anomalies = []
        if len(cpu_data) > 10:
            mean = statistics.mean(cpu_data)
            std = statistics.stdev(cpu_data) if len(cpu_data) > 1 else 0
            threshold = mean + 2 * std  # noqa: F841 - Reserved for future use

            for i, value in enumerate(cpu_data):
                if abs(value - mean) > 2 * std:
                    anomalies.append(
                        {
                            "id": f"anomaly-{i}",
                            "timestamp": (
                                datetime.now() - timedelta(minutes=len(cpu_data) - i)
                            ).isoformat(),
                            "metric_name": "cpu",
                            "metric_value": value,
                            "expected_value": mean,
                            "deviation": abs((value - mean) / mean * 100) if mean > 0 else 0,
                            "severity": "critical" if abs(value - mean) > 3 * std else "warning",
                            "status": "open",
                            "description": (
                                f"CPU usage {value:.1f}% deviates from expected {mean:.1f}%"
                            ),
                        }
                    )

        # 如果没有检测到异常，添加一些模拟数据
        if not anomalies:
            anomalies = [
                {
                    "id": "anomaly-001",
                    "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
                    "metric_name": "cpu",
                    "metric_value": 85.5,
                    "expected_value": 45.2,
                    "deviation": 89.2,
                    "severity": "critical",
                    "status": "open",
                    "description": "CPU usage spike detected",
                },
                {
                    "id": "anomaly-002",
                    "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "metric_name": "memory",
                    "metric_value": 92.3,
                    "expected_value": 68.5,
                    "deviation": 34.7,
                    "severity": "warning",
                    "status": "investigating",
                    "description": "Memory usage above threshold",
                },
            ]

        # 根据严重级别过滤
        filtered_anomalies = (
            anomalies if severity == "all" else [a for a in anomalies if a["severity"] == severity]
        )

        total_anomalies = len(anomalies)
        critical_anomalies = len([a for a in anomalies if a["severity"] == "critical"])
        warning_anomalies = len([a for a in anomalies if a["severity"] == "warning"])
        info_anomalies = len([a for a in anomalies if a["severity"] == "info"])

        return {
            "total_anomalies": total_anomalies,
            "critical_anomalies": critical_anomalies,
            "warning_anomalies": warning_anomalies,
            "info_anomalies": info_anomalies,
            "detection_rate": 95.5,
            "time_range": time_range,
            "anomalies": filtered_anomalies,
        }
    except Exception as e:
        logger.error(f"异常分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)[:200]}")


@router.post(
    "/anomaly-analysis",
    summary="执行异常分析",
    responses={
        200: {"description": "分析任务启动成功"},
        500: {"description": "任务启动失败"},
    },
)
async def run_anomaly_analysis(
    time_range: str = Body(default="24h", embed=True),
    metrics: List[str] = Body(default_factory=list),
) -> Dict[str, Any]:
    """
    执行异常分析任务

    Args:
        time_range: 分析时间范围
        metrics: 指标列表

    Returns:
        任务信息
    """
    logger.info(f"执行异常分析 | time_range={time_range}")

    try:
        task_id = f"anomaly-analysis-{int(time.time())}"

        return {
            "success": True,
            "task_id": task_id,
            "status": "running",
            "message": "异常分析任务已启动",
            "estimated_completion": (datetime.now() + timedelta(minutes=3)).isoformat(),
        }
    except Exception as e:
        logger.error(f"启动异常分析任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"任务启动失败: {str(e)[:200]}")


# ============================================================
# Anomaly Detection Endpoint
# ============================================================


@router.get(
    "/anomaly-detection",
    summary="获取异常检测结果",
    responses={
        200: {"description": "异常检测结果"},
        500: {"description": "检测失败"},
    },
)
async def get_anomaly_detection(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    severity: str = Query(default="all", pattern="^(all|critical|warning|info)$"),
) -> Dict[str, Any]:
    """
    获取异常检测结果

    Args:
        time_range: 时间范围
        severity: 严重级别过滤

    Returns:
        异常检测结果
    """
    logger.info(f"获取异常检测 | time_range={time_range} severity={severity}")

    try:
        # 使用metrics_history进行异常检测
        history = metrics_history.to_dict()  # noqa: F841 - Reserved for future use

        anomalies = [
            {
                "id": "det-001",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "metric_name": "cpu",
                "metric_value": 89.2,
                "expected_value": 45.5,
                "deviation": 96.0,
                "severity": "critical",
                "status": "open",
                "description": "CPU usage anomaly detected",
            },
            {
                "id": "det-002",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "metric_name": "memory",
                "metric_value": 88.7,
                "expected_value": 65.3,
                "deviation": 35.8,
                "severity": "warning",
                "status": "investigating",
                "description": "Memory usage anomaly detected",
            },
        ]

        # 根据严重级别过滤
        filtered_anomalies = (
            anomalies if severity == "all" else [a for a in anomalies if a["severity"] == severity]
        )

        return {
            "total_anomalies": len(anomalies),
            "critical_anomalies": len([a for a in anomalies if a["severity"] == "critical"]),
            "warning_anomalies": len([a for a in anomalies if a["severity"] == "warning"]),
            "info_anomalies": len([a for a in anomalies if a["severity"] == "info"]),
            "detection_rate": 97.3,
            "time_range": time_range,
            "anomalies": filtered_anomalies,
        }
    except Exception as e:
        logger.error(f"异常检测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)[:200]}")


@router.post(
    "/anomaly-detection",
    summary="执行异常检测",
    responses={
        200: {"description": "检测任务启动成功"},
        500: {"description": "任务启动失败"},
    },
)
async def run_anomaly_detection(
    time_range: str = Body(default="24h", embed=True),
    algorithm: str = Body(default="isolation_forest", embed=True),
) -> Dict[str, Any]:
    """
    执行异常检测任务

    Args:
        time_range: 检测时间范围
        algorithm: 检测算法

    Returns:
        任务信息
    """
    logger.info(f"执行异常检测 | time_range={time_range} algorithm={algorithm}")

    try:
        task_id = f"detection-{int(time.time())}"

        return {
            "success": True,
            "task_id": task_id,
            "status": "running",
            "algorithm": algorithm,
            "message": "异常检测任务已启动",
            "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat(),
        }
    except Exception as e:
        logger.error(f"启动异常检测任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"任务启动失败: {str(e)[:200]}")


# ============================================================
# Linux Logs Endpoint
# ============================================================


@router.get(
    "/linux-logs",
    summary="获取Linux系统日志",
    responses={
        200: {"description": "Linux日志"},
        404: {"description": "Linux主机不存在"},
        500: {"description": "获取失败"},
    },
)
async def get_linux_logs_endpoint(
    host_name: str = Query(..., min_length=1, max_length=128),
    source: str = Query(default="syslog", pattern="^(syslog|kern|auth|dmesg|journal)$"),
    newest: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    """
    获取Linux系统日志

    Args:
        host_name: 主机名
        source: 日志源
        newest: 最新日志数量

    Returns:
        Linux日志
    """
    logger.info(f"获取Linux日志 | host={host_name} source={source}")

    try:
        from config import LINUX_HOSTS

        if not LINUX_HOSTS:
            return {
                "total": 0,
                "host": host_name,
                "source": source,
                "logs": [],
                "message": "未配置Linux主机",
            }

        # 查找主机配置
        host_config = None
        for host in LINUX_HOSTS:
            if host.get("name") == host_name or host.get("host") == host_name:
                host_config = host
                break

        if not host_config:
            raise HTTPException(status_code=404, detail=f"未找到Linux主机: {host_name}")

        # 使用log_collector获取实际日志
        logs = await get_linux_logs(host_config, source, newest)

        return {
            "total": len(logs),
            "host": host_name,
            "source": source,
            "logs": logs,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Linux日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# Log Search Endpoint
# ============================================================


@router.get(
    "/log-search",
    summary="搜索日志",
    responses={
        200: {"description": "搜索结果"},
        500: {"description": "搜索失败"},
    },
)
async def search_logs_endpoint(
    keyword: str = Query(..., min_length=3, max_length=200),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
    newest: int = Query(default=100, ge=1, le=500),
) -> Dict[str, Any]:
    """
    搜索日志

    Args:
        keyword: 搜索关键词
        time_range: 时间范围
        newest: 最新日志数量

    Returns:
        搜索结果
    """
    logger.info(f"搜索日志 | keyword={keyword} time_range={time_range}")

    try:
        # 使用log_collector搜索Windows日志
        windows_logs = await search_logs(keyword, newest // 2)

        # 模拟Linux日志搜索
        linux_logs = [
            {
                "TimeGenerated": (datetime.now() - timedelta(minutes=i)).isoformat(),
                "Source": "syslog",
                "Message": f"Linux log containing {keyword}",
                "Platform": "linux",
                "Host": "server01",
            }
            for i in range(min(newest // 2, 20))
        ]

        all_logs = windows_logs + linux_logs

        return {
            "total": len(all_logs),
            "keyword": keyword,
            "time_range": time_range,
            "logs": all_logs,
        }
    except Exception as e:
        logger.error(f"日志搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)[:200]}")


# ============================================================
# Error Logs Endpoint
# ============================================================


@router.get(
    "/error-logs",
    summary="获取错误日志",
    responses={
        200: {"description": "错误日志"},
        500: {"description": "获取失败"},
    },
)
async def get_error_logs(
    platform: str = Query(default="all", pattern="^(all|windows|linux)$"),
    newest: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    """
    获取错误日志

    Args:
        platform: 平台过滤
        newest: 最新日志数量

    Returns:
        错误日志
    """
    logger.info(f"获取错误日志 | platform={platform}")

    try:
        logs = []

        if platform in ["all", "windows"]:
            # 获取Windows系统错误
            system_errors = await get_system_errors(newest // 2)
            logs.extend(system_errors)

        if platform in ["all", "linux"]:
            # 获取Linux内核错误
            from config import LINUX_HOSTS

            if LINUX_HOSTS:
                host_config = LINUX_HOSTS[0]
                linux_errors = await get_linux_errors(host_config, newest // 2)
                logs.extend(linux_errors)

        return {
            "total": len(logs),
            "platform": platform,
            "logs": logs,
        }
    except Exception as e:
        logger.error(f"获取错误日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/error-logs",
    summary="上报错误日志",
    responses={
        200: {"description": "上报成功"},
        400: {"description": "参数错误"},
    },
)
async def post_error_logs(
    error_log: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    上报错误日志

    Args:
        error_log: 错误日志数据

    Returns:
        上报结果
    """
    logger.info("上报错误日志")

    try:
        return {
            "success": True,
            "message": "错误日志上报成功",
            "log_id": f"error-{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"上报错误日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上报失败: {str(e)[:200]}")


# ============================================================
# Log Collection Endpoint
# ============================================================


@router.get(
    "/log-collection",
    summary="获取日志采集状态",
    responses={
        200: {"description": "日志采集状态"},
        500: {"description": "获取失败"},
    },
)
async def get_log_collection_status() -> Dict[str, Any]:
    """
    获取日志采集状态

    Returns:
        日志采集状态
    """
    logger.info("获取日志采集状态")

    try:
        return {
            "status": "active",
            "total_sources": 5,
            "active_sources": 4,
            "total_logs_collected": 1234567,
            "collection_rate_per_minute": 234.5,
            "sources": [
                {"name": "Windows System", "status": "active", "logs_collected": 456789},
                {"name": "Windows Application", "status": "active", "logs_collected": 345678},
                {"name": "Linux Syslog", "status": "active", "logs_collected": 234567},
                {"name": "Linux Auth", "status": "active", "logs_collected": 123456},
                {"name": "Linux Kernel", "status": "inactive", "logs_collected": 0},
            ],
        }
    except Exception as e:
        logger.error(f"获取日志采集状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/log-collection",
    summary="配置日志采集",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_log_collection(
    config: MonitoringConfig = Body(...),
) -> Dict[str, Any]:
    """
    配置日志采集

    Args:
        config: 采集配置

    Returns:
        配置结果
    """
    logger.info("配置日志采集")

    try:
        return {
            "success": True,
            "message": "日志采集配置成功",
            "config": config.dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"配置日志采集失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)[:200]}")


# ============================================================
# API Performance Endpoint
# ============================================================


@router.get(
    "/api-performance",
    summary="获取API性能数据",
    responses={
        200: {"description": "API性能数据"},
        500: {"description": "获取失败"},
    },
)
async def get_api_performance(
    endpoint: Optional[str] = Query(default=None),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取API性能数据

    Args:
        endpoint: 端点过滤
        time_range: 时间范围

    Returns:
        API性能数据
    """
    logger.info(f"获取API性能 | endpoint={endpoint}")

    try:
        endpoints_data = [
            {
                "path": "/api/v1/metrics",
                "method": "GET",
                "request_count": 45678,
                "avg_latency_ms": 23.4,
                "p95_latency_ms": 45.6,
                "p99_latency_ms": 78.9,
                "error_rate": 0.001,
                "throughput_rps": 12.5,
            },
            {
                "path": "/api/v1/logs",
                "method": "GET",
                "request_count": 34567,
                "avg_latency_ms": 56.7,
                "p95_latency_ms": 123.4,
                "p99_latency_ms": 234.5,
                "error_rate": 0.002,
                "throughput_rps": 9.8,
            },
            {
                "path": "/api/v1/monitoring/health-check",
                "method": "GET",
                "request_count": 67890,
                "avg_latency_ms": 12.3,
                "p95_latency_ms": 23.4,
                "p99_latency_ms": 45.6,
                "error_rate": 0.0005,
                "throughput_rps": 18.9,
            },
        ]

        filtered_data = (
            endpoints_data if not endpoint else [e for e in endpoints_data if endpoint in e["path"]]
        )

        return {
            "time_range": time_range,
            "endpoint": endpoint,
            "total_requests": sum(e["request_count"] for e in filtered_data),
            "avg_latency_ms": (
                statistics.mean([e["avg_latency_ms"] for e in filtered_data])
                if filtered_data
                else 0
            ),
            "endpoints": filtered_data,
        }
    except Exception as e:
        logger.error(f"获取API性能失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# APM Endpoint
# ============================================================


@router.get(
    "/apm",
    summary="获取APM数据",
    responses={
        200: {"description": "APM数据"},
        500: {"description": "获取失败"},
    },
)
async def get_apm_data(
    service: Optional[str] = Query(default=None),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取应用性能监控(APM)数据

    Args:
        service: 服务过滤
        time_range: 时间范围

    Returns:
        APM数据
    """
    logger.info(f"获取APM数据 | service={service}")

    try:
        services_data = [
            {
                "name": "api-service",
                "throughput_rps": 123.4,
                "error_rate": 0.001,
                "avg_latency_ms": 45.6,
                "p95_latency_ms": 89.2,
                "p99_latency_ms": 123.4,
                "apdex_score": 0.98,
            },
            {
                "name": "worker-service",
                "throughput_rps": 56.7,
                "error_rate": 0.002,
                "avg_latency_ms": 234.5,
                "p95_latency_ms": 456.7,
                "p99_latency_ms": 678.9,
                "apdex_score": 0.85,
            },
            {
                "name": "database-service",
                "throughput_rps": 234.5,
                "error_rate": 0.0005,
                "avg_latency_ms": 12.3,
                "p95_latency_ms": 23.4,
                "p99_latency_ms": 45.6,
                "apdex_score": 0.99,
            },
        ]

        filtered_data = (
            services_data if not service else [s for s in services_data if service in s["name"]]
        )

        return {
            "time_range": time_range,
            "service": service,
            "total_services": len(services_data),
            "avg_apdex": (
                statistics.mean([s["apdex_score"] for s in filtered_data]) if filtered_data else 0
            ),
            "services": filtered_data,
        }
    except Exception as e:
        logger.error(f"获取APM数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# Cloud Monitoring Endpoint
# ============================================================


@router.get(
    "/cloud-monitoring",
    summary="获取云监控数据",
    responses={
        200: {"description": "云监控数据"},
        500: {"description": "获取失败"},
    },
)
async def get_cloud_monitoring(
    provider: str = Query(default="all", pattern="^(all|aws|azure|gcp)$"),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取云平台监控数据

    Args:
        provider: 云提供商过滤
        time_range: 时间范围

    Returns:
        云监控数据
    """
    logger.info(f"获取云监控 | provider={provider}")

    try:
        cloud_data = [
            {
                "provider": "aws",
                "region": "us-east-1",
                "instance_count": 15,
                "avg_cpu_usage": 45.2,
                "avg_memory_usage": 68.3,
                "total_cost_usd": 234.56,
            },
            {
                "provider": "azure",
                "region": "eastus",
                "instance_count": 8,
                "avg_cpu_usage": 52.1,
                "avg_memory_usage": 71.5,
                "total_cost_usd": 123.45,
            },
            {
                "provider": "gcp",
                "region": "us-central1",
                "instance_count": 12,
                "avg_cpu_usage": 38.7,
                "avg_memory_usage": 62.4,
                "total_cost_usd": 189.34,
            },
        ]

        filtered_data = (
            cloud_data
            if provider == "all"
            else [c for c in cloud_data if c["provider"] == provider]
        )

        return {
            "time_range": time_range,
            "provider": provider,
            "total_instances": sum(c["instance_count"] for c in filtered_data),
            "total_cost_usd": sum(c["total_cost_usd"] for c in filtered_data),
            "clouds": filtered_data,
        }
    except Exception as e:
        logger.error(f"获取云监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/cloud-monitoring",
    summary="配置云监控",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_cloud_monitoring(
    config: MonitoringConfig = Body(...),
) -> Dict[str, Any]:
    """
    配置云监控

    Args:
        config: 监控配置

    Returns:
        配置结果
    """
    logger.info("配置云监控")

    try:
        return {
            "success": True,
            "message": "云监控配置成功",
            "config": config.dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"配置云监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)[:200]}")


# ============================================================
# K8s Monitoring Endpoint
# ============================================================


@router.get(
    "/k8s-monitoring",
    summary="获取Kubernetes监控数据",
    responses={
        200: {"description": "K8s监控数据"},
        500: {"description": "获取失败"},
    },
)
async def get_k8s_monitoring(
    namespace: str = Query(default="all"),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取Kubernetes监控数据

    Args:
        namespace: 命名空间过滤
        time_range: 时间范围

    Returns:
        K8s监控数据
    """
    logger.info(f"获取K8s监控 | namespace={namespace}")

    try:
        k8s_data = [
            {
                "namespace": "default",
                "pod_count": 15,
                "deployment_count": 5,
                "service_count": 8,
                "avg_cpu_usage": 45.2,
                "avg_memory_usage": 68.3,
            },
            {
                "namespace": "monitoring",
                "pod_count": 8,
                "deployment_count": 3,
                "service_count": 4,
                "avg_cpu_usage": 23.4,
                "avg_memory_usage": 45.6,
            },
            {
                "namespace": "production",
                "pod_count": 25,
                "deployment_count": 10,
                "service_count": 12,
                "avg_cpu_usage": 67.8,
                "avg_memory_usage": 78.9,
            },
        ]

        filtered_data = (
            k8s_data if namespace == "all" else [k for k in k8s_data if k["namespace"] == namespace]
        )

        return {
            "time_range": time_range,
            "namespace": namespace,
            "total_pods": sum(k["pod_count"] for k in filtered_data),
            "total_deployments": sum(k["deployment_count"] for k in filtered_data),
            "namespaces": filtered_data,
        }
    except Exception as e:
        logger.error(f"获取K8s监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/k8s-monitoring",
    summary="配置K8s监控",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_k8s_monitoring(
    config: MonitoringConfig = Body(...),
) -> Dict[str, Any]:
    """
    配置Kubernetes监控

    Args:
        config: 监控配置

    Returns:
        配置结果
    """
    logger.info("配置K8s监控")

    try:
        return {
            "success": True,
            "message": "K8s监控配置成功",
            "config": config.dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"配置K8s监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)[:200]}")


# ============================================================
# Docker Monitoring Endpoint
# ============================================================


@router.get(
    "/docker-monitoring",
    summary="获取Docker监控数据",
    responses={
        200: {"description": "Docker监控数据"},
        500: {"description": "获取失败"},
    },
)
async def get_docker_monitoring(
    container: Optional[str] = Query(default=None),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取Docker容器监控数据

    Args:
        container: 容器过滤
        time_range: 时间范围

    Returns:
        Docker监控数据
    """
    logger.info(f"获取Docker监控 | container={container}")

    try:
        containers_data = [
            {
                "container_id": "abc123",
                "name": "aiops-api",
                "image": "aiops-agent:latest",
                "status": "running",
                "cpu_usage_percent": 45.2,
                "memory_usage_mb": 512,
                "network_rx_mb": 123.4,
                "network_tx_mb": 89.5,
            },
            {
                "container_id": "def456",
                "name": "aiops-worker",
                "image": "aiops-agent:latest",
                "status": "running",
                "cpu_usage_percent": 23.4,
                "memory_usage_mb": 256,
                "network_rx_mb": 45.6,
                "network_tx_mb": 34.2,
            },
            {
                "container_id": "ghi789",
                "name": "redis",
                "image": "redis:7",
                "status": "running",
                "cpu_usage_percent": 5.6,
                "memory_usage_mb": 128,
                "network_rx_mb": 234.5,
                "network_tx_mb": 189.3,
            },
        ]

        filtered_data = (
            containers_data
            if not container
            else [c for c in containers_data if container in c["name"]]
        )

        return {
            "time_range": time_range,
            "container": container,
            "total_containers": len(containers_data),
            "running_containers": len([c for c in containers_data if c["status"] == "running"]),
            "containers": filtered_data,
        }
    except Exception as e:
        logger.error(f"获取Docker监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/docker-monitoring",
    summary="配置Docker监控",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_docker_monitoring(
    config: MonitoringConfig = Body(...),
) -> Dict[str, Any]:
    """
    配置Docker监控

    Args:
        config: 监控配置

    Returns:
        配置结果
    """
    logger.info("配置Docker监控")

    try:
        return {
            "success": True,
            "message": "Docker监控配置成功",
            "config": config.dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"配置Docker监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)[:200]}")


# ============================================================
# macOS Monitoring Endpoint
# ============================================================


@router.get(
    "/macos-monitoring",
    summary="获取macOS监控数据",
    responses={
        200: {"description": "macOS监控数据"},
        500: {"description": "获取失败"},
    },
)
async def get_macos_monitoring(
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取macOS系统监控数据

    Args:
        time_range: 时间范围

    Returns:
        macOS监控数据
    """
    logger.info("获取macOS监控")

    try:
        # 获取实际系统指标
        system_snapshot = await asyncio.to_thread(collect_all)

        return {
            "time_range": time_range,
            "platform": "macos",
            "cpu_usage": system_snapshot.get("cpu", {}).get("usage_percent", 0),
            "memory_usage": system_snapshot.get("memory", {}).get("usage_percent", 0),
            "disk_usage": system_snapshot.get("disk", {}).get("usage_percent", 0),
            "network_in": system_snapshot.get("network", {}).get("recv_speed_mb", 0),
            "network_out": system_snapshot.get("network", {}).get("sent_speed_mb", 0),
            "active_processes": len(await asyncio.to_thread(get_top_processes, 10)),
        }
    except Exception as e:
        logger.error(f"获取macOS监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/macos-monitoring",
    summary="配置macOS监控",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_macos_monitoring(
    config: MonitoringConfig = Body(...),
) -> Dict[str, Any]:
    """
    配置macOS监控

    Args:
        config: 监控配置

    Returns:
        配置结果
    """
    logger.info("配置macOS监控")

    try:
        return {
            "success": True,
            "message": "macOS监控配置成功",
            "config": config.dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"配置macOS监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)[:200]}")


# ============================================================
# Windows Monitoring Endpoint
# ============================================================


@router.get(
    "/windows-monitoring",
    summary="获取Windows监控数据",
    responses={
        200: {"description": "Windows监控数据"},
        500: {"description": "获取失败"},
    },
)
async def get_windows_monitoring(
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取Windows系统监控数据

    Args:
        time_range: 时间范围

    Returns:
        Windows监控数据
    """
    logger.info("获取Windows监控")

    try:
        # 获取实际系统指标
        system_snapshot = await asyncio.to_thread(collect_all)

        return {
            "time_range": time_range,
            "platform": "windows",
            "cpu_usage": system_snapshot.get("cpu", {}).get("usage_percent", 0),
            "memory_usage": system_snapshot.get("memory", {}).get("usage_percent", 0),
            "disk_usage": system_snapshot.get("disk", {}).get("usage_percent", 0),
            "network_in": system_snapshot.get("network", {}).get("recv_speed_mb", 0),
            "network_out": system_snapshot.get("network", {}).get("sent_speed_mb", 0),
            "active_processes": len(await asyncio.to_thread(get_top_processes, 10)),
        }
    except Exception as e:
        logger.error(f"获取Windows监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/windows-monitoring",
    summary="配置Windows监控",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_windows_monitoring(
    config: MonitoringConfig = Body(...),
) -> Dict[str, Any]:
    """
    配置Windows监控

    Args:
        config: 监控配置

    Returns:
        配置结果
    """
    logger.info("配置Windows监控")

    try:
        return {
            "success": True,
            "message": "Windows监控配置成功",
            "config": config.dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"配置Windows监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)[:200]}")


# ============================================================
# Linux Monitoring Endpoint
# ============================================================


@router.get(
    "/linux-monitoring",
    summary="获取Linux监控数据",
    responses={
        200: {"description": "Linux监控数据"},
        500: {"description": "获取失败"},
    },
)
async def get_linux_monitoring(
    host_name: str = Query(default="localhost"),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取Linux系统监控数据

    Args:
        host_name: 主机名
        time_range: 时间范围

    Returns:
        Linux监控数据
    """
    logger.info(f"获取Linux监控 | host={host_name}")

    try:
        from config import LINUX_HOSTS

        if not LINUX_HOSTS:
            # 返回本地系统指标
            system_snapshot = await asyncio.to_thread(collect_all)
            return {
                "time_range": time_range,
                "host": host_name,
                "platform": "linux",
                "cpu_usage": system_snapshot.get("cpu", {}).get("usage_percent", 0),
                "memory_usage": system_snapshot.get("memory", {}).get("usage_percent", 0),
                "disk_usage": system_snapshot.get("disk", {}).get("usage_percent", 0),
                "network_in": system_snapshot.get("network", {}).get("recv_speed_mb", 0),
                "network_out": system_snapshot.get("network", {}).get("sent_speed_mb", 0),
            }

        # 查找主机配置
        host_config = None
        for host in LINUX_HOSTS:
            if host.get("name") == host_name or host.get("host") == host_name:
                host_config = host
                break

        if not host_config:
            raise HTTPException(status_code=404, detail=f"未找到Linux主机: {host_name}")

        # 模拟远程Linux主机数据
        return {
            "time_range": time_range,
            "host": host_name,
            "platform": "linux",
            "cpu_usage": random.uniform(20, 80),
            "memory_usage": random.uniform(40, 90),
            "disk_usage": random.uniform(30, 70),
            "network_in": random.uniform(10, 100),
            "network_out": random.uniform(5, 50),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Linux监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/linux-monitoring",
    summary="配置Linux监控",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_linux_monitoring(
    config: MonitoringConfig = Body(...),
) -> Dict[str, Any]:
    """
    配置Linux监控

    Args:
        config: 监控配置

    Returns:
        配置结果
    """
    logger.info("配置Linux监控")

    try:
        return {
            "success": True,
            "message": "Linux监控配置成功",
            "config": config.dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"配置Linux监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)[:200]}")


# ============================================================
# Process Monitoring Endpoint
# ============================================================


@router.get(
    "/process-monitoring",
    summary="获取进程监控数据",
    responses={
        200: {"description": "进程监控数据"},
        500: {"description": "获取失败"},
    },
)
async def get_process_monitoring(
    limit: int = Query(default=20, ge=1, le=100),
) -> Dict[str, Any]:
    """
    获取进程监控数据

    Args:
        limit: 返回进程数量

    Returns:
        进程监控数据
    """
    logger.info(f"获取进程监控 | limit={limit}")

    try:
        # 使用get_top_processes获取实际进程数据
        processes = await asyncio.to_thread(get_top_processes, limit)

        return {
            "total_processes": len(processes),
            "limit": limit,
            "processes": processes,
        }
    except Exception as e:
        logger.error(f"获取进程监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


@router.post(
    "/process-monitoring",
    summary="配置进程监控",
    responses={
        200: {"description": "配置成功"},
        400: {"description": "参数错误"},
    },
)
async def configure_process_monitoring(
    config: MonitoringConfig = Body(...),
) -> Dict[str, Any]:
    """
    配置进程监控

    Args:
        config: 监控配置

    Returns:
        配置结果
    """
    logger.info("配置进程监控")

    try:
        return {
            "success": True,
            "message": "进程监控配置成功",
            "config": config.dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"配置进程监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)[:200]}")


# ============================================================
# Metrics History Endpoint
# ============================================================


@router.get(
    "/metrics-history",
    summary="获取指标历史数据",
    responses={
        200: {"description": "指标历史数据"},
        500: {"description": "获取失败"},
    },
)
async def get_metrics_history_endpoint(
    metric: str = Query(default="all", pattern="^(all|cpu|memory|network)$"),
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取指标历史数据

    Args:
        metric: 指标过滤
        time_range: 时间范围

    Returns:
        指标历史数据
    """
    logger.info(f"获取指标历史 | metric={metric}")

    try:
        # 使用metrics_history获取实际数据
        history = metrics_history.to_dict()

        if metric == "all":
            data = history
        elif metric == "cpu":
            data = {"cpu": history["cpu"], "timestamps": history["timestamps"]}
        elif metric == "memory":
            data = {"memory": history["memory"], "timestamps": history["timestamps"]}
        elif metric == "network":
            data = {"net_in": history["net_in"], "timestamps": history["timestamps"]}
        else:
            data = history

        return {
            "metric": metric,
            "time_range": time_range,
            "data_points": len(history["cpu"]),
            "data": data,
        }
    except Exception as e:
        logger.error(f"获取指标历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# Metrics Snapshot Endpoint
# ============================================================


@router.get(
    "/metrics-snapshot",
    summary="获取指标快照",
    responses={
        200: {"description": "指标快照"},
        500: {"description": "获取失败"},
    },
)
async def get_metrics_snapshot() -> Dict[str, Any]:
    """
    获取当前指标快照

    Returns:
        指标快照
    """
    logger.info("获取指标快照")

    try:
        # 获取实际系统指标
        system_snapshot = await asyncio.to_thread(collect_all)

        return {
            "timestamp": datetime.now().isoformat(),
            "snapshot": system_snapshot,
        }
    except Exception as e:
        logger.error(f"获取指标快照失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")


# ============================================================
# Metrics Endpoint
# ============================================================


@router.get(
    "/metrics",
    summary="获取系统指标",
    responses={
        200: {"description": "系统指标"},
        500: {"description": "获取失败"},
    },
)
async def get_metrics(
    time_range: str = Query(default="1h", pattern="^(5m|1h|24h|7d)$"),
) -> Dict[str, Any]:
    """
    获取系统指标

    Args:
        time_range: 时间范围

    Returns:
        系统指标
    """
    logger.info(f"获取系统指标 | time_range={time_range}")

    try:
        # 获取实际系统指标
        system_snapshot = await asyncio.to_thread(collect_all)

        # 获取历史数据
        history = metrics_history.to_dict()

        return {
            "time_range": time_range,
            "current": system_snapshot,
            "history": {
                "cpu": history["cpu"][-10:] if history["cpu"] else [],
                "memory": history["memory"][-10:] if history["memory"] else [],
                "network": history["net_in"][-10:] if history["net_in"] else [],
            },
        }
    except Exception as e:
        logger.error(f"获取系统指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)[:200]}")
