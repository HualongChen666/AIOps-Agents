# -*- coding: utf-8 -*-
"""
Service Monitoring Advanced API Router
Provides advanced API endpoints for service monitoring with full CRUD operations
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/service-monitoring", tags=["Service Monitoring Advanced"])


# Pydantic Models
class AlertCreate(BaseModel):
    """Alert creation model"""

    name: str = Field(..., description="Alert name")
    service_name: str = Field(..., description="Service name")
    metric_name: str = Field(..., description="Metric name")
    condition: str = Field(..., description="Alert condition (greater_than, less_than, equals)")
    threshold: float = Field(..., description="Threshold value")
    severity: str = Field(
        default="warning", description="Alert severity (info, warning, error, critical)"
    )
    description: Optional[str] = Field(None, description="Alert description")
    enabled: bool = Field(default=True, description="Alert enabled status")
    notification_channels: List[str] = Field(
        default_factory=list, description="Notification channels"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Alert metadata")


class AlertUpdate(BaseModel):
    """Alert update model"""

    name: Optional[str] = Field(None, description="Alert name")
    condition: Optional[str] = Field(None, description="Alert condition")
    threshold: Optional[float] = Field(None, description="Threshold value")
    severity: Optional[str] = Field(None, description="Alert severity")
    description: Optional[str] = Field(None, description="Alert description")
    enabled: Optional[bool] = Field(None, description="Alert enabled status")
    notification_channels: Optional[List[str]] = Field(None, description="Notification channels")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Alert metadata")


class DashboardCreate(BaseModel):
    """Dashboard creation model"""

    name: str = Field(..., description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    widgets: List[Dict[str, Any]] = Field(..., description="Dashboard widgets")
    refresh_interval_seconds: int = Field(default=30, ge=5, description="Refresh interval")
    is_public: bool = Field(default=False, description="Public dashboard")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dashboard metadata")


class DashboardUpdate(BaseModel):
    """Dashboard update model"""

    name: Optional[str] = Field(None, description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    widgets: Optional[List[Dict[str, Any]]] = Field(None, description="Dashboard widgets")
    refresh_interval_seconds: Optional[int] = Field(None, ge=5, description="Refresh interval")
    is_public: Optional[bool] = Field(None, description="Public dashboard")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Dashboard metadata")


# In-memory storage (in production, use a database)
_alerts_db: Dict[str, Dict[str, Any]] = {}
_dashboards_db: Dict[str, Dict[str, Any]] = {}
_alert_history_db: Dict[str, List[Dict[str, Any]]] = {}


def _generate_alert_id() -> str:
    """Generate unique alert ID"""
    return str(uuid4())


def _generate_dashboard_id() -> str:
    """Generate unique dashboard ID"""
    return str(uuid4())


@router.get(
    "/services",
    summary="List all monitored services",
    responses={
        200: {"description": "List of monitored services"},
        500: {"description": "Internal server error"},
    },
)
async def list_monitored_services(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all monitored services with optional filtering

    Args:
        status: Filter by service status
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of monitored services
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()
        summary = manager.get_monitoring_summary()

        services = []
        for service_name in summary.get("services", []):
            service_data = {
                "name": service_name,
                "status": "active",
                "metrics_count": manager.service_metrics.get(service_name, {}).get(
                    "total_metrics", 0
                ),
                "last_updated": manager.service_metrics.get(service_name, {}).get("last_updated"),
            }

            if status and service_data["status"] != status:
                continue

            services.append(service_data)

        # Apply pagination
        total = len(services)
        paginated_services = services[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "services": paginated_services,
                "total": total,
                "limit": limit,
                "offset": offset,
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing monitored services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/metrics",
    summary="Get service metrics",
    responses={
        200: {"description": "Service metrics"},
        500: {"description": "Internal server error"},
    },
)
async def get_metrics(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    time_range_hours: int = Query(1, ge=1, le=168, description="Time range in hours"),
    aggregation: str = Query("raw", description="Aggregation type (raw, avg, min, max, sum)"),
):
    """
    Get service metrics with optional filtering and aggregation

    Args:
        service_name: Filter by service name
        metric_name: Filter by metric name
        time_range_hours: Time range in hours
        aggregation: Aggregation type

    Returns:
        Service metrics
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()

        time_range = timedelta(hours=time_range_hours)
        all_metrics = []

        if service_name:
            metrics = manager.get_service_metrics(service_name, time_range)
            if metric_name:
                metrics = [m for m in metrics if m.metric_name == metric_name]
            all_metrics.extend(metrics)
        else:
            # Get metrics for all services
            for svc_name in manager.service_metrics.keys():
                metrics = manager.get_service_metrics(svc_name, time_range)
                if metric_name:
                    metrics = [m for m in metrics if m.metric_name == metric_name]
                all_metrics.extend(metrics)

        # Apply aggregation
        if aggregation == "avg":
            metric_values = [m.value for m in all_metrics]
            aggregated_value = sum(metric_values) / len(metric_values) if metric_values else 0
            metrics_data = [{"aggregation": "avg", "value": aggregated_value}]
        elif aggregation == "min":
            metric_values = [m.value for m in all_metrics]
            aggregated_value = min(metric_values) if metric_values else 0
            metrics_data = [{"aggregation": "min", "value": aggregated_value}]
        elif aggregation == "max":
            metric_values = [m.value for m in all_metrics]
            aggregated_value = max(metric_values) if metric_values else 0
            metrics_data = [{"aggregation": "max", "value": aggregated_value}]
        elif aggregation == "sum":
            metric_values = [m.value for m in all_metrics]
            aggregated_value = sum(metric_values)
            metrics_data = [{"aggregation": "sum", "value": aggregated_value}]
        else:
            metrics_data = [
                {
                    "metric_name": m.metric_name,
                    "service_name": m.service_name,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat(),
                    "labels": m.labels,
                }
                for m in all_metrics
            ]

        return {
            "status": "success",
            "data": {
                "metrics": metrics_data,
                "count": len(metrics_data),
                "time_range_hours": time_range_hours,
                "aggregation": aggregation,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    summary="Get service health status",
    responses={
        200: {"description": "Service health status"},
        500: {"description": "Internal server error"},
    },
)
async def get_health_status(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    include_details: bool = Query(False, description="Include detailed health information"),
):
    """
    Get service health status

    Args:
        service_name: Filter by service name
        include_details: Include detailed health information

    Returns:
        Service health status
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()
        summary = manager.get_monitoring_summary()

        services_to_check = [service_name] if service_name else summary.get("services", [])

        health_data = []
        for svc_name in services_to_check:
            # Get recent metrics for health assessment
            time_range = timedelta(minutes=5)
            metrics = manager.get_service_metrics(svc_name, time_range)

            # Calculate health score based on metrics
            error_count = len([m for m in metrics if m.metric_name == "error_count"])
            total_requests = len([m for m in metrics if m.metric_name == "request_count"])
            latency_values = [m.value for m in metrics if m.metric_name == "latency_ms"]

            error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
            avg_latency = (sum(latency_values) / len(latency_values)) if latency_values else 0

            # Determine health status
            if error_rate > 5 or avg_latency > 1000:
                health_status = "unhealthy"
            elif error_rate > 1 or avg_latency > 500:
                health_status = "degraded"
            else:
                health_status = "healthy"

            health_info = {
                "service_name": svc_name,
                "health_status": health_status,
                "error_rate": round(error_rate, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "total_requests": total_requests,
            }

            if include_details:
                health_info["details"] = {
                    "metrics_count": len(metrics),
                    "last_updated": datetime.utcnow().isoformat(),
                    "recent_errors": error_count,
                }

            health_data.append(health_info)

        return {
            "status": "success",
            "data": {
                "health_status": health_data,
                "total": len(health_data),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sla",
    summary="Get service SLA metrics",
    responses={
        200: {"description": "SLA metrics"},
        500: {"description": "Internal server error"},
    },
)
async def get_sla_metrics(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    time_range_hours: int = Query(24, ge=1, le=720, description="Time range in hours"),
):
    """
    Get service SLA metrics

    Args:
        service_name: Filter by service name
        time_range_hours: Time range in hours

    Returns:
        SLA metrics
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()
        summary = manager.get_monitoring_summary()

        time_range = timedelta(hours=time_range_hours)

        sla_data = []
        services_to_check = [service_name] if service_name else summary.get("services", [])

        for svc_name in services_to_check:
            metrics = manager.get_service_metrics(svc_name, time_range)

            # Calculate SLA metrics
            total_requests = len([m for m in metrics if m.metric_name == "request_count"])
            error_count = len([m for m in metrics if m.metric_name == "error_count"])
            total_latency = sum([m.value for m in metrics if m.metric_name == "latency_ms"])
            latency_count = len([m for m in metrics if m.metric_name == "latency_ms"])

            availability = (
                ((total_requests - error_count) / total_requests * 100)
                if total_requests > 0
                else 100.0
            )
            avg_latency = (total_latency / latency_count) if latency_count > 0 else 0

            sla_data.append(
                {
                    "service_name": svc_name,
                    "availability_percentage": round(availability, 2),
                    "avg_latency_ms": round(avg_latency, 2),
                    "total_requests": total_requests,
                    "error_count": error_count,
                    "error_rate": round(
                        (error_count / total_requests * 100) if total_requests > 0 else 0, 2
                    ),
                    "time_range_hours": time_range_hours,
                }
            )

        return {
            "status": "success",
            "data": {
                "sla_metrics": sla_data,
                "total": len(sla_data),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting SLA metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/alerts",
    summary="List all alerts",
    responses={
        200: {"description": "List of alerts"},
        500: {"description": "Internal server error"},
    },
)
async def list_alerts(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(
        None, description="Filter by status (active, resolved, acknowledged)"
    ),
    enabled_only: bool = Query(False, description="Only return enabled alerts"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all alerts with optional filtering

    Args:
        service_name: Filter by service name
        severity: Filter by severity
        status: Filter by status
        enabled_only: Only return enabled alerts
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of alerts
    """
    try:
        filtered_alerts = []
        for alert_id, alert in _alerts_db.items():
            if service_name and alert.get("service_name") != service_name:
                continue
            if severity and alert.get("severity") != severity:
                continue
            if status and alert.get("status") != status:
                continue
            if enabled_only and not alert.get("enabled", True):
                continue
            filtered_alerts.append({"id": alert_id, **alert})

        # Apply pagination
        total = len(filtered_alerts)
        paginated_alerts = filtered_alerts[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "alerts": paginated_alerts,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alerts",
    summary="Create an alert",
    responses={
        201: {"description": "Alert created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_alert(alert: AlertCreate):
    """
    Create a new alert

    Args:
        alert: Alert creation data

    Returns:
        Created alert
    """
    try:
        from core.service_monitoring_manager import (
            AlertSeverity,
            get_service_monitoring_manager,
        )

        alert_id = _generate_alert_id()
        rule_id = f"rule-{alert_id[:8]}"

        # Create alert in database
        _alerts_db[alert_id] = {
            "name": alert.name,
            "service_name": alert.service_name,
            "metric_name": alert.metric_name,
            "condition": alert.condition,
            "threshold": alert.threshold,
            "severity": alert.severity,
            "description": alert.description,
            "enabled": alert.enabled,
            "notification_channels": alert.notification_channels,
            "metadata": alert.metadata,
            "status": "active",
            "triggered_count": 0,
            "last_triggered": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Create alert rule in monitoring manager
        manager = get_service_monitoring_manager()
        severity_enum = AlertSeverity(alert.severity)
        manager.create_alert_rule(
            rule_id=rule_id,
            service_name=alert.service_name,
            metric_name=alert.metric_name,
            threshold=alert.threshold,
            comparison=alert.condition,
            severity=severity_enum,
        )

        logger.info(f"Created alert: {alert.name} with ID: {alert_id}")

        return {
            "status": "success",
            "data": {"id": alert_id, "rule_id": rule_id, **_alerts_db[alert_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/dashboards",
    summary="List all dashboards",
    responses={
        200: {"description": "List of dashboards"},
        500: {"description": "Internal server error"},
    },
)
async def list_dashboards(
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all dashboards with optional filtering

    Args:
        is_public: Filter by public status
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of dashboards
    """
    try:
        filtered_dashboards = []
        for dashboard_id, dashboard in _dashboards_db.items():
            if is_public is not None and dashboard.get("is_public") != is_public:
                continue
            filtered_dashboards.append({"id": dashboard_id, **dashboard})

        # Apply pagination
        total = len(filtered_dashboards)
        paginated_dashboards = filtered_dashboards[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "dashboards": paginated_dashboards,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing dashboards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/dashboards",
    summary="Create a dashboard",
    responses={
        201: {"description": "Dashboard created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_dashboard(dashboard: DashboardCreate):
    """
    Create a new dashboard

    Args:
        dashboard: Dashboard creation data

    Returns:
        Created dashboard
    """
    try:
        dashboard_id = _generate_dashboard_id()

        # Create dashboard in database
        _dashboards_db[dashboard_id] = {
            "name": dashboard.name,
            "description": dashboard.description,
            "widgets": dashboard.widgets,
            "refresh_interval_seconds": dashboard.refresh_interval_seconds,
            "is_public": dashboard.is_public,
            "metadata": dashboard.metadata,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Created dashboard: {dashboard.name} with ID: {dashboard_id}")

        return {
            "status": "success",
            "data": {"id": dashboard_id, **_dashboards_db[dashboard_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/dashboards/{dashboard_id}",
    summary="Get dashboard by ID",
    responses={
        200: {"description": "Dashboard details"},
        404: {"description": "Dashboard not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_dashboard(dashboard_id: str):
    """
    Get dashboard details by ID

    Args:
        dashboard_id: Dashboard ID

    Returns:
        Dashboard details
    """
    try:
        if dashboard_id not in _dashboards_db:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")

        dashboard = _dashboards_db[dashboard_id]

        return {
            "status": "success",
            "data": {"id": dashboard_id, **dashboard},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/dashboards/{dashboard_id}",
    summary="Update dashboard",
    responses={
        200: {"description": "Dashboard updated successfully"},
        404: {"description": "Dashboard not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_dashboard(dashboard_id: str, dashboard_update: DashboardUpdate):
    """
    Update dashboard details

    Args:
        dashboard_id: Dashboard ID
        dashboard_update: Dashboard update data

    Returns:
        Updated dashboard
    """
    try:
        if dashboard_id not in _dashboards_db:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")

        dashboard = _dashboards_db[dashboard_id]

        # Update fields
        if dashboard_update.name is not None:
            dashboard["name"] = dashboard_update.name
        if dashboard_update.description is not None:
            dashboard["description"] = dashboard_update.description
        if dashboard_update.widgets is not None:
            dashboard["widgets"] = dashboard_update.widgets
        if dashboard_update.refresh_interval_seconds is not None:
            dashboard["refresh_interval_seconds"] = dashboard_update.refresh_interval_seconds
        if dashboard_update.is_public is not None:
            dashboard["is_public"] = dashboard_update.is_public
        if dashboard_update.metadata is not None:
            dashboard["metadata"] = dashboard_update.metadata

        dashboard["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Updated dashboard: {dashboard_id}")

        return {
            "status": "success",
            "data": {"id": dashboard_id, **dashboard},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/dashboards/{dashboard_id}",
    summary="Delete dashboard",
    responses={
        200: {"description": "Dashboard deleted successfully"},
        404: {"description": "Dashboard not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_dashboard(dashboard_id: str):
    """
    Delete dashboard by ID

    Args:
        dashboard_id: Dashboard ID

    Returns:
        Deletion result
    """
    try:
        if dashboard_id not in _dashboards_db:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")

        del _dashboards_db[dashboard_id]

        logger.info(f"Deleted dashboard: {dashboard_id}")

        return {
            "status": "success",
            "data": {"id": dashboard_id, "message": "Dashboard deleted successfully"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/reports",
    summary="Get monitoring reports",
    responses={
        200: {"description": "Monitoring reports"},
        500: {"description": "Internal server error"},
    },
)
async def get_reports(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    report_type: str = Query("summary", description="Report type (summary, detailed, sla)"),
    time_range_hours: int = Query(24, ge=1, le=720, description="Time range in hours"),
):
    """
    Get monitoring reports

    Args:
        service_name: Filter by service name
        report_type: Report type
        time_range_hours: Time range in hours

    Returns:
        Monitoring reports
    """
    try:
        from core.service_monitoring_manager import get_service_monitoring_manager

        manager = get_service_monitoring_manager()
        summary = manager.get_monitoring_summary()

        time_range = timedelta(hours=time_range_hours)

        if report_type == "summary":
            report_data = {
                "report_type": "summary",
                "time_range_hours": time_range_hours,
                "total_services": summary.get("total_services_monitored", 0),
                "total_metrics": summary.get("total_metrics_collected", 0),
                "total_alerts": summary.get("total_alerts_generated", 0),
                "active_alerts": summary.get("active_alerts", 0),
                "total_anomalies": summary.get("total_anomalies_detected", 0),
            }
        elif report_type == "detailed":
            services_data = []
            services_to_check = [service_name] if service_name else summary.get("services", [])

            for svc_name in services_to_check:
                metrics = manager.get_service_metrics(svc_name, time_range)
                analysis = manager.analyze_service_performance(svc_name, time_range)

                services_data.append(
                    {
                        "service_name": svc_name,
                        "metrics_count": len(metrics),
                        "performance_analysis": analysis,
                    }
                )

            report_data = {
                "report_type": "detailed",
                "time_range_hours": time_range_hours,
                "services": services_data,
            }
        elif report_type == "sla":
            sla_data = []
            services_to_check = [service_name] if service_name else summary.get("services", [])

            for svc_name in services_to_check:
                metrics = manager.get_service_metrics(svc_name, time_range)

                total_requests = len([m for m in metrics if m.metric_name == "request_count"])
                error_count = len([m for m in metrics if m.metric_name == "error_count"])

                availability = (
                    ((total_requests - error_count) / total_requests * 100)
                    if total_requests > 0
                    else 100.0
                )

                sla_data.append(
                    {
                        "service_name": svc_name,
                        "availability_percentage": round(availability, 2),
                        "total_requests": total_requests,
                        "error_count": error_count,
                    }
                )

            report_data = {
                "report_type": "sla",
                "time_range_hours": time_range_hours,
                "sla_metrics": sla_data,
            }
        else:
            raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")

        return {
            "status": "success",
            "data": report_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))
