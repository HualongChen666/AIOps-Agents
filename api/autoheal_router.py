# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Any, Optional, cast
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Query, Depends
from pydantic import BaseModel, Field, field_validator

from config import INTERNAL_API_KEY
from core.auto_heal import get_pending_approvals
from api.common import get_client_ip, handle_service_error

# Import self-healing module
try:
    from modules.high_availability.self_healing import (
        create_self_healing_engine,
        FailureType,
        RemediationAction,
        SelfHealingPolicy,
        FailureEvent,
        RemediationResult,
    )
    SELF_HEALING_AVAILABLE = True
except ImportError as e:
    SELF_HEALING_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Self-healing module not available: {e}")

# Global self-healing engine instance
_self_healing_engine = None

def get_self_healing_engine():
    """Get or create the self-healing engine instance."""
    global _self_healing_engine
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Self-healing module not available")
    if _self_healing_engine is None:
        _self_healing_engine = create_self_healing_engine()
    return _self_healing_engine


def _verify_internal_key(request: Request) -> None:
    """Verify X-Internal-Key for protected approval endpoints."""
    if not INTERNAL_API_KEY:
        return
    provided_key = request.headers.get("X-Internal-Key")
    if not provided_key:
        raise HTTPException(status_code=403, detail="Missing X-Internal-Key header")
    if provided_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid X-Internal-Key")


try:
    from core.db_engine import async_update_approval_status_by_alert
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    async_update_approval_status_by_alert = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/approvals",
    tags=["自动修复审批"],
)
_STATUS_HINT_MAP: dict[str, str] = {
    "approved_no_script": (
        " | 提示:此审批为高风险方案,需手动执行 /api/repair/execute(Windows)或"
        " /api/linux/repair/execute(Linux)并传入 PID 等参数"
    ),
    "executed_success": " | 提示:此审批已成功执行,无需重复操作",
    "executed_failed": " | 提示:此审批已执行但失败,请查看修复历史或重新触发新告警",
    "execute_error": " | 提示:此审批执行时发生异常,请查看服务日志定位",
    "rejected": " | 提示:此审批已被驳回",
}


def _enrich_error_msg(error_msg: str) -> str:
    """
    🔧 AH3:为错误信息附加操作引导提示
    集中管理避免分散的字符串匹配
    """
    if not error_msg:
        return error_msg
    for status_key, hint in _STATUS_HINT_MAP.items():
        if status_key in error_msg:
            return error_msg + hint
    return error_msg


def _find_alert_by_id(alert_id: str) -> Optional[dict]:
    """从 alert_history 中查找告警"""
    try:
        from core.alert_engine import alert_history
    except ImportError as e:
        logger.error(f"alert_history 导入失败: {e}")
        raise HTTPException(status_code=500, detail="告警引擎未就绪")
    for a in alert_history:
        if isinstance(a, dict) and a.get("id") == alert_id:
            return a
    return None


async def _collect_rich_context_for_ai() -> tuple[Optional[dict], Optional[dict]]:
    """为 AI 方案生成采集富上下文"""
    rich_context = None
    snapshot = None
    try:
        from api.ai_router import _collect_rich_context
        from core.collector import collect_all

        snapshot = await asyncio.to_thread(collect_all) or {}
        rich_context = await _collect_rich_context(snapshot)
        logger.debug(
            f"AI 方案生成:富上下文采集完成 | 进程={len(rich_context.get('top_processes', []))}"
        )
    except ImportError as imp_err:
        logger.warning(f"AI 方案生成:富上下文模块导入失败,降级到无上下文模式: {imp_err}")
    except asyncio.CancelledError:
        raise
    except Exception as ctx_err:
        logger.warning(f"AI 方案生成:富上下文采集失败,降级到无上下文: {ctx_err}")
    return rich_context, snapshot


async def _generate_runbook(
    target_alert: dict, rich_context: Optional[dict], alert_id: str, operator_ip: str
) -> dict[str, Any]:
    """调用 Runbook 生成器"""
    try:
        result = await generate_repair_runbook(target_alert, rich_context)
    except asyncio.CancelledError:
        logger.info(f"Runbook 生成被取消 | alert_id={alert_id}")
        raise
    except Exception as e:
        logger.error(
            f"AI 方案生成异常 | operator={operator_ip} | alert_id={alert_id} | {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"AI 方案生成失败: {str(e)[:200]}")
    return cast(dict[str, Any], result)


def _validate_runbook_result(result: Any) -> dict[str, Any]:
    """验证 Runbook 生成结果"""
    if not result or not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="Runbook 生成器返回空结果")
    if not result.get("success"):
        error_detail = str(result.get("error", "AI 方案生成失败"))
        if "guard_results" in result:
            error_detail += " | 详见返回的 guard_results 字段"
        raise HTTPException(status_code=400, detail=error_detail)
    return result


class ApproveRequest(BaseModel):
    alert_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="待审批的告警 ID",
        examples=["ALERT-20250101103045-CPU"],
    )

    @field_validator("alert_id")
    @classmethod
    def _strip_alert_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("alert_id 不能为纯空白字符串")
        return v

    model_config = {"extra": "ignore", "json_schema_extra": {"example": {"alert_id": "example"}}}


@router.get(
    "/pending",
    summary="获取待审批修复方案列表",
    responses={
        (200): {
            "description": "待审批修复方案列表",
            "content": {
                "application/json": {
                    "example": {
                        "total": 5,
                        "items": [
                            {
                                "alert_id": "ALERT-123",
                                "proposal": "Restart service",
                                "status": "pending",
                            }
                        ],
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "服务器内部错误"},
    },
)
async def list_pending(request: Request) -> dict:
    _verify_internal_key(request)
    """
    返回所有等待人工审批的高风险修复方案列表

    🔧 AH5 [P1]:改回 async def
        - get_pending_approvals 内部走 SQLite 查询(I/O)
        - 普通 def 会被 FastAPI 调度到工作线程池(默认 40 线程)
        - 高频请求场景下耗尽线程资源
        - async def 由事件循环调度,无线程消耗
    """
    logger.info("请求待审批修复方案列表")
    try:
        if asyncio.iscoroutinefunction(get_pending_approvals):
            items = await get_pending_approvals()
        else:
            items = get_pending_approvals()  # type: ignore
        logger.debug(f"待审批列表查询成功,共 {len(items)} 条")
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"获取待审批列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误,获取待审批列表失败")


@router.patch(
    "/{alert_id}",
    summary="审批通过并执行修复",
    responses={
        (200): {
            "description": "审批通过并执行成功",
            "content": {
                "application/json": {
                    "example": {
                        "alert_id": "ALERT-123",
                        "status": "approved",
                        "success": True,
                        "output": "Repair executed successfully",
                    }
                }
            },
        },
        (400): {"description": "审批执行业务失败"},
        (401): {"description": "未授权"},
        (404): {"description": "告警不存在"},
        (500): {"description": "服务器内部错误"},
    },
)
async def approve(alert_id: str, request: Request) -> dict:
    _verify_internal_key(request)
    """
    ✅ 新增:通过此接口触发 LangGraph 业务闭环修复

    工作流说明:
    1. 从审批系统获取待处理告警
    2. 调用 `heal_via_langgraph` 执行完整的 LangGraph 工作流
    3. 返回工作流最终状态及关键字段

    该实现复用了 `core.auto_heal.heal_via_langgraph`，在 `autoheal_router`
    中统一对外暴露，便于前端或外部系统直接调用。
    人工审批通过后触发高风险修复脚本执行

    工作流说明:
    1. 高风险告警触发后生成修复方案(状态:pending)
    2. 运维人员查看 GET /pending 确认方案内容
    3. 调用本接口传入 alert_id 确认执行
    4. 系统执行对应的 PowerShell/Bash 修复脚本
    5. 返回执行结果(success/output)

    🔧 AH3 [P1]:错误提示改为字典查表
    🔧 AH4 [P1]:记录操作 IP 用于审计
    🔧 AH6 [P2]:CancelledError 显式 reraise
    """
    operator_ip = request.client.host if request.client else "unknown"
    logger.warning(f"收到修复审批确认 | operator={operator_ip} | alert_id='{alert_id}'")
    try:
        from gateway.services_client import approve_and_execute

        # S1: mark the latest pending approval for this alert as approved before execution.
        if async_update_approval_status_by_alert is not None:
            try:
                await async_update_approval_status_by_alert(alert_id, "approved")
            except Exception as approve_err:
                logger.warning(f"审批状态更新失败(继续执行) | alert_id={alert_id}: {approve_err}")

        target_alert = _find_alert_by_id(alert_id)
        if not target_alert:
            # Fallback to a minimal alert payload so the workflow can still run
            # when the alert is only referenced by id (e.g. in-memory cache miss).
            target_alert = {
                "id": alert_id,
                "title": "Auto-heal approval",
                "platform": "windows",
            }

        result = await approve_and_execute(alert_id, target_alert)
    except asyncio.CancelledError:
        logger.info(f"审批执行被取消 | alert_id='{alert_id}'")
        raise
    except Exception as e:
        logger.error(f"审批执行异常: alert_id='{alert_id}' | {e}", exc_info=True)
        result = {
            "alert_id": alert_id,
            "success": False,
            "status": "pending",
            "message": f"审批执行过程中发生内部错误: {e}",
            "fix_applied": False,
            "output": "",
        }
    if result is None:
        logger.error(f"approve_and_execute 返回 None | alert_id='{alert_id}'")
        raise HTTPException(status_code=500, detail="修复引擎未返回结果,请检查服务日志")
    if not result.get("success") and "error" in result:
        error_msg = _enrich_error_msg(str(result["error"]))
        logger.warning(
            f"审批执行业务失败 | operator={operator_ip} | alert_id='{alert_id}' | error={error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)
    logger.info(
        f"审批执行完成 | operator={operator_ip} | alert_id='{alert_id}' |"
        f" success={result.get('success')}"
    )
    return result


class RejectRequest(BaseModel):
    alert_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="待驳回的告警 ID",
        examples=["AI-windows-CPU-09:12:29"],
    )
    reason: str = Field(default="用户驳回", max_length=500, description="驳回原因(可选,记录到审计)")

    @field_validator("alert_id")
    @classmethod
    def _strip_alert_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("alert_id 不能为纯空白字符串")
        return v

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, v: str) -> str:
        v = (v or "用户驳回").strip()[:500]
        return v or "用户驳回"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"alert_id": "example", "reason": "example"}},
    }


@router.post(
    "/reject",
    summary="驳回 AI 修复方案",
    responses={
        (200): {
            "description": "驳回成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "alert_id": "ALERT-123",
                        "status": "rejected",
                        "pending_count": 4,
                    }
                }
            },
        },
        (400): {"description": "业务失败(状态非pending或记录不存在)"},
        (401): {"description": "未授权"},
        (422): {"description": "参数校验失败"},
        (500): {"description": "服务器内部错误"},
    },
)
async def reject(payload: RejectRequest, request: Request) -> dict:
    """
    🔧 新增:人工驳回审批方案

    # 工作流:
      1. 验证 alert_id 存在且状态为 pending
      2. SQLite 持久化更新状态为 rejected
      3. 内存字典同步状态
      4. 返回结果给前端展示

    🔧 AH4 [P1]:记录操作 IP
    🔧 AH6 [P2]:CancelledError 显式 reraise
    🔧 AH7 [P2]:返回字段增加 pending_count 供前端刷新红点

    HTTP 状态码:
      - 200: 驳回成功
      - 422: alert_id 校验失败(空白等,Pydantic 拦截)
      - 400: 业务失败(状态非 pending、记录不存在等)
      - 500: 内部错误
    """
    from core.auto_heal import reject_repair

    operator_ip = request.client.host if request.client else "unknown"
    alert_id = payload.alert_id
    safe_reason = payload.reason
    logger.warning(
        f"收到驳回请求 | operator={operator_ip} | alert_id='{alert_id}' |"
        f" reason='{safe_reason[:80]}'"
    )
    try:
        if asyncio.iscoroutinefunction(reject_repair):
            result = await reject_repair(
                alert_id, reason=safe_reason, approver=operator_ip, rejection_reason=safe_reason
            )
        else:
            result = reject_repair(alert_id, safe_reason)  # type: ignore
    except asyncio.CancelledError:
        logger.info(f"驳回操作被取消 | alert_id='{alert_id}'")
        raise
    except Exception as e:
        logger.error(
            f"驳回执行异常 | operator={operator_ip} | alert_id='{alert_id}' | {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="驳回操作失败,请查看服务日志")

    if result is None:
        raise HTTPException(status_code=500, detail="驳回引擎未返回结果")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=str(result.get("error", "驳回失败")))
    try:
        if asyncio.iscoroutinefunction(get_pending_approvals):
            pending_count = len(await get_pending_approvals())
        else:
            pending_count = len(get_pending_approvals())  # type: ignore
        result["pending_count"] = pending_count
    except Exception as e:
        logger.debug(f"AH7: pending_count 计算失败(已忽略): {e}")
    return result


@router.post(
    "/takeover/{alert_id}",
    summary="一键接管：人工中断 Agent 并取消审批",
    responses={
        (200): {
            "description": "接管成功",
            "content": {
                "application/json": {
                    "example": {
                        "alert_id": "ALERT-123",
                        "success": True,
                        "status": "cancelled",
                        "message": "Agent 已接管，审批已取消",
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "服务器内部错误"},
    },
)
async def takeover(alert_id: str, request: Request) -> dict:
    """
    人工一键接管：立即中断 Agent 执行并取消对应告警的审批。

    行为：
      1. 将最新审批记录标记为 rejected（记录操作人、IP、原因）。
      2. 返回取消结果，后续 apply_fix / run_heal 看到 rejected 状态会停止执行。
    """
    operator_ip = request.client.host if request.client else "unknown"
    safe_alert_id = alert_id.strip() if isinstance(alert_id, str) else ""
    logger.warning(f"收到一键接管请求 | operator={operator_ip} | alert_id='{safe_alert_id}'")
    if not safe_alert_id:
        raise HTTPException(status_code=422, detail="alert_id 不能为空")

    from core.auto_heal import reject_repair

    takeover_reason = f"manual takeover by {operator_ip}"
    try:
        if asyncio.iscoroutinefunction(reject_repair):
            await reject_repair(
                safe_alert_id,
                reason=takeover_reason,
                approver=operator_ip,
                rejection_reason=takeover_reason,
            )
        else:
            reject_repair(safe_alert_id, reason=takeover_reason)  # type: ignore
    except Exception as e:
        logger.error(
            f"接管调用 reject_repair 失败 | operator={operator_ip} | alert_id='{safe_alert_id}' | {e}",
            exc_info=True,
        )

    return {
        "alert_id": safe_alert_id,
        "success": True,
        "status": "cancelled",
        "message": "Agent 已接管，审批已取消",
    }


class AIProposeRequest(BaseModel):
    alert_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="告警 ID(从 /api/alerts/ 接口获取)",
        examples=["CPU-09:12:29"],
    )

    @field_validator("alert_id")
    @classmethod
    def _strip_alert_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("alert_id 不能为纯空白字符串")
        return v

    model_config = {"extra": "ignore", "json_schema_extra": {"example": {"alert_id": "example"}}}


is_runbook_available: bool = False
_runbook_import_error: Optional[str] = None
try:
    from core.runbook_generator import generate_repair_runbook

    is_runbook_available = True
except ImportError as _imp_err:
    _runbook_import_error = str(_imp_err)[:200]
    logger.error(
        f"AH1: runbook_generator 模块导入失败,/ai/propose 接口将禁用 | {_runbook_import_error}"
    )


async def _validate_ai_propose_request(
    payload: AIProposeRequest, request: Request
) -> tuple[dict, str]:
    """验证AI方案生成请求

    Returns:
        (target_alert, operator_ip)

    Raises:
        HTTPException: 如果模块不可用或告警不存在
    """
    if not is_runbook_available:
        raise HTTPException(
            status_code=503,
            detail=(
                f"AI 方案生成模块不可用: {_runbook_import_error}。请检查 core/runbook_generator.py"
                " 是否正常加载"
            ),
        )
    operator_ip = request.client.host if request.client else "unknown"
    alert_id = payload.alert_id
    target_alert = _find_alert_by_id(alert_id)
    if not target_alert:
        logger.warning(f"AI 方案生成:告警不存在 | operator={operator_ip} | alert_id='{alert_id}'")
        raise HTTPException(
            status_code=404,
            detail=f"未找到告警: {alert_id}(可能已超出内存缓存,请刷新告警列表后重试)",
        )
    logger.warning(
        f"🤖 用户请求 AI 生成修复方案 | operator={operator_ip} | alert_id={alert_id} |"
        f" title={str(target_alert.get('title', ''))[:50]}"
    )
    return target_alert, operator_ip


async def _execute_ai_propose_workflow(alert: dict, alert_id: str, operator_ip: str) -> dict:
    """执行AI方案生成工作流

    Returns:
        生成结果
    """
    try:
        rich_context, snapshot = await _collect_rich_context_for_ai()
    except asyncio.CancelledError:
        logger.info(f"富上下文采集被取消 | alert_id={alert_id}")
        raise
    result = await _generate_runbook(alert, rich_context, alert_id, operator_ip)
    result = _validate_runbook_result(result)
    try:
        result["pending_count"] = len(await get_pending_approvals())
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
    return result


@router.post(
    "/propose",
    summary="AI 生成修复方案",
    responses={
        (200): {
            "description": "修复方案已生成",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "alert_id": "ALERT-123",
                        "proposal": "Restart service",
                        "risk_level": "MEDIUM",
                    }
                }
            },
        },
        (400): {"description": "业务失败"},
        (401): {"description": "未授权"},
        (404): {"description": "告警不存在"},
        (503): {"description": "AI 方案生成模块不可用"},
    },
)
async def ai_propose_repair(payload: AIProposeRequest, request: Request) -> dict:
    target_alert, operator_ip = await _validate_ai_propose_request(payload, request)
    alert_id = payload.alert_id
    return await _execute_ai_propose_workflow(target_alert, alert_id, operator_ip)


@router.get(
    "/statistics",
    summary="获取自动修复统计信息",
    responses={
        (200): {
            "description": "统计信息",
            "content": {
                "application/json": {
                    "example": {
                        "total_tasks": 100,
                        "pending_tasks": 10,
                        "approved_tasks": 20,
                        "executing_tasks": 5,
                        "completed_tasks": 60,
                        "failed_tasks": 5,
                        "success_rate": 0.92,
                        "avg_execution_time": 120.5,
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "服务器内部错误"},
    },
)
async def get_statistics(request: Request) -> dict:
    """
    获取自动修复系统的统计信息

    包括：
    - 总任务数
    - 各状态任务数（待审批、已批准、执行中、已完成、失败）
    - 成功率
    - 平均执行时间
    """
    _verify_internal_key(request)
    logger.info("请求自动修复统计信息")
    try:
        # Get all pending approvals
        if asyncio.iscoroutinefunction(get_pending_approvals):
            pending_items = await get_pending_approvals()
        else:
            pending_items = get_pending_approvals()  # type: ignore

        # Calculate statistics based on pending items
        total_tasks = len(pending_items)
        pending_tasks = len([item for item in pending_items if item.get("status") == "pending"])
        approved_tasks = len([item for item in pending_items if item.get("status") == "approved"])
        executing_tasks = len([item for item in pending_items if item.get("status") == "executing"])
        completed_tasks = len([item for item in pending_items if item.get("status") == "completed"])
        failed_tasks = len([item for item in pending_items if item.get("status") == "failed"])

        # Calculate success rate
        total_completed = completed_tasks + failed_tasks
        success_rate = completed_tasks / total_completed if total_completed > 0 else 0.0

        # Calculate average execution time (placeholder - would need actual execution time data)
        avg_execution_time = 120.5  # Default placeholder value

        statistics = {
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "approved_tasks": approved_tasks,
            "executing_tasks": executing_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": success_rate,
            "avg_execution_time": avg_execution_time,
        }

        logger.debug(f"统计信息获取成功: {statistics}")
        return statistics
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取统计信息失败")


# ----------------------------------------------------------------------
# 7️⃣ 策略管理端点 (4个)
# ----------------------------------------------------------------------


class CreatePolicyRequest(BaseModel):
    """创建自愈策略请求"""
    id: str = Field(..., min_length=1, max_length=128, description="策略ID")
    name: str = Field(..., min_length=1, max_length=256, description="策略名称")
    failure_type: str = Field(..., description="故障类型")
    remediation_actions: list[str] = Field(..., min_items=1, description="修复动作列表")
    conditions: dict[str, Any] = Field(default_factory=dict, description="触发条件")
    enabled: bool = Field(default=True, description="是否启用")
    max_attempts: int = Field(default=3, ge=1, le=10, description="最大尝试次数")
    cooldown_seconds: int = Field(default=300, ge=0, le=86400, description="冷却时间(秒)")

    @field_validator("failure_type")
    @classmethod
    def validate_failure_type(cls, v: str) -> str:
        valid_types = [ft.value for ft in FailureType]
        if v not in valid_types:
            raise ValueError(f"无效的故障类型，必须是: {', '.join(valid_types)}")
        return v

    @field_validator("remediation_actions")
    @classmethod
    def validate_remediation_actions(cls, v: list[str]) -> list[str]:
        valid_actions = [ra.value for ra in RemediationAction]
        for action in v:
            if action not in valid_actions:
                raise ValueError(f"无效的修复动作: {action}，必须是: {', '.join(valid_actions)}")
        return v

    model_config = {"extra": "ignore"}


@router.post(
    "/policies",
    summary="创建自愈策略",
    responses={
        200: {"description": "策略创建成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def create_policy(payload: CreatePolicyRequest, request: Request) -> dict:
    """创建新的自愈策略"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"创建自愈策略 | operator={operator_ip} | policy_id={payload.id}")

    try:
        engine = get_self_healing_engine()

        # 检查策略是否已存在
        if payload.id in engine.policies:
            raise HTTPException(status_code=400, detail=f"策略ID {payload.id} 已存在")

        # 创建策略
        policy = SelfHealingPolicy(
            id=payload.id,
            name=payload.name,
            failure_type=FailureType(payload.failure_type),
            remediation_actions=[RemediationAction(a) for a in payload.remediation_actions],
            conditions=payload.conditions,
            enabled=payload.enabled,
            max_attempts=payload.max_attempts,
            cooldown_seconds=payload.cooldown_seconds,
        )

        engine.add_policy(policy)

        logger.info(f"策略创建成功 | policy_id={payload.id} | name={payload.name}")
        return {
            "success": True,
            "policy_id": policy.id,
            "name": policy.name,
            "message": "策略创建成功",
        }
    except ValueError as e:
        logger.error(f"策略参数验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建策略失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建策略失败: {str(e)}")


@router.get(
    "/policies",
    summary="获取所有自愈策略",
    responses={
        200: {"description": "策略列表"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def list_policies(request: Request) -> dict:
    """获取所有自愈策略"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info("获取所有自愈策略")

    try:
        engine = get_self_healing_engine()

        policies = []
        for policy in engine.policies.values():
            policies.append(
                {
                    "id": policy.id,
                    "name": policy.name,
                    "failure_type": policy.failure_type.value,
                    "remediation_actions": [a.value for a in policy.remediation_actions],
                    "conditions": policy.conditions,
                    "enabled": policy.enabled,
                    "max_attempts": policy.max_attempts,
                    "cooldown_seconds": policy.cooldown_seconds,
                }
            )

        logger.debug(f"获取策略成功，共 {len(policies)} 个")
        return {"total": len(policies), "items": policies}
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略列表失败: {str(e)}")


@router.get(
    "/policies/{policy_id}",
    summary="获取单个自愈策略",
    responses={
        200: {"description": "策略详情"},
        401: {"description": "未授权"},
        404: {"description": "策略不存在"},
        503: {"description": "自愈模块不可用"},
    },
)
async def get_policy(policy_id: str, request: Request) -> dict:
    """获取指定ID的自愈策略"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info(f"获取自愈策略 | policy_id={policy_id}")

    try:
        engine = get_self_healing_engine()

        if policy_id not in engine.policies:
            raise HTTPException(status_code=404, detail=f"策略 {policy_id} 不存在")

        policy = engine.policies[policy_id]

        return {
            "id": policy.id,
            "name": policy.name,
            "failure_type": policy.failure_type.value,
            "remediation_actions": [a.value for a in policy.remediation_actions],
            "conditions": policy.conditions,
            "enabled": policy.enabled,
            "max_attempts": policy.max_attempts,
            "cooldown_seconds": policy.cooldown_seconds,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略失败: {str(e)}")


@router.delete(
    "/policies/{policy_id}",
    summary="删除自愈策略",
    responses={
        200: {"description": "策略删除成功"},
        401: {"description": "未授权"},
        404: {"description": "策略不存在"},
        503: {"description": "自愈模块不可用"},
    },
)
async def delete_policy(policy_id: str, request: Request) -> dict:
    """删除指定的自愈策略"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.warning(f"删除自愈策略 | operator={operator_ip} | policy_id={policy_id}")

    try:
        engine = get_self_healing_engine()

        if policy_id not in engine.policies:
            raise HTTPException(status_code=404, detail=f"策略 {policy_id} 不存在")

        engine.remove_policy(policy_id)

        logger.info(f"策略删除成功 | policy_id={policy_id}")
        return {"success": True, "policy_id": policy_id, "message": "策略删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除策略失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除策略失败: {str(e)}")


# ----------------------------------------------------------------------
# 8️⃣ 故障管理端点 (5个)
# ----------------------------------------------------------------------


class DetectFailureRequest(BaseModel):
    """检测故障请求"""
    failure_type: str = Field(..., description="故障类型")
    component: str = Field(..., min_length=1, max_length=256, description="组件名称")
    severity: str = Field(..., description="严重程度: low, medium, high, critical")
    description: str = Field(..., min_length=1, max_length=1024, description="故障描述")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")

    @field_validator("failure_type")
    @classmethod
    def validate_failure_type(cls, v: str) -> str:
        valid_types = [ft.value for ft in FailureType]
        if v not in valid_types:
            raise ValueError(f"无效的故障类型，必须是: {', '.join(valid_types)}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid_severities = ["low", "medium", "high", "critical"]
        if v not in valid_severities:
            raise ValueError(f"无效的严重程度，必须是: {', '.join(valid_severities)}")
        return v

    model_config = {"extra": "ignore"}


@router.post(
    "/failures/detect",
    summary="检测故障",
    responses={
        200: {"description": "故障检测成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def detect_failure(payload: DetectFailureRequest, request: Request) -> dict:
    """检测并记录故障"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"检测故障 | operator={operator_ip} | component={payload.component}")

    try:
        engine = get_self_healing_engine()

        failure_event = engine.detect_failure(
            failure_type=FailureType(payload.failure_type),
            component=payload.component,
            severity=payload.severity,
            description=payload.description,
            metadata=payload.metadata,
        )

        logger.info(f"故障检测成功 | failure_id={failure_event.id}")
        return {
            "success": True,
            "failure_id": failure_event.id,
            "failure_type": failure_event.failure_type.value,
            "component": failure_event.component,
            "severity": failure_event.severity,
            "detected_at": failure_event.detected_at,
        }
    except ValueError as e:
        logger.error(f"故障参数验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"检测故障失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检测故障失败: {str(e)}")


@router.get(
    "/failures",
    summary="获取故障历史",
    responses={
        200: {"description": "故障历史列表"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def list_failures(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> dict:
    """获取故障历史记录"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info(f"获取故障历史 | limit={limit} | offset={offset}")

    try:
        engine = get_self_healing_engine()

        failures = [f.to_dict() for f in engine.failure_history]
        failures.reverse()  # 最新的在前

        total = len(failures)
        paginated_failures = failures[offset : offset + limit]

        logger.debug(f"获取故障历史成功，共 {total} 条，返回 {len(paginated_failures)} 条")
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": paginated_failures,
        }
    except Exception as e:
        logger.error(f"获取故障历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取故障历史失败: {str(e)}")


@router.get(
    "/failures/{failure_id}",
    summary="获取故障详情",
    responses={
        200: {"description": "故障详情"},
        401: {"description": "未授权"},
        404: {"description": "故障不存在"},
        503: {"description": "自愈模块不可用"},
    },
)
async def get_failure(failure_id: str, request: Request) -> dict:
    """获取指定ID的故障详情"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info(f"获取故障详情 | failure_id={failure_id}")

    try:
        engine = get_self_healing_engine()

        failure = next((f for f in engine.failure_history if f.id == failure_id), None)
        if failure is None:
            raise HTTPException(status_code=404, detail=f"故障 {failure_id} 不存在")

        return failure.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取故障详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取故障详情失败: {str(e)}")


@router.post(
    "/failures/{failure_id}/heal",
    summary="触发自愈",
    responses={
        200: {"description": "自愈触发成功"},
        401: {"description": "未授权"},
        404: {"description": "故障不存在"},
        503: {"description": "自愈模块不可用"},
    },
)
async def trigger_healing(failure_id: str, request: Request) -> dict:
    """对指定故障触发自愈"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"触发自愈 | operator={operator_ip} | failure_id={failure_id}")

    try:
        engine = get_self_healing_engine()

        failure = next((f for f in engine.failure_history if f.id == failure_id), None)
        if failure is None:
            raise HTTPException(status_code=404, detail=f"故障 {failure_id} 不存在")

        results = engine.trigger_self_healing(failure)

        logger.info(f"自愈触发成功 | failure_id={failure_id} | actions={len(results)}")
        return {
            "success": True,
            "failure_id": failure_id,
            "remediation_count": len(results),
            "remediations": [r.to_dict() for r in results],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发自愈失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"触发自愈失败: {str(e)}")


@router.post(
    "/failures/{failure_id}/verify",
    summary="验证修复效果",
    responses={
        200: {"description": "验证完成"},
        401: {"description": "未授权"},
        404: {"description": "故障不存在"},
        503: {"description": "自愈模块不可用"},
    },
)
async def verify_remediation(failure_id: str, request: Request) -> dict:
    """验证指定故障的修复效果"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info(f"验证修复效果 | failure_id={failure_id}")

    try:
        engine = get_self_healing_engine()

        failure = next((f for f in engine.failure_history if f.id == failure_id), None)
        if failure is None:
            raise HTTPException(status_code=404, detail=f"故障 {failure_id} 不存在")

        verified = engine.verify_remediation(failure)

        logger.info(f"修复验证完成 | failure_id={failure_id} | verified={verified}")
        return {
            "success": True,
            "failure_id": failure_id,
            "verified": verified,
            "message": "修复验证成功" if verified else "修复验证失败",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证修复失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"验证修复失败: {str(e)}")


# ----------------------------------------------------------------------
# 9️⃣ 修复动作端点 (7个)
# ----------------------------------------------------------------------


class ExecuteActionRequest(BaseModel):
    """执行修复动作请求"""
    component: str = Field(..., min_length=1, max_length=256, description="组件名称")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")

    model_config = {"extra": "ignore"}


@router.post(
    "/actions/restart",
    summary="重启服务",
    responses={
        200: {"description": "重启成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def action_restart(payload: ExecuteActionRequest, request: Request) -> dict:
    """执行重启服务动作"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"执行重启服务 | operator={operator_ip} | component={payload.component}")

    try:
        engine = get_self_healing_engine()

        # 创建临时故障事件用于执行动作
        failure_event = FailureEvent(
            id=f"manual-{int(datetime.now().timestamp())}",
            failure_type=FailureType.SERVICE_DOWN,
            component=payload.component,
            severity="medium",
            description=f"手动重启服务: {payload.component}",
            metadata=payload.metadata,
        )

        success, message = engine._handle_restart(failure_event)

        logger.info(f"重启服务完成 | component={payload.component} | success={success}")
        return {
            "success": success,
            "action": "restart_service",
            "component": payload.component,
            "message": message,
        }
    except Exception as e:
        logger.error(f"重启服务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重启服务失败: {str(e)}")


@router.post(
    "/actions/scale-up",
    summary="扩容",
    responses={
        200: {"description": "扩容成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def action_scale_up(payload: ExecuteActionRequest, request: Request) -> dict:
    """执行扩容动作"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"执行扩容 | operator={operator_ip} | component={payload.component}")

    try:
        engine = get_self_healing_engine()

        failure_event = FailureEvent(
            id=f"manual-{int(datetime.now().timestamp())}",
            failure_type=FailureType.HIGH_LATENCY,
            component=payload.component,
            severity="medium",
            description=f"手动扩容: {payload.component}",
            metadata=payload.metadata,
        )

        success, message = engine._handle_scale_up(failure_event)

        logger.info(f"扩容完成 | component={payload.component} | success={success}")
        return {
            "success": success,
            "action": "scale_up",
            "component": payload.component,
            "message": message,
        }
    except Exception as e:
        logger.error(f"扩容失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"扩容失败: {str(e)}")


@router.post(
    "/actions/scale-down",
    summary="缩容",
    responses={
        200: {"description": "缩容成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def action_scale_down(payload: ExecuteActionRequest, request: Request) -> dict:
    """执行缩容动作"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"执行缩容 | operator={operator_ip} | component={payload.component}")

    try:
        engine = get_self_healing_engine()

        failure_event = FailureEvent(
            id=f"manual-{int(datetime.now().timestamp())}",
            failure_type=FailureType.RESOURCE_EXHAUSTION,
            component=payload.component,
            severity="medium",
            description=f"手动缩容: {payload.component}",
            metadata=payload.metadata,
        )

        success, message = engine._handle_scale_down(failure_event)

        logger.info(f"缩容完成 | component={payload.component} | success={success}")
        return {
            "success": success,
            "action": "scale_down",
            "component": payload.component,
            "message": message,
        }
    except Exception as e:
        logger.error(f"缩容失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"缩容失败: {str(e)}")


@router.post(
    "/actions/rollback",
    summary="回滚",
    responses={
        200: {"description": "回滚成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def action_rollback(payload: ExecuteActionRequest, request: Request) -> dict:
    """执行回滚动作"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"执行回滚 | operator={operator_ip} | component={payload.component}")

    try:
        engine = get_self_healing_engine()

        failure_event = FailureEvent(
            id=f"manual-{int(datetime.now().timestamp())}",
            failure_type=FailureType.HIGH_ERROR_RATE,
            component=payload.component,
            severity="high",
            description=f"手动回滚: {payload.component}",
            metadata=payload.metadata,
        )

        success, message = engine._handle_rollback(failure_event)

        logger.info(f"回滚完成 | component={payload.component} | success={success}")
        return {
            "success": success,
            "action": "rollback",
            "component": payload.component,
            "message": message,
        }
    except Exception as e:
        logger.error(f"回滚失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")


@router.post(
    "/actions/clear-cache",
    summary="清空缓存",
    responses={
        200: {"description": "清空缓存成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def action_clear_cache(payload: ExecuteActionRequest, request: Request) -> dict:
    """执行清空缓存动作"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"执行清空缓存 | operator={operator_ip} | component={payload.component}")

    try:
        engine = get_self_healing_engine()

        failure_event = FailureEvent(
            id=f"manual-{int(datetime.now().timestamp())}",
            failure_type=FailureType.DATA_INCONSISTENCY,
            component=payload.component,
            severity="medium",
            description=f"手动清空缓存: {payload.component}",
            metadata=payload.metadata,
        )

        success, message = engine._handle_clear_cache(failure_event)

        logger.info(f"清空缓存完成 | component={payload.component} | success={success}")
        return {
            "success": success,
            "action": "clear_cache",
            "component": payload.component,
            "message": message,
        }
    except Exception as e:
        logger.error(f"清空缓存失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清空缓存失败: {str(e)}")


@router.post(
    "/actions/rebalance",
    summary="重新平衡",
    responses={
        200: {"description": "重新平衡成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def action_rebalance(payload: ExecuteActionRequest, request: Request) -> dict:
    """执行重新平衡动作"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"执行重新平衡 | operator={operator_ip} | component={payload.component}")

    try:
        engine = get_self_healing_engine()

        failure_event = FailureEvent(
            id=f"manual-{int(datetime.now().timestamp())}",
            failure_type=FailureType.NETWORK_PARTITION,
            component=payload.component,
            severity="medium",
            description=f"手动重新平衡: {payload.component}",
            metadata=payload.metadata,
        )

        success, message = engine._handle_rebalance(failure_event)

        logger.info(f"重新平衡完成 | component={payload.component} | success={success}")
        return {
            "success": success,
            "action": "rebalance",
            "component": payload.component,
            "message": message,
        }
    except Exception as e:
        logger.error(f"重新平衡失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新平衡失败: {str(e)}")


@router.post(
    "/actions/isolate",
    summary="隔离组件",
    responses={
        200: {"description": "隔离成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def action_isolate(payload: ExecuteActionRequest, request: Request) -> dict:
    """执行隔离组件动作"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.warning(f"执行隔离组件 | operator={operator_ip} | component={payload.component}")

    try:
        engine = get_self_healing_engine()

        failure_event = FailureEvent(
            id=f"manual-{int(datetime.now().timestamp())}",
            failure_type=FailureType.SERVICE_DOWN,
            component=payload.component,
            severity="critical",
            description=f"手动隔离组件: {payload.component}",
            metadata=payload.metadata,
        )

        success, message = engine._handle_isolate(failure_event)

        logger.info(f"隔离组件完成 | component={payload.component} | success={success}")
        return {
            "success": success,
            "action": "isolate",
            "component": payload.component,
            "message": message,
        }
    except Exception as e:
        logger.error(f"隔离组件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"隔离组件失败: {str(e)}")


# ----------------------------------------------------------------------
# 🔟 批量操作端点 (3个)
# ----------------------------------------------------------------------


class BatchDetectFailuresRequest(BaseModel):
    """批量检测故障请求"""
    failures: list[DetectFailureRequest] = Field(..., min_items=1, max_items=50, description="故障列表")

    model_config = {"extra": "ignore"}


@router.post(
    "/batch/detect-failures",
    summary="批量检测故障",
    responses={
        200: {"description": "批量检测成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def batch_detect_failures(payload: BatchDetectFailuresRequest, request: Request) -> dict:
    """批量检测并记录故障"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"批量检测故障 | operator={operator_ip} | count={len(payload.failures)}")

    try:
        engine = get_self_healing_engine()

        results = []
        batch_size = 10  # 分批处理，避免速率限制

        for i in range(0, len(payload.failures), batch_size):
            batch = payload.failures[i : i + batch_size]
            for failure_req in batch:
                try:
                    failure_event = engine.detect_failure(
                        failure_type=FailureType(failure_req.failure_type),
                        component=failure_req.component,
                        severity=failure_req.severity,
                        description=failure_req.description,
                        metadata=failure_req.metadata,
                    )
                    results.append(
                        {
                            "success": True,
                            "failure_id": failure_event.id,
                            "component": failure_event.component,
                        }
                    )
                except Exception as e:
                    logger.error(f"检测单个故障失败: {e}")
                    results.append(
                        {
                            "success": False,
                            "component": failure_req.component,
                            "error": str(e),
                        }
                    )

        success_count = sum(1 for r in results if r["success"])
        logger.info(f"批量检测完成 | total={len(results)} | success={success_count}")

        return {
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "failure_count": len(results) - success_count,
            "results": results,
        }
    except Exception as e:
        logger.error(f"批量检测故障失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量检测故障失败: {str(e)}")


class BatchHealFailuresRequest(BaseModel):
    """批量触发自愈请求"""
    failure_ids: list[str] = Field(..., min_items=1, max_items=50, description="故障ID列表")

    model_config = {"extra": "ignore"}


@router.post(
    "/batch/heal-failures",
    summary="批量触发自愈",
    responses={
        200: {"description": "批量自愈成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def batch_heal_failures(payload: BatchHealFailuresRequest, request: Request) -> dict:
    """批量触发自愈"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"批量触发自愈 | operator={operator_ip} | count={len(payload.failure_ids)}")

    try:
        engine = get_self_healing_engine()

        results = []
        batch_size = 10  # 分批处理，避免速率限制

        for i in range(0, len(payload.failure_ids), batch_size):
            batch = payload.failure_ids[i : i + batch_size]
            for failure_id in batch:
                try:
                    failure = next((f for f in engine.failure_history if f.id == failure_id), None)
                    if failure is None:
                        results.append(
                            {
                                "success": False,
                                "failure_id": failure_id,
                                "error": "故障不存在",
                            }
                        )
                        continue

                    remediation_results = engine.trigger_self_healing(failure)
                    results.append(
                        {
                            "success": True,
                            "failure_id": failure_id,
                            "remediation_count": len(remediation_results),
                        }
                    )
                except Exception as e:
                    logger.error(f"触发单个自愈失败: {e}")
                    results.append(
                        {
                            "success": False,
                            "failure_id": failure_id,
                            "error": str(e),
                        }
                    )

        success_count = sum(1 for r in results if r["success"])
        logger.info(f"批量自愈完成 | total={len(results)} | success={success_count}")

        return {
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "failure_count": len(results) - success_count,
            "results": results,
        }
    except Exception as e:
        logger.error(f"批量触发自愈失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量触发自愈失败: {str(e)}")


class BatchVerifyRemediationsRequest(BaseModel):
    """批量验证修复请求"""
    failure_ids: list[str] = Field(..., min_items=1, max_items=50, description="故障ID列表")

    model_config = {"extra": "ignore"}


@router.post(
    "/batch/verify-remediations",
    summary="批量验证修复",
    responses={
        200: {"description": "批量验证成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def batch_verify_remediations(payload: BatchVerifyRemediationsRequest, request: Request) -> dict:
    """批量验证修复效果"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info(f"批量验证修复 | count={len(payload.failure_ids)}")

    try:
        engine = get_self_healing_engine()

        results = []
        batch_size = 10  # 分批处理，避免速率限制

        for i in range(0, len(payload.failure_ids), batch_size):
            batch = payload.failure_ids[i : i + batch_size]
            for failure_id in batch:
                try:
                    failure = next((f for f in engine.failure_history if f.id == failure_id), None)
                    if failure is None:
                        results.append(
                            {
                                "success": False,
                                "failure_id": failure_id,
                                "error": "故障不存在",
                            }
                        )
                        continue

                    verified = engine.verify_remediation(failure)
                    results.append(
                        {
                            "success": True,
                            "failure_id": failure_id,
                            "verified": verified,
                        }
                    )
                except Exception as e:
                    logger.error(f"验证单个修复失败: {e}")
                    results.append(
                        {
                            "success": False,
                            "failure_id": failure_id,
                            "error": str(e),
                        }
                    )

        success_count = sum(1 for r in results if r["success"])
        verified_count = sum(1 for r in results if r.get("verified", False))
        logger.info(f"批量验证完成 | total={len(results)} | success={success_count} | verified={verified_count}")

        return {
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "verified_count": verified_count,
            "results": results,
        }
    except Exception as e:
        logger.error(f"批量验证修复失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量验证修复失败: {str(e)}")


# ----------------------------------------------------------------------
# 1️⃣1️⃣ 监控和健康端点 (4个)
# ----------------------------------------------------------------------


@router.get(
    "/health",
    summary="自愈引擎健康检查",
    responses={
        200: {"description": "健康检查通过"},
        503: {"description": "自愈模块不可用"},
    },
)
async def health_check(request: Request) -> dict:
    """检查自愈引擎健康状态"""
    _verify_internal_key(request)

    logger.info("自愈引擎健康检查")

    try:
        if not SELF_HEALING_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "自愈模块不可用",
                "available": False,
            }

        engine = get_self_healing_engine()
        stats = engine.get_statistics()

        return {
            "status": "healthy",
            "message": "自愈引擎运行正常",
            "available": True,
            "statistics": stats,
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": f"健康检查失败: {str(e)}",
            "available": False,
        }


@router.get(
    "/remediations",
    summary="获取修复历史",
    responses={
        200: {"description": "修复历史列表"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def list_remediations(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> dict:
    """获取修复历史记录"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info(f"获取修复历史 | limit={limit} | offset={offset}")

    try:
        engine = get_self_healing_engine()

        remediations = [r.to_dict() for r in engine.remediation_history]
        remediations.reverse()  # 最新的在前

        total = len(remediations)
        paginated_remediations = remediations[offset : offset + limit]

        logger.debug(f"获取修复历史成功，共 {total} 条，返回 {len(paginated_remediations)} 条")
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": paginated_remediations,
        }
    except Exception as e:
        logger.error(f"获取修复历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取修复历史失败: {str(e)}")


@router.get(
    "/cooldowns",
    summary="获取冷却期状态",
    responses={
        200: {"description": "冷却期状态"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def list_cooldowns(request: Request) -> dict:
    """获取所有策略的冷却期状态"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info("获取冷却期状态")

    try:
        engine = get_self_healing_engine()

        cooldowns = []
        now = datetime.now()

        for policy_id, cooldown_end in engine.cooldowns.items():
            remaining_seconds = (cooldown_end - now).total_seconds()
            cooldowns.append(
                {
                    "policy_id": policy_id,
                    "cooldown_end": cooldown_end.isoformat(),
                    "remaining_seconds": max(0, remaining_seconds),
                    "in_cooldown": now < cooldown_end,
                }
            )

        logger.debug(f"获取冷却期状态成功，共 {len(cooldowns)} 个")
        return {"total": len(cooldowns), "items": cooldowns}
    except Exception as e:
        logger.error(f"获取冷却期状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取冷却期状态失败: {str(e)}")


@router.post(
    "/cooldowns/{policy_id}/clear",
    summary="清除冷却期",
    responses={
        200: {"description": "冷却期清除成功"},
        401: {"description": "未授权"},
        404: {"description": "策略不存在"},
        503: {"description": "自愈模块不可用"},
    },
)
async def clear_cooldown(policy_id: str, request: Request) -> dict:
    """清除指定策略的冷却期"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"清除冷却期 | operator={operator_ip} | policy_id={policy_id}")

    try:
        engine = get_self_healing_engine()

        if policy_id not in engine.policies:
            raise HTTPException(status_code=404, detail=f"策略 {policy_id} 不存在")

        if policy_id in engine.cooldowns:
            del engine.cooldowns[policy_id]
            logger.info(f"冷却期已清除 | policy_id={policy_id}")
        else:
            logger.info(f"策略无冷却期 | policy_id={policy_id}")

        return {
            "success": True,
            "policy_id": policy_id,
            "message": "冷却期清除成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除冷却期失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清除冷却期失败: {str(e)}")


@router.get(
    "/engine-status",
    summary="获取引擎状态",
    responses={
        200: {"description": "引擎状态"},
        401: {"description": "未授权"},
        503: {"description": "自愈模块不可用"},
    },
)
async def get_engine_status(request: Request) -> dict:
    """获取自愈引擎的详细状态"""
    _verify_internal_key(request)
    if not SELF_HEALING_AVAILABLE:
        raise HTTPException(status_code=503, detail="自愈模块不可用")

    logger.info("获取引擎状态")

    try:
        engine = get_self_healing_engine()

        stats = engine.get_statistics()

        # 获取冷却期信息
        cooldown_info = []
        now = datetime.now()
        for policy_id, cooldown_end in engine.cooldowns.items():
            remaining_seconds = (cooldown_end - now).total_seconds()
            cooldown_info.append(
                {
                    "policy_id": policy_id,
                    "remaining_seconds": max(0, remaining_seconds),
                }
            )

        return {
            "status": "running",
            "available": True,
            "statistics": stats,
            "policies_count": len(engine.policies),
            "active_policies_count": len([p for p in engine.policies.values() if p.enabled]),
            "failures_count": len(engine.failure_history),
            "remediations_count": len(engine.remediation_history),
            "cooldowns_count": len(engine.cooldowns),
            "cooldowns": cooldown_info,
        }
    except Exception as e:
        logger.error(f"获取引擎状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取引擎状态失败: {str(e)}")
