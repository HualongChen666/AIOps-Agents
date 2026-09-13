# -*- coding: utf-8 -*-
"""Change approval API (``/api/v1/change-approval``).

Backs ``frontend/app/workflow/change-approval``.  Approvals are not a separate
store: they are the *approval view* of the durable change requests owned by
:mod:`core.change_management_engine`.  Approving / rejecting here advances the
real change lifecycle (``pending → approved`` / ``rejected``) and appends the
reviewer's comment to the request's audit trail.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.change_management_engine import (
    ChangeManagementError,
    add_audit_comment,
    approve_request,
    get_request,
    list_requests,
    reject_request,
)
from core.change_page_support import to_approval
from core.workflow_page_support import tenant_of

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/change-approval", tags=["变更审批"])


class DecisionBody(BaseModel):
    """审批决策请求体。"""

    comment: str = Field(default="", description="审批意见")


def _actor(request: Request) -> str:
    user = getattr(request.state, "user", None)
    return str(getattr(user, "username", None) or "admin")


@router.get("", summary="列出变更审批请求")
async def list_approvals(request: Request) -> list[dict[str, Any]]:
    """Return every change request projected onto the approval page model."""
    try:
        requests = await list_requests(tenant_id=tenant_of(request))
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("加载审批请求失败: %s", exc)
        raise HTTPException(status_code=500, detail="加载审批请求失败") from exc
    return [to_approval(req.model_dump(mode="json")) for req in requests]


@router.post("/{request_id}/approve", summary="批准变更请求")
async def approve(request_id: str, body: DecisionBody, request: Request) -> dict[str, Any]:
    """Approve a pending change request and record the reviewer's comment."""
    tenant = tenant_of(request)
    try:
        await approve_request(request_id, tenant_id=tenant)
        if body.comment:
            await add_audit_comment(request_id, body.comment, actor=_actor(request), tenant_id=tenant)
        updated = await get_request(request_id, tenant_id=tenant)
    except ChangeManagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("批准变更请求失败: %s", exc)
        raise HTTPException(status_code=500, detail="批准变更请求失败") from exc
    return to_approval(updated.model_dump(mode="json"))


@router.post("/{request_id}/reject", summary="拒绝变更请求")
async def reject(request_id: str, body: DecisionBody, request: Request) -> dict[str, Any]:
    """Reject a change request and record the reviewer's comment."""
    tenant = tenant_of(request)
    try:
        await reject_request(request_id, tenant_id=tenant)
        if body.comment:
            await add_audit_comment(request_id, body.comment, actor=_actor(request), tenant_id=tenant)
        updated = await get_request(request_id, tenant_id=tenant)
    except ChangeManagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("拒绝变更请求失败: %s", exc)
        raise HTTPException(status_code=500, detail="拒绝变更请求失败") from exc
    return to_approval(updated.model_dump(mode="json"))
