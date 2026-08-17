# -*- coding: utf-8 -*-
"""
api/slo_router.py
=================

REST API for SLO/SLA management.

Endpoints:
- GET    /api/v1/slo/        List all SLOs with live status
- POST   /api/v1/slo/        Create a new SLO rule
- GET    /api/v1/slo/{id}    Get one SLO with current error budget
- PUT    /api/v1/slo/{id}    Update an SLO rule
- GET    /api/v1/slo/reports Generate SLA compliance reports
- DELETE /api/v1/slo/{id}    Delete an SLO rule
"""

from __future__ import annotations

import datetime
import hmac
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

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
from core.sla_report_storage import delete_report as delete_sla_report
from core.sla_report_storage import get_report as get_sla_report
from core.sla_report_storage import list_reports as list_sla_reports
from core.sla_report_storage import save_reports as save_sla_reports
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
    tags=["SLO/SLA"],
)


class SLOCreate(BaseModel):
    """Request body for creating an SLO."""

    name: str
    service: str
    metric: str
    # Percent value (0-100) presented by the UI.
    target: float
    # e.g. "1h", "24h", "7d", "30d", "90d".
    window: str
    # Optional alert threshold as a percent; derived if omitted.
    alert_threshold: Optional[float] = None
    # Optional aggregation strategy (good_ratio, uptime, p99_lt, mean_lt).
    aggregation: Optional[str] = None


class SLOUpdate(BaseModel):
    """Request body for updating an SLO. All fields are optional."""

    name: Optional[str] = None
    service: Optional[str] = None
    metric: Optional[str] = None
    target: Optional[float] = None
    window: Optional[str] = None
    alert_threshold: Optional[float] = None
    aggregation: Optional[str] = None


def _get_metric_points(rule: SLORule) -> list[Any]:
    """Fetch metric points for the rule's evaluation window."""
    end_dt = datetime.datetime.utcnow()
    start_dt = end_dt - datetime.timedelta(hours=rule.window)
    return metrics_history.query(rule.metric, rule.service, start_dt, end_dt)


def _serialize(rule: SLORule) -> dict[str, Any]:
    """Convert an SLORule into the frontend SLO card shape."""
    points = _get_metric_points(rule)
    result = evaluate_slo(rule, points)
    return {
        "id": rule.id,
        "name": rule.name,
        "service": rule.service,
        "metric": rule.metric,
        "target": round(rule.target * 100.0, 4),
        "current": round(result["current"] * 100.0, 2),
        "window": format_window(rule.window),
        "errorBudget": round(result["error_budget_remaining_percent"], 2),
        "burnRate": round(result["burn_rate"], 2),
        "status": result["status"],
        "aggregation": rule.aggregation,
    }


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


@router.get("/", summary="列出所有 SLO 及其实时状态")
async def list_slo_status(
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return all SLO rules with their current SLI and error budget."""
    logger.debug("Listing SLOs")
    rules = list_slos()
    if current_user.role == "business":
        rules = [r for r in rules if can_view_asset(current_user, _resolve_asset_id(r.service))]
    return {"slos": [_serialize(rule) for rule in rules]}


@router.post("/", summary="创建 SLO 规则")
async def create_slo_endpoint(
    body: SLOCreate,
    current_user: User = Depends(require_roles("admin", "operator", "business")),
) -> dict[str, Any]:
    """Create a new SLO rule. Target and alert_threshold are supplied as percents."""
    if current_user.role == "business":
        asset_id = _resolve_asset_id(body.service)
        if asset_id is None or not can_edit_asset(current_user, asset_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to create SLO for this service",
            )

    target_frac = body.target / 100.0
    alert_frac = body.alert_threshold / 100.0 if body.alert_threshold is not None else None
    try:
        rule = create_slo(
            name=body.name,
            service=body.service,
            metric=body.metric,
            target=target_frac,
            window=parse_window(body.window),
            alert_threshold=alert_frac,
            aggregation=body.aggregation,
        )
    except Exception as e:
        logger.error(f"Failed to create SLO: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid SLO data: {e}") from e
    return _serialize(rule)


@router.post("/reports", summary="生成并保存 SLA 合规报告")
async def create_sla_reports_endpoint(
    period: str = "30d",
    current_user: User = Depends(require_roles("admin", "operator", "business")),
) -> dict[str, Any]:
    """Generate SLA reports for the given period and persist them."""
    if current_user.role == "business":
        if not any(can_edit_asset(current_user, _resolve_asset_id(r.service)) for r in list_slos()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No editable asset to generate report",
            )
    generated = generate_sla_report(period)
    ids = save_sla_reports(generated)
    return {"reports": list_sla_reports(), "generated_ids": ids}


@router.get("/reports", summary="列出已保存的 SLA 合规报告")
async def list_sla_reports_endpoint(
    period: Optional[str] = None,
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return persisted SLA reports, optionally filtered by period."""
    reports = list_sla_reports(period=period)
    if current_user.role == "business":
        reports = [
            r for r in reports if can_view_asset(current_user, _resolve_asset_id(r.get("service")))
        ]
    return {"reports": reports}


@router.get("/reports/{report_id}", summary="获取单个 SLA 报告详情")
async def get_sla_report_endpoint(
    report_id: str,
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return a single persisted SLA report."""
    report = get_sla_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="SLA report not found")
    if current_user.role == "business":
        if not can_view_asset(current_user, _resolve_asset_id(report.get("service"))):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to view this report",
            )
    return report


@router.delete("/reports/{report_id}", summary="删除 SLA 合规报告")
async def delete_sla_report_endpoint(
    report_id: str,
    current_user: User = Depends(require_roles("admin", "operator", "business")),
) -> dict[str, Any]:
    """Delete a persisted SLA report."""
    report = get_sla_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="SLA report not found")
    if current_user.role == "business":
        if not can_edit_asset(current_user, _resolve_asset_id(report.get("service"))):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to delete this report",
            )
    if delete_sla_report(report_id):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="SLA report not found")


@router.get("/{slo_id}", summary="获取单个 SLO 详情")
async def get_slo_endpoint(
    slo_id: str,
    current_user: User = Depends(_get_current_user_or_internal),
) -> dict[str, Any]:
    """Return a single SLO with its current error budget."""
    rule = get_slo(slo_id)
    if not rule:
        raise HTTPException(status_code=404, detail="SLO not found")
    if current_user.role == "business":
        if not can_view_asset(current_user, _resolve_asset_id(rule.service)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to view this SLO",
            )
    return _serialize(rule)


@router.put("/{slo_id}", summary="更新 SLO 规则")
async def update_slo_endpoint(
    slo_id: str,
    body: SLOUpdate,
    current_user: User = Depends(require_roles("admin", "operator", "business")),
) -> dict[str, Any]:
    """Update an existing SLO rule."""
    existing = get_slo(slo_id)
    if not existing:
        raise HTTPException(status_code=404, detail="SLO not found")

    if current_user.role == "business":
        if not can_edit_asset(current_user, _resolve_asset_id(existing.service)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to update this SLO",
            )
        if body.service and body.service != existing.service:
            if not can_edit_asset(current_user, _resolve_asset_id(body.service)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot change SLO to a service you cannot edit",
                )

    try:
        kwargs = body.model_dump(exclude_unset=True)
        if "window" in kwargs:
            kwargs["window"] = parse_window(kwargs["window"])
        if "target" in kwargs:
            kwargs["target"] = kwargs["target"] / 100.0
        if "alert_threshold" in kwargs:
            kwargs["alert_threshold"] = kwargs["alert_threshold"] / 100.0

        updated = update_slo(slo_id, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid SLO data: {e}") from e
    if not updated:
        raise HTTPException(status_code=404, detail="SLO not found")
    return _serialize(updated)


@router.delete("/{slo_id}", summary="删除 SLO 规则")
async def delete_slo_endpoint(
    slo_id: str,
    current_user: User = Depends(require_roles("admin", "operator", "business")),
) -> dict[str, Any]:
    """Delete an SLO rule."""
    rule = get_slo(slo_id)
    if not rule:
        raise HTTPException(status_code=404, detail="SLO not found")
    if current_user.role == "business":
        if not can_edit_asset(current_user, _resolve_asset_id(rule.service)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to delete this SLO",
            )
    if delete_slo(slo_id):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="SLO not found")
