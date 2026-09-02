# -*- coding: utf-8 -*-
"""变更管理 API 路由."""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.auth_db import User
from core.auth_service import require_roles
from core.change_management_engine import (
    AuditEntry,
    ChangeManagementError,
    ChangeRequest,
    ChangeStatus,
    RiskLevel,
    add_audit_comment,
    approve_request,
    assign_approver,
    bulk_create_requests,
    bulk_delete_requests,
    cancel_request,
    clone_request,
    create_request,
    delete_request,
    export_requests,
    get_request,
    get_request_audit_log,
    get_request_statistics,
    import_requests,
    implement_request,
    list_requests,
    list_requests_by_approver,
    list_requests_by_requester,
    list_requests_by_risk_level,
    list_requests_by_service,
    list_requests_by_status,
    reject_request,
    review_request,
    rollback_request,
    schedule_request,
    search_requests,
    submit_request,
    update_request,
    validate_request,
)
from core.command_guard import record_audit

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
            tenant_id=(
                str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None
            ),
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
            tenant_id=(
                str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None
            ),
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
            tenant_id=(
                str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None
            ),
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
            tenant_id=(
                str(current_user.tenant_id) if getattr(current_user, "tenant_id", None) else None
            ),
        )
        return result
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("回滚变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"回滚变更请求失败: {e}")


# ============================================================================
# 新增32个API端点
# ============================================================================


class ChangeRequestUpdate(BaseModel):
    """更新变更请求请求体."""

    title: str | None = Field(None, description="标题")
    description: str | None = Field(None, description="描述")
    approver: str | None = Field(None, description="审批人")
    risk_level: RiskLevel | None = Field(None, description="风险等级")
    schedule: str | None = Field(None, description="计划执行时间/窗口")
    affected_services: list[str] | None = Field(None, description="受影响服务")
    implementation_plan: str | None = Field(None, description="实施方案")
    rollback_plan: str | None = Field(None, description="回滚方案")


@router.put(
    "/requests/{id}",
    response_model=ChangeRequest,
    summary="更新变更请求",
)
async def put_change_request(
    request: Request,
    id: str,
    payload: ChangeRequestUpdate,
) -> ChangeRequest:
    """更新变更请求信息."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        update_data = {k: v for k, v in payload.model_dump(mode="json").items() if v is not None}
        return await update_request(id, update_data, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("更新变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新变更请求失败: {e}")


@router.delete(
    "/requests/{id}",
    status_code=204,
    summary="删除变更请求",
)
async def delete_change_request(
    request: Request,
    id: str,
) -> None:
    """删除草稿或已拒绝状态的变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        await delete_request(id, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("删除变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除变更请求失败: {e}")


@router.post(
    "/requests/{id}/cancel",
    response_model=ChangeRequest,
    summary="取消变更请求",
)
async def cancel_change_request(
    request: Request,
    id: str,
) -> ChangeRequest:
    """取消待审批或已批准的变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await cancel_request(id, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("取消变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"取消变更请求失败: {e}")


@router.post(
    "/requests/{id}/review",
    response_model=ChangeRequest,
    summary="审核变更请求",
)
async def review_change_request(
    request: Request,
    id: str,
) -> ChangeRequest:
    """将变更请求转入审核状态."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await review_request(id, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("审核变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"审核变更请求失败: {e}")


@router.get(
    "/requests/status/{status}",
    response_model=list[ChangeRequest],
    summary="按状态筛选变更请求",
)
async def get_requests_by_status(
    request: Request,
    status: ChangeStatus,
) -> list[ChangeRequest]:
    """按状态筛选变更请求列表."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests_by_status(status, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("按状态筛选变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"按状态筛选变更请求失败: {e}")


@router.get(
    "/requests/risk/{risk_level}",
    response_model=list[ChangeRequest],
    summary="按风险等级筛选变更请求",
)
async def get_requests_by_risk_level(
    request: Request,
    risk_level: RiskLevel,
) -> list[ChangeRequest]:
    """按风险等级筛选变更请求列表."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests_by_risk_level(risk_level, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("按风险等级筛选变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"按风险等级筛选变更请求失败: {e}")


@router.get(
    "/requests/requester/{requester}",
    response_model=list[ChangeRequest],
    summary="按申请人筛选变更请求",
)
async def get_requests_by_requester(
    request: Request,
    requester: str,
) -> list[ChangeRequest]:
    """按申请人筛选变更请求列表."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests_by_requester(requester, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("按申请人筛选变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"按申请人筛选变更请求失败: {e}")


@router.get(
    "/requests/approver/{approver}",
    response_model=list[ChangeRequest],
    summary="按审批人筛选变更请求",
)
async def get_requests_by_approver(
    request: Request,
    approver: str,
) -> list[ChangeRequest]:
    """按审批人筛选变更请求列表."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests_by_approver(approver, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("按审批人筛选变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"按审批人筛选变更请求失败: {e}")


@router.get(
    "/requests/service/{service}",
    response_model=list[ChangeRequest],
    summary="按服务筛选变更请求",
)
async def get_requests_by_service(
    request: Request,
    service: str,
) -> list[ChangeRequest]:
    """按受影响服务筛选变更请求列表."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests_by_service(service, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("按服务筛选变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"按服务筛选变更请求失败: {e}")


@router.get(
    "/requests/{id}/audit-log",
    response_model=list[AuditEntry],
    summary="获取变更请求审计日志",
)
async def get_change_request_audit_log(
    request: Request,
    id: str,
) -> list[AuditEntry]:
    """获取变更请求的审计日志."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await get_request_audit_log(id, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _logger.error("获取审计日志失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取审计日志失败: {e}")


class AuditCommentRequest(BaseModel):
    """审计评论请求体."""

    comment: str = Field(..., description="评论内容")
    actor: str = Field(..., description="操作人")


@router.post(
    "/requests/{id}/audit-comment",
    response_model=ChangeRequest,
    summary="添加审计评论",
)
async def post_audit_comment(
    request: Request,
    id: str,
    payload: AuditCommentRequest,
) -> ChangeRequest:
    """为变更请求添加审计评论."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await add_audit_comment(id, payload.comment, payload.actor, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _logger.error("添加审计评论失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加审计评论失败: {e}")


class BulkCreateRequest(BaseModel):
    """批量创建请求体."""

    requests: list[ChangeRequestCreate] = Field(..., description="变更请求列表")


@router.post(
    "/requests/bulk",
    response_model=list[ChangeRequest],
    summary="批量创建变更请求",
)
async def post_bulk_change_requests(
    request: Request,
    payload: BulkCreateRequest,
) -> list[ChangeRequest]:
    """批量创建变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        data_list = [req.model_dump(mode="json") for req in payload.requests]
        return await bulk_create_requests(data_list, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("批量创建变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量创建变更请求失败: {e}")


class BulkDeleteRequest(BaseModel):
    """批量删除请求体."""

    request_ids: list[str] = Field(..., description="变更请求ID列表")


@router.post(
    "/requests/bulk-delete",
    response_model=dict[str, bool],
    summary="批量删除变更请求",
)
async def post_bulk_delete_change_requests(
    request: Request,
    payload: BulkDeleteRequest,
) -> dict[str, bool]:
    """批量删除变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await bulk_delete_requests(payload.request_ids, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("批量删除变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量删除变更请求失败: {e}")


@router.get(
    "/requests/search",
    response_model=list[ChangeRequest],
    summary="搜索变更请求",
)
async def search_change_requests(
    request: Request,
    q: str = Query(..., description="搜索关键词"),
) -> list[ChangeRequest]:
    """搜索变更请求（标题和描述）."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await search_requests(q, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("搜索变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索变更请求失败: {e}")


@router.get(
    "/statistics",
    response_model=dict[str, Any],
    summary="获取变更请求统计信息",
)
async def get_change_statistics(
    request: Request,
) -> dict[str, Any]:
    """获取变更请求统计信息."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await get_request_statistics(tenant_id=tenant_id)
    except Exception as e:
        _logger.error("获取统计信息失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {e}")


@router.get(
    "/requests/{id}/validate",
    response_model=dict[str, Any],
    summary="验证变更请求",
)
async def validate_change_request(
    request: Request,
    id: str,
) -> dict[str, Any]:
    """验证变更请求的完整性."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await validate_request(id, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _logger.error("验证变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"验证变更请求失败: {e}")


class ScheduleRequestModel(BaseModel):
    """设置计划请求体."""

    schedule: str = Field(..., description="计划执行时间")


@router.post(
    "/requests/{id}/schedule",
    response_model=ChangeRequest,
    summary="设置变更请求执行计划",
)
async def schedule_change_request(
    request: Request,
    id: str,
    payload: ScheduleRequestModel,
) -> ChangeRequest:
    """设置变更请求的执行计划时间."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await schedule_request(id, payload.schedule, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("设置执行计划失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"设置执行计划失败: {e}")


class AssignApproverRequest(BaseModel):
    """分配审批人请求体."""

    approver: str = Field(..., description="审批人")


@router.post(
    "/requests/{id}/assign-approver",
    response_model=ChangeRequest,
    summary="分配审批人",
)
async def assign_change_approver(
    request: Request,
    id: str,
    payload: AssignApproverRequest,
) -> ChangeRequest:
    """为变更请求分配审批人."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await assign_approver(id, payload.approver, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("分配审批人失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"分配审批人失败: {e}")


@router.post(
    "/requests/{id}/clone",
    response_model=ChangeRequest,
    summary="克隆变更请求",
)
async def clone_change_request(
    request: Request,
    id: str,
) -> ChangeRequest:
    """克隆变更请求创建副本."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await clone_request(id, tenant_id=tenant_id)
    except ChangeManagementError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _logger.error("克隆变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"克隆变更请求失败: {e}")


@router.get(
    "/export",
    response_model=dict[str, Any],
    summary="导出变更请求数据",
)
async def export_change_requests(
    request: Request,
) -> dict[str, Any]:
    """导出变更请求数据."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await export_requests(tenant_id=tenant_id)
    except Exception as e:
        _logger.error("导出变更请求数据失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出变更请求数据失败: {e}")


class ImportRequest(BaseModel):
    """导入请求体."""

    requests: list[dict[str, Any]] = Field(..., description="变更请求数据列表")
    overwrite: bool = Field(default=False, description="是否覆盖已存在的请求")


@router.post(
    "/import",
    response_model=dict[str, Any],
    summary="导入变更请求数据",
)
async def import_change_requests(
    request: Request,
    payload: ImportRequest,
) -> dict[str, Any]:
    """导入变更请求数据."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        data = {"requests": payload.requests}
        return await import_requests(data, tenant_id=tenant_id, overwrite=payload.overwrite)
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("导入变更请求数据失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入变更请求数据失败: {e}")


# 额外的业务端点


class BatchUpdateRequest(BaseModel):
    """批量更新请求体."""

    request_ids: list[str] = Field(..., description="变更请求ID列表")
    updates: ChangeRequestUpdate = Field(..., description="更新内容")


@router.post(
    "/requests/batch-update",
    response_model=list[ChangeRequest],
    summary="批量更新变更请求",
)
async def batch_update_change_requests(
    request: Request,
    payload: BatchUpdateRequest,
) -> list[ChangeRequest]:
    """批量更新变更请求（分批处理避免速率限制）."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        update_data = {k: v for k, v in payload.updates.model_dump(mode="json").items() if v is not None}
        results = []
        batch_size = 10
        for i in range(0, len(payload.request_ids), batch_size):
            batch = payload.request_ids[i:i + batch_size]
            for request_id in batch:
                try:
                    result = await update_request(request_id, update_data, tenant_id=tenant_id)
                    results.append(result)
                except ChangeManagementError as e:
                    _logger.warning("更新请求 %s 失败: %s", request_id, e)
        return results
    except Exception as e:
        _logger.error("批量更新变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量更新变更请求失败: {e}")


@router.get(
    "/requests/{id}/history",
    response_model=list[dict[str, Any]],
    summary="获取变更请求历史",
)
async def get_change_request_history(
    request: Request,
    id: str,
) -> list[dict[str, Any]]:
    """获取变更请求的完整历史记录."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        change_request = await get_request(id, tenant_id=tenant_id)
        history = []
        for entry in change_request.audit_log:
            history.append({
                "timestamp": entry.timestamp,
                "actor": entry.actor,
                "action": entry.action,
                "message": entry.message,
            })
        return sorted(history, key=lambda x: x["timestamp"])
    except ChangeManagementError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _logger.error("获取变更请求历史失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取变更请求历史失败: {e}")


@router.get(
    "/requests/pending-approval",
    response_model=list[ChangeRequest],
    summary="获取待审批变更请求",
)
async def get_pending_approval_requests(
    request: Request,
) -> list[ChangeRequest]:
    """获取所有待审批状态的变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests_by_status(ChangeStatus.PENDING, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("获取待审批变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取待审批变更请求失败: {e}")


@router.get(
    "/requests/approved",
    response_model=list[ChangeRequest],
    summary="获取已批准变更请求",
)
async def get_approved_requests(
    request: Request,
) -> list[ChangeRequest]:
    """获取所有已批准状态的变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests_by_status(ChangeStatus.APPROVED, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("获取已批准变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取已批准变更请求失败: {e}")


@router.get(
    "/requests/in-progress",
    response_model=list[ChangeRequest],
    summary="获取进行中变更请求",
)
async def get_in_progress_requests(
    request: Request,
) -> list[ChangeRequest]:
    """获取所有进行中状态的变更请求（待审批、审核中、已批准）."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        all_requests = await list_requests(tenant_id=tenant_id)
        in_progress = [
            r for r in all_requests
            if r.status in (ChangeStatus.PENDING, ChangeStatus.REVIEW, ChangeStatus.APPROVED)
        ]
        return sorted(in_progress, key=lambda r: r.id)
    except Exception as e:
        _logger.error("获取进行中变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取进行中变更请求失败: {e}")


@router.get(
    "/requests/high-risk",
    response_model=list[ChangeRequest],
    summary="获取高风险变更请求",
)
async def get_high_risk_requests(
    request: Request,
) -> list[ChangeRequest]:
    """获取所有高风险等级的变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        return await list_requests_by_risk_level(RiskLevel.HIGH, tenant_id=tenant_id)
    except Exception as e:
        _logger.error("获取高风险变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取高风险变更请求失败: {e}")


@router.get(
    "/dashboard/summary",
    response_model=dict[str, Any],
    summary="获取变更管理仪表板摘要",
)
async def get_dashboard_summary(
    request: Request,
) -> dict[str, Any]:
    """获取变更管理仪表板摘要信息."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        stats = await get_request_statistics(tenant_id=tenant_id)
        pending = await list_requests_by_status(ChangeStatus.PENDING, tenant_id=tenant_id)
        approved = await list_requests_by_status(ChangeStatus.APPROVED, tenant_id=tenant_id)
        high_risk = await list_requests_by_risk_level(RiskLevel.HIGH, tenant_id=tenant_id)
        return {
            "total": stats["total"],
            "pending_count": len(pending),
            "approved_count": len(approved),
            "high_risk_count": len(high_risk),
            "by_status": stats["by_status"],
            "by_risk_level": stats["by_risk_level"],
        }
    except Exception as e:
        _logger.error("获取仪表板摘要失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取仪表板摘要失败: {e}")


@router.post(
    "/requests/{id}/reopen",
    response_model=ChangeRequest,
    summary="重新打开变更请求",
)
async def reopen_change_request(
    request: Request,
    id: str,
) -> ChangeRequest:
    """重新打开已拒绝或已回滚的变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        change_request = await get_request(id, tenant_id=tenant_id)
        if change_request.status not in (ChangeStatus.REJECTED, ChangeStatus.ROLLED_BACK):
            raise ChangeManagementError("只有已拒绝或已回滚的变更请求可以重新打开")
        change_request.status = ChangeStatus.DRAFT
        change_request.audit_log.append(
            AuditEntry(
                actor=change_request.approver or change_request.requester or "system",
                action="reopened",
                message="变更请求已重新打开",
            )
        )
        from core.change_management_engine import _persist
        await _persist()
        return change_request
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("重新打开变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新打开变更请求失败: {e}")


@router.get(
    "/requests/recent",
    response_model=list[ChangeRequest],
    summary="获取最近的变更请求",
)
async def get_recent_requests(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100, description="返回数量限制"),
) -> list[ChangeRequest]:
    """获取最近的变更请求."""
    try:
        tenant_id = getattr(request.state, "tenant_id", "default")
        all_requests = await list_requests(tenant_id=tenant_id)
        sorted_requests = sorted(
            all_requests,
            key=lambda r: r.audit_log[-1].timestamp if r.audit_log else "",
            reverse=True
        )
        return sorted_requests[:limit]
    except Exception as e:
        _logger.error("获取最近变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取最近变更请求失败: {e}")


@router.post(
    "/requests/batch-approve",
    response_model=dict[str, str],
    summary="批量审批变更请求",
)
async def batch_approve_requests(
    request: Request,
    payload: BulkDeleteRequest,
    current_user: User = Depends(require_roles("admin")),
) -> dict[str, str]:
    """批量审批变更请求（分批处理避免速率限制）."""
    try:
        tenant_id = str(current_user.tenant_id)
        results = {}
        batch_size = 10
        for i in range(0, len(payload.request_ids), batch_size):
            batch = payload.request_ids[i:i + batch_size]
            for request_id in batch:
                try:
                    await approve_request(request_id, tenant_id=tenant_id)
                    record_audit(
                        host=request_id,
                        command="CHANGE_APPROVE",
                        risk_level="high",
                        executor=current_user.username,
                        result="approved",
                        user_id=str(current_user.id) if current_user.id else None,
                        tenant_id=tenant_id,
                    )
                    results[request_id] = "approved"
                except ChangeManagementError as e:
                    results[request_id] = f"failed: {e}"
                    _logger.warning("审批请求 %s 失败: %s", request_id, e)
        return results
    except Exception as e:
        _logger.error("批量审批变更请求失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量审批变更请求失败: {e}")


@router.get(
    "/health",
    response_model=dict[str, str],
    summary="变更管理服务健康检查",
)
async def health_check() -> dict[str, str]:
    """变更管理服务健康检查端点."""
    return {
        "status": "healthy",
        "service": "change-management",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
