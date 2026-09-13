# -*- coding: utf-8 -*-
"""Mapping helpers shared by the change-approval / change-records page routers.

Both pages are *projections* of the same source of truth — the durable change
requests maintained by :mod:`core.change_management_engine`.  Rather than each
router re-deriving the page-specific view (and risk divergence), the field
mapping lives here.

All mappings are deterministic derivations from the real change request:

* ``type``      ← ``risk_level`` (low→routine, medium→standard, high→emergency)
* ``priority``  ← ``risk_level`` (low→low, medium→medium, high→high)
* timestamps    ← the audit-log trail captured by the engine
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

_TYPE_BY_RISK = {"low": "routine", "medium": "standard", "high": "emergency"}
_PRIORITY_BY_RISK = {"low": "low", "medium": "medium", "high": "high"}

# Approval page status values.
_APPROVAL_PENDING = {"draft", "pending", "review"}
_APPROVAL_APPROVED = {"approved", "implemented", "rolled_back"}

# Record page terminal statuses.
_RECORD_STATUS = {"implemented": "completed", "rolled_back": "rolled_back", "rejected": "failed"}


def change_type(risk_level: str) -> str:
    return _TYPE_BY_RISK.get(str(risk_level), "routine")


def change_priority(risk_level: str) -> str:
    return _PRIORITY_BY_RISK.get(str(risk_level), "low")


def _parse(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def audit_timeline(request: dict[str, Any]) -> dict[str, Any]:
    """Extract the meaningful audit checkpoints from a change request payload."""
    entries = request.get("audit_log") or []
    timeline: dict[str, Any] = {
        "createdAt": None,
        "submittedAt": None,
        "approvedAt": None,
        "decidedAt": None,
        "terminalAt": None,
        "lastComment": None,
        "actor": None,
    }
    for entry in entries:
        action = str(entry.get("action") or "")
        ts = entry.get("timestamp")
        if timeline["createdAt"] is None:
            timeline["createdAt"] = ts
        if action == "submit":
            timeline["submittedAt"] = ts
        elif action == "approve":
            timeline["approvedAt"] = ts
            timeline["decidedAt"] = ts
            timeline["actor"] = entry.get("actor")
        elif action == "reject":
            timeline["decidedAt"] = ts
            timeline["actor"] = entry.get("actor")
            timeline["lastComment"] = entry.get("message")
        elif action in {"implement", "rollback"}:
            timeline["terminalAt"] = ts
            timeline["actor"] = entry.get("actor") or timeline["actor"]
        elif action == "comment":
            timeline["lastComment"] = entry.get("message")
    if timeline["lastComment"] is None and entries:
        timeline["lastComment"] = entries[-1].get("message")
    return timeline


def _duration_seconds(start: Optional[str], end: Optional[str]) -> Optional[float]:
    start_dt, end_dt = _parse(start), _parse(end)
    if start_dt is None or end_dt is None:
        return None
    return round(max(0.0, (end_dt - start_dt).total_seconds()), 1)


def to_approval(request: dict[str, Any]) -> dict[str, Any]:
    """Project an engine change request onto the change-approval page model."""
    risk = str(request.get("risk_level") or "low")
    status = str(request.get("status") or "draft")
    if status in _APPROVAL_PENDING:
        page_status = "pending"
    elif status in _APPROVAL_APPROVED:
        page_status = "approved"
    else:
        page_status = "rejected"

    timeline = audit_timeline(request)
    schedule = request.get("schedule") or None
    return {
        "id": request.get("id"),
        "changeId": request.get("id"),
        "changeTitle": request.get("title"),
        "changeDescription": request.get("description", ""),
        "requester": request.get("requester"),
        "type": change_type(risk),
        "priority": change_priority(risk),
        "riskLevel": risk,
        "scheduledStart": schedule,
        "scheduledEnd": None,
        "status": page_status,
        "approver": request.get("approver") or None,
        "comment": timeline["lastComment"],
        "approvedAt": timeline["decidedAt"],
        "createdAt": timeline["createdAt"],
    }


def to_record(request: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Project a *terminal* change request onto the change-records page model.

    Returns ``None`` for requests that are not finished (there is nothing to
    record yet).
    """
    status = str(request.get("status") or "")
    if status not in _RECORD_STATUS:
        return None

    risk = str(request.get("risk_level") or "low")
    timeline = audit_timeline(request)
    started = timeline["approvedAt"] or timeline["submittedAt"] or timeline["createdAt"]
    completed = timeline["terminalAt"] or timeline["decidedAt"]
    services = request.get("affected_services") or []
    return {
        "id": request.get("id"),
        "changeId": request.get("id"),
        "changeTitle": request.get("title"),
        "type": change_type(risk),
        "status": _RECORD_STATUS[status],
        "requester": request.get("requester"),
        "approver": request.get("approver") or None,
        "executor": timeline["actor"] or request.get("approver") or None,
        "scheduledStart": request.get("schedule") or timeline["createdAt"],
        "scheduledEnd": None,
        "actualStart": started,
        "actualEnd": completed,
        "duration": _duration_seconds(started, completed),
        "riskLevel": risk,
        "impact": ", ".join(str(s) for s in services) if services else None,
        "rollbackExecuted": status == "rolled_back",
        "createdAt": timeline["createdAt"],
        "completedAt": completed,
    }


def record_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the change-records summary cards from the record list."""
    total = len(records)
    completed = sum(1 for r in records if r["status"] == "completed")
    rolled_back = sum(1 for r in records if r["status"] == "rolled_back")
    failed = sum(1 for r in records if r["status"] == "failed")
    durations = [r["duration"] for r in records if isinstance(r.get("duration"), (int, float))]
    finished = completed + rolled_back + failed
    return {
        "totalChanges": total,
        "completedChanges": completed,
        "rolledBackChanges": rolled_back,
        "failedChanges": failed,
        "avgDuration": round(sum(durations) / len(durations), 1) if durations else 0,
        "successRate": round(completed / finished * 100, 1) if finished else 0,
    }
