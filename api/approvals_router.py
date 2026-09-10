# -*- coding: utf-8 -*-
"""
Approvals Router
审批路由，提供 /api/v1/approvals/* 端点
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

try:
    from core.authentication import get_current_active_user
except ImportError:
    async def get_current_active_user():
        return None

try:
    from core.rbac import role_required
except ImportError:
    def role_required(role):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


def _verify_internal_key(request: Request):
    """Verify X-Internal-Key against config.INTERNAL_API_KEY (fail-closed).

    Returns ``(payload, status_code)`` to return on failure, or ``None`` when
    the caller is authorised.  An unconfigured key disables the endpoints
    instead of accepting a hard-coded development default.
    """
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        return {"status": "error", "message": "Missing internal key"}, 403

    from config import INTERNAL_API_KEY

    if not INTERNAL_API_KEY:
        return (
            {"status": "error", "message": "INTERNAL_API_KEY is not configured"},
            503,
        )
    if internal_key != INTERNAL_API_KEY:
        return {"status": "error", "message": "Invalid internal key"}, 403
    return None


@router.get("/pending")
async def get_pending_approvals(request: Request, user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取待审批列表"""
    auth_error = _verify_internal_key(request)
    if auth_error is not None:
        return auth_error
    
    # 返回真实的待审批列表（core.approval_store）
    from core.approval_store import get_pending_only_snapshot

    pending = get_pending_only_snapshot()
    approvals = [
        {
            "id": str(info.get("approval_id") or alert_id),
            "alert_id": alert_id,
            "type": info.get("type", "autoheal"),
            "status": info.get("status", "pending"),
            "created_at": info.get("created_at"),
            "proposed_by": info.get("proposed_by", "system"),
        }
        for alert_id, info in pending.items()
    ]
    return {"status": "success", "approvals": approvals}


@router.patch("/{approval_id}")
async def update_approval(
    approval_id: str,
    request: Request,
    user=Depends(get_current_active_user) if get_current_active_user else None
):
    """更新审批状态"""
    auth_error = _verify_internal_key(request)
    if auth_error is not None:
        return auth_error
    
    # 真实更新审批状态（core.approval_store）
    from core.approval_store import update_approval_status

    data = await request.json()
    action = data.get("action", "approve")
    new_status = "approved_no_script" if action == "approve" else action
    if not update_approval_status(approval_id, new_status):
        raise HTTPException(
            status_code=404, detail=f"Approval {approval_id} not found"
        )

    return {
        "status": "success",
        "approval_id": approval_id,
        "action": action,
        "message": f"Approval {approval_id} {action}d successfully",
    }


@router.post("/reject")
async def reject_approval(
    request: Request,
    user=Depends(get_current_active_user) if get_current_active_user else None
):
    """拒绝审批"""
    auth_error = _verify_internal_key(request)
    if auth_error is not None:
        return auth_error
    
    from core.approval_store import update_approval_status

    data = await request.json()
    alert_id = data.get("alert_id")
    reason = data.get("reason", "")

    if not alert_id or not update_approval_status(alert_id, "rejected"):
        raise HTTPException(
            status_code=404, detail=f"Approval for alert {alert_id} not found"
        )

    return {
        "status": "success",
        "alert_id": alert_id,
        "reason": reason,
        "message": f"Approval for alert {alert_id} rejected",
    }


@router.post("/takeover/{approval_id}")
async def takeover_approval(
    approval_id: str,
    request: Request,
    user=Depends(get_current_active_user) if get_current_active_user else None
):
    """接管审批"""
    auth_error = _verify_internal_key(request)
    if auth_error is not None:
        return auth_error
    
    from core.approval_store import get_approval, update_approval_field

    if get_approval(approval_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Approval {approval_id} not found"
        )
    operator = getattr(user, "username", None) or "unknown"
    update_approval_field(approval_id, "assigned_to", operator)

    return {
        "status": "success",
        "approval_id": approval_id,
        "assigned_to": operator,
        "message": f"Approval {approval_id} taken over",
    }


@router.post("/propose")
async def propose_approval(
    request: Request,
    user=Depends(get_current_active_user) if get_current_active_user else None
):
    """提议审批"""
    auth_error = _verify_internal_key(request)
    if auth_error is not None:
        return auth_error
    
    from datetime import datetime, timezone

    from core.approval_store import upsert_approval

    data = await request.json()
    alert_id = data.get("alert_id")
    if not alert_id:
        raise HTTPException(status_code=400, detail="alert_id is required")

    upsert_approval(
        alert_id,
        {
            "status": "pending",
            "type": data.get("type", "autoheal"),
            "proposal": data.get("proposal", ""),
            "script_key": data.get("script_key", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "proposed_by": getattr(user, "username", None) or "system",
        },
    )

    return {
        "status": "success",
        "alert_id": alert_id,
        "message": f"Approval for alert {alert_id} proposed",
    }
