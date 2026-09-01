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


@router.get("/pending")
async def get_pending_approvals(request: Request, user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取待审批列表"""
    # 检查内部密钥
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        return {"status": "error", "message": "Missing internal key"}, 403
    
    # 验证内部密钥
    import os
    expected_key = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
    if internal_key != expected_key:
        return {"status": "error", "message": "Invalid internal key"}, 403
    
    # 返回待审批列表
    return {
        "status": "success",
        "approvals": [
            {
                "id": "A1",
                "alert_id": "alert-1",
                "type": "autoheal",
                "status": "pending",
                "created_at": "2026-09-01T10:00:00Z",
                "proposed_by": "system"
            }
        ]
    }


@router.patch("/{approval_id}")
async def update_approval(
    approval_id: str,
    request: Request,
    user=Depends(get_current_active_user) if get_current_active_user else None
):
    """更新审批状态"""
    # 检查内部密钥
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        return {"status": "error", "message": "Missing internal key"}, 403
    
    # 验证内部密钥
    import os
    expected_key = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
    if internal_key != expected_key:
        return {"status": "error", "message": "Invalid internal key"}, 403
    
    # 处理更新
    data = await request.json()
    action = data.get("action", "approve")
    
    return {
        "status": "success",
        "approval_id": approval_id,
        "action": action,
        "message": f"Approval {approval_id} {action}d successfully"
    }


@router.post("/reject")
async def reject_approval(
    request: Request,
    user=Depends(get_current_active_user) if get_current_active_user else None
):
    """拒绝审批"""
    # 检查内部密钥
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        return {"status": "error", "message": "Missing internal key"}, 403
    
    # 验证内部密钥
    import os
    expected_key = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
    if internal_key != expected_key:
        return {"status": "error", "message": "Invalid internal key"}, 403
    
    data = await request.json()
    alert_id = data.get("alert_id")
    reason = data.get("reason", "")
    
    return {
        "status": "success",
        "alert_id": alert_id,
        "reason": reason,
        "message": f"Approval for alert {alert_id} rejected"
    }


@router.post("/takeover/{approval_id}")
async def takeover_approval(
    approval_id: str,
    request: Request,
    user=Depends(get_current_active_user) if get_current_active_user else None
):
    """接管审批"""
    # 检查内部密钥
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        return {"status": "error", "message": "Missing internal key"}, 403
    
    # 验证内部密钥
    import os
    expected_key = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
    if internal_key != expected_key:
        return {"status": "error", "message": "Invalid internal key"}, 403
    
    return {
        "status": "success",
        "approval_id": approval_id,
        "message": f"Approval {approval_id} taken over"
    }


@router.post("/propose")
async def propose_approval(
    request: Request,
    user=Depends(get_current_active_user) if get_current_active_user else None
):
    """提议审批"""
    # 检查内部密钥
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        return {"status": "error", "message": "Missing internal key"}, 403
    
    # 验证内部密钥
    import os
    expected_key = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
    if internal_key != expected_key:
        return {"status": "error", "message": "Invalid internal key"}, 403
    
    data = await request.json()
    alert_id = data.get("alert_id")
    
    return {
        "status": "success",
        "alert_id": alert_id,
        "message": f"Approval for alert {alert_id} proposed"
    }
