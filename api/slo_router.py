# -*- coding: utf-8 -*-
"""
api/slo_router.py
=================

REST API for SLO/SLA management.

Endpoints:
- GET    /api/v1/slo/        List all SLOs with live status
- POST   /api/v1/slo/        Create a new SLO rule
- GET    /api/v1/slo/{id}    Get one SLO with current error budget
- DELETE /api/v1/slo/{id}    Delete an SLO rule
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel


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


class SLOUpdate(BaseModel):
    """Request body for updating an SLO. All fields are optional."""

    name: Optional[str] = None
    service: Optional[str] = None
    metric: Optional[str] = None
    target: Optional[float] = None
    window: Optional[str] = None
    alert_threshold: Optional[float] = None


def _get_metric_history(metric: str) -> list[float]:
    """Fetch the latest metric samples and normalize known percent metrics."""
    raw = metrics_history.to_dict()
    if metric not in raw:
        return []
    values = raw[metric]
    if metric in {"cpu", "memory"}:
        # metrics_history stores CPU/memory as 0-100 percentages.
        return [float(v) / 100.0 for v in values]
    return [float(v) for v in values]


def _serialize(rule: SLORule) -> dict[str, Any]:
    """Convert an SLORule into the frontend SLO card shape."""
    history = _get_metric_history(rule.metric)
    result = evaluate_slo(rule, history)
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
    }


@router.get("/", summary="列出所有 SLO 及其实时状态")
async def list_slo_status() -> dict[str, Any]:
    """Return all SLO rules with their current SLI and error budget."""
    logger.debug("Listing SLOs")
    return {"slos": [_serialize(rule) for rule in list_slos()]}


@router.post("/", summary="创建 SLO 规则")
async def create_slo_endpoint(body: SLOCreate) -> dict[str, Any]:
    """Create a new SLO rule. Target and alert_threshold are supplied as percents."""
    target_frac = body.target / 100.0
    alert_frac = (
        body.alert_threshold / 100.0
        if body.alert_threshold is not None
        else None
    )
    try:
        rule = create_slo(
            name=body.name,
            service=body.service,
            metric=body.metric,
            target=target_frac,
            window=parse_window(body.window),
            alert_threshold=alert_frac,
        )
    except Exception as e:
        logger.error(f"Failed to create SLO: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid SLO data: {e}") from e
    return _serialize(rule)


@router.get("/{slo_id}", summary="获取单个 SLO 详情")
async def get_slo_endpoint(slo_id: str) -> dict[str, Any]:
    """Return a single SLO with its current error budget."""
    rule = get_slo(slo_id)
    if not rule:
        raise HTTPException(status_code=404, detail="SLO not found")
    return _serialize(rule)


@router.put("/{slo_id}", summary="更新 SLO 规则")
async def update_slo_endpoint(slo_id: str, body: SLOUpdate) -> dict[str, Any]:
    """Update an existing SLO rule."""
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


@router.get("/reports", summary="生成 SLA 合规报告")
async def list_sla_reports(period: str = "30d") -> dict[str, Any]:
    """Generate SLA compliance reports for all SLO rules over the given period."""
    return {"reports": generate_sla_report(period)}


@router.delete("/{slo_id}", summary="删除 SLO 规则")
async def delete_slo_endpoint(slo_id: str) -> dict[str, Any]:
    """Delete an SLO rule."""
    if delete_slo(slo_id):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="SLO not found")
