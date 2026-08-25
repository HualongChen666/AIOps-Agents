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
