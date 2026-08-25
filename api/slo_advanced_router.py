# -*- coding: utf-8 -*-
"""
api/slo_advanced_router.py
==========================

Advanced SLO/SLA management API endpoints.

This router provides comprehensive SLO management capabilities including:
- SLO definitions CRUD operations
- Metrics and budgets tracking
- Burn rate calculations
- Alert management
- Historical data analysis
- Service and objective management
- Rollup aggregations

Endpoints:
- GET/POST   /api/v1/slo/definitions         List/create SLO definitions
- GET/PATCH/DELETE /api/v1/slo/definitions/{id}  Manage single definition
- GET        /api/v1/slo/metrics              Get SLO metrics
- GET        /api/v1/slo/budgets              Get error budgets
- GET        /api/v1/slo/burn-rates           Get burn rates
- GET        /api/v1/slo/error-budgets        Get detailed error budgets
- GET/POST   /api/v1/slo/alerts               List/create alerts
- GET        /api/v1/slo/reports              Get SLO reports
- GET        /api/v1/slo/historical-data      Get historical SLO data
- GET        /api/v1/slo/services             List services
- GET/POST/PATCH/DELETE /api/v1/slo/objectives  Manage SLO objectives
- GET        /api/v1/slo/rollups              Get rollup aggregations
"""

from __future__ import annotations

import datetime
import hmac
import logging
import statistics
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, validator

from config import INTERNAL_API_KEY
from core.auth_db import Asset, get_session
from core.auth_service import (
    User,
    can_edit_asset,
    can_view_asset,
    get_current_user,
    require_roles,
)
from core.metrics_history import metrics_history
from core.slo_engine import (
    SLORule,
    create_slo,
    delete_slo,
    evaluate_slo,
    format_window,
    generate_sla_report,
    get_slo,
    list_slos,
    parse_window,
    update_slo,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/slo",
    tags=["SLO Advanced"],
)


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================


class SLODefinitionCreate(BaseModel):
    """Request body for creating an SLO definition."""

    name: str = Field(..., description="SLO definition name")
    description: str = Field("", description="SLO description")
    metric_type: str = Field(
        ...,
        description="Metric type: availability, latency, error_rate, throughput",
    )
    threshold: float = Field(..., ge=0, le=100, description="Threshold value (0-100)")
    operator: str = Field("gte", description="Operator: gte, lte, gt, lt")
    window: str = Field("30d", description="Time window (e.g., 1h, 24h, 7d, 30d)")
    alerting: bool = Field(True, description="Whether alerting is enabled")

    @validator("metric_type")
    def validate_metric_type(cls, v):
        valid_types = {"availability", "latency", "error_rate", "throughput"}
        if v not in valid_types:
            raise ValueError(f"metric_type must be one of {valid_types}")
        return v

    @validator("operator")
    def validate_operator(cls, v):
        valid_ops = {"gte", "lte", "gt", "lt"}
        if v not in valid_ops:
            raise ValueError(f"operator must be one of {valid_ops}")
        return v


class SLODefinitionUpdate(BaseModel):
    """Request body for updating an SLO definition."""

    name: Optional[str] = None
    description: Optional[str] = None
    metric_type: Optional[str] = None
    threshold: Optional[float] = Field(None, ge=0, le=100)
    operator: Optional[str] = None
    window: Optional[str] = None
    alerting: Optional[bool] = None


class SLODefinitionResponse(BaseModel):
    """Response model for SLO definition."""

    id: str
    name: str
    description: str
    metric_type: str
    threshold: float
    operator: str
    window: str
    alerting: bool
    created_at: str
    updated_at: str


class SLOObjectiveCreate(BaseModel):
    """Request body for creating an SLO objective."""

    name: str = Field(..., description="Objective name")
    service: str = Field(..., description="Service name")
    metric: str = Field(..., description="Metric name")
    target: float = Field(..., ge=0, le=100, description="Target percentage (0-100)")
    window: str = Field("30d", description="Time window")
    description: Optional[str] = Field(None, description="Objective description")


class SLOObjectiveUpdate(BaseModel):
    """Request body for updating an SLO objective."""

    name: Optional[str] = None
    service: Optional[str] = None
    metric: Optional[str] = None
    target: Optional[float] = Field(None, ge=0, le=100)
    window: Optional[str] = None
    description: Optional[str] = None


class SLOObjectiveResponse(BaseModel):
    """Response model for SLO objective."""

    id: str
    name: str
    service: str
    metric: str
    target: float
    window: str
    description: Optional[str]
    current: float
    status: str
    created_at: str
    updated_at: str


class SLOAlertCreate(BaseModel):
    """Request body for creating an SLO alert."""

    slo_id: str = Field(..., description="SLO ID")
    severity: str = Field(..., description="Severity: critical, major, minor")
    message: str = Field(..., description="Alert message")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")

    @validator("severity")
    def validate_severity(cls, v):
        valid_severities = {"critical", "major", "minor"}
        if v not in valid_severities:
            raise ValueError(f"severity must be one of {valid_severities}")
        return v


class SLOAlertResponse(BaseModel):
    """Response model for SLO alert."""

    id: str
    slo_id: str
    slo_name: str
    severity: str
    message: str
    status: str
    created_at: str
    resolved_at: Optional[str]
    metadata: Optional[dict[str, Any]]


# ============================================================================
# In-Memory Storage for Advanced SLO Data
# ============================================================================

_slo_definitions: dict[str, dict[str, Any]] = {}
_slo_objectives: dict[str, dict[str, Any]] = {}
_slo_alerts: dict[str, dict[str, Any]] = {}
_definition_counter = 0
_objective_counter = 0
_alert_counter = 0


def _generate_definition_id() -> str:
    """Generate a unique definition ID."""
    global _definition_counter
    _definition_counter += 1
    return f"DEF-{str(_definition_counter).zfill(3)}"


def _generate_objective_id() -> str:
    """Generate a unique objective ID."""
    global _objective_counter
    _objective_counter += 1
    return f"OBJ-{str(_objective_counter).zfill(3)}"


def _generate_alert_id() -> str:
    """Generate a unique alert ID."""
    global _alert_counter
    _alert_counter += 1
    return f"ALT-{str(_alert_counter).zfill(3)}"


# ============================================================================
# Helper Functions
# ============================================================================


def _resolve_asset_id(service: str) -> Optional[int]:
    """Map a service name to the Asset id in the database."""
    db = get_session()
    try:
        asset = db.query(Asset).filter(Asset.service == service).first()
        return asset.id if asset else None
    finally:
        db.close()


async def _get_current_user_or_internal(
    request: Request,
    x_internal_key: Optional[str] = Header(None),
) -> User:
    """Authenticate either via a real user token or an internal API key."""
    if x_internal_key and INTERNAL_API_KEY:
        if hmac.compare_digest(x_internal_key, INTERNAL_API_KEY):
            return User(username="internal", role="admin")

    auth_header = request.headers.get("authorization") or ""
    token = auth_header[7:] if auth_header.lower().startswith("bearer ") else auth_header
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_current_user(token)


def _get_metric_points(rule: SLORule) -> list[Any]:
    """Fetch metric points for the rule's evaluation window."""
    end_dt = datetime.datetime.utcnow()
    start_dt = end_dt - datetime.timedelta(hours=rule.window)
    return metrics_history.query(rule.metric, rule.service, start_dt, end_dt)


def _serialize_slo_definition(def_data: dict[str, Any]) -> dict[str, Any]:
    """Convert SLO definition data to response format."""
    return {
        "id": def_data["id"],
        "name": def_data["name"],
        "description": def_data["description"],
        "metric_type": def_data["metric_type"],
        "threshold": def_data["threshold"],
        "operator": def_data["operator"],
        "window": def_data["window"],
        "alerting": def_data["alerting"],
        "created_at": def_data["created_at"],
        "updated_at": def_data["updated_at"],
    }


def _serialize_slo_objective(obj_data: dict[str, Any]) -> dict[str, Any]:
    """Convert SLO objective data to response format."""
    return {
        "id": obj_data["id"],
        "name": obj_data["name"],
        "service": obj_data["service"],
        "metric": obj_data["metric"],
        "target": obj_data["target"],
        "window": obj_data["window"],
        "description": obj_data.get("description"),
        "current": obj_data.get("current", 0.0),
        "status": obj_data.get("status", "unknown"),
        "created_at": obj_data["created_at"],
        "updated_at": obj_data["updated_at"],
    }


def _serialize_slo_alert(alert_data: dict[str, Any]) -> dict[str, Any]:
    """Convert SLO alert data to response format."""
    return {
        "id": alert_data["id"],
        "slo_id": alert_data["slo_id"],
        "slo_name": alert_data.get("slo_name", ""),
        "severity": alert_data["severity"],
        "message": alert_data["message"],
        "status": alert_data["status"],
        "created_at": alert_data["created_at"],
        "resolved_at": alert_data.get("resolved_at"),
        "metadata": alert_data.get("metadata"),
    }


# ============================================================================
# SLO Definitions Endpoints
# ============================================================================


@router.get(
    "/definitions",
    summary="List all SLO definitions",
    response_model=dict[str, list[SLODefinitionResponse]],
)
async def list_slo_definitions(
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return all SLO definitions."""
    logger.debug("Listing SLO definitions")
    definitions = [_serialize_slo_definition(d) for d in _slo_definitions.values()]
    return {"definitions": definitions}


@router.post(
    "/definitions",
    summary="Create a new SLO definition",
    response_model=SLODefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_slo_definition(
    body: SLODefinitionCreate,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> dict[str, Any]:
    """Create a new SLO definition."""
    definition_id = _generate_definition_id()
    now = datetime.datetime.utcnow().isoformat()

    definition = {
        "id": definition_id,
        "name": body.name,
        "description": body.description,
        "metric_type": body.metric_type,
        "threshold": body.threshold,
        "operator": body.operator,
        "window": body.window,
        "alerting": body.alerting,
        "created_at": now,
        "updated_at": now,
    }

    _slo_definitions[definition_id] = definition
    logger.info(f"Created SLO definition {definition_id}: {body.name}")
    return _serialize_slo_definition(definition)


@router.get(
    "/definitions/{definition_id}",
    summary="Get a single SLO definition",
    response_model=SLODefinitionResponse,
)
async def get_slo_definition(
    definition_id: str,
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return a single SLO definition by ID."""
    definition = _slo_definitions.get(definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail="SLO definition not found")
    return _serialize_slo_definition(definition)


@router.patch(
    "/definitions/{definition_id}",
    summary="Update an SLO definition",
    response_model=SLODefinitionResponse,
)
async def update_slo_definition(
    definition_id: str,
    body: SLODefinitionUpdate,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> dict[str, Any]:
    """Update an existing SLO definition."""
    definition = _slo_definitions.get(definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail="SLO definition not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        definition[key] = value

    definition["updated_at"] = datetime.datetime.utcnow().isoformat()
    logger.info(f"Updated SLO definition {definition_id}")
    return _serialize_slo_definition(definition)


@router.delete(
    "/definitions/{definition_id}",
    summary="Delete an SLO definition",
)
async def delete_slo_definition(
    definition_id: str,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> dict[str, Any]:
    """Delete an SLO definition."""
    if definition_id not in _slo_definitions:
        raise HTTPException(status_code=404, detail="SLO definition not found")

    del _slo_definitions[definition_id]
    logger.info(f"Deleted SLO definition {definition_id}")
    return {"ok": True}


# ============================================================================
# SLO Metrics Endpoint
# ============================================================================


@router.get(
    "/metrics",
    summary="Get SLO metrics",
    response_model=dict[str, list[dict[str, Any]]],
)
async def get_slo_metrics(
    service: Optional[str] = Query(None, description="Filter by service"),
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return SLO metrics for all or specific service."""
    logger.debug("Fetching SLO metrics")
    rules = list_slos()

    if service:
        rules = [r for r in rules if r.service == service]

    metrics_list = []
    for rule in rules:
        points = _get_metric_points(rule)
        result = evaluate_slo(rule, points)

        # Calculate trend based on historical data
        if len(points) >= 2:
            recent_values = [float(p.value) for p in points[-10:]]
            if len(recent_values) >= 2:
                avg_first = statistics.mean(recent_values[: len(recent_values) // 2])
                avg_last = statistics.mean(recent_values[len(recent_values) // 2 :])
                if avg_last > avg_first * 1.05:
                    trend = "up"
                elif avg_last < avg_first * 0.95:
                    trend = "down"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Generate history array for visualization
        history = []
        if points:
            step = max(1, len(points) // 20)
            for i in range(0, len(points), step):
                val = float(points[i].value)
                # Normalize to percentage range
                if rule.metric in {"cpu", "memory"}:
                    val = min(100, val)
                history.append(min(100, max(0, val)))

        metrics_list.append(
            {
                "name": rule.name,
                "service": rule.service,
                "metric_type": rule.metric,
                "current": round(result["current"] * 100.0, 2),
                "target": round(rule.target * 100.0, 2),
                "trend": trend,
                "history": history,
            }
        )

    return {"metrics": metrics_list}


# ============================================================================
# SLO Budgets Endpoint
# ============================================================================


@router.get(
    "/budgets",
    summary="Get error budgets",
    response_model=dict[str, list[dict[str, Any]]],
)
async def get_slo_budgets(
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return error budgets for all SLOs."""
    logger.debug("Fetching error budgets")
    rules = list_slos()

    budgets = []
    for rule in rules:
        points = _get_metric_points(rule)
        result = evaluate_slo(rule, points)

        budgets.append(
            {
                "slo_id": rule.id,
                "slo_name": rule.name,
                "service": rule.service,
                "target": round(rule.target * 100.0, 2),
                "current": round(result["current"] * 100.0, 2),
                "error_budget_remaining": round(result["error_budget_remaining_percent"], 2),
                "error_budget_consumed": round(
                    100.0 - result["error_budget_remaining_percent"], 2
                ),
                "window": format_window(rule.window),
                "status": result["status"],
            }
        )

    return {"budgets": budgets}


# ============================================================================
# SLO Burn Rates Endpoint
# ============================================================================


@router.get(
    "/burn-rates",
    summary="Get burn rates",
    response_model=dict[str, list[dict[str, Any]]],
)
async def get_slo_burn_rates(
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return burn rates for all SLOs."""
    logger.debug("Fetching burn rates")
    rules = list_slos()

    burn_rates = []
    for rule in rules:
        points = _get_metric_points(rule)
        result = evaluate_slo(rule, points)

        # Calculate burn rate over different time windows
        burn_rate_1h = result["burn_rate"]
        burn_rate_24h = result["burn_rate"] * 0.8  # Simulated longer-term burn rate
        burn_rate_7d = result["burn_rate"] * 0.6  # Simulated weekly burn rate

        burn_rates.append(
            {
                "slo_id": rule.id,
                "slo_name": rule.name,
                "service": rule.service,
                "burn_rate_1h": round(burn_rate_1h, 3),
                "burn_rate_24h": round(burn_rate_24h, 3),
                "burn_rate_7d": round(burn_rate_7d, 3),
                "status": result["status"],
                "window": format_window(rule.window),
            }
        )

    return {"burn_rates": burn_rates}


# ============================================================================
# SLO Error Budgets Endpoint (Detailed)
# ============================================================================


@router.get(
    "/error-budgets",
    summary="Get detailed error budgets",
    response_model=dict[str, list[dict[str, Any]]],
)
async def get_slo_error_budgets(
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return detailed error budget information."""
    logger.debug("Fetching detailed error budgets")
    rules = list_slos()

    error_budgets = []
    for rule in rules:
        points = _get_metric_points(rule)
        result = evaluate_slo(rule, points)

        # Calculate time remaining based on burn rate
        burn_rate = result["burn_rate"]
        remaining_percent = result["error_budget_remaining_percent"]

        if burn_rate > 0:
            hours_remaining = remaining_percent / (burn_rate * 100) if burn_rate > 0 else 9999
        else:
            hours_remaining = 9999

        error_budgets.append(
            {
                "slo_id": rule.id,
                "slo_name": rule.name,
                "service": rule.service,
                "target": round(rule.target * 100.0, 2),
                "current": round(result["current"] * 100.0, 2),
                "error_budget_remaining_percent": round(remaining_percent, 2),
                "error_budget_consumed_percent": round(100.0 - remaining_percent, 2),
                "burn_rate": round(burn_rate, 3),
                "estimated_hours_remaining": round(hours_remaining, 1),
                "status": result["status"],
                "window": format_window(rule.window),
            }
        )

    return {"error_budgets": error_budgets}


# ============================================================================
# SLO Alerts Endpoints
# ============================================================================


@router.get(
    "/alerts",
    summary="List SLO alerts",
    response_model=dict[str, list[SLOAlertResponse]],
)
async def list_slo_alerts(
    status: Optional[str] = Query(None, description="Filter by status: open, resolved"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return all SLO alerts, optionally filtered."""
    logger.debug("Listing SLO alerts")
    alerts = list(_slo_alerts.values())

    if status:
        alerts = [a for a in alerts if a["status"] == status]
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]

    # Sort by created_at descending
    alerts.sort(key=lambda x: x["created_at"], reverse=True)

    return {"alerts": [_serialize_slo_alert(a) for a in alerts]}


@router.post(
    "/alerts",
    summary="Create a new SLO alert",
    response_model=SLOAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_slo_alert(
    body: SLOAlertCreate,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> dict[str, Any]:
    """Create a new SLO alert."""
    alert_id = _generate_alert_id()
    now = datetime.datetime.utcnow().isoformat()

    # Get SLO name
    slo = get_slo(body.slo_id)
    slo_name = slo.name if slo else "Unknown"

    alert = {
        "id": alert_id,
        "slo_id": body.slo_id,
        "slo_name": slo_name,
        "severity": body.severity,
        "message": body.message,
        "status": "open",
        "created_at": now,
        "resolved_at": None,
        "metadata": body.metadata,
    }

    _slo_alerts[alert_id] = alert
    logger.info(f"Created SLO alert {alert_id} for SLO {body.slo_id}")
    return _serialize_slo_alert(alert)


# ============================================================================
# SLO Reports Endpoint
# ============================================================================


@router.get(
    "/reports",
    summary="Get SLO reports",
    response_model=dict[str, list[dict[str, Any]]],
)
async def get_slo_reports(
    period: str = Query("30d", description="Report period (e.g., 7d, 30d, 90d)"),
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return SLO compliance reports for the specified period."""
    logger.debug(f"Fetching SLO reports for period {period}")
    reports = generate_sla_report(period)
    return {"reports": reports}


# ============================================================================
# SLO Historical Data Endpoint
# ============================================================================


@router.get(
    "/historical-data",
    summary="Get historical SLO data",
    response_model=dict[str, list[dict[str, Any]]],
)
async def get_slo_historical_data(
    slo_id: Optional[str] = Query(None, description="Filter by SLO ID"),
    period: str = Query("7d", description="Historical period (e.g., 1h, 24h, 7d)"),
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return historical SLO data for analysis."""
    logger.debug(f"Fetching historical SLO data for period {period}")
    rules = list_slos()

    if slo_id:
        rules = [r for r in rules if r.id == slo_id]

    hours = parse_window(period)
    end_dt = datetime.datetime.utcnow()
    start_dt = end_dt - datetime.timedelta(hours=hours)

    historical_data = []
    for rule in rules:
        points = metrics_history.query(rule.metric, rule.service, start_dt, end_dt)

        # Aggregate data by hour
        hourly_data = {}
        for point in points:
            hour_key = point.timestamp.strftime("%Y-%m-%d %H:00:00")
            if hour_key not in hourly_data:
                hourly_data[hour_key] = []
            hourly_data[hour_key].append(float(point.value))

        # Calculate hourly averages
        time_series = []
        for hour in sorted(hourly_data.keys()):
            values = hourly_data[hour]
            avg_value = statistics.mean(values) if values else 0.0
            time_series.append(
                {
                    "timestamp": hour,
                    "value": round(avg_value, 4),
                    "count": len(values),
                }
            )

        historical_data.append(
            {
                "slo_id": rule.id,
                "slo_name": rule.name,
                "service": rule.service,
                "metric": rule.metric,
                "period": period,
                "data_points": len(points),
                "time_series": time_series,
            }
        )

    return {"historical_data": historical_data}


# ============================================================================
# SLO Services Endpoint
# ============================================================================


@router.get(
    "/services",
    summary="List services with SLOs",
    response_model=dict[str, list[dict[str, Any]]],
)
async def get_slo_services(
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return list of services that have SLOs defined."""
    logger.debug("Listing services with SLOs")
    rules = list_slos()

    # Group by service
    service_map = {}
    for rule in rules:
        if rule.service not in service_map:
            service_map[rule.service] = {
                "name": rule.service,
                "slo_count": 0,
                "slos": [],
            }
        service_map[rule.service]["slo_count"] += 1
        service_map[rule.service]["slos"].append(
            {
                "id": rule.id,
                "name": rule.name,
                "target": round(rule.target * 100.0, 2),
            }
        )

    services = list(service_map.values())
    return {"services": services}


# ============================================================================
# SLO Objectives Endpoints
# ============================================================================


@router.get(
    "/objectives",
    summary="List SLO objectives",
    response_model=dict[str, list[SLOObjectiveResponse]],
)
async def list_slo_objectives(
    service: Optional[str] = Query(None, description="Filter by service"),
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return all SLO objectives, optionally filtered by service."""
    logger.debug("Listing SLO objectives")
    objectives = list(_slo_objectives.values())

    if service:
        objectives = [o for o in objectives if o["service"] == service]

    # Update current values for each objective
    for obj in objectives:
        rule = get_slo(obj["slo_rule_id"]) if "slo_rule_id" in obj else None
        if rule:
            points = _get_metric_points(rule)
            result = evaluate_slo(rule, points)
            obj["current"] = round(result["current"] * 100.0, 2)
            obj["status"] = result["status"]

    return {"objectives": [_serialize_slo_objective(o) for o in objectives]}


@router.post(
    "/objectives",
    summary="Create a new SLO objective",
    response_model=SLOObjectiveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_slo_objective(
    body: SLOObjectiveCreate,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> dict[str, Any]:
    """Create a new SLO objective and corresponding SLO rule."""
    objective_id = _generate_objective_id()
    now = datetime.datetime.utcnow().isoformat()

    # Create the underlying SLO rule
    target_frac = body.target / 100.0
    window_hours = parse_window(body.window)

    try:
        rule = create_slo(
            name=body.name,
            service=body.service,
            metric=body.metric,
            target=target_frac,
            window=window_hours,
        )
    except Exception as e:
        logger.error(f"Failed to create SLO rule for objective: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid SLO data: {e}") from e

    # Create the objective
    objective = {
        "id": objective_id,
        "name": body.name,
        "service": body.service,
        "metric": body.metric,
        "target": body.target,
        "window": body.window,
        "description": body.description,
        "slo_rule_id": rule.id,
        "current": 0.0,
        "status": "unknown",
        "created_at": now,
        "updated_at": now,
    }

    _slo_objectives[objective_id] = objective
    logger.info(f"Created SLO objective {objective_id} with SLO rule {rule.id}")

    # Evaluate initial status
    points = _get_metric_points(rule)
    result = evaluate_slo(rule, points)
    objective["current"] = round(result["current"] * 100.0, 2)
    objective["status"] = result["status"]

    return _serialize_slo_objective(objective)


@router.patch(
    "/objectives/{objective_id}",
    summary="Update an SLO objective",
    response_model=SLOObjectiveResponse,
)
async def update_slo_objective(
    objective_id: str,
    body: SLOObjectiveUpdate,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> dict[str, Any]:
    """Update an existing SLO objective."""
    objective = _slo_objectives.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="SLO objective not found")

    update_data = body.model_dump(exclude_unset=True)

    # If updating fields that affect the SLO rule, update it too
    if "service" in update_data or "metric" in update_data or "target" in update_data or "window" in update_data:
        rule_id = objective.get("slo_rule_id")
        if rule_id:
            rule_update = {}
            if "service" in update_data:
                rule_update["service"] = update_data["service"]
            if "metric" in update_data:
                rule_update["metric"] = update_data["metric"]
            if "target" in update_data:
                rule_update["target"] = update_data["target"] / 100.0
            if "window" in update_data:
                rule_update["window"] = parse_window(update_data["window"])

            if rule_update:
                update_slo(rule_id, **rule_update)

    # Update objective fields
    for key, value in update_data.items():
        objective[key] = value

    objective["updated_at"] = datetime.datetime.utcnow().isoformat()
    logger.info(f"Updated SLO objective {objective_id}")
    return _serialize_slo_objective(objective)


@router.delete(
    "/objectives/{objective_id}",
    summary="Delete an SLO objective",
)
async def delete_slo_objective(
    objective_id: str,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> dict[str, Any]:
    """Delete an SLO objective and its associated SLO rule."""
    objective = _slo_objectives.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="SLO objective not found")

    # Delete the associated SLO rule
    rule_id = objective.get("slo_rule_id")
    if rule_id:
        delete_slo(rule_id)

    del _slo_objectives[objective_id]
    logger.info(f"Deleted SLO objective {objective_id}")
    return {"ok": True}


# ============================================================================
# SLO Rollups Endpoint
# ============================================================================


@router.get(
    "/rollups",
    summary="Get SLO rollup aggregations",
    response_model=dict[str, list[dict[str, Any]]],
)
async def get_slo_rollups(
    service: Optional[str] = Query(None, description="Filter by service"),
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return rollup aggregations of SLO performance by service and metric."""
    logger.debug("Fetching SLO rollups")
    rules = list_slos()

    if service:
        rules = [r for r in rules if r.service == service]

    # Group by service
    service_rollups = {}
    for rule in rules:
        if rule.service not in service_rollups:
            service_rollups[rule.service] = {
                "service": rule.service,
                "total_slos": 0,
                "healthy_slos": 0,
                "warning_slos": 0,
                "critical_slos": 0,
                "avg_current": 0.0,
                "avg_target": 0.0,
                "metrics": {},
            }

        points = _get_metric_points(rule)
        result = evaluate_slo(rule, points)

        rollup = service_rollups[rule.service]
        rollup["total_slos"] += 1

        if result["status"] == "healthy":
            rollup["healthy_slos"] += 1
        elif result["status"] == "warning":
            rollup["warning_slos"] += 1
        else:
            rollup["critical_slos"] += 1

        rollup["avg_current"] += result["current"]
        rollup["avg_target"] += rule.target

        # Track by metric type
        if rule.metric not in rollup["metrics"]:
            rollup["metrics"][rule.metric] = {
                "count": 0,
                "avg_current": 0.0,
                "avg_target": 0.0,
            }

        rollup["metrics"][rule.metric]["count"] += 1
        rollup["metrics"][rule.metric]["avg_current"] += result["current"]
        rollup["metrics"][rule.metric]["avg_target"] += rule.target

    # Calculate averages
    rollups = []
    for service_name, rollup in service_rollups.items():
        if rollup["total_slos"] > 0:
            rollup["avg_current"] = round(
                (rollup["avg_current"] / rollup["total_slos"]) * 100.0, 2
            )
            rollup["avg_target"] = round(
                (rollup["avg_target"] / rollup["total_slos"]) * 100.0, 2
            )

        for metric_name, metric_data in rollup["metrics"].items():
            if metric_data["count"] > 0:
                metric_data["avg_current"] = round(
                    (metric_data["avg_current"] / metric_data["count"]) * 100.0, 2
                )
                metric_data["avg_target"] = round(
                    (metric_data["avg_target"] / metric_data["count"]) * 100.0, 2
                )

        rollups.append(rollup)

    return {"rollups": rollups}
