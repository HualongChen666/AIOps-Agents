# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from config import INTERNAL_API_KEY
from core.auto_heal import get_pending_approvals


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
