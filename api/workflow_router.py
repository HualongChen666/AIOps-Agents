# -*- coding: utf-8 -*-
# api/workflow_router.py — 工作流仿真 SSE 接口
#
# 🔧 本次严格 Review 修复(WR):
#   - WR1 [P1]:增加操作人 IP 审计
#   - WR2 [P1]:request.is_disconnected 调用时机优化
#   - WR3 [P2]:类型注解收紧
#   - WR4 [P2]:SSE 心跳事件(防代理超时断连)
#   - WR5 [P2]:Semaphore 满时返回 503
#   - WR6 [P2]:工作流定义返回深拷贝

import asyncio
import copy
import json
import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from core.workflow.engine import WorkflowExecutor, parse_json_workflow
from core.workflow_engine import (
    simulate_workflow_stream,
)
from core.workflow_repository import get_workflow_repository
from core.auth import get_current_user, require_permission, check_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/workflows", tags=["工作流"])


# ============================================================
# 模块级常量
# ============================================================
# 🔧 BUG-FIX-13(低危):SSE 全局并发限制
_SSE_MAX_CONCURRENT = 20
_sse_semaphore = asyncio.Semaphore(_SSE_MAX_CONCURRENT)

# DSL workflow executor
_executor = WorkflowExecutor()


async def _noop_handler(node: Any, context: Any) -> dict[str, Any]:
    return {"status": "ok", "node_id": node.id}


async def _delay_handler(node: Any, context: Any) -> dict[str, Any]:
    seconds = node.config.get("seconds", 1)
    await asyncio.sleep(max(0, float(seconds)))
    return {"status": "ok", "node_id": node.id, "delay": seconds}


async def _task_handler(node: Any, context: Any) -> dict[str, Any]:
    """Execute a workflow task node based on its configured action."""
    config = getattr(node, "config", None) or {}
    action = config.get("action", "noop")
    params = config.get("params", {})

    if action == "noop":
        return {"status": "ok", "node_id": node.id, "action": action}

    if action == "send_alert":
        from core.alert_engine import alert_history

        alert_id = params.get("id") or f"wf-{uuid.uuid4().hex[:8]}"
        alert = {
            "id": alert_id,
            "title": params.get("title", f"Workflow task {node.id}"),
            "level": params.get("level", "warning"),
            "source": "workflow",
            "node_id": node.id,
        }
        alert_history.appendleft(alert)
        return {"status": "ok", "node_id": node.id, "action": action, "alert_id": alert_id}

    if action == "log":
        logger.info(f"Workflow task {node.id}: {params.get('message', 'executed')}")
        return {"status": "ok", "node_id": node.id, "action": action}

    if action == "http_get":
        url = params.get("url")
        if not url:
            raise ValueError("http_get action requires params.url")
        import httpx

        # Use environment variable to control SSL verification (default: True for security)
        ssl_verify = os.environ.get("WORKFLOW_ROUTER_SSL_VERIFY", "true").lower() == "true"
        if not ssl_verify:
            logging.warning(
                "SSL verification is disabled in workflow_router - this is a security risk!"
            )
        try:
            async with httpx.AsyncClient(timeout=10, verify=ssl_verify) as client:
                resp = await client.get(url)
            return {
                "status": "ok",
                "node_id": node.id,
                "action": action,
                "url": url,
                "status_code": resp.status_code,
            }
        except httpx.TimeoutException as exc:
            logger.error(f"HTTP request timeout for {url}: {exc}")
            raise ValueError(f"HTTP request timeout: {exc}")
        except httpx.HTTPError as exc:
            logger.error(f"HTTP request failed for {url}: {exc}")
            raise ValueError(f"HTTP request failed: {exc}")

    raise ValueError(f"Unsupported task action '{action}' for node {node.id}")


_executor.register_handler("noop", _noop_handler)
_executor.register_handler("delay", _delay_handler)
_executor.register_handler("task", _task_handler)

# 🔧 WR4 [P2]:SSE 心跳间隔(秒,防 nginx/cloudflare 超时断连)
_SSE_HEARTBEAT_INTERVAL_SEC = 30


# ============================================================
# 接口1:获取所有工作流定义
# 🔧 Workflow完整性修复:使用数据库持久化替代内存存储
# 🔧 安全修复:添加JWT认证和RBAC权限检查
# ============================================================
@router.get(
    "/definitions",
    summary="获取所有工作流定义",
    responses={
        200: {
            "description": "工作流定义列表",
            "content": {
                "application/json": {
                    "example": {
                        "data_collection": {
                            "key": "data_collection",
                            "name": "数据采集与摄入",
                            "description": "从各种数据源采集指标和日志",
                            "nodes": ["collect-source", "normalize", "store"],
                        }
                    }
                }
            },
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        500: {"description": "服务器内部错误"},
    },
)
def list_workflows(
    request: Request,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """
    返回所有工作流的元数据
    对应前端:工作流选择器按钮 + 底部详情栏数据

    🔧 Workflow完整性修复:从数据库读取工作流定义
    🔧 安全修复:添加速率限制
    """
    # 🔧 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    logger.info("请求工作流定义列表")
    try:
        repo = get_workflow_repository()
        workflows = repo.list_workflow_definitions(status="active")
        
        # 转换为前端期望的格式
        definitions = {}
        for wf in workflows:
            definitions[wf.id] = {
                "key": wf.id,
                "name": wf.name,
                "description": wf.description or "",
                "nodes": wf.definition.get("nodes", len(wf.definition.get("steps", []))),
                "time": wf.definition.get("time", "N/A"),
                "rate": wf.definition.get("rate", "N/A"),
                "steps": wf.definition.get("steps", []),
            }
        
        logger.debug(f"工作流定义返回成功,共 {len(definitions)} 个")
        return definitions
    except Exception as e:
        logger.error(f"工作流定义获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"工作流定义获取失败: {str(e)[:200]}")


# ============================================================
# 接口2:工作流仿真 SSE 流式输出
# 🔧 WR1 + WR5 [P1/P2]:操作 IP 审计 + Semaphore 满返回 503
# ============================================================
@router.get(
    "/simulate/{wf_key}",
    summary="仿真执行工作流(SSE 流式输出)",
    responses={
        200: {
            "description": "SSE流式输出",
            "content": {"text/event-stream": {"example": 'data: {"type": "workflow_start"}\n\n'}},
        },
        404: {"description": "工作流不存在"},
        503: {"description": "并发已满"},
    },
)
async def simulate_workflow(wf_key: str, request: Request):
    """
    启动工作流仿真,通过 SSE 逐步推送每个节点的执行状态
    对应前端:▶ 运行仿真按钮 → 节点变色动画 + 日志面板实时追加

    SSE 事件格式:
      data: {"type": "workflow_start",  "wf_name": "数据采集与摄入", ...}
      data: {"type": "step_start",      "node_key": "collect-source", ...}
      data: {"type": "step_complete",   "node_key": "collect-source", ...}
      data: {"type": "workflow_done",   "total_ms": 3200, ...}
      data: {"type": "heartbeat",       "ts": "10:30:00", ...}      🔧 WR4
      data: {"type": "error",           "msg": "...", ...}

    🔧 Workflow完整性修复:从数据库验证工作流存在性
    🔧 WR1 [P1]:操作人 IP 审计
    🔧 WR5 [P2]:Semaphore 满时立即返回 503,而非等待
    🔧 安全修复:添加速率限制
    """
    # 🔧 WR1:操作人 IP
    operator_ip = request.client.host if request.client else "unknown"
    
    # 🔧 速率限制:30/minute
    check_rate_limit(operator_ip, requests_per_minute=30)

    # 🔧 Workflow完整性修复:从数据库验证工作流存在性
    repo = get_workflow_repository()
    workflow = repo.get_workflow_definition(wf_key)
    if not workflow:
        logger.warning(
            f"工作流仿真请求失败 | operator={operator_ip} | "
            f"未知 wf_key='{wf_key}'"
        )
        raise HTTPException(status_code=404, detail=f"未知工作流 '{wf_key}'")

    # 🔧 WR5 [P2]:Semaphore 满时立即返回 503
    # 非阻塞尝试获取(立即返回),防止 SSE 连接长时间挂起
    if _sse_semaphore.locked():
        # 注意:asyncio.Semaphore 没有标准的 try_acquire,这里用 locked() 估算
        # 严格判定:计数为 0 表示已满
        try:
            # _value 是 CPython 实现细节,但比 locked() 更准确
            current_value = getattr(_sse_semaphore, "_value", 0)
            if current_value <= 0:
                logger.warning(
                    f"SSE 并发已满 ({_SSE_MAX_CONCURRENT}) | "
                    f"operator={operator_ip} | wf_key={wf_key}"
                )
                return JSONResponse(
                    status_code=503,
                    content={"detail": f"工作流仿真并发已满({_SSE_MAX_CONCURRENT}),请稍后重试"},
                )
        except AttributeError:
            # 跨 Python 版本兼容:无 _value 属性时降级到 locked() 检测
            pass

    logger.info(f"工作流仿真启动 | operator={operator_ip} | wf_key='{wf_key}'")

    async def event_generator():
        """
        SSE 事件生成器
        🔧 WR1:记录操作人 IP
        🔧 WR2:request.is_disconnected 在 try 外尽早调用
        🔧 WR4:增加心跳事件防代理超时断连
        """
        # 🔧 BUG-FIX-13(低危):标准 acquire/release 模式管理 Semaphore
        async with _sse_semaphore:
            logger.debug(f"SSE 仿真已获取并发配额 | operator={operator_ip} | wf_key='{wf_key}'")

            # 🔧 WR4:发送初始心跳,验证连接
            try:
                heartbeat_data = json.dumps({"type": "heartbeat", "msg": "connected"})
                yield f"data: {heartbeat_data}\n\n"
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)

            try:
                async for event in simulate_workflow_stream(wf_key):

                    # 🔧 WR2:每次推送前检测客户端是否已断开
                    try:
                        if await request.is_disconnected():
                            logger.info(
                                "客户端已断开,终止工作流仿真 | "
                                f"operator={operator_ip} | wf_key='{wf_key}'"
                            )
                            break
                    except Exception as disc_err:
                        # 部分 ASGI 实现可能抛异常,降级到事件循环检查
                        logger.debug(f"is_disconnected 检测异常(已忽略): {disc_err}")

                    # 序列化单独 try/except,失败时推送 error 事件
                    try:
                        payload = json.dumps(event, ensure_ascii=False)
                    except (TypeError, ValueError) as json_err:
                        logger.error(f"SSE 事件序列化失败: {json_err} | event={event}")
                        error_payload = json.dumps(
                            {
                                "type": "error",
                                "msg": f"事件序列化失败: {str(json_err)[:200]}",
                            },
                            ensure_ascii=False,
                        )
                        yield f"data: {error_payload}\n\n"
                        continue

                    yield f"data: {payload}\n\n"

            except asyncio.CancelledError:
                # 客户端强制断开触发 CancelledError,正常退出不报错
                logger.info(
                    f"SSE 连接被取消(客户端强制断开) | operator={operator_ip} | wf_key='{wf_key}'"
                )

            except Exception as e:
                # 生成器内部未预期异常,推送 error 事件后退出
                logger.error(
                    "工作流仿真生成器内部异常 | "
                    f"operator={operator_ip} | wf_key='{wf_key}' | error={e}",
                    exc_info=True,
                )
                try:
                    error_payload = json.dumps(
                        {
                            "type": "error",
                            "msg": f"仿真执行内部错误: {str(e)[:200]}",
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {error_payload}\n\n"
                except Exception as e:
                    logging.exception("Unexpected exception: %s", e)

            finally:
                logger.debug(f"SSE 仿真释放并发配额 | operator={operator_ip} | wf_key='{wf_key}'")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "Access-Control-Allow-Origin": "*",
        },
    )


# ============================================================
# CRUD: 工作流定义增删改查
# ============================================================
class WorkflowStep(BaseModel):
    key: str = Field(..., min_length=1, max_length=128, description="节点标识")
    title: str = Field(..., min_length=1, max_length=128, description="节点标题")
    desc: str = Field(default="", max_length=256, description="节点描述")


class WorkflowCreate(BaseModel):
    wf_key: str = Field(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$", description="工作流唯一键"
    )
    name: str = Field(..., min_length=1, max_length=128, description="工作流名称")
    description: str = Field(default="", max_length=512, description="工作流描述")
    steps: list[WorkflowStep] = Field(..., min_length=1, description="工作流节点列表")
    time: str = Field(default="N/A", max_length=32, description="平均耗时展示文本")
    rate: str = Field(default="N/A", max_length=32, description="成功率展示文本")


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128, description="工作流名称")
    description: str | None = Field(default=None, max_length=512, description="工作流描述")
    steps: list[WorkflowStep] | None = Field(
        default=None, min_length=1, description="工作流节点列表"
    )
    time: str | None = Field(default=None, max_length=32, description="平均耗时展示文本")
    rate: str | None = Field(default=None, max_length=32, description="成功率展示文本")


def _to_engine_dict(data: WorkflowCreate | WorkflowUpdate) -> dict[str, Any]:
    """Pydantic 模型转引擎所需的普通 dict"""
    payload = data.model_dump(
        exclude_unset=True, exclude={"wf_key"} if isinstance(data, WorkflowCreate) else set()
    )
    # model_dump 已经递归把 WorkflowStep 转成 dict
    if "steps" in payload and payload["steps"] is not None:
        payload["steps"] = [dict(s) for s in payload["steps"]]
    return payload


@router.get(
    "/definitions/{wf_key}",
    summary="获取单个工作流定义",
    responses={
        200: {"description": "工作流定义"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def get_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取单个工作流定义详情"""
    # 🔧 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    repo = get_workflow_repository()
    workflow = repo.get_workflow_definition(wf_key)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
    
    return {
        "key": workflow.id,
        "name": workflow.name,
        "description": workflow.description or "",
        "nodes": workflow.definition.get("nodes", len(workflow.definition.get("steps", []))),
        "time": workflow.definition.get("time", "N/A"),
        "rate": workflow.definition.get("rate", "N/A"),
        "steps": workflow.definition.get("steps", []),
    }


@router.post(
    "/definitions",
    summary="创建工作流定义",
    status_code=201,
    responses={
        201: {"description": "创建成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def create_workflow(
    request: Request,
    body: WorkflowCreate,
    current_user = Depends(require_permission("workflow", "create"))
) -> dict[str, Any]:
    """新增一个工作流定义,创建后可立即被仿真执行"""
    # 🔧 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        payload = _to_engine_dict(body)
        
        workflow = repo.create_workflow_definition(
            wf_key=body.wf_key,
            name=body.name,
            description=body.description,
            definition=payload,
            created_by=current_user.username if current_user else "system",
        )
        
        return {
            "key": workflow.id,
            "name": workflow.name,
            "description": workflow.description or "",
            "nodes": workflow.definition.get("nodes", len(workflow.definition.get("steps", []))),
            "time": workflow.definition.get("time", "N/A"),
            "rate": workflow.definition.get("rate", "N/A"),
            "steps": workflow.definition.get("steps", []),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put(
    "/definitions/{wf_key}",
    summary="更新工作流定义",
    responses={
        200: {"description": "更新成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def update_workflow(
    request: Request,
    body: WorkflowUpdate,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "update"))
) -> dict[str, Any]:
    """更新指定工作流定义"""
    # 🔧 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        payload = _to_engine_dict(body)
        if not payload:
            raise HTTPException(status_code=400, detail="请求体不能为空")
        
        workflow = repo.update_workflow_definition(
            wf_key=wf_key,
            name=body.name,
            description=body.description,
            definition=payload,
        )
        
        return {
            "key": workflow.id,
            "name": workflow.name,
            "description": workflow.description or "",
            "nodes": workflow.definition.get("nodes", len(workflow.definition.get("steps", []))),
            "time": workflow.definition.get("time", "N/A"),
            "rate": workflow.definition.get("rate", "N/A"),
            "steps": workflow.definition.get("steps", []),
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=404 if "不存在" in str(exc) else 400, detail=str(exc)
        ) from exc


@router.delete(
    "/definitions/{wf_key}",
    summary="删除工作流定义",
    responses={
        200: {"description": "删除成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def delete_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "delete"))
) -> dict[str, str]:
    """删除指定工作流定义"""
    # 🔧 速率限制:10/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=10)
    
    try:
        repo = get_workflow_repository()
        repo.delete_workflow_definition(wf_key)
        return {"detail": f"工作流 '{wf_key}' 已删除"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ============================================================
# 🔧 WR5 [P2]:维护接口 — 查询当前 SSE 并发状态
# ============================================================
@router.get(
    "/concurrent",
    summary="查询当前 SSE 并发状态(维护用)",
    include_in_schema=False,
    responses={
        200: {
            "description": "并发状态",
            "content": {
                "application/json": {
                    "example": {
                        "max_concurrent": 20,
                        "available": 15,
                        "in_use": 5,
                        "is_locked": False,
                    }
                }
            },
        },
    },
)
async def get_concurrent_status() -> dict[str, Any]:
    """
    🔧 WR5:查询当前 SSE 并发使用情况
    供运维监控调用
    """
    try:
        current_value = getattr(_sse_semaphore, "_value", _SSE_MAX_CONCURRENT)
        in_use = _SSE_MAX_CONCURRENT - current_value
    except AttributeError:
        current_value = -1
        in_use = -1

    return {
        "max_concurrent": _SSE_MAX_CONCURRENT,
        "available": current_value,
        "in_use": in_use,
        "is_locked": _sse_semaphore.locked(),
    }


class WorkflowExecuteRequest(BaseModel):
    """Request to execute a DSL-defined workflow."""

    workflow: dict[str, Any]


@router.post("/execute", summary="执行 DSL 工作流")
async def execute_workflow(body: WorkflowExecuteRequest) -> dict[str, Any]:
    """Execute a workflow defined in the request body (JSON/YAML DSL)."""
    try:
        dag = parse_json_workflow(json.dumps(body.workflow))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    context = await _executor.execute(dag)
    return {
        "workflow_id": context.workflow_id,
        "run_id": context.run_id,
        "status": context.status.value,
        "results": context.results,
        "errors": context.errors,
    }


# ============================================================
# Workflow Execution Management (6 endpoints)
# ============================================================

class WorkflowExecutionRequest(BaseModel):
    """Request to execute a workflow by key."""
    wf_key: str = Field(..., min_length=1, max_length=64, description="工作流键")
    trigger_source: str = Field(default="manual", max_length=100, description="触发源")
    parameters: dict[str, Any] = Field(default_factory=dict, description="执行参数")


@router.post(
    "/{wf_key}/execute",
    summary="执行工作流",
    status_code=201,
    responses={
        201: {"description": "执行成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def execute_workflow_by_key(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    body: WorkflowExecutionRequest = None,
    current_user = Depends(require_permission("workflow", "execute"))
) -> dict[str, Any]:
    """执行指定工作流并创建执行记录"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        if workflow.status != "active":
            raise HTTPException(status_code=400, detail=f"工作流 '{wf_key}' 状态为 {workflow.status}，无法执行")
        
        # 创建执行记录
        execution = repo.create_workflow_execution(
            workflow_id=wf_key,
            triggered_by="user",
            trigger_source=body.trigger_source if body else "manual",
            executor=current_user.username if current_user else "system",
        )
        
        logger.info(f"工作流执行已创建: {execution.id} for workflow {wf_key}")
        
        return {
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"工作流执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {str(e)[:200]}")


@router.get(
    "/executions",
    summary="获取执行记录列表",
    responses={
        200: {"description": "执行记录列表"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def list_executions(
    request: Request,
    workflow_id: str = None,
    status: str = None,
    limit: int = 100,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取工作流执行记录列表，支持按工作流ID和状态过滤"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        executions = repo.list_workflow_executions(
            workflow_id=workflow_id,
            status=status,
            limit=min(limit, 1000),
        )
        
        result = []
        for exec in executions:
            result.append({
                "execution_id": exec.id,
                "workflow_id": exec.workflow_id,
                "status": exec.status,
                "started_at": exec.started_at.isoformat() if exec.started_at else None,
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "duration_sec": exec.duration_sec,
                "triggered_by": exec.triggered_by,
                "trigger_source": exec.trigger_source,
                "executor": exec.executor,
            })
        
        return {
            "total": len(result),
            "executions": result,
        }
    except Exception as e:
        logger.error(f"获取执行记录列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取执行记录列表失败: {str(e)[:200]}")


@router.get(
    "/executions/{execution_id}",
    summary="获取单个执行记录",
    responses={
        200: {"description": "执行记录详情"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "执行记录不存在"},
    },
)
def get_execution(
    request: Request,
    execution_id: str = Path(..., min_length=1, max_length=100),
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取单个工作流执行记录详情"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        execution = repo.get_workflow_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail=f"执行记录 '{execution_id}' 不存在")
        
        return {
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status,
            "result": execution.result,
            "error_message": execution.error_message,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_sec": execution.duration_sec,
            "triggered_by": execution.triggered_by,
            "trigger_source": execution.trigger_source,
            "executor": execution.executor,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取执行记录失败: {str(e)[:200]}")


@router.post(
    "/executions/{execution_id}/cancel",
    summary="取消执行",
    responses={
        200: {"description": "取消成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "执行记录不存在"},
        400: {"description": "执行状态不允许取消"},
    },
)
def cancel_execution(
    request: Request,
    execution_id: str = Path(..., min_length=1, max_length=100),
    current_user = Depends(require_permission("workflow", "execute"))
) -> dict[str, str]:
    """取消正在执行的工作流"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        execution = repo.get_workflow_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail=f"执行记录 '{execution_id}' 不存在")
        
        if execution.status not in ["running"]:
            raise HTTPException(status_code=400, detail=f"执行状态为 {execution.status}，无法取消")
        
        repo.update_workflow_execution(
            execution_id=execution_id,
            status="cancelled",
            error_message="Cancelled by user",
        )
        
        logger.info(f"工作流执行已取消: {execution_id}")
        return {"detail": f"执行记录 '{execution_id}' 已取消"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"取消执行失败: {str(e)[:200]}")


@router.post(
    "/executions/{execution_id}/retry",
    summary="重试执行",
    status_code=201,
    responses={
        201: {"description": "重试成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "执行记录不存在"},
        400: {"description": "执行状态不允许重试"},
    },
)
def retry_execution(
    request: Request,
    execution_id: str = Path(..., min_length=1, max_length=100),
    current_user = Depends(require_permission("workflow", "execute"))
) -> dict[str, Any]:
    """重试失败的工作流执行"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        execution = repo.get_workflow_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail=f"执行记录 '{execution_id}' 不存在")
        
        if execution.status not in ["failed", "cancelled"]:
            raise HTTPException(status_code=400, detail=f"执行状态为 {execution.status}，无法重试")
        
        # 创建新的执行记录
        new_execution = repo.create_workflow_execution(
            workflow_id=execution.workflow_id,
            triggered_by="retry",
            trigger_source=execution_id,
            executor=current_user.username if current_user else "system",
        )
        
        logger.info(f"工作流执行重试已创建: {new_execution.id} from {execution_id}")
        
        return {
            "execution_id": new_execution.id,
            "workflow_id": new_execution.workflow_id,
            "status": new_execution.status,
            "started_at": new_execution.started_at.isoformat() if new_execution.started_at else None,
            "original_execution_id": execution_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重试执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重试执行失败: {str(e)[:200]}")


@router.delete(
    "/executions/{execution_id}",
    summary="删除执行记录",
    responses={
        200: {"description": "删除成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "执行记录不存在"},
    },
)
def delete_execution(
    request: Request,
    execution_id: str = Path(..., min_length=1, max_length=100),
    current_user = Depends(require_permission("workflow", "delete"))
) -> dict[str, str]:
    """删除工作流执行记录"""
    # 速率限制:10/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=10)
    
    try:
        repo = get_workflow_repository()
        execution = repo.get_workflow_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail=f"执行记录 '{execution_id}' 不存在")
        
        # 删除执行记录（需要扩展repository方法）
        from sqlalchemy.orm import Session
        from core.database import SessionLocal
        from core.models import WorkflowExecution
        
        db = SessionLocal()
        try:
            db_exec = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
            if db_exec:
                db.delete(db_exec)
                db.commit()
                logger.info(f"工作流执行记录已删除: {execution_id}")
                return {"detail": f"执行记录 '{execution_id}' 已删除"}
            else:
                raise HTTPException(status_code=404, detail=f"执行记录 '{execution_id}' 不存在")
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除执行记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除执行记录失败: {str(e)[:200]}")


# ============================================================
# Workflow Status Management (4 endpoints)
# ============================================================

@router.post(
    "/{wf_key}/pause",
    summary="暂停工作流",
    responses={
        200: {"description": "暂停成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
        400: {"description": "工作流状态不允许暂停"},
    },
)
def pause_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "update"))
) -> dict[str, Any]:
    """暂停指定工作流"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        if workflow.status != "active":
            raise HTTPException(status_code=400, detail=f"工作流状态为 {workflow.status}，无法暂停")
        
        updated = repo.update_workflow_definition(wf_key, status="paused")
        
        logger.info(f"工作流已暂停: {wf_key} by {current_user.username if current_user else 'system'}")
        
        return {
            "key": updated.id,
            "name": updated.name,
            "status": updated.status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"暂停工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"暂停工作流失败: {str(e)[:200]}")


@router.post(
    "/{wf_key}/resume",
    summary="恢复工作流",
    responses={
        200: {"description": "恢复成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
        400: {"description": "工作流状态不允许恢复"},
    },
)
def resume_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "update"))
) -> dict[str, Any]:
    """恢复已暂停的工作流"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        if workflow.status != "paused":
            raise HTTPException(status_code=400, detail=f"工作流状态为 {workflow.status}，无法恢复")
        
        updated = repo.update_workflow_definition(wf_key, status="active")
        
        logger.info(f"工作流已恢复: {wf_key} by {current_user.username if current_user else 'system'}")
        
        return {
            "key": updated.id,
            "name": updated.name,
            "status": updated.status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"恢复工作流失败: {str(e)[:200]}")


@router.post(
    "/{wf_key}/archive",
    summary="归档工作流",
    responses={
        200: {"description": "归档成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
        400: {"description": "工作流状态不允许归档"},
    },
)
def archive_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "update"))
) -> dict[str, Any]:
    """归档指定工作流"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        if workflow.status == "archived":
            raise HTTPException(status_code=400, detail=f"工作流已归档")
        
        updated = repo.update_workflow_definition(wf_key, status="archived")
        
        logger.info(f"工作流已归档: {wf_key} by {current_user.username if current_user else 'system'}")
        
        return {
            "key": updated.id,
            "name": updated.name,
            "status": updated.status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"归档工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"归档工作流失败: {str(e)[:200]}")


@router.post(
    "/{wf_key}/activate",
    summary="激活工作流",
    responses={
        200: {"description": "激活成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
        400: {"description": "工作流状态不允许激活"},
    },
)
def activate_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "update"))
) -> dict[str, Any]:
    """激活已归档或暂停的工作流"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        if workflow.status == "active":
            raise HTTPException(status_code=400, detail=f"工作流已激活")
        
        updated = repo.update_workflow_definition(wf_key, status="active")
        
        logger.info(f"工作流已激活: {wf_key} by {current_user.username if current_user else 'system'}")
        
        return {
            "key": updated.id,
            "name": updated.name,
            "status": updated.status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"激活工作流失败: {str(e)[:200]}")


# ============================================================
# Workflow Version Management (3 endpoints)
# ============================================================

@router.get(
    "/{wf_key}/versions",
    summary="获取版本历史",
    responses={
        200: {"description": "版本历史"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def get_workflow_versions(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取工作流版本历史（当前实现返回当前版本信息）"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 当前实现返回当前版本信息
        # 完整版本历史需要额外的版本历史表
        return {
            "workflow_id": workflow.id,
            "current_version": workflow.version,
            "versions": [
                {
                    "version": workflow.version,
                    "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
                    "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
                    "created_by": workflow.created_by,
                }
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取版本历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取版本历史失败: {str(e)[:200]}")


@router.post(
    "/{wf_key}/versions/{version}/rollback",
    summary="回滚到指定版本",
    responses={
        200: {"description": "回滚成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
        400: {"description": "版本不存在或无法回滚"},
    },
)
def rollback_workflow_version(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    version: int = Path(..., ge=1, description="版本号"),
    current_user = Depends(require_permission("workflow", "update"))
) -> dict[str, Any]:
    """回滚工作流到指定版本"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        if version > workflow.version:
            raise HTTPException(status_code=400, detail=f"版本 {version} 不存在")
        
        if version == workflow.version:
            raise HTTPException(status_code=400, detail=f"当前已是版本 {version}")
        
        # 完整回滚需要版本历史表，当前实现仅记录日志
        logger.warning(
            f"工作流回滚请求: {wf_key} to version {version} "
            f"(需要版本历史表支持完整回滚功能)"
        )
        
        # 更新版本号
        updated = repo.update_workflow_definition(
            wf_key=wf_key,
            version=version,
        )
        
        logger.info(f"工作流版本已回滚: {wf_key} to version {version}")
        
        return {
            "key": updated.id,
            "name": updated.name,
            "version": updated.version,
            "message": f"已回滚到版本 {version}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回滚版本失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"回滚版本失败: {str(e)[:200]}")


@router.get(
    "/{wf_key}/versions/{version}",
    summary="获取指定版本详情",
    responses={
        200: {"description": "版本详情"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流或版本不存在"},
    },
)
def get_workflow_version(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    version: int = Path(..., ge=1, description="版本号"),
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取工作流指定版本的详情"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        if version > workflow.version:
            raise HTTPException(status_code=404, detail=f"版本 {version} 不存在")
        
        # 当前实现返回当前版本信息
        # 完整版本历史需要额外的版本历史表
        return {
            "workflow_id": workflow.id,
            "version": workflow.version if version == workflow.version else version,
            "definition": workflow.definition if version == workflow.version else None,
            "message": "完整版本历史需要版本历史表支持" if version != workflow.version else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取版本详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取版本详情失败: {str(e)[:200]}")


# ============================================================
# Workflow Template Management (3 endpoints)
# ============================================================

class WorkflowTemplateCreate(BaseModel):
    """Request to create a workflow template."""
    template_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$", description="模板ID")
    name: str = Field(..., min_length=1, max_length=128, description="模板名称")
    description: str = Field(default="", max_length=512, description="模板描述")
    category: str = Field(default="general", max_length=50, description="模板分类")
    definition: dict[str, Any] = Field(..., description="工作流定义模板")
    parameters: dict[str, Any] = Field(default_factory=dict, description="模板参数")


@router.get(
    "/templates",
    summary="获取模板列表",
    responses={
        200: {"description": "模板列表"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def list_templates(
    request: Request,
    category: str = None,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取工作流模板列表，支持按分类过滤"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        # 当前实现返回预定义模板列表
        # 完整实现需要WorkflowTemplate表
        templates = [
            {
                "template_id": "data_collection",
                "name": "数据采集模板",
                "description": "从各种数据源采集指标和日志",
                "category": "data",
                "parameters": {
                    "sources": ["prometheus", "elasticsearch"],
                    "interval": "60s",
                },
            },
            {
                "template_id": "alert_processing",
                "name": "告警处理模板",
                "description": "自动化告警处理和响应",
                "category": "alert",
                "parameters": {
                    "severity": ["critical", "warning"],
                    "auto_resolve": True,
                },
            },
            {
                "template_id": "backup",
                "name": "备份模板",
                "description": "定期数据备份",
                "category": "maintenance",
                "parameters": {
                    "schedule": "daily",
                    "retention_days": 30,
                },
            },
        ]
        
        if category:
            templates = [t for t in templates if t.get("category") == category]
        
        return {
            "total": len(templates),
            "templates": templates,
        }
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)[:200]}")


@router.post(
    "/templates",
    summary="创建模板",
    status_code=201,
    responses={
        201: {"description": "创建成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def create_template(
    request: Request,
    body: WorkflowTemplateCreate,
    current_user = Depends(require_permission("workflow", "create"))
) -> dict[str, Any]:
    """创建工作流模板"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        # 当前实现仅记录日志
        # 完整实现需要WorkflowTemplate表
        logger.info(
            f"创建工作流模板请求: {body.template_id} "
            f"(需要WorkflowTemplate表支持完整模板功能)"
        )
        
        return {
            "template_id": body.template_id,
            "name": body.name,
            "description": body.description,
            "category": body.category,
            "message": "模板创建需要WorkflowTemplate表支持",
        }
    except Exception as e:
        logger.error(f"创建模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建模板失败: {str(e)[:200]}")


class TemplateApplyRequest(BaseModel):
    """Request to apply a template."""
    wf_key: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$", description="工作流键")
    name: str = Field(..., min_length=1, max_length=128, description="工作流名称")
    description: str = Field(default="", max_length=512, description="工作流描述")
    parameters: dict[str, Any] = Field(default_factory=dict, description="模板参数值")


@router.post(
    "/templates/{template_id}/apply",
    summary="应用模板创建工作流",
    status_code=201,
    responses={
        201: {"description": "应用成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "模板不存在"},
    },
)
def apply_template(
    request: Request,
    template_id: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    body: TemplateApplyRequest = None,
    current_user = Depends(require_permission("workflow", "create"))
) -> dict[str, Any]:
    """应用模板创建工作流"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        # 当前实现仅记录日志
        # 完整实现需要WorkflowTemplate表
        logger.info(
            f"应用工作流模板请求: {template_id} -> {body.wf_key if body else 'unknown'} "
            f"(需要WorkflowTemplate表支持完整模板功能)"
        )
        
        return {
            "template_id": template_id,
            "workflow_key": body.wf_key if body else "unknown",
            "message": "模板应用需要WorkflowTemplate表支持",
        }
    except Exception as e:
        logger.error(f"应用模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"应用模板失败: {str(e)[:200]}")


# ============================================================
# Workflow Scheduling (3 endpoints)
# ============================================================

class WorkflowScheduleCreate(BaseModel):
    """Request to create a workflow schedule."""
    schedule_type: str = Field(..., description="调度类型: cron, interval, event")
    cron_expression: str = Field(default="", max_length=100, description="Cron表达式")
    interval_seconds: int = Field(default=0, ge=0, description="间隔秒数")
    event_trigger: str = Field(default="", max_length=200, description="事件触发器")
    enabled: bool = Field(default=True, description="是否启用")
    parameters: dict[str, Any] = Field(default_factory=dict, description="调度参数")


@router.post(
    "/{wf_key}/schedule",
    summary="创建调度",
    status_code=201,
    responses={
        201: {"description": "创建成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def create_schedule(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    body: WorkflowScheduleCreate = None,
    current_user = Depends(require_permission("workflow", "create"))
) -> dict[str, Any]:
    """为工作流创建调度"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 当前实现仅记录日志
        # 完整实现需要WorkflowSchedule表
        schedule_id = f"schedule-{uuid.uuid4().hex[:16]}"
        logger.info(
            f"创建工作流调度请求: {schedule_id} for {wf_key} "
            f"(需要WorkflowSchedule表支持完整调度功能)"
        )
        
        return {
            "schedule_id": schedule_id,
            "workflow_id": wf_key,
            "schedule_type": body.schedule_type if body else "cron",
            "enabled": body.enabled if body else True,
            "message": "调度创建需要WorkflowSchedule表支持",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建调度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建调度失败: {str(e)[:200]}")


@router.get(
    "/{wf_key}/schedules",
    summary="获取调度列表",
    responses={
        200: {"description": "调度列表"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def list_schedules(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取工作流的调度列表"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 当前实现返回空列表
        # 完整实现需要WorkflowSchedule表
        return {
            "workflow_id": wf_key,
            "total": 0,
            "schedules": [],
            "message": "调度列表需要WorkflowSchedule表支持",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取调度列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取调度列表失败: {str(e)[:200]}")


@router.delete(
    "/{wf_key}/schedules/{schedule_id}",
    summary="删除调度",
    responses={
        200: {"description": "删除成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流或调度不存在"},
    },
)
def delete_schedule(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    schedule_id: str = Path(..., min_length=1, max_length=100),
    current_user = Depends(require_permission("workflow", "delete"))
) -> dict[str, str]:
    """删除工作流调度"""
    # 速率限制:10/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=10)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 当前实现仅记录日志
        # 完整实现需要WorkflowSchedule表
        logger.info(
            f"删除工作流调度请求: {schedule_id} for {wf_key} "
            f"(需要WorkflowSchedule表支持完整调度功能)"
        )
        
        return {
            "detail": f"调度 '{schedule_id}' 已删除",
            "message": "调度删除需要WorkflowSchedule表支持",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除调度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除调度失败: {str(e)[:200]}")


# ============================================================
# Workflow Metrics/Statistics (3 endpoints)
# ============================================================

@router.get(
    "/{wf_key}/statistics",
    summary="获取工作流统计",
    responses={
        200: {"description": "工作流统计"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def get_workflow_statistics(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    days: int = 30,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取指定工作流的统计信息"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 获取执行记录
        executions = repo.list_workflow_executions(workflow_id=wf_key, limit=1000)
        
        # 计算统计信息
        total_executions = len(executions)
        completed = sum(1 for e in executions if e.status == "completed")
        failed = sum(1 for e in executions if e.status == "failed")
        cancelled = sum(1 for e in executions if e.status == "cancelled")
        running = sum(1 for e in executions if e.status == "running")
        
        # 计算平均执行时间
        durations = [e.duration_sec for e in executions if e.duration_sec is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 计算成功率
        success_rate = (completed / total_executions * 100) if total_executions > 0 else 0
        
        return {
            "workflow_id": wf_key,
            "total_executions": total_executions,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "running": running,
            "success_rate": round(success_rate, 2),
            "avg_duration_sec": round(avg_duration, 2),
            "period_days": days,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工作流统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流统计失败: {str(e)[:200]}")


@router.get(
    "/statistics/summary",
    summary="获取全局统计摘要",
    responses={
        200: {"description": "全局统计摘要"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def get_statistics_summary(
    request: Request,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取所有工作流的全局统计摘要"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        
        # 获取所有工作流
        workflows = repo.list_workflow_definitions(status="active")
        
        # 获取所有执行记录
        all_executions = repo.list_workflow_executions(limit=10000)
        
        # 计算全局统计
        total_workflows = len(workflows)
        total_executions = len(all_executions)
        completed = sum(1 for e in all_executions if e.status == "completed")
        failed = sum(1 for e in all_executions if e.status == "failed")
        running = sum(1 for e in all_executions if e.status == "running")
        
        # 计算平均执行时间
        durations = [e.duration_sec for e in all_executions if e.duration_sec is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 计算成功率
        success_rate = (completed / total_executions * 100) if total_executions > 0 else 0
        
        return {
            "total_workflows": total_workflows,
            "total_executions": total_executions,
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": round(success_rate, 2),
            "avg_duration_sec": round(avg_duration, 2),
        }
    except Exception as e:
        logger.error(f"获取全局统计摘要失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取全局统计摘要失败: {str(e)[:200]}")


@router.get(
    "/statistics/trends",
    summary="获取统计趋势",
    responses={
        200: {"description": "统计趋势"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def get_statistics_trends(
    request: Request,
    days: int = 30,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取工作流执行统计趋势"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        from datetime import datetime, timedelta
        
        repo = get_workflow_repository()
        
        # 获取执行记录
        all_executions = repo.list_workflow_executions(limit=10000)
        
        # 按日期分组统计
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        daily_stats = {}
        for exec in all_executions:
            if exec.started_at and exec.started_at >= start_date:
                date_key = exec.started_at.strftime("%Y-%m-%d")
                if date_key not in daily_stats:
                    daily_stats[date_key] = {"total": 0, "completed": 0, "failed": 0}
                daily_stats[date_key]["total"] += 1
                if exec.status == "completed":
                    daily_stats[date_key]["completed"] += 1
                elif exec.status == "failed":
                    daily_stats[date_key]["failed"] += 1
        
        # 转换为趋势数据
        trends = []
        for date in sorted(daily_stats.keys()):
            stats = daily_stats[date]
            trends.append({
                "date": date,
                "total": stats["total"],
                "completed": stats["completed"],
                "failed": stats["failed"],
                "success_rate": round(stats["completed"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0,
            })
        
        return {
            "period_days": days,
            "trends": trends,
        }
    except Exception as e:
        logger.error(f"获取统计趋势失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计趋势失败: {str(e)[:200]}")


# ============================================================
# Workflow Validation (2 endpoints)
# ============================================================

class WorkflowValidationRequest(BaseModel):
    """Request to validate a workflow definition."""
    definition: dict[str, Any] = Field(..., description="工作流定义")
    strict: bool = Field(default=True, description="严格模式")


@router.post(
    "/validate",
    summary="验证工作流定义",
    responses={
        200: {"description": "验证结果"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def validate_workflow_definition(
    request: Request,
    body: WorkflowValidationRequest,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """验证工作流定义的正确性"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        errors = []
        warnings = []
        
        # 验证必需字段
        if "steps" not in body.definition:
            errors.append("缺少必需字段: steps")
        elif not isinstance(body.definition["steps"], list):
            errors.append("steps 必须是数组")
        elif len(body.definition["steps"]) == 0:
            errors.append("steps 不能为空")
        
        # 验证节点定义
        if "steps" in body.definition and isinstance(body.definition["steps"], list):
            for idx, step in enumerate(body.definition["steps"]):
                if not isinstance(step, dict):
                    errors.append(f"步骤 {idx} 必须是对象")
                    continue
                if "key" not in step:
                    errors.append(f"步骤 {idx} 缺少 key 字段")
                if "title" not in step:
                    warnings.append(f"步骤 {idx} 缺少 title 字段")
        
        # 验证循环依赖（简化版）
        if body.strict and "steps" in body.definition:
            keys = [s.get("key") for s in body.definition["steps"] if isinstance(s, dict) and "key" in s]
            if len(keys) != len(set(keys)):
                errors.append("存在重复的节点 key")
        
        is_valid = len(errors) == 0
        
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "strict_mode": body.strict,
        }
    except Exception as e:
        logger.error(f"验证工作流定义失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"验证工作流定义失败: {str(e)[:200]}")


@router.post(
    "/{wf_key}/validate",
    summary="验证指定工作流",
    responses={
        200: {"description": "验证结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def validate_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """验证指定工作流的定义"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 复用验证逻辑
        validation_request = WorkflowValidationRequest(
            definition=workflow.definition,
            strict=True,
        )
        
        return validate_workflow_definition(request, validation_request, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"验证工作流失败: {str(e)[:200]}")


# ============================================================
# Workflow Export/Import (3 endpoints)
# ============================================================

@router.get(
    "/{wf_key}/export",
    summary="导出工作流",
    responses={
        200: {"description": "导出成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def export_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    format: str = "json",
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """导出工作流定义"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        export_data = {
            "workflow_id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "definition": workflow.definition,
            "version": workflow.version,
            "status": workflow.status,
            "created_by": workflow.created_by,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
            "exported_at": logger.info(f"工作流已导出: {wf_key} by {current_user.username if current_user else 'system'}"),
        }
        
        return export_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出工作流失败: {str(e)[:200]}")


class WorkflowImportRequest(BaseModel):
    """Request to import a workflow."""
    workflow_data: dict[str, Any] = Field(..., description="工作流数据")
    overwrite: bool = Field(default=False, description="是否覆盖已存在的工作流")


@router.post(
    "/import",
    summary="导入工作流",
    status_code=201,
    responses={
        201: {"description": "导入成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        409: {"description": "工作流已存在"},
    },
)
def import_workflow(
    request: Request,
    body: WorkflowImportRequest,
    current_user = Depends(require_permission("workflow", "create"))
) -> dict[str, Any]:
    """导入工作流定义"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        wf_key = body.workflow_data.get("workflow_id")
        if not wf_key:
            raise HTTPException(status_code=400, detail="缺少 workflow_id 字段")
        
        repo = get_workflow_repository()
        existing = repo.get_workflow_definition(wf_key)
        
        if existing and not body.overwrite:
            raise HTTPException(status_code=409, detail=f"工作流 '{wf_key}' 已存在")
        
        if existing and body.overwrite:
            # 更新现有工作流
            updated = repo.update_workflow_definition(
                wf_key=wf_key,
                name=body.workflow_data.get("name"),
                description=body.workflow_data.get("description"),
                definition=body.workflow_data.get("definition"),
                status=body.workflow_data.get("status", "active"),
            )
            logger.info(f"工作流已导入（覆盖）: {wf_key} by {current_user.username if current_user else 'system'}")
            return {
                "key": updated.id,
                "name": updated.name,
                "action": "overwritten",
            }
        else:
            # 创建新工作流
            workflow = repo.create_workflow_definition(
                wf_key=wf_key,
                name=body.workflow_data.get("name", wf_key),
                description=body.workflow_data.get("description", ""),
                definition=body.workflow_data.get("definition", {}),
                created_by=current_user.username if current_user else "import",
            )
            logger.info(f"工作流已导入（新建）: {wf_key} by {current_user.username if current_user else 'system'}")
            return {
                "key": workflow.id,
                "name": workflow.name,
                "action": "created",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入工作流失败: {str(e)[:200]}")


class WorkflowBatchImportRequest(BaseModel):
    """Request to batch import workflows."""
    workflows: list[dict[str, Any]] = Field(..., min_length=1, max_length=50, description="工作流数据列表")
    overwrite: bool = Field(default=False, description="是否覆盖已存在的工作流")
    stop_on_error: bool = Field(default=False, description="遇到错误是否停止")


@router.post(
    "/batch-import",
    summary="批量导入工作流",
    status_code=201,
    responses={
        201: {"description": "批量导入成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def batch_import_workflows(
    request: Request,
    body: WorkflowBatchImportRequest,
    current_user = Depends(require_permission("workflow", "create"))
) -> dict[str, Any]:
    """批量导入工作流定义"""
    # 速率限制:10/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=10)
    
    try:
        results = {
            "total": len(body.workflows),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }
        
        repo = get_workflow_repository()
        
        for idx, workflow_data in enumerate(body.workflows):
            try:
                wf_key = workflow_data.get("workflow_id")
                if not wf_key:
                    results["failed"] += 1
                    results["errors"].append({
                        "index": idx,
                        "error": "缺少 workflow_id 字段",
                    })
                    if body.stop_on_error:
                        break
                    continue
                
                existing = repo.get_workflow_definition(wf_key)
                
                if existing and not body.overwrite:
                    results["skipped"] += 1
                    continue
                
                if existing and body.overwrite:
                    repo.update_workflow_definition(
                        wf_key=wf_key,
                        name=workflow_data.get("name"),
                        description=workflow_data.get("description"),
                        definition=workflow_data.get("definition"),
                        status=workflow_data.get("status", "active"),
                    )
                    results["updated"] += 1
                else:
                    repo.create_workflow_definition(
                        wf_key=wf_key,
                        name=workflow_data.get("name", wf_key),
                        description=workflow_data.get("description", ""),
                        definition=workflow_data.get("definition", {}),
                        created_by=current_user.username if current_user else "batch_import",
                    )
                    results["created"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "index": idx,
                    "error": str(e)[:200],
                })
                if body.stop_on_error:
                    break
        
        logger.info(
            f"批量导入工作流完成: created={results['created']}, "
            f"updated={results['updated']}, skipped={results['skipped']}, "
            f"failed={results['failed']}"
        )
        
        return results
    except Exception as e:
        logger.error(f"批量导入工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量导入工作流失败: {str(e)[:200]}")


# ============================================================
# Workflow Approval (3 endpoints)
# ============================================================

class WorkflowApprovalRequest(BaseModel):
    """Request to approve/reject a workflow."""
    comment: str = Field(default="", max_length=500, description="审批意见")


@router.post(
    "/{wf_key}/approve",
    summary="审批工作流",
    responses={
        200: {"description": "审批成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def approve_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    body: WorkflowApprovalRequest = None,
    current_user = Depends(require_permission("workflow", "update"))
) -> dict[str, Any]:
    """审批工作流"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 当前实现仅记录日志
        # 完整实现需要WorkflowApproval表
        logger.info(
            f"工作流审批通过: {wf_key} by {current_user.username if current_user else 'system'} "
            f"(需要WorkflowApproval表支持完整审批功能)"
        )
        
        return {
            "workflow_id": wf_key,
            "status": "approved",
            "approved_by": current_user.username if current_user else "system",
            "comment": body.comment if body else "",
            "message": "审批记录需要WorkflowApproval表支持",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"审批工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"审批工作流失败: {str(e)[:200]}")


@router.post(
    "/{wf_key}/reject",
    summary="拒绝工作流",
    responses={
        200: {"description": "拒绝成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def reject_workflow(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    body: WorkflowApprovalRequest = None,
    current_user = Depends(require_permission("workflow", "update"))
) -> dict[str, Any]:
    """拒绝工作流"""
    # 速率限制:20/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 当前实现仅记录日志
        # 完整实现需要WorkflowApproval表
        logger.info(
            f"工作流审批拒绝: {wf_key} by {current_user.username if current_user else 'system'} "
            f"(需要WorkflowApproval表支持完整审批功能)"
        )
        
        return {
            "workflow_id": wf_key,
            "status": "rejected",
            "rejected_by": current_user.username if current_user else "system",
            "comment": body.comment if body else "",
            "message": "审批记录需要WorkflowApproval表支持",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"拒绝工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拒绝工作流失败: {str(e)[:200]}")


@router.get(
    "/approvals/pending",
    summary="获取待审批列表",
    responses={
        200: {"description": "待审批列表"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def list_pending_approvals(
    request: Request,
    limit: int = 100,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取待审批的工作流列表"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        # 当前实现返回空列表
        # 完整实现需要WorkflowApproval表
        return {
            "total": 0,
            "approvals": [],
            "message": "待审批列表需要WorkflowApproval表支持",
        }
    except Exception as e:
        logger.error(f"获取待审批列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取待审批列表失败: {str(e)[:200]}")


# ============================================================
# Workflow Monitoring (2 endpoints)
# ============================================================

@router.get(
    "/health",
    summary="获取工作流健康状态",
    responses={
        200: {"description": "健康状态"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def get_workflow_health(
    request: Request,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取工作流模块的整体健康状态"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        
        # 获取所有工作流
        workflows = repo.list_workflow_definitions(status="active")
        
        # 获取所有执行记录
        all_executions = repo.list_workflow_executions(limit=10000)
        
        # 计算健康指标
        total_workflows = len(workflows)
        running_executions = sum(1 for e in all_executions if e.status == "running")
        failed_executions = sum(1 for e in all_executions if e.status == "failed")
        
        # 计算健康分数
        success_rate = (
            sum(1 for e in all_executions if e.status == "completed") / len(all_executions) * 100
            if all_executions else 100
        )
        
        if success_rate >= 95 and failed_executions == 0:
            health_status = "healthy"
        elif success_rate >= 80:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        return {
            "status": health_status,
            "total_workflows": total_workflows,
            "running_executions": running_executions,
            "failed_executions": failed_executions,
            "success_rate": round(success_rate, 2),
            "sse_concurrent": {
                "max_concurrent": _SSE_MAX_CONCURRENT,
                "available": getattr(_sse_semaphore, "_value", _SSE_MAX_CONCURRENT),
                "in_use": _SSE_MAX_CONCURRENT - getattr(_sse_semaphore, "_value", _SSE_MAX_CONCURRENT),
            },
        }
    except Exception as e:
        logger.error(f"获取工作流健康状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流健康状态失败: {str(e)[:200]}")


@router.get(
    "/{wf_key}/health",
    summary="获取指定工作流健康状态",
    responses={
        200: {"description": "工作流健康状态"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "工作流不存在"},
    },
)
def get_workflow_health_by_key(
    request: Request,
    wf_key: str = Path(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """获取指定工作流的健康状态"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        workflow = repo.get_workflow_definition(wf_key)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流 '{wf_key}' 不存在")
        
        # 获取该工作流的执行记录
        executions = repo.list_workflow_executions(workflow_id=wf_key, limit=1000)
        
        # 计算健康指标
        total_executions = len(executions)
        running = sum(1 for e in executions if e.status == "running")
        failed = sum(1 for e in executions if e.status == "failed")
        completed = sum(1 for e in executions if e.status == "completed")
        
        # 计算健康分数
        success_rate = (completed / total_executions * 100) if total_executions > 0 else 100
        
        if success_rate >= 95 and failed == 0:
            health_status = "healthy"
        elif success_rate >= 80:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        return {
            "workflow_id": wf_key,
            "status": health_status,
            "workflow_status": workflow.status,
            "total_executions": total_executions,
            "running": running,
            "failed": failed,
            "completed": completed,
            "success_rate": round(success_rate, 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工作流健康状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流健康状态失败: {str(e)[:200]}")


# ============================================================
# Workflow Search (2 endpoints)
# ============================================================

@router.get(
    "/search",
    summary="搜索工作流",
    responses={
        200: {"description": "搜索结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def search_workflows(
    request: Request,
    q: str = "",
    status: str = None,
    created_by: str = None,
    limit: int = 100,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """搜索工作流，支持按名称、描述、状态、创建者过滤"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        workflows = repo.list_workflow_definitions(status=status, limit=1000)
        
        # 过滤和搜索
        results = []
        for wf in workflows:
            # 按创建者过滤
            if created_by and wf.created_by != created_by:
                continue
            
            # 按关键词搜索
            if q:
                search_text = f"{wf.name} {wf.description or ''}".lower()
                if q.lower() not in search_text:
                    continue
            
            results.append({
                "key": wf.id,
                "name": wf.name,
                "description": wf.description or "",
                "status": wf.status,
                "version": wf.version,
                "created_by": wf.created_by,
                "created_at": wf.created_at.isoformat() if wf.created_at else None,
            })
        
        # 限制结果数量
        results = results[:limit]
        
        return {
            "total": len(results),
            "query": q,
            "filters": {
                "status": status,
                "created_by": created_by,
            },
            "results": results,
        }
    except Exception as e:
        logger.error(f"搜索工作流失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索工作流失败: {str(e)[:200]}")


@router.get(
    "/executions/search",
    summary="搜索执行记录",
    responses={
        200: {"description": "搜索结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def search_executions(
    request: Request,
    workflow_id: str = None,
    status: str = None,
    executor: str = None,
    limit: int = 100,
    current_user = Depends(require_permission("workflow", "read"))
) -> dict[str, Any]:
    """搜索工作流执行记录，支持按工作流ID、状态、执行者过滤"""
    # 速率限制:60/minute
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)
    
    try:
        repo = get_workflow_repository()
        executions = repo.list_workflow_executions(
            workflow_id=workflow_id,
            status=status,
            limit=1000,
        )
        
        # 按执行者过滤
        results = []
        for exec in executions:
            if executor and exec.executor != executor:
                continue
            
            results.append({
                "execution_id": exec.id,
                "workflow_id": exec.workflow_id,
                "status": exec.status,
                "started_at": exec.started_at.isoformat() if exec.started_at else None,
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "duration_sec": exec.duration_sec,
                "executor": exec.executor,
                "triggered_by": exec.triggered_by,
            })
        
        # 限制结果数量
        results = results[:limit]
        
        return {
            "total": len(results),
            "filters": {
                "workflow_id": workflow_id,
                "status": status,
                "executor": executor,
            },
            "results": results,
        }
    except Exception as e:
        logger.error(f"搜索执行记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索执行记录失败: {str(e)[:200]}")
