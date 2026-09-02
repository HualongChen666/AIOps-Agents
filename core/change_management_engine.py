# -*- coding: utf-8 -*-
"""变更管理引擎 - JSON 文件持久化的变更请求生命周期实现."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from config import BASE_DIR

# ============================================================
# 数据目录与持久化文件
# ============================================================
_DATA_DIR: Path = BASE_DIR / "data"
_DATA_FILE: Path = _DATA_DIR / "change_requests.json"

_LOCK: asyncio.Lock = asyncio.Lock()
_LOADED: bool = False
_REQUESTS: dict[str, ChangeRequest] = {}


class ChangeManagementError(Exception):
    """变更管理业务异常."""


class ChangeStatus(str, Enum):
    """变更请求生命周期状态."""

    DRAFT = "draft"
    PENDING = "pending"
    REVIEW = "review"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    """风险等级."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AuditEntry(BaseModel):
    """审计日志条目."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str = Field(..., description="操作人")
    action: str = Field(..., description="操作动作")
    message: str = Field(default="", description="操作说明")


class ChangeRequest(BaseModel):
    """变更请求模型."""

    id: str = Field(default_factory=lambda: _generate_id(), description="变更请求唯一标识")
    tenant_id: str = Field(default="default", description="租户 ID")
    title: str = Field(..., description="标题")
    description: str = Field(default="", description="描述")
    requester: str = Field(..., description="申请人")
    approver: str = Field(default="", description="审批人")
    status: ChangeStatus = Field(default=ChangeStatus.DRAFT, description="状态")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="风险等级")
    schedule: str = Field(default="", description="计划执行时间/窗口")
    affected_services: list[str] = Field(default_factory=list, description="受影响服务")
    implementation_plan: str = Field(default="", description="实施方案")
    rollback_plan: str = Field(default="", description="回滚方案")
    audit_log: list[AuditEntry] = Field(default_factory=list, description="审计日志")


def _generate_id() -> str:
    """生成变更请求 ID."""
    return f"CR-{uuid.uuid4().hex[:8].upper()}"


async def _load_store() -> None:
    """从 JSON 文件加载变更请求数据."""
    global _LOADED, _REQUESTS
    if _LOADED:
        return

    async with _LOCK:
        if _LOADED:
            return

        if _DATA_FILE.is_file():
            raw_text = await asyncio.to_thread(partial(_DATA_FILE.read_text, encoding="utf-8"))
            raw_data: dict[str, Any] = json.loads(raw_text)
            _REQUESTS = {rid: ChangeRequest(**payload) for rid, payload in raw_data.items()}
        else:
            _REQUESTS = {}

        _LOADED = True


async def _persist() -> None:
    """将变更请求数据保存到 JSON 文件."""
    import os
    import stat

    async with _LOCK:
        await asyncio.to_thread(partial(_DATA_DIR.mkdir, parents=True, exist_ok=True))
        payload = {rid: req.model_dump(mode="json") for rid, req in _REQUESTS.items()}
        await asyncio.to_thread(
            partial(
                _DATA_FILE.write_text,
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        )

        # Set restrictive permissions for change request file (600 - owner read/write only)
        def _set_permissions():
            try:
                os.chmod(_DATA_FILE, stat.S_IRUSR | stat.S_IWUSR)
            except (OSError, AttributeError):
                # chmod may fail on Windows or non-Unix systems
                pass

        await asyncio.to_thread(_set_permissions)


async def create_request(data: dict[str, Any], tenant_id: str = "default") -> ChangeRequest:
    """创建新的变更请求.

    Args:
        data: 变更请求字段字典.
        tenant_id: 租户 ID.

    Returns:
        创建后的变更请求.

    Raises:
        ChangeManagementError: ID 已存在或数据校验失败.
    """
    await _load_store()
    data = dict(data)
    if not data.get("id"):
        data["id"] = _generate_id()
    data.setdefault("tenant_id", tenant_id)

    if data["id"] in _REQUESTS:
        raise ChangeManagementError(f"变更请求 {data['id']} 已存在")

    request = ChangeRequest(**data)
    request.audit_log.append(
        AuditEntry(
            actor=request.requester or "system",
            action="created",
            message="创建变更请求",
        )
    )
    _REQUESTS[request.id] = request
    await _persist()
    return request


async def list_requests(tenant_id: str | None = None) -> list[ChangeRequest]:
    """获取变更请求列表,可选按租户过滤.

    Args:
        tenant_id: 可选租户过滤.

    Returns:
        变更请求列表.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    return sorted(requests, key=lambda r: r.id)


async def get_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """获取单个变更请求.

    Args:
        request_id: 变更请求 ID.
        tenant_id: 可选租户 ID，提供时会校验租户隔离.

    Returns:
        变更请求对象.

    Raises:
        ChangeManagementError: 变更请求不存在.
        PermissionError: 租户不匹配.
    """
    await _load_store()
    if request_id not in _REQUESTS:
        raise ChangeManagementError(f"变更请求 {request_id} 不存在")
    req = _REQUESTS[request_id]
    if tenant_id is not None and req.tenant_id != tenant_id:
        raise PermissionError(f"无权限访问变更请求 {request_id}")
    return req


def _add_audit(request: ChangeRequest, action: str, message: str) -> None:
    """追加审计日志."""
    actor = request.approver or request.requester or "system"
    request.audit_log.append(AuditEntry(actor=actor, action=action, message=message))


async def submit_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """提交变更请求进入审批.

    Args:
        request_id: 变更请求 ID.
        tenant_id: 可选租户 ID 校验.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 状态转换不合法或请求不存在.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status != ChangeStatus.DRAFT:
        raise ChangeManagementError("只有草稿状态的变更请求可以提交")
    request.status = ChangeStatus.PENDING
    _add_audit(request, "submit", "提交变更请求进入审批")
    await _persist()
    return request


async def approve_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """审批通过变更请求.

    Args:
        request_id: 变更请求 ID.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 状态转换不合法或请求不存在.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status not in (ChangeStatus.PENDING, ChangeStatus.REVIEW):
        raise ChangeManagementError("只有待审批/审核中的变更请求可以批准")
    request.status = ChangeStatus.APPROVED
    _add_audit(request, "approve", "审批通过")
    await _persist()
    return request


async def reject_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """拒绝变更请求.

    Args:
        request_id: 变更请求 ID.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 状态转换不合法或请求不存在.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status not in (
        ChangeStatus.DRAFT,
        ChangeStatus.PENDING,
        ChangeStatus.REVIEW,
    ):
        raise ChangeManagementError("当前状态无法拒绝")
    request.status = ChangeStatus.REJECTED
    _add_audit(request, "reject", "变更请求被拒绝")
    await _persist()
    return request


async def implement_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """实施已批准的变更请求.

    Args:
        request_id: 变更请求 ID.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 状态转换不合法或请求不存在.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status != ChangeStatus.APPROVED:
        raise ChangeManagementError("只有已批准的变更请求可以实施")
    request.status = ChangeStatus.IMPLEMENTED
    _add_audit(request, "implement", "变更已实施")
    await _persist()
    return request


async def rollback_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """回滚已实施的变更请求.

    Args:
        request_id: 变更请求 ID.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 状态转换不合法或请求不存在.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status != ChangeStatus.IMPLEMENTED:
        raise ChangeManagementError("只有已实施的变更请求可以回滚")
    request.status = ChangeStatus.ROLLED_BACK
    _add_audit(request, "rollback", "变更已回滚")
    await _persist()
    return request


async def update_request(request_id: str, data: dict[str, Any], tenant_id: str | None = None) -> ChangeRequest:
    """更新变更请求.

    Args:
        request_id: 变更请求 ID.
        data: 更新字段字典.
        tenant_id: 可选租户 ID 校验.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 变更请求不存在或状态不允许更新.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status not in (ChangeStatus.DRAFT, ChangeStatus.PENDING):
        raise ChangeManagementError("只有草稿或待审批状态的变更请求可以更新")
    for key, value in data.items():
        if key not in ("id", "tenant_id", "audit_log"):
            setattr(request, key, value)
    _add_audit(request, "updated", "变更请求已更新")
    await _persist()
    return request


async def delete_request(request_id: str, tenant_id: str | None = None) -> None:
    """删除变更请求.

    Args:
        request_id: 变更请求 ID.
        tenant_id: 可选租户 ID 校验.

    Raises:
        ChangeManagementError: 变更请求不存在或状态不允许删除.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status not in (ChangeStatus.DRAFT, ChangeStatus.REJECTED):
        raise ChangeManagementError("只有草稿或已拒绝状态的变更请求可以删除")
    del _REQUESTS[request_id]
    await _persist()


async def cancel_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """取消变更请求.

    Args:
        request_id: 变更请求 ID.
        tenant_id: 可选租户 ID 校验.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 变更请求不存在或状态不允许取消.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status not in (ChangeStatus.PENDING, ChangeStatus.REVIEW, ChangeStatus.APPROVED):
        raise ChangeManagementError("当前状态无法取消")
    request.status = ChangeStatus.REJECTED
    _add_audit(request, "cancelled", "变更请求已取消")
    await _persist()
    return request


async def review_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """将变更请求转入审核状态.

    Args:
        request_id: 变更请求 ID.
        tenant_id: 可选租户 ID 校验.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 变更请求不存在或状态转换不合法.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status != ChangeStatus.PENDING:
        raise ChangeManagementError("只有待审批状态的变更请求可以转入审核")
    request.status = ChangeStatus.REVIEW
    _add_audit(request, "review", "变更请求转入审核")
    await _persist()
    return request


async def list_requests_by_status(status: ChangeStatus, tenant_id: str | None = None) -> list[ChangeRequest]:
    """按状态筛选变更请求.

    Args:
        status: 变更状态.
        tenant_id: 可选租户过滤.

    Returns:
        变更请求列表.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    requests = [r for r in requests if r.status == status]
    return sorted(requests, key=lambda r: r.id)


async def list_requests_by_risk_level(risk_level: RiskLevel, tenant_id: str | None = None) -> list[ChangeRequest]:
    """按风险等级筛选变更请求.

    Args:
        risk_level: 风险等级.
        tenant_id: 可选租户过滤.

    Returns:
        变更请求列表.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    requests = [r for r in requests if r.risk_level == risk_level]
    return sorted(requests, key=lambda r: r.id)


async def list_requests_by_requester(requester: str, tenant_id: str | None = None) -> list[ChangeRequest]:
    """按申请人筛选变更请求.

    Args:
        requester: 申请人.
        tenant_id: 可选租户过滤.

    Returns:
        变更请求列表.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    requests = [r for r in requests if r.requester == requester]
    return sorted(requests, key=lambda r: r.id)


async def list_requests_by_approver(approver: str, tenant_id: str | None = None) -> list[ChangeRequest]:
    """按审批人筛选变更请求.

    Args:
        approver: 审批人.
        tenant_id: 可选租户过滤.

    Returns:
        变更请求列表.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    requests = [r for r in requests if r.approver == approver]
    return sorted(requests, key=lambda r: r.id)


async def list_requests_by_service(service: str, tenant_id: str | None = None) -> list[ChangeRequest]:
    """按受影响服务筛选变更请求.

    Args:
        service: 服务名称.
        tenant_id: 可选租户过滤.

    Returns:
        变更请求列表.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    requests = [r for r in requests if service in r.affected_services]
    return sorted(requests, key=lambda r: r.id)


async def get_request_audit_log(request_id: str, tenant_id: str | None = None) -> list[AuditEntry]:
    """获取变更请求的审计日志.

    Args:
        request_id: 变更请求 ID.
        tenant_id: 可选租户 ID 校验.

    Returns:
        审计日志列表.

    Raises:
        ChangeManagementError: 变更请求不存在.
    """
    request = await get_request(request_id, tenant_id=tenant_id)
    return request.audit_log


async def add_audit_comment(request_id: str, comment: str, actor: str, tenant_id: str | None = None) -> ChangeRequest:
    """为变更请求添加审计评论.

    Args:
        request_id: 变更请求 ID.
        comment: 评论内容.
        actor: 操作人.
        tenant_id: 可选租户 ID 校验.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 变更请求不存在.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    request.audit_log.append(AuditEntry(actor=actor, action="comment", message=comment))
    await _persist()
    return request


async def bulk_create_requests(data_list: list[dict[str, Any]], tenant_id: str = "default") -> list[ChangeRequest]:
    """批量创建变更请求.

    Args:
        data_list: 变更请求数据列表.
        tenant_id: 租户 ID.

    Returns:
        创建的变更请求列表.

    Raises:
        ChangeManagementError: 任何请求创建失败.
    """
    await _load_store()
    created_requests = []
    for data in data_list:
        data = dict(data)
        if not data.get("id"):
            data["id"] = _generate_id()
        data.setdefault("tenant_id", tenant_id)
        if data["id"] in _REQUESTS:
            raise ChangeManagementError(f"变更请求 {data['id']} 已存在")
        request = ChangeRequest(**data)
        request.audit_log.append(
            AuditEntry(
                actor=request.requester or "system",
                action="created",
                message="批量创建变更请求",
            )
        )
        _REQUESTS[request.id] = request
        created_requests.append(request)
    await _persist()
    return created_requests


async def bulk_delete_requests(request_ids: list[str], tenant_id: str | None = None) -> dict[str, bool]:
    """批量删除变更请求.

    Args:
        request_ids: 变更请求 ID 列表.
        tenant_id: 可选租户 ID 校验.

    Returns:
        删除结果字典 {request_id: success}.
    """
    await _load_store()
    results = {}
    for request_id in request_ids:
        try:
            request = await get_request(request_id, tenant_id=tenant_id)
            if request.status not in (ChangeStatus.DRAFT, ChangeStatus.REJECTED):
                results[request_id] = False
                continue
            del _REQUESTS[request_id]
            results[request_id] = True
        except (ChangeManagementError, PermissionError):
            results[request_id] = False
    await _persist()
    return results


async def search_requests(query: str, tenant_id: str | None = None) -> list[ChangeRequest]:
    """搜索变更请求（标题和描述）.

    Args:
        query: 搜索关键词.
        tenant_id: 可选租户过滤.

    Returns:
        匹配的变更请求列表.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    query_lower = query.lower()
    requests = [
        r
        for r in requests
        if query_lower in r.title.lower() or query_lower in r.description.lower()
    ]
    return sorted(requests, key=lambda r: r.id)


async def get_request_statistics(tenant_id: str | None = None) -> dict[str, Any]:
    """获取变更请求统计信息.

    Args:
        tenant_id: 可选租户过滤.

    Returns:
        统计信息字典.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    total = len(requests)
    status_counts = {}
    risk_counts = {}
    for request in requests:
        status_counts[request.status.value] = status_counts.get(request.status.value, 0) + 1
        risk_counts[request.risk_level.value] = risk_counts.get(request.risk_level.value, 0) + 1
    return {
        "total": total,
        "by_status": status_counts,
        "by_risk_level": risk_counts,
    }


async def validate_request(request_id: str, tenant_id: str | None = None) -> dict[str, Any]:
    """验证变更请求的完整性.

    Args:
        request_id: 变更请求 ID.
        tenant_id: 可选租户 ID 校验.

    Returns:
        验证结果字典.

    Raises:
        ChangeManagementError: 变更请求不存在.
    """
    request = await get_request(request_id, tenant_id=tenant_id)
    errors = []
    warnings = []
    if not request.title:
        errors.append("标题不能为空")
    if not request.requester:
        errors.append("申请人不能为空")
    if not request.implementation_plan and request.status in (ChangeStatus.APPROVED, ChangeStatus.IMPLEMENTED):
        warnings.append("实施方案未填写")
    if not request.rollback_plan and request.status in (ChangeStatus.APPROVED, ChangeStatus.IMPLEMENTED):
        warnings.append("回滚方案未填写")
    if not request.affected_services:
        warnings.append("未指定受影响服务")
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


async def schedule_request(request_id: str, schedule: str, tenant_id: str | None = None) -> ChangeRequest:
    """设置变更请求的执行计划时间.

    Args:
        request_id: 变更请求 ID.
        schedule: 计划执行时间.
        tenant_id: 可选租户 ID 校验.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 变更请求不存在或状态不允许设置计划.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status not in (ChangeStatus.DRAFT, ChangeStatus.PENDING, ChangeStatus.APPROVED):
        raise ChangeManagementError("当前状态无法设置执行计划")
    request.schedule = schedule
    _add_audit(request, "scheduled", f"设置执行计划: {schedule}")
    await _persist()
    return request


async def assign_approver(request_id: str, approver: str, tenant_id: str | None = None) -> ChangeRequest:
    """为变更请求分配审批人.

    Args:
        request_id: 变更请求 ID.
        approver: 审批人.
        tenant_id: 可选租户 ID 校验.

    Returns:
        更新后的变更请求.

    Raises:
        ChangeManagementError: 变更请求不存在或状态不允许分配审批人.
    """
    await _load_store()
    request = await get_request(request_id, tenant_id=tenant_id)
    if request.status not in (ChangeStatus.DRAFT, ChangeStatus.PENDING):
        raise ChangeManagementError("当前状态无法分配审批人")
    request.approver = approver
    _add_audit(request, "assigned", f"分配审批人: {approver}")
    await _persist()
    return request


async def clone_request(request_id: str, tenant_id: str | None = None) -> ChangeRequest:
    """克隆变更请求.

    Args:
        request_id: 变更请求 ID.
        tenant_id: 可选租户 ID 校验.

    Returns:
        新创建的变更请求.

    Raises:
        ChangeManagementError: 变更请求不存在.
    """
    await _load_store()
    original = await get_request(request_id, tenant_id=tenant_id)
    new_id = _generate_id()
    data = original.model_dump(mode="json")
    data["id"] = new_id
    data["status"] = ChangeStatus.DRAFT
    data["title"] = f"{data['title']} (副本)"
    data["audit_log"] = []
    new_request = ChangeRequest(**data)
    new_request.audit_log.append(
        AuditEntry(
            actor=original.requester or "system",
            action="cloned",
            message=f"克隆自 {request_id}",
        )
    )
    _REQUESTS[new_id] = new_request
    await _persist()
    return new_request


async def export_requests(tenant_id: str | None = None) -> dict[str, Any]:
    """导出变更请求数据.

    Args:
        tenant_id: 可选租户过滤.

    Returns:
        导出数据字典.
    """
    await _load_store()
    requests = _REQUESTS.values()
    if tenant_id is not None:
        requests = [r for r in requests if r.tenant_id == tenant_id]
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(requests),
        "requests": [r.model_dump(mode="json") for r in requests],
    }


async def import_requests(data: dict[str, Any], tenant_id: str = "default", overwrite: bool = False) -> dict[str, Any]:
    """导入变更请求数据.

    Args:
        data: 导入数据字典.
        tenant_id: 租户 ID.
        overwrite: 是否覆盖已存在的请求.

    Returns:
        导入结果字典.

    Raises:
        ChangeManagementError: 导入数据格式错误.
    """
    await _load_store()
    if "requests" not in data:
        raise ChangeManagementError("导入数据格式错误: 缺少 requests 字段")
    imported = 0
    skipped = 0
    errors = []
    for request_data in data["requests"]:
        try:
            request_id = request_data.get("id")
            if not request_id:
                request_id = _generate_id()
                request_data["id"] = request_id
            if request_id in _REQUESTS and not overwrite:
                skipped += 1
                continue
            request_data.setdefault("tenant_id", tenant_id)
            request_data["audit_log"] = request_data.get("audit_log", [])
            request = ChangeRequest(**request_data)
            _REQUESTS[request_id] = request
            imported += 1
        except Exception as e:
            errors.append(f"导入请求失败: {e}")
    await _persist()
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }
