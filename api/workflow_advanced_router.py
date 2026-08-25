# -*- coding: utf-8 -*-
# api/workflow_advanced_router.py — 工作流高级管理接口
#
# 实现工作流定义、执行、调度、触发器、变量、审计日志和统计的完整CRUD操作
# 共18个API端点

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from extensions.addons.operations.workflow_service.orchestrator import WorkflowOrchestrator
from extensions.addons.operations.workflow_service.repository import (
    InMemoryWorkflowRepository,
    get_repository,
)
from extensions.addons.operations.workflow_service.schemas import (
    ScheduledTask,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRequest,
    WorkflowStatus,
)

# Optional metrics import
try:
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Workflow metrics not available, metrics tracking disabled")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/workflow", tags=["工作流高级管理"])

# ============================================================
# 模块级常量和初始化
# ============================================================
_repository: Optional[InMemoryWorkflowRepository] = None
_orchestrator: Optional[WorkflowOrchestrator] = None


async def _get_repository() -> InMemoryWorkflowRepository:
    """获取工作流仓储实例（单例模式）"""
    global _repository
    if _repository is None:
        _repository = await get_repository()  # type: ignore
    return _repository


async def _get_orchestrator() -> WorkflowOrchestrator:
    """获取工作流编排器实例（单例模式）"""
    global _orchestrator
    if _orchestrator is None:
        repo = await _get_repository()
        _orchestrator = WorkflowOrchestrator(repo)
    return _orchestrator


# ============================================================
# Pydantic 数据模型
# ============================================================


class WorkflowDefinitionCreate(BaseModel):
    """创建工作流定义请求"""

    workflow_id: str = Field(..., min_length=1, max_length=128, description="工作流唯一标识")
    name: str = Field(..., min_length=1, max_length=128, description="工作流名称")
    description: str = Field(default="", max_length=512, description="工作流描述")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="工作流节点列表")
    schedule: Optional[str] = Field(None, description="Cron调度表达式")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class WorkflowDefinitionUpdate(BaseModel):
    """更新工作流定义请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    nodes: Optional[List[Dict[str, Any]]] = None
    schedule: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowExecutionCreate(BaseModel):
    """创建工作流执行请求"""

    workflow_id: str = Field(..., min_length=1, max_length=128, description="工作流ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="执行参数")
    requested_by: str = Field(default="system", description="请求者")
    priority: str = Field(default="medium", description="优先级: low/medium/high/critical")


class WorkflowExecutionUpdate(BaseModel):
    """更新工作流执行请求"""

    status: Optional[str] = None
    current_node: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ScheduleCreate(BaseModel):
    """创建调度请求"""

    schedule_id: str = Field(..., min_length=1, max_length=128, description="调度ID")
    workflow_id: str = Field(..., min_length=1, max_length=128, description="工作流ID")
    cron: str = Field(..., description="Cron表达式")
    params: Dict[str, Any] = Field(default_factory=dict, description="调度参数")


class ScheduleUpdate(BaseModel):
    """更新调度请求"""

    cron: Optional[str] = None
    enabled: Optional[bool] = None
    params: Optional[Dict[str, Any]] = None


class TriggerCreate(BaseModel):
    """创建触发器请求"""

    trigger_id: str = Field(..., min_length=1, max_length=128, description="触发器ID")
    name: str = Field(..., min_length=1, max_length=128, description="触发器名称")
    workflow_id: str = Field(..., min_length=1, max_length=128, description="工作流ID")
    trigger_type: str = Field(..., description="触发器类型: webhook/event/manual")
    config: Dict[str, Any] = Field(default_factory=dict, description="触发器配置")
    enabled: bool = Field(default=True, description="是否启用")


class TriggerUpdate(BaseModel):
    """更新触发器请求"""

    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class VariableCreate(BaseModel):
    """创建变量请求"""

    variable_id: str = Field(..., min_length=1, max_length=128, description="变量ID")
    name: str = Field(..., min_length=1, max_length=128, description="变量名称")
    value: Any = Field(..., description="变量值")
    variable_type: str = Field(default="string", description="变量类型: string/number/boolean/json")
    description: str = Field(default="", max_length=256, description="变量描述")


class VariableUpdate(BaseModel):
    """更新变量请求"""

    name: Optional[str] = None
    value: Optional[Any] = None
    variable_type: Optional[str] = None
    description: Optional[str] = None


class AuditLogResponse(BaseModel):
    """审计日志响应"""

    log_id: str
    action: str
    resource_type: str
    resource_id: str
    user: str
    timestamp: datetime
    details: Dict[str, Any]
    ip_address: str


class StatisticsResponse(BaseModel):
    """统计信息响应"""

    total_workflows: int
    active_workflows: int
    total_executions: int
    running_executions: int
    completed_executions: int
    failed_executions: int
    success_rate: float
    avg_duration_seconds: float
    total_schedules: int
    active_schedules: int
    total_triggers: int
    active_triggers: int
    total_variables: int


# ============================================================
# 内存存储（用于演示，生产环境应使用数据库）
# ============================================================
_schedules: Dict[str, ScheduledTask] = {}
_triggers: Dict[str, Dict[str, Any]] = {}
_variables: Dict[str, Dict[str, Any]] = {}
_audit_logs: List[Dict[str, Any]] = []


def _add_audit_log(
    action: str, resource_type: str, resource_id: str, user: str, details: Dict[str, Any], ip: str
) -> None:
    """添加审计日志"""
    log = {
        "log_id": f"LOG-{uuid.uuid4().hex[:16].upper()}",
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user": user,
        "timestamp": datetime.utcnow(),
        "details": details,
        "ip_address": ip,
    }
    _audit_logs.insert(0, log)
    # 保留最近1000条日志
    if len(_audit_logs) > 1000:
        _audit_logs.pop()


# ============================================================
# 工作流定义相关端点 (5个)
# ============================================================


@router.get("/definitions", summary="获取所有工作流定义")
async def list_workflow_definitions(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取所有工作流定义列表

    支持分页查询，返回工作流定义的详细信息
    """
    try:
        repo = await _get_repository()
        definitions = await repo.list_definitions(limit=limit + offset)
        paginated = definitions[offset : offset + limit]

        return {
            "total": len(definitions),
            "limit": limit,
            "offset": offset,
            "data": [d.model_dump() for d in paginated],
        }
    except Exception as e:
        logger.error(f"获取工作流定义列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流定义列表失败: {str(e)}")


@router.post("/definitions", summary="创建工作流定义", status_code=201)
async def create_workflow_definition(
    body: WorkflowDefinitionCreate, request: Request
) -> Dict[str, Any]:
    """
    创建新的工作流定义

    支持定义工作流的节点、调度和元数据
    """
    try:
        repo = await _get_repository()

        # 检查是否已存在
        existing = await repo.get_definition(body.workflow_id)
        if existing:
            raise HTTPException(status_code=400, detail=f"工作流定义 '{body.workflow_id}' 已存在")

        # 转换节点数据
        nodes = []
        for node_data in body.nodes:
            node = WorkflowNode(
                node_id=node_data.get("node_id", str(uuid.uuid4())),
                name=node_data.get("name", ""),
                node_type=node_data.get("node_type", "task"),
                command=node_data.get("command", ""),
                dependencies=node_data.get("dependencies", []),
                retries=node_data.get("retries", 0),
                timeout_seconds=node_data.get("timeout_seconds", 60),
                params=node_data.get("params", {}),
            )
            nodes.append(node)

        definition = WorkflowDefinition(
            workflow_id=body.workflow_id,
            name=body.name,
            description=body.description,
            nodes=nodes,
            schedule=body.schedule,
            metadata=body.metadata,
        )

        await repo.save_definition(definition)

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="create",
            resource_type="workflow_definition",
            resource_id=body.workflow_id,
            user="system",
            details={"name": body.name},
            ip=ip,
        )

        logger.info(f"创建工作流定义成功: {body.workflow_id}")
        return definition.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建工作流定义失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建工作流定义失败: {str(e)}")


@router.get("/definitions/{id}", summary="获取单个工作流定义")
async def get_workflow_definition(
    id: str = Path(..., min_length=1, description="工作流定义ID"),
) -> Dict[str, Any]:
    """
    获取指定工作流定义的详细信息
    """
    try:
        repo = await _get_repository()
        definition = await repo.get_definition(id)

        if not definition:
            raise HTTPException(status_code=404, detail=f"工作流定义 '{id}' 不存在")

        return definition.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工作流定义失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流定义失败: {str(e)}")


@router.patch("/definitions/{id}", summary="更新工作流定义")
async def update_workflow_definition(
    id: str = Path(..., min_length=1, description="工作流定义ID"),
    body: WorkflowDefinitionUpdate = None,
    request: Request = None,
) -> Dict[str, Any]:
    """
    更新工作流定义

    支持部分更新，只更新提供的字段
    """
    try:
        repo = await _get_repository()
        definition = await repo.get_definition(id)

        if not definition:
            raise HTTPException(status_code=404, detail=f"工作流定义 '{id}' 不存在")

        # 更新字段
        if body.name is not None:
            definition.name = body.name
        if body.description is not None:
            definition.description = body.description
        if body.nodes is not None:
            nodes = []
            for node_data in body.nodes:
                node = WorkflowNode(
                    node_id=node_data.get("node_id", str(uuid.uuid4())),
                    name=node_data.get("name", ""),
                    node_type=node_data.get("node_type", "task"),
                    command=node_data.get("command", ""),
                    dependencies=node_data.get("dependencies", []),
                    retries=node_data.get("retries", 0),
                    timeout_seconds=node_data.get("timeout_seconds", 60),
                    params=node_data.get("params", {}),
                )
                nodes.append(node)
            definition.nodes = nodes
        if body.schedule is not None:
            definition.schedule = body.schedule
        if body.metadata is not None:
            definition.metadata = body.metadata

        await repo.save_definition(definition)

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="update",
            resource_type="workflow_definition",
            resource_id=id,
            user="system",
            details=body.model_dump(exclude_unset=True) if body else {},
            ip=ip,
        )

        logger.info(f"更新工作流定义成功: {id}")
        return definition.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新工作流定义失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新工作流定义失败: {str(e)}")


@router.delete("/definitions/{id}", summary="删除工作流定义")
async def delete_workflow_definition(
    id: str = Path(..., min_length=1, description="工作流定义ID"),
    request: Request = None,
) -> Dict[str, str]:
    """
    删除指定的工作流定义
    """
    try:
        repo = await _get_repository()
        definition = await repo.get_definition(id)

        if not definition:
            raise HTTPException(status_code=404, detail=f"工作流定义 '{id}' 不存在")

        # 从内存中删除
        if hasattr(repo, "_definitions") and id in repo._definitions:
            del repo._definitions[id]

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="delete",
            resource_type="workflow_definition",
            resource_id=id,
            user="system",
            details={"name": definition.name},
            ip=ip,
        )

        logger.info(f"删除工作流定义成功: {id}")
        return {"detail": f"工作流定义 '{id}' 已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除工作流定义失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除工作流定义失败: {str(e)}")


# ============================================================
# 工作流执行相关端点 (6个)
# ============================================================


@router.get("/executions", summary="获取所有工作流执行记录")
async def list_workflow_executions(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    status: Optional[str] = Query(None, description="按状态过滤"),
) -> Dict[str, Any]:
    """
    获取工作流执行记录列表

    支持分页和状态过滤
    """
    try:
        repo = await _get_repository()
        tasks = await repo.list_tasks(limit=limit + offset)

        # 状态过滤
        if status:
            tasks = [t for t in tasks if t.status.value == status]

        paginated = tasks[offset : offset + limit]

        return {
            "total": len(tasks),
            "limit": limit,
            "offset": offset,
            "data": [t.model_dump() for t in paginated],
        }
    except Exception as e:
        logger.error(f"获取工作流执行记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流执行记录失败: {str(e)}")


@router.post("/executions", summary="创建工作流执行", status_code=201)
async def create_workflow_execution(
    body: WorkflowExecutionCreate, request: Request
) -> Dict[str, Any]:
    """
    创建新的工作流执行实例

    根据工作流定义创建执行任务
    """
    try:
        orchestrator = await _get_orchestrator()

        # 创建工作流请求
        workflow_request = WorkflowRequest(
            workflow_id=body.workflow_id,
            params=body.params,
            requested_by=body.requested_by,
            priority=body.priority,  # type: ignore
        )

        # 创建任务
        task = await orchestrator.create_task(workflow_request)

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="create",
            resource_type="workflow_execution",
            resource_id=task.task_id,
            user=body.requested_by,
            details={"workflow_id": body.workflow_id, "priority": body.priority},
            ip=ip,
        )

        logger.info(f"创建工作流执行成功: {task.task_id}")
        return task.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"创建工作流执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建工作流执行失败: {str(e)}")


@router.get("/executions/{id}", summary="获取单个工作流执行")
async def get_workflow_execution(
    id: str = Path(..., min_length=1, description="执行ID"),
) -> Dict[str, Any]:
    """
    获取指定工作流执行的详细信息
    """
    try:
        repo = await _get_repository()
        task = await repo.get_task(id)

        if not task:
            raise HTTPException(status_code=404, detail=f"工作流执行 '{id}' 不存在")

        return task.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工作流执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流执行失败: {str(e)}")


@router.patch("/executions/{id}", summary="更新工作流执行")
async def update_workflow_execution(
    id: str = Path(..., min_length=1, description="执行ID"),
    body: WorkflowExecutionUpdate = None,
    request: Request = None,
) -> Dict[str, Any]:
    """
    更新工作流执行状态和信息

    支持部分更新
    """
    try:
        repo = await _get_repository()
        task = await repo.get_task(id)

        if not task:
            raise HTTPException(status_code=404, detail=f"工作流执行 '{id}' 不存在")

        # 构建更新数据
        update_data = {}
        if body.status is not None:
            update_data["status"] = body.status
        if body.current_node is not None:
            update_data["current_node"] = body.current_node
        if body.result is not None:
            update_data["result"] = body.result
        if body.error is not None:
            update_data["error"] = body.error

        await repo.update_task(id, update_data)

        # 获取更新后的任务
        updated_task = await repo.get_task(id)

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="update",
            resource_type="workflow_execution",
            resource_id=id,
            user="system",
            details=update_data,
            ip=ip,
        )

        logger.info(f"更新工作流执行成功: {id}")
        return updated_task.model_dump() if updated_task else {}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新工作流执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新工作流执行失败: {str(e)}")


@router.post("/executions/{id}/start", summary="启动工作流执行")
async def start_workflow_execution(
    id: str = Path(..., min_length=1, description="执行ID"),
    request: Request = None,
) -> Dict[str, Any]:
    """
    启动工作流执行

    调用workflow_service的实际执行逻辑
    """
    try:
        repo = await _get_repository()
        orchestrator = await _get_orchestrator()

        task = await repo.get_task(id)
        if not task:
            raise HTTPException(status_code=404, detail=f"工作流执行 '{id}' 不存在")

        if task.status == WorkflowStatus.RUNNING:
            raise HTTPException(status_code=400, detail=f"工作流执行 '{id}' 已在运行中")

        # 异步执行工作流
        async def execute_workflow():
            try:
                result = await orchestrator.execute(task)
                logger.info(f"工作流执行完成: {id}, success={result.success}")
            except Exception as e:
                logger.error(f"工作流执行异常: {id}, error={e}", exc_info=True)
                await repo.update_task(id, {"status": WorkflowStatus.FAILED, "error": str(e)})

        # 在后台执行
        asyncio.create_task(execute_workflow())

        # 更新状态为运行中
        await repo.update_task(id, {"status": WorkflowStatus.RUNNING})

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="start",
            resource_type="workflow_execution",
            resource_id=id,
            user="system",
            details={"workflow_id": task.workflow_id},
            ip=ip,
        )

        logger.info(f"启动工作流执行成功: {id}")
        return {"detail": f"工作流执行 '{id}' 已启动", "task_id": id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动工作流执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动工作流执行失败: {str(e)}")


@router.post("/executions/{id}/stop", summary="停止工作流执行")
async def stop_workflow_execution(
    id: str = Path(..., min_length=1, description="执行ID"),
    request: Request = None,
) -> Dict[str, Any]:
    """
    停止正在运行的工作流执行
    """
    try:
        repo = await _get_repository()
        task = await repo.get_task(id)

        if not task:
            raise HTTPException(status_code=404, detail=f"工作流执行 '{id}' 不存在")

        if task.status != WorkflowStatus.RUNNING:
            raise HTTPException(status_code=400, detail=f"工作流执行 '{id}' 未在运行中，无法停止")

        # 更新状态为失败（模拟停止）
        await repo.update_task(
            id, {"status": WorkflowStatus.FAILED, "error": "Execution stopped by user"}
        )

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="stop",
            resource_type="workflow_execution",
            resource_id=id,
            user="system",
            details={"workflow_id": task.workflow_id},
            ip=ip,
        )

        logger.info(f"停止工作流执行成功: {id}")
        return {"detail": f"工作流执行 '{id}' 已停止"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止工作流执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"停止工作流执行失败: {str(e)}")


@router.post("/executions/{id}/pause", summary="暂停工作流执行")
async def pause_workflow_execution(
    id: str = Path(..., min_length=1, description="执行ID"),
    request: Request = None,
) -> Dict[str, Any]:
    """
    暂停正在运行的工作流执行
    """
    try:
        repo = await _get_repository()
        task = await repo.get_task(id)

        if not task:
            raise HTTPException(status_code=404, detail=f"工作流执行 '{id}' 不存在")

        if task.status != WorkflowStatus.RUNNING:
            raise HTTPException(status_code=400, detail=f"工作流执行 '{id}' 未在运行中，无法暂停")

        # 更新状态为暂停
        await repo.update_task(id, {"status": WorkflowStatus.PAUSED})

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="pause",
            resource_type="workflow_execution",
            resource_id=id,
            user="system",
            details={"workflow_id": task.workflow_id},
            ip=ip,
        )

        logger.info(f"暂停工作流执行成功: {id}")
        return {"detail": f"工作流执行 '{id}' 已暂停"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"暂停工作流执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"暂停工作流执行失败: {str(e)}")


@router.post("/executions/{id}/resume", summary="恢复工作流执行")
async def resume_workflow_execution(
    id: str = Path(..., min_length=1, description="执行ID"),
    request: Request = None,
) -> Dict[str, Any]:
    """
    恢复已暂停的工作流执行
    """
    try:
        repo = await _get_repository()
        orchestrator = await _get_orchestrator()

        task = await repo.get_task(id)
        if not task:
            raise HTTPException(status_code=404, detail=f"工作流执行 '{id}' 不存在")

        if task.status != WorkflowStatus.PAUSED:
            raise HTTPException(status_code=400, detail=f"工作流执行 '{id}' 未暂停，无法恢复")

        # 异步恢复执行
        async def resume_workflow():
            try:
                result = await orchestrator.execute(task)
                logger.info(f"工作流执行恢复完成: {id}, success={result.success}")
            except Exception as e:
                logger.error(f"工作流执行恢复异常: {id}, error={e}", exc_info=True)
                await repo.update_task(id, {"status": WorkflowStatus.FAILED, "error": str(e)})

        asyncio.create_task(resume_workflow())

        # 更新状态为运行中
        await repo.update_task(id, {"status": WorkflowStatus.RUNNING})

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="resume",
            resource_type="workflow_execution",
            resource_id=id,
            user="system",
            details={"workflow_id": task.workflow_id},
            ip=ip,
        )

        logger.info(f"恢复工作流执行成功: {id}")
        return {"detail": f"工作流执行 '{id}' 已恢复"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复工作流执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"恢复工作流执行失败: {str(e)}")


# ============================================================
# 工作流调度相关端点 (5个)
# ============================================================


@router.get("/schedules", summary="获取所有调度")
async def list_schedules(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取工作流调度列表
    """
    try:
        schedules_list = list(_schedules.values())
        paginated = schedules_list[offset : offset + limit]

        return {
            "total": len(schedules_list),
            "limit": limit,
            "offset": offset,
            "data": [s.model_dump() for s in paginated],
        }
    except Exception as e:
        logger.error(f"获取调度列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取调度列表失败: {str(e)}")


@router.post("/schedules", summary="创建调度", status_code=201)
async def create_schedule(body: ScheduleCreate, request: Request) -> Dict[str, Any]:
    """
    创建新的工作流调度
    """
    try:
        if body.schedule_id in _schedules:
            raise HTTPException(status_code=400, detail=f"调度 '{body.schedule_id}' 已存在")

        schedule = ScheduledTask(
            schedule_id=body.schedule_id,
            workflow_id=body.workflow_id,
            cron=body.cron,
            params=body.params,
            enabled=True,
        )

        _schedules[body.schedule_id] = schedule

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="create",
            resource_type="schedule",
            resource_id=body.schedule_id,
            user="system",
            details={"workflow_id": body.workflow_id, "cron": body.cron},
            ip=ip,
        )

        logger.info(f"创建调度成功: {body.schedule_id}")
        return schedule.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建调度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建调度失败: {str(e)}")


@router.get("/schedules/{id}", summary="获取单个调度")
async def get_schedule(
    id: str = Path(..., min_length=1, description="调度ID"),
) -> Dict[str, Any]:
    """
    获取指定调度的详细信息
    """
    try:
        schedule = _schedules.get(id)
        if not schedule:
            raise HTTPException(status_code=404, detail=f"调度 '{id}' 不存在")

        return schedule.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取调度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取调度失败: {str(e)}")


@router.patch("/schedules/{id}", summary="更新调度")
async def update_schedule(
    id: str = Path(..., min_length=1, description="调度ID"),
    body: ScheduleUpdate = None,
    request: Request = None,
) -> Dict[str, Any]:
    """
    更新工作流调度
    """
    try:
        schedule = _schedules.get(id)
        if not schedule:
            raise HTTPException(status_code=404, detail=f"调度 '{id}' 不存在")

        if body.cron is not None:
            schedule.cron = body.cron
        if body.enabled is not None:
            schedule.enabled = body.enabled
        if body.params is not None:
            schedule.params = body.params

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="update",
            resource_type="schedule",
            resource_id=id,
            user="system",
            details=body.model_dump(exclude_unset=True) if body else {},
            ip=ip,
        )

        logger.info(f"更新调度成功: {id}")
        return schedule.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新调度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新调度失败: {str(e)}")


@router.delete("/schedules/{id}", summary="删除调度")
async def delete_schedule(
    id: str = Path(..., min_length=1, description="调度ID"),
    request: Request = None,
) -> Dict[str, str]:
    """
    删除指定的工作流调度
    """
    try:
        schedule = _schedules.get(id)
        if not schedule:
            raise HTTPException(status_code=404, detail=f"调度 '{id}' 不存在")

        del _schedules[id]

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="delete",
            resource_type="schedule",
            resource_id=id,
            user="system",
            details={"workflow_id": schedule.workflow_id},
            ip=ip,
        )

        logger.info(f"删除调度成功: {id}")
        return {"detail": f"调度 '{id}' 已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除调度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除调度失败: {str(e)}")


@router.post("/schedules/{id}/enable", summary="启用调度")
async def enable_schedule(
    id: str = Path(..., min_length=1, description="调度ID"),
    request: Request = None,
) -> Dict[str, Any]:
    """
    启用工作流调度
    """
    try:
        schedule = _schedules.get(id)
        if not schedule:
            raise HTTPException(status_code=404, detail=f"调度 '{id}' 不存在")

        schedule.enabled = True

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="enable",
            resource_type="schedule",
            resource_id=id,
            user="system",
            details={"workflow_id": schedule.workflow_id},
            ip=ip,
        )

        logger.info(f"启用调度成功: {id}")
        return schedule.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启用调度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启用调度失败: {str(e)}")


@router.post("/schedules/{id}/disable", summary="禁用调度")
async def disable_schedule(
    id: str = Path(..., min_length=1, description="调度ID"),
    request: Request = None,
) -> Dict[str, Any]:
    """
    禁用工作流调度
    """
    try:
        schedule = _schedules.get(id)
        if not schedule:
            raise HTTPException(status_code=404, detail=f"调度 '{id}' 不存在")

        schedule.enabled = False

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="disable",
            resource_type="schedule",
            resource_id=id,
            user="system",
            details={"workflow_id": schedule.workflow_id},
            ip=ip,
        )

        logger.info(f"禁用调度成功: {id}")
        return schedule.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用调度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"禁用调度失败: {str(e)}")


# ============================================================
# 工作流触发器相关端点 (5个)
# ============================================================


@router.get("/triggers", summary="获取所有触发器")
async def list_triggers(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取工作流触发器列表
    """
    try:
        triggers_list = list(_triggers.values())
        paginated = triggers_list[offset : offset + limit]

        return {
            "total": len(triggers_list),
            "limit": limit,
            "offset": offset,
            "data": paginated,
        }
    except Exception as e:
        logger.error(f"获取触发器列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取触发器列表失败: {str(e)}")


@router.post("/triggers", summary="创建触发器", status_code=201)
async def create_trigger(body: TriggerCreate, request: Request) -> Dict[str, Any]:
    """
    创建新的工作流触发器
    """
    try:
        if body.trigger_id in _triggers:
            raise HTTPException(status_code=400, detail=f"触发器 '{body.trigger_id}' 已存在")

        trigger = {
            "trigger_id": body.trigger_id,
            "name": body.name,
            "workflow_id": body.workflow_id,
            "trigger_type": body.trigger_type,
            "config": body.config,
            "enabled": body.enabled,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        _triggers[body.trigger_id] = trigger

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="create",
            resource_type="trigger",
            resource_id=body.trigger_id,
            user="system",
            details={
                "workflow_id": body.workflow_id,
                "trigger_type": body.trigger_type,
            },
            ip=ip,
        )

        logger.info(f"创建触发器成功: {body.trigger_id}")
        return trigger

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建触发器失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建触发器失败: {str(e)}")


@router.get("/triggers/{id}", summary="获取单个触发器")
async def get_trigger(
    id: str = Path(..., min_length=1, description="触发器ID"),
) -> Dict[str, Any]:
    """
    获取指定触发器的详细信息
    """
    try:
        trigger = _triggers.get(id)
        if not trigger:
            raise HTTPException(status_code=404, detail=f"触发器 '{id}' 不存在")

        return trigger

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取触发器失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取触发器失败: {str(e)}")


@router.patch("/triggers/{id}", summary="更新触发器")
async def update_trigger(
    id: str = Path(..., min_length=1, description="触发器ID"),
    body: TriggerUpdate = None,
    request: Request = None,
) -> Dict[str, Any]:
    """
    更新工作流触发器
    """
    try:
        trigger = _triggers.get(id)
        if not trigger:
            raise HTTPException(status_code=404, detail=f"触发器 '{id}' 不存在")

        if body.name is not None:
            trigger["name"] = body.name
        if body.config is not None:
            trigger["config"] = body.config
        if body.enabled is not None:
            trigger["enabled"] = body.enabled
        trigger["updated_at"] = datetime.utcnow()

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="update",
            resource_type="trigger",
            resource_id=id,
            user="system",
            details=body.model_dump(exclude_unset=True) if body else {},
            ip=ip,
        )

        logger.info(f"更新触发器成功: {id}")
        return trigger

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新触发器失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新触发器失败: {str(e)}")


@router.delete("/triggers/{id}", summary="删除触发器")
async def delete_trigger(
    id: str = Path(..., min_length=1, description="触发器ID"),
    request: Request = None,
) -> Dict[str, str]:
    """
    删除指定的工作流触发器
    """
    try:
        trigger = _triggers.get(id)
        if not trigger:
            raise HTTPException(status_code=404, detail=f"触发器 '{id}' 不存在")

        del _triggers[id]

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="delete",
            resource_type="trigger",
            resource_id=id,
            user="system",
            details={"workflow_id": trigger["workflow_id"]},
            ip=ip,
        )

        logger.info(f"删除触发器成功: {id}")
        return {"detail": f"触发器 '{id}' 已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除触发器失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除触发器失败: {str(e)}")


# ============================================================
# 工作流变量相关端点 (5个)
# ============================================================


@router.get("/variables", summary="获取所有变量")
async def list_variables(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取工作流变量列表
    """
    try:
        variables_list = list(_variables.values())
        paginated = variables_list[offset : offset + limit]

        return {
            "total": len(variables_list),
            "limit": limit,
            "offset": offset,
            "data": paginated,
        }
    except Exception as e:
        logger.error(f"获取变量列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取变量列表失败: {str(e)}")


@router.post("/variables", summary="创建变量", status_code=201)
async def create_variable(body: VariableCreate, request: Request) -> Dict[str, Any]:
    """
    创建新的工作流变量
    """
    try:
        if body.variable_id in _variables:
            raise HTTPException(status_code=400, detail=f"变量 '{body.variable_id}' 已存在")

        variable = {
            "variable_id": body.variable_id,
            "name": body.name,
            "value": body.value,
            "variable_type": body.variable_type,
            "description": body.description,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        _variables[body.variable_id] = variable

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="create",
            resource_type="variable",
            resource_id=body.variable_id,
            user="system",
            details={"name": body.name, "variable_type": body.variable_type},
            ip=ip,
        )

        logger.info(f"创建变量成功: {body.variable_id}")
        return variable

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建变量失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建变量失败: {str(e)}")


@router.get("/variables/{id}", summary="获取单个变量")
async def get_variable(
    id: str = Path(..., min_length=1, description="变量ID"),
) -> Dict[str, Any]:
    """
    获取指定变量的详细信息
    """
    try:
        variable = _variables.get(id)
        if not variable:
            raise HTTPException(status_code=404, detail=f"变量 '{id}' 不存在")

        return variable

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取变量失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取变量失败: {str(e)}")


@router.patch("/variables/{id}", summary="更新变量")
async def update_variable(
    id: str = Path(..., min_length=1, description="变量ID"),
    body: VariableUpdate = None,
    request: Request = None,
) -> Dict[str, Any]:
    """
    更新工作流变量
    """
    try:
        variable = _variables.get(id)
        if not variable:
            raise HTTPException(status_code=404, detail=f"变量 '{id}' 不存在")

        if body.name is not None:
            variable["name"] = body.name
        if body.value is not None:
            variable["value"] = body.value
        if body.variable_type is not None:
            variable["variable_type"] = body.variable_type
        if body.description is not None:
            variable["description"] = body.description
        variable["updated_at"] = datetime.utcnow()

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="update",
            resource_type="variable",
            resource_id=id,
            user="system",
            details=body.model_dump(exclude_unset=True) if body else {},
            ip=ip,
        )

        logger.info(f"更新变量成功: {id}")
        return variable

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新变量失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新变量失败: {str(e)}")


@router.delete("/variables/{id}", summary="删除变量")
async def delete_variable(
    id: str = Path(..., min_length=1, description="变量ID"),
    request: Request = None,
) -> Dict[str, str]:
    """
    删除指定的工作流变量
    """
    try:
        variable = _variables.get(id)
        if not variable:
            raise HTTPException(status_code=404, detail=f"变量 '{id}' 不存在")

        del _variables[id]

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="delete",
            resource_type="variable",
            resource_id=id,
            user="system",
            details={"name": variable["name"]},
            ip=ip,
        )

        logger.info(f"删除变量成功: {id}")
        return {"detail": f"变量 '{id}' 已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除变量失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除变量失败: {str(e)}")


# ============================================================
# 审计日志相关端点 (1个)
# ============================================================


@router.get("/audit-logs", summary="获取审计日志")
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    action: Optional[str] = Query(None, description="按操作类型过滤"),
    resource_type: Optional[str] = Query(None, description="按资源类型过滤"),
) -> Dict[str, Any]:
    """
    获取工作流审计日志

    支持按操作类型和资源类型过滤
    """
    try:
        logs = _audit_logs

        # 过滤
        if action:
            logs = [log for log in logs if log["action"] == action]
        if resource_type:
            logs = [log for log in logs if log["resource_type"] == resource_type]

        paginated = logs[offset : offset + limit]

        return {
            "total": len(logs),
            "limit": limit,
            "offset": offset,
            "data": paginated,
        }
    except Exception as e:
        logger.error(f"获取审计日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取审计日志失败: {str(e)}")


# ============================================================
# 统计信息相关端点 (1个)
# ============================================================


@router.get("/statistics", summary="获取工作流统计信息")
async def get_statistics() -> Dict[str, Any]:
    """
    获取工作流系统的统计信息

    包括工作流数量、执行情况、调度、触发器、变量等统计
    """
    try:
        repo = await _get_repository()
        definitions = await repo.list_definitions(limit=1000)
        tasks = await repo.list_tasks(limit=1000)

        # 计算统计信息
        total_workflows = len(definitions)
        active_workflows = sum(1 for d in definitions if d.schedule)  # 有调度的视为活跃

        total_executions = len(tasks)
        running_executions = sum(1 for t in tasks if t.status == WorkflowStatus.RUNNING)
        completed_executions = sum(1 for t in tasks if t.status == WorkflowStatus.SUCCEEDED)
        failed_executions = sum(1 for t in tasks if t.status == WorkflowStatus.FAILED)

        success_rate = (
            (completed_executions / total_executions * 100) if total_executions > 0 else 0
        )

        # 计算平均执行时长
        completed_tasks = [t for t in tasks if t.status == WorkflowStatus.SUCCEEDED]
        avg_duration = 0
        if completed_tasks:
            durations = [(t.updated_at - t.created_at).total_seconds() for t in completed_tasks]
            avg_duration = sum(durations) / len(durations)

        total_schedules = len(_schedules)
        active_schedules = sum(1 for s in _schedules.values() if s.enabled)

        total_triggers = len(_triggers)
        active_triggers = sum(1 for t in _triggers.values() if t.get("enabled", False))

        total_variables = len(_variables)

        statistics = {
            "total_workflows": total_workflows,
            "active_workflows": active_workflows,
            "total_executions": total_executions,
            "running_executions": running_executions,
            "completed_executions": completed_executions,
            "failed_executions": failed_executions,
            "success_rate": round(success_rate, 2),
            "avg_duration_seconds": round(avg_duration, 2),
            "total_schedules": total_schedules,
            "active_schedules": active_schedules,
            "total_triggers": total_triggers,
            "active_triggers": active_triggers,
            "total_variables": total_variables,
        }

        return statistics

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
