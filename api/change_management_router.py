# -*- coding: utf-8 -*-
"""变更管理 API 路由."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth_db import User
from core.auth_service import require_roles
from core.command_guard import record_audit
from core.change_management_engine import (
    ChangeManagementError,
    ChangeRequest,
    RiskLevel,
    approve_request,
    create_request,
    get_request,
    implement_request,
    list_requests,
    reject_request,
    rollback_request,
    submit_request,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/change-management", tags=["变更管理"])


class ChangeRequestCreate(BaseModel):
    """创建变更请求请求体."""

    title: str = Field(..., description="标题")
    description: str = Field(default="", description="描述")
    requester: str = Field(..., description="申请人")
    approver: str = Field(default="", description="审批人")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="风险等级")
    schedule: str = Field(default="", description="计划执行时间/窗口")
    affected_services: list[str] = Field(default_factory=list, description="受影响服务")
    implementation_plan: str = Field(default="", description="实施方案")
    rollback_plan: str = Field(default="", description="回滚方案")


@router.get("/requests", response_model=list[ChangeRequest], summary="列出所有变更请求")
async def get_change_requests(request: Request) -> list[ChangeRequest]:
    """获取当前租户变更请求列表."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests(tenant_id=tenant_id)
    except Exception as e:
        _logger.error("获取变更请求列表失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取变更请求列表失败: {e}")


@router.post(
    "/requests",
    response_model=ChangeRequest,
    status_code=201,
    summary="创建变更请求",
)
async def post_change_request(request: Request, payload: ChangeRequestCreate) -> ChangeRequest:
    """创建新的变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await create_request(payload.model_dump(mode="json"), tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("创建变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建变更请求失败: {e}")


@router.get("/requests/{id}", response_model=ChangeRequest, summary="获取单个变更请求")
async def get_change_request(request: Request, id: str) -> ChangeRequest:
    """根据 ID 获取单个变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await get_request(id, tenant_id=tenant_id)
    except (ChangeManagementError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _logger.error("获取变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取变更请求失败: {e}")


@router.post(
    "/requests/{id}/submit",
    response_model=ChangeRequest,
    summary="提交变更请求",
)
async def submit_change_request(request: Request, id: str) -> ChangeRequest:
    """将草稿状态的变更请求提交进入审批."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await submit_request(id, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("提交变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交变更请求失败: {e}")


@router.post(
    "/requests/{id}/approve",
    response_model=ChangeRequest,
    summary="审批通过变更请求",
)
async def approve_change_request(
    id: str,
    current_user: User = Depends(require_roles("admin")),
) -> ChangeRequest:
    """审批通过待审批/审核中的变更请求."""
    try:
        tenant_id = str(current_user.tenant_id)
        result = await approve_request(id, tenant_id=tenant_id)
        record_audit(
            host=id,
            command="CHANGE_APPROVE",
            risk_level="high",
            executor=current_user.username,
            result="approved",
            user_id=str(current_user.id) if current_user.id else None,
            tenant_id=str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None,
        )
        return result
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("审批变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"审批变更请求失败: {e}")


@router.post(
    "/requests/{id}/reject",
    response_model=ChangeRequest,
    summary="拒绝变更请求",
)
async def reject_change_request(
    id: str,
    current_user: User = Depends(require_roles("admin")),
) -> ChangeRequest:
    """拒绝变更请求."""
    try:
        tenant_id = str(current_user.tenant_id)
        result = await reject_request(id, tenant_id=tenant_id)
        record_audit(
            host=id,
            command="CHANGE_REJECT",
            risk_level="high",
            executor=current_user.username,
            result="rejected",
            user_id=str(current_user.id) if current_user.id else None,
            tenant_id=str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None,
        )
        return result
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("拒绝变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"拒绝变更请求失败: {e}")


@router.post(
    "/requests/{id}/implement",
    response_model=ChangeRequest,
    summary="实施变更请求",
)
async def implement_change_request(
    id: str,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> ChangeRequest:
    """实施已批准的变更请求."""
    try:
        tenant_id = str(current_user.tenant_id)
        result = await implement_request(id, tenant_id=tenant_id)
        record_audit(
            host=id,
            command="CHANGE_IMPLEMENT",
            risk_level="critical",
            executor=current_user.username,
            result="implemented",
            user_id=str(current_user.id) if current_user.id else None,
            tenant_id=str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None,
        )
        return result
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("实施变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"实施变更请求失败: {e}")


@router.post(
    "/requests/{id}/rollback",
    response_model=ChangeRequest,
    summary="回滚变更请求",
)
async def rollback_change_request(
    id: str,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> ChangeRequest:
    """回滚已实施的变更请求."""
    try:
        tenant_id = str(current_user.tenant_id)
        result = await rollback_request(id, tenant_id=tenant_id)
        record_audit(
            host=id,
            command="CHANGE_ROLLBACK",
            risk_level="critical",
            executor=current_user.username,
            result="rolled_back",
            user_id=str(current_user.id) if current_user.id else None,
            tenant_id=str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None,
        )
        return result
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("回滚变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"回滚变更请求失败: {e}")
