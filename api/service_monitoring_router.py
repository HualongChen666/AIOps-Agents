# -*- coding: utf-8 -*-
"""
Service Monitoring API Router
Provides API endpoints for service monitoring and alerting
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

router = APIRouter(prefix="/api/service-monitoring", tags=["Service Monitoring"])


@router.get(
    "/status",
    summary="获取服务监控状态",
    responses={
        200: {
            "description": "服务监控状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"monitored_services": 10, "active_alerts": 2},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_monitoring_status():
    """
    Get service monitoring status

    Returns:
        Service monitoring status
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()
        status = manager.get_monitoring_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/metric",
    summary="记录服务指标",
    responses={
        200: {
            "description": "记录结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Metric cpu_usage recorded for api-service",
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "记录失败"},
    },
)
async def record_metric(
    metric_name: str, service_name: str, value: float, metric_type: str = "gauge"
):
    """
    Record service metric

    Args:
        metric_name: Metric name
        service_name: Service name
        value: Metric value
        metric_type: Metric type

    Returns:
        Recording result
    """
    try:
        from core.service_monitoring_manager import MetricType, get_service_monitoring_manager

        manager = get_service_monitoring_manager()

        metric_type_enum = MetricType(metric_type)
        manager.record_metric(
            metric_name=metric_name,
            service_name=service_name,
            value=value,
            metric_type=metric_type_enum,
        )

        return {
            "status": "success",
            "message": f"Metric {metric_name} recorded for {service_name}",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error recording metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/metrics/{service_name}",
    summary="获取服务指标",
    responses={
        200: {
            "description": "服务指标",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "service_name": "api-service",
                            "metrics": [{"name": "cpu_usage", "value": 75.5}],
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_service_metrics(
    service_name: str,
    time_range_hours: int = Query(1, ge=1, le=24, description="Time range in hours"),
):
    """
    Get service metrics

    Args:
        service_name: Service name
        time_range_hours: Time range in hours

    Returns:
        Service metrics
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()

        time_range = timedelta(hours=time_range_hours)
        metrics = manager.get_service_metrics(service_name, time_range)

        return {
            "status": "success",
            "data": {
                "service_name": service_name,
                "time_range_hours": time_range_hours,
                "metrics": [
                    {
                        "metric_name": m.metric_name,
                        "value": m.value,
                        "timestamp": m.timestamp.isoformat(),
                        "labels": m.labels,
                    }
                    for m in metrics
                ],
                "count": len(metrics),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting service metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/analysis/{service_name}",
    summary="分析服务性能",
    responses={
        200: {
            "description": "性能分析结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "service_name": "api-service",
                            "avg_response_time": 150,
                            "error_rate": 0.02,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "分析失败"},
    },
)
async def analyze_service_performance(
    service_name: str,
    time_range_hours: int = Query(1, ge=1, le=24, description="Time range in hours"),
):
    """
    Analyze service performance

    Args:
        service_name: Service name
        time_range_hours: Time range in hours

    Returns:
        Performance analysis
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()

        time_range = timedelta(hours=time_range_hours)
        analysis = manager.analyze_service_performance(service_name, time_range)

        return {"status": "success", "data": analysis, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error analyzing service performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/anomaly/detect",
    summary="检测异常",
    responses={
        200: {
            "description": "异常检测结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"is_anomaly": True, "anomaly_score": 0.95, "threshold": 0.8},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "检测失败"},
    },
)
async def detect_anomaly(metric_name: str, service_name: str, current_value: float):
    """
    Detect anomaly in metric

    Args:
        metric_name: Metric name
        service_name: Service name
        current_value: Current metric value

    Returns:
        Anomaly detection result
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()

        detection = manager.detect_anomaly(
            metric_name=metric_name, service_name=service_name, current_value=current_value
        )

        return {
            "status": "success",
            "data": {
                "service_name": detection.service_name,
                "metric_name": detection.metric_name,
                "is_anomaly": detection.is_anomaly,
                "anomaly_score": detection.anomaly_score,
                "expected_value": detection.expected_value,
                "actual_value": detection.actual_value,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error detecting anomaly: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alert-rule",
    summary="创建告警规则",
    responses={
        200: {
            "description": "创建结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Alert rule rule-123 created",
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "创建失败"},
    },
)
async def create_alert_rule(
    rule_id: str,
    service_name: str,
    metric_name: str,
    threshold: float,
    comparison: str = "greater_than",
    severity: str = "warning",
):
    """
    Create alert rule

    Args:
        rule_id: Rule ID
        service_name: Service name
        metric_name: Metric name
        threshold: Threshold value
        comparison: Comparison operator
        severity: Alert severity

    Returns:
        Alert rule creation result
    """
    try:
        from core.service_monitoring_manager import AlertSeverity, get_service_monitoring_manager

        manager = get_service_monitoring_manager()

        severity_enum = AlertSeverity(severity)
        manager.create_alert_rule(
            rule_id=rule_id,
            service_name=service_name,
            metric_name=metric_name,
            threshold=threshold,
            comparison=comparison,
            severity=severity_enum,
        )

        return {
            "status": "success",
            "message": f"Alert rule {rule_id} created",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating alert rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alert/check",
    summary="检查告警规则",
    responses={
        200: {
            "description": "告警检查结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"triggered_alerts": 2, "total_rules": 10},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "检查失败"},
    },
)
async def check_alert_rules():
    """
    Check alert rules and generate alerts

    Returns:
        Generated alerts
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()

        alerts = manager.check_alert_rules()

        return {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "alert_id": alert.alert_id,
                        "service_name": alert.service_name,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "metric_name": alert.metric_name,
                        "threshold": alert.threshold,
                        "current_value": alert.current_value,
                        "timestamp": alert.timestamp.isoformat(),
                    }
                    for alert in alerts
                ],
                "count": len(alerts),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error checking alert rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))
