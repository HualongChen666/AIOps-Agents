# -*- coding: utf-8 -*-
"""
HITL API Router
Phase 4 集成: HITL（人在回路）路由
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth_db import User
from core.auth_service import require_roles
from core.command_guard import record_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hitl", tags=["hitl"])

# Phase 4 集成: HITL 组件
try:
    from core.hitl import (
        ApprovalHistory,
        ApprovalNotifier,
        ApprovalStep,
        ApprovalTimeoutHandler,
        ApprovalWorkflow,
        ConditionalApproval,
        MultiLevelApprover,
    )

    HITL_AVAILABLE = True
except ImportError:
    HITL_AVAILABLE = False
    logger.warning("Phase 4 HITL not available")

try:
    from core.agent.subagent import SubAgentDispatcher

    SUBAGENT_AVAILABLE = True
except ImportError:
    SUBAGENT_AVAILABLE = False
    SubAgentDispatcher = None  # type: ignore[misc,assignment]


_approval_workflow: Optional[ApprovalWorkflow] = None
_multi_level_approver: Optional[MultiLevelApprover] = None
_conditional_approval: Optional[ConditionalApproval] = None
_approval_history: Optional[ApprovalHistory] = None
_approval_timeout_handler: Optional[ApprovalTimeoutHandler] = None
_approval_notifier: Optional[ApprovalNotifier] = None

if HITL_AVAILABLE:
    try:
        _approval_workflow = ApprovalWorkflow()
        _multi_level_approver = MultiLevelApprover(_approval_workflow)
        _conditional_approval = ConditionalApproval()
        _approval_history = ApprovalHistory()
        _approval_notifier = ApprovalNotifier()
        _approval_notifier.auto_configure_from_env()
        _approval_timeout_handler = ApprovalTimeoutHandler(_approval_workflow, _approval_notifier)
        logger.info("Phase 4 HITL components initialized")
    except Exception as e:
        logger.error(f"Failed to initialize HITL components: {e}")
        HITL_AVAILABLE = False
        _approval_notifier = None
        _approval_timeout_handler = None


@router.get(
    "/health",
    summary="HITL健康检查",
    responses={
        200: {
            "description": "健康状态",
            "content": {
                "application/json": {"example": {"status": "healthy", "hitl_available": True}}
            },
        },
    },
)
async def hitl_health() -> Dict[str, Any]:
    """HITL health check endpoint"""
    status = "healthy" if HITL_AVAILABLE else "degraded"
    return {"status": status, "hitl_available": HITL_AVAILABLE}


@router.post(
    "/approval/request",
    summary="创建审批请求",
    responses={
        200: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "request_id": "req-123",
                        "workflow_id": "default",
                        "title": "修复方案审批",
                        "status": "pending",
                        "created_at": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        503: {"description": "HITL不可用"},
        500: {"description": "创建失败"},
    },
)
async def create_approval_request(
    request: Request,
    request_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create approval request"""
    if not HITL_AVAILABLE or not _approval_workflow:
        raise HTTPException(status_code=503, detail="HITL not available")

    try:
        steps = [
            ApprovalStep(
                step_id=step["step_id"],
                name=step["name"],
                approver=step["approver"],
                required=step.get("required", True),
                timeout_minutes=step.get("timeout_minutes", 60),
            )
            for step in request_data.get("steps", [])
        ]

        tenant_id = getattr(request.state, "tenant_id", "default")
        request = _approval_workflow.create_request(
            workflow_id=request_data.get("workflow_id", "default"),
            title=request_data.get("title", "Approval Request"),
            description=request_data.get("description", ""),
            steps=steps,
            context=request_data.get("context", {}),
            tenant_id=tenant_id,
        )

        if _approval_timeout_handler is not None:
            _approval_timeout_handler.start_monitoring(request.request_id)

        if _approval_notifier is not None and request.steps:
            first_step = request.steps[0]
            notify_result = _approval_notifier.send_approval_request(
                first_step.approver, request.to_dict()
            )
            if asyncio.iscoroutine(notify_result):
                await notify_result

        return request.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Request creation failed: {str(e)}")


@router.post(
    "/approval/approve",
    summary="批准审批步骤",
    responses={
        200: {
            "description": "批准成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "approved",
                        "request_id": "req-123",
                        "step_id": "step-1",
                        "approved_at": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        400: {"description": "批准失败"},
        503: {"description": "HITL不可用"},
        500: {"description": "批准失败"},
    },
)
async def approve_step(
    request_id: str,
    step_id: str,
    comment: Optional[str] = None,
    approver: Optional[str] = None,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> Dict[str, Any]:
    """Approve an approval step"""
    if not HITL_AVAILABLE or not _approval_workflow:
        raise HTTPException(status_code=503, detail="HITL not available")

    effective_approver = approver or current_user.username
    tenant_id = (
        str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else "default"
    )
    try:
        success = _approval_workflow.approve_step(
            request_id, step_id, effective_approver, comment, tenant_id=tenant_id
        )
        if not success:
            raise HTTPException(status_code=400, detail="Approval failed")

        if _approval_timeout_handler is not None:
            _approval_timeout_handler.stop_monitoring(request_id)

        record_audit(
            host=request_id,
            command="HITL_APPROVE",
            risk_level="high",
            executor=effective_approver,
            result="approved",
            user_id=str(current_user.id) if current_user.id else None,
            tenant_id=(
                str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None
            ),
        )

        return {"status": "approved", "request_id": request_id, "step_id": step_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@router.post(
    "/approval/reject",
    summary="拒绝审批步骤",
    responses={
        200: {
            "description": "拒绝成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "rejected",
                        "request_id": "req-123",
                        "step_id": "step-1",
                        "rejected_at": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        400: {"description": "拒绝失败"},
        503: {"description": "HITL不可用"},
        500: {"description": "拒绝失败"},
    },
)
async def reject_step(
    request_id: str,
    step_id: str,
    comment: Optional[str] = None,
    approver: Optional[str] = None,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> Dict[str, Any]:
    """Reject an approval step"""
    if not HITL_AVAILABLE or not _approval_workflow:
        raise HTTPException(status_code=503, detail="HITL not available")

    effective_approver = approver or current_user.username
    tenant_id = (
        str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else "default"
    )
    try:
        success = _approval_workflow.reject_step(
            request_id, step_id, effective_approver, comment, tenant_id=tenant_id
        )
        if not success:
            raise HTTPException(status_code=400, detail="Rejection failed")

        if _approval_timeout_handler is not None:
            _approval_timeout_handler.stop_monitoring(request_id)

        record_audit(
            host=request_id,
            command="HITL_REJECT",
            risk_level="high",
            executor=effective_approver,
            result="rejected",
            user_id=str(current_user.id) if current_user.id else None,
            tenant_id=(
                str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None
            ),
        )

        return {"status": "rejected", "request_id": request_id, "step_id": step_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rejection failed: {str(e)}")


@router.get(
    "/approval/{request_id}",
    summary="获取审批状态",
    responses={
        200: {
            "description": "审批状态",
            "content": {
                "application/json": {
                    "example": {
                        "request_id": "req-123",
                        "status": "approved",
                        "current_step": "step-2",
                        "steps": [
                            {
                                "step_id": "step-1",
                                "status": "approved",
                                "approver": "admin",
                            }
                        ],
                        "created_at": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        503: {"description": "HITL不可用"},
        500: {"description": "状态查询失败"},
    },
)
async def get_approval_status(request: Request, request_id: str) -> Dict[str, Any]:
    """Get approval request status"""
    if not HITL_AVAILABLE or not _approval_workflow:
        raise HTTPException(status_code=503, detail="HITL not available")

    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return _approval_workflow.get_request_status(request_id, tenant_id=tenant_id) or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post(
    "/takeover/{request_id}",
    summary="人工接管/取消审批工作流",
    responses={
        200: {"description": "接管成功"},
        404: {"description": "请求不存在"},
        503: {"description": "HITL不可用"},
    },
)
async def manual_takeover(
    request: Request, request_id: str, reason: str = "manual takeover"
) -> Dict[str, Any]:
    """人工接管：取消活跃的审批工作流并把状态标记为已接管"""
    if not HITL_AVAILABLE or not _approval_workflow:
        raise HTTPException(status_code=503, detail="HITL not available")

    try:
        if _approval_timeout_handler is not None:
            _approval_timeout_handler.stop_monitoring(request_id)

        tenant_id = getattr(request.state, "tenant_id", "default")
        success = _approval_workflow.cancel_request(request_id, reason=reason, tenant_id=tenant_id)
        if not success:
            raise HTTPException(status_code=404, detail="Request not found or not active")
        return {"request_id": request_id, "status": "taken_over", "reason": reason}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Takeover failed: {str(e)}")


@router.post(
    "/interrupt/{agent_id}",
    summary="中断运行中的子代理",
    responses={
        200: {"description": "中断请求已发送"},
        404: {"description": "子代理不存在"},
        503: {"description": "子代理调度器不可用"},
    },
)
async def interrupt_agent(agent_id: str) -> Dict[str, Any]:
    """中断/终止指定子代理的执行"""
    if not SUBAGENT_AVAILABLE or SubAgentDispatcher is None:
        raise HTTPException(status_code=503, detail="SubAgent dispatcher not available")

    try:
        # O12: support both module-level dispatcher and a default singleton
        dispatcher = getattr(SubAgentDispatcher, "_instance", None) or SubAgentDispatcher()
        terminated = dispatcher.terminate(agent_id)
        if not terminated:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"agent_id": agent_id, "status": "interrupted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interrupt failed: {str(e)}")
