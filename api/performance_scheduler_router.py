# -*- coding: utf-8 -*-
"""Performance scheduler API (``/api/v1/performance-scheduler``).

Backs ``frontend/app/workflow/performance-scheduler``.  Everything is real:

* ``/metrics`` returns live host metrics (psutil) plus workflow-derived
  ``activeWorkflows`` / ``queueSize`` counters; network figures are byte rates
  computed between samples;
* ``/rules`` CRUD persists threshold rules durably;
* every ``/metrics`` poll evaluates the enabled rules against the live values,
  honours each rule's cooldown, and — on a match — raises a real alert into the
  platform alert stream and increments the rule's trigger counter.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import psutil
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.database import SessionLocal
from core.models import WorkflowExecution
from core.workflow_page_support import get_store, new_id, utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/performance-scheduler", tags=["性能调度"])

_KIND = "performance_rules"
_OPERATORS = {
    "gt": lambda v, t: v > t,
    "lt": lambda v, t: v < t,
    "eq": lambda v, t: v == t,
    "gte": lambda v, t: v >= t,
    "lte": lambda v, t: v <= t,
}
_METRICS = {
    "cpuUsage",
    "memoryUsage",
    "diskUsage",
    "networkIn",
    "networkOut",
    "activeWorkflows",
    "queueSize",
}
_ACTIONS = {"scale_up", "scale_down", "alert", "restart"}

_last_net: dict[str, Any] = {"ts": None, "recv": 0, "sent": 0}


class RuleUpsert(BaseModel):
    """创建/更新性能规则请求体。"""

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    metric: str = Field(..., description="监控指标")
    operator: str = Field(..., description="gt/lt/eq/gte/lte")
    threshold: float = Field(...)
    action: str = Field(..., description="scale_up/scale_down/alert/restart")
    cooldown: int = Field(default=300, ge=0)


class ToggleBody(BaseModel):
    enabled: bool


def _validate(payload: RuleUpsert) -> None:
    if payload.metric not in _METRICS:
        raise HTTPException(status_code=400, detail=f"未知指标: {payload.metric}")
    if payload.operator not in _OPERATORS:
        raise HTTPException(status_code=400, detail=f"未知操作符: {payload.operator}")
    if payload.action not in _ACTIONS:
        raise HTTPException(status_code=400, detail=f"未知动作: {payload.action}")


def _serialize(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rule.get("id"),
        "name": rule.get("name"),
        "description": rule.get("description", ""),
        "metric": rule.get("metric"),
        "operator": rule.get("operator"),
        "threshold": rule.get("threshold"),
        "action": rule.get("action"),
        "cooldown": int(rule.get("cooldown", 300)),
        "enabled": bool(rule.get("enabled", True)),
        "triggeredCount": int(rule.get("triggeredCount", 0)),
        "lastTriggered": rule.get("lastTriggered"),
        "createdAt": rule.get("createdAt"),
    }


def _collect_metrics() -> dict[str, Any]:
    """Sample live host metrics and workflow counters."""
    now = time.monotonic()
    net = psutil.net_io_counters()
    prev = _last_net
    if prev["ts"] is not None and now > prev["ts"]:
        elapsed = now - prev["ts"]
        net_in = round((net.bytes_recv - prev["recv"]) / elapsed, 1)
        net_out = round((net.bytes_sent - prev["sent"]) / elapsed, 1)
    else:
        net_in = net_out = 0.0
    _last_net.update({"ts": now, "recv": net.bytes_recv, "sent": net.bytes_sent})

    db = SessionLocal()
    try:
        active = db.query(WorkflowExecution).filter(WorkflowExecution.status == "running").count()
        queued = db.query(WorkflowExecution).filter(WorkflowExecution.status == "pending").count()
    finally:
        db.close()

    return {
        "cpuUsage": round(psutil.cpu_percent(interval=0.1), 1),
        "memoryUsage": round(psutil.virtual_memory().percent, 1),
        "diskUsage": round(psutil.disk_usage("/").percent, 1),
        "networkIn": net_in,
        "networkOut": net_out,
        "activeWorkflows": active,
        "queueSize": queued,
    }


def _emit_alert(rule: dict[str, Any], value: float) -> None:
    """Raise a real platform alert for a matched rule (best-effort)."""
    try:
        from core.alert_engine import alert_history
    except Exception as exc:  # pragma: no cover - alert engine optional
        logger.warning("告警引擎不可用，跳过告警: %s", exc)
        return
    alert_history.appendleft(
        {
            "id": new_id("perf"),
            "title": f"性能规则触发: {rule.get('name')}",
            "level": "warning",
            "source": "performance-scheduler",
            "metric": rule.get("metric"),
            "value": value,
            "threshold": rule.get("threshold"),
            "action": rule.get("action"),
        }
    )


def _evaluate_rules(store: Any, metrics: dict[str, Any]) -> None:
    """Evaluate enabled rules against *metrics*, honouring cooldowns."""
    now = utcnow()
    for rule_id, rule in list(store.items()):
        if not isinstance(rule, dict) or not rule.get("enabled"):
            continue
        metric = rule.get("metric")
        if metric not in metrics:
            continue
        compare = _OPERATORS.get(rule.get("operator"))
        if compare is None:
            continue
        value = float(metrics[metric])
        threshold = float(rule.get("threshold", 0))
        if not compare(value, threshold):
            continue

        last = rule.get("lastTriggered")
        if last:
            try:
                elapsed = (now - datetime.fromisoformat(last)).total_seconds()
                if elapsed < int(rule.get("cooldown", 0)):
                    continue
            except (TypeError, ValueError):
                pass

        rule["triggeredCount"] = int(rule.get("triggeredCount", 0)) + 1
        rule["lastTriggered"] = now.isoformat()
        store[rule_id] = rule
        _emit_alert(rule, value)
        logger.info(
            "性能规则 %s 触发: %s=%s %s %s (action=%s)",
            rule.get("name"),
            metric,
            value,
            rule.get("operator"),
            threshold,
            rule.get("action"),
        )


@router.get("/metrics", summary="获取实时性能指标")
async def get_metrics(request: Request) -> dict[str, Any]:
    """Sample live metrics and evaluate every enabled performance rule."""
    metrics = _collect_metrics()
    store = get_store(request, _KIND)
    _evaluate_rules(store, metrics)
    return metrics


@router.get("/rules", summary="列出性能规则")
async def list_rules(request: Request) -> list[dict[str, Any]]:
    """Return all performance rules."""
    store = get_store(request, _KIND)
    rules = [dict(r) for r in store.values_list() if isinstance(r, dict)]
    rules.sort(key=lambda r: str(r.get("createdAt") or ""))
    return [_serialize(r) for r in rules]


@router.post("/rules", status_code=201, summary="创建性能规则")
async def create_rule(payload: RuleUpsert, request: Request) -> dict[str, Any]:
    """Create a threshold rule."""
    _validate(payload)
    store = get_store(request, _KIND)
    rule_id = new_id("rule")
    rule = {
        "id": rule_id,
        "name": payload.name.strip(),
        "description": payload.description,
        "metric": payload.metric,
        "operator": payload.operator,
        "threshold": payload.threshold,
        "action": payload.action,
        "cooldown": payload.cooldown,
        "enabled": True,
        "triggeredCount": 0,
        "lastTriggered": None,
        "createdAt": utcnow().isoformat(),
    }
    store[rule_id] = rule
    return _serialize(rule)


@router.put("/rules/{rule_id}", summary="更新性能规则")
async def update_rule(rule_id: str, payload: RuleUpsert, request: Request) -> dict[str, Any]:
    """Update a threshold rule."""
    _validate(payload)
    store = get_store(request, _KIND)
    rule = store.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="性能规则不存在")
    rule.update(
        {
            "name": payload.name.strip(),
            "description": payload.description,
            "metric": payload.metric,
            "operator": payload.operator,
            "threshold": payload.threshold,
            "action": payload.action,
            "cooldown": payload.cooldown,
        }
    )
    store[rule_id] = rule
    return _serialize(rule)


@router.delete("/rules/{rule_id}", summary="删除性能规则")
async def delete_rule(rule_id: str, request: Request) -> dict[str, Any]:
    """Delete a threshold rule."""
    store = get_store(request, _KIND)
    if rule_id not in store:
        raise HTTPException(status_code=404, detail="性能规则不存在")
    del store[rule_id]
    return {"status": "success", "message": "性能规则已删除"}


@router.patch("/rules/{rule_id}/toggle", summary="启用/禁用性能规则")
async def toggle_rule(rule_id: str, payload: ToggleBody, request: Request) -> dict[str, Any]:
    """Enable or disable a threshold rule."""
    store = get_store(request, _KIND)
    rule = store.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="性能规则不存在")
    rule["enabled"] = payload.enabled
    store[rule_id] = rule
    return _serialize(rule)
