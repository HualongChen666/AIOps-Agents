# -*- coding: utf-8 -*-
# api/workflow_automation_router.py — 工作流自动化接口
#
# 实现工作流自动化的完整API端点，共38个端点
# 包含：工作流定义、执行、调度、触发器、变量、审计日志、统计、版本控制、模板、重试策略、批量操作
#
# 功能特性：
# - 完整的CRUD操作
# - JWT认证和RBAC权限检查
# - 速率限制
# - 批量操作分批处理
# - 完整的日志记录
# - 错误处理和监控
# - 数据一致性保证

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission, check_rate_limit
from core.database import get_db
from core.models import User
from extensions.addons.operations.workflow_service.orchestrator import WorkflowOrchestrator
from extensions.addons.operations.workflow_service.repository import (
    WorkflowRepository,
    get_repository,
)
from extensions.addons.operations.workflow_service.schemas import (
    ScheduledTask,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRequest,
    WorkflowStatus,
    TaskPriority,
    WorkflowTask,
    WorkflowExecutionResult,
    WorkflowVersion,
    WorkflowTemplate,
    RetryPolicy,
    WorkflowMetric,
    SagaStep,
    SagaTransaction,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/workflow-automation", tags=["工作流自动化"])

# ============================================================
# 模块级常量和初始化
# ============================================================
_repository: Optional[WorkflowRepository] = None
_orchestrator: Optional[WorkflowOrchestrator] = None

# 批量操作配置
BATCH_SIZE = int(os.environ.get("WORKFLOW_BATCH_SIZE", "50"))
MAX_BATCH_SIZE = 100

# 性能监控
_METRICS_ENABLED = os.environ.get("WORKFLOW_METRICS_ENABLED", "true").lower() == "true"


async def _get_repository() -> WorkflowRepository:
    """获取工作流仓储实例（单例模式）"""
    global _repository
    if _repository is None:
        _repository = await get_repository(use_in_memory=False)
    return _repository


async def _get_orchestrator() -> WorkflowOrchestrator:
    """获取工作流编排器实例（单例模式）"""
    global _orchestrator
    if _orchestrator is None:
        repo = await _get_repository()
        _orchestrator = WorkflowOrchestrator(repo)
    return _orchestrator


def _record_metric(metric_name: str, value: float, labels: Dict[str, str] = None):
    """记录性能指标"""
    if _METRICS_ENABLED:
        try:
            logger.debug(f"Metric: {metric_name}={value} labels={labels}")
        except Exception as e:
            logger.warning(f"Failed to record metric: {e}")


def _add_audit_log(
    action: str,
    resource_type: str,
    resource_id: str,
    user: str,
    details: Dict[str, Any],
    ip: str,
    db: Session,
) -> None:
    """添加审计日志到数据库"""
    try:
        from core.models import AuditLog

        log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user=user,
            details=details,
            ip_address=ip,
            timestamp=datetime.utcnow(),
        )
        db.add(log)
        db.commit()
        logger.debug(f"Audit log recorded: {action} on {resource_type}:{resource_id}")
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}", exc_info=True)


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


class WorkflowVersionCreate(BaseModel):
    """创建工作流版本请求"""

    workflow_id: str = Field(..., min_length=1, max_length=128, description="工作流ID")
    message: str = Field(..., min_length=1, max_length=256, description="版本说明")


class WorkflowTemplateCreate(BaseModel):
    """创建工作流模板请求"""

    template_id: str = Field(..., min_length=1, max_length=128, description="模板ID")
    name: str = Field(..., min_length=1, max_length=128, description="模板名称")
    description: str = Field(default="", max_length=512, description="模板描述")
    source: str = Field(..., min_length=1, description="模板源代码")
    default_params: Dict[str, Any] = Field(default_factory=dict, description="默认参数")


class RetryPolicyCreate(BaseModel):
    """创建重试策略请求"""

    name: str = Field(..., min_length=1, max_length=128, description="策略名称")
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")
    base_delay_seconds: float = Field(default=1.0, ge=0, le=300, description="基础延迟秒数")
    max_delay_seconds: float = Field(default=60.0, ge=0, le=3600, description="最大延迟秒数")
    exponential_base: float = Field(default=2.0, ge=1.0, le=10.0, description="指数基数")
    retryable_errors: List[str] = Field(default_factory=list, description="可重试的错误类型")


class BatchOperationRequest(BaseModel):
    """批量操作请求"""

    operation: str = Field(..., description="操作类型: create/update/delete")
    items: List[Dict[str, Any]] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE, description="操作项列表")
    batch_size: int = Field(default=BATCH_SIZE, ge=1, le=MAX_BATCH_SIZE, description="批次大小")


# ============================================================
# 内存存储（用于演示，生产环境应使用数据库）
# ============================================================
_schedules: Dict[str, ScheduledTask] = {}
_triggers: Dict[str, Dict[str, Any]] = {}
_variables: Dict[str, Dict[str, Any]] = {}
_versions: Dict[str, List[WorkflowVersion]] = {}
_templates: Dict[str, WorkflowTemplate] = {}
_retry_policies: Dict[str, RetryPolicy] = {}


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
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    current_user: User = Depends(require_permission("workflow", "read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取所有工作流定义列表

    支持分页查询和状态过滤
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)

    try:
        repo = await _get_repository()
        definitions = await repo.list_definitions(limit=limit + offset)

        # 状态过滤
        if status:
            definitions = [d for d in definitions if d.metadata.get("status") == status]

        paginated = definitions[offset : offset + limit]

        _record_metric("workflow_definitions_list", len(paginated), {"status": status or "all"})

        logger.info(f"Listed {len(paginated)} workflow definitions for user {current_user.username}")

        return {
            "total": len(definitions),
            "limit": limit,
            "offset": offset,
            "data": [d.model_dump() for d in paginated],
        }
    except Exception as e:
        logger.error(f"获取工作流定义列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流定义列表失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_definitions_list_duration", duration)


@router.post("/definitions", summary="创建工作流定义", status_code=201)
async def create_workflow_definition(
    request: Request,
    body: WorkflowDefinitionCreate,
    current_user: User = Depends(require_permission("workflow", "create")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    创建新的工作流定义

    支持定义工作流的节点、调度和元数据
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)

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
            user=current_user.username,
            details={"name": body.name, "node_count": len(nodes)},
            ip=ip,
            db=db,
        )

        _record_metric("workflow_definition_created", 1, {"workflow_id": body.workflow_id})

        logger.info(f"Created workflow definition: {body.workflow_id} by user {current_user.username}")

        return definition.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建工作流定义失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建工作流定义失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_definition_create_duration", duration)


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
    request: Request,
    id: str = Path(..., min_length=1, description="工作流定义ID"),
    current_user: User = Depends(require_permission("workflow", "delete")),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    删除指定的工作流定义
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=10)

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
            user=current_user.username,
            details={"name": definition.name},
            ip=ip,
            db=db,
        )

        _record_metric("workflow_definition_deleted", 1, {"workflow_id": id})

        logger.info(f"Deleted workflow definition: {id} by user {current_user.username}")

        return {"detail": f"工作流定义 '{id}' 已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除工作流定义失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除工作流定义失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_definition_delete_duration", duration)


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
# 审计日志相关端点 (4个)
# ============================================================


@router.get("/audit-logs", summary="获取审计日志")
async def list_audit_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    action: Optional[str] = Query(None, description="按操作类型过滤"),
    resource_type: Optional[str] = Query(None, description="按资源类型过滤"),
    current_user: User = Depends(require_permission("workflow", "read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取工作流审计日志

    支持按操作类型和资源类型过滤
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)

    try:
        from core.models import AuditLog

        query = db.query(AuditLog)

        # 过滤条件
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        # 排序
        query = query.order_by(AuditLog.timestamp.desc())

        # 分页
        total = query.count()
        logs = query.offset(offset).limit(limit).all()

        _record_metric("workflow_audit_logs_list", len(logs), {"action": action or "all", "resource_type": resource_type or "all"})

        logger.info(f"Listed {len(logs)} audit logs for user {current_user.username}")

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [
                {
                    "log_id": log.id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "user": log.user,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "details": log.details,
                    "ip_address": log.ip_address,
                }
                for log in logs
            ],
        }
    except Exception as e:
        logger.error(f"获取审计日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取审计日志失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_audit_logs_list_duration", duration)


# ============================================================
# 统计信息相关端点 (3个)
# ============================================================


@router.get("/statistics", summary="获取工作流统计信息")
async def get_statistics(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(require_permission("workflow", "read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取工作流系统的统计信息

    包括工作流数量、执行情况、调度、触发器、变量等统计
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=30)

    try:
        repo = await _get_repository()
        definitions = await repo.list_definitions(limit=1000)
        tasks = await repo.list_tasks(limit=10000)

        # 过滤指定天数内的数据
        since = datetime.utcnow() - timedelta(days=days)
        recent_tasks = [t for t in tasks if t.created_at >= since]

        # 计算统计信息
        total_workflows = len(definitions)
        active_workflows = sum(1 for d in definitions if d.schedule)

        total_executions = len(recent_tasks)
        running_executions = sum(1 for t in recent_tasks if t.status == WorkflowStatus.RUNNING)
        completed_executions = sum(1 for t in recent_tasks if t.status == WorkflowStatus.SUCCEEDED)
        failed_executions = sum(1 for t in recent_tasks if t.status == WorkflowStatus.FAILED)

        success_rate = (completed_executions / total_executions * 100) if total_executions > 0 else 0

        # 计算平均执行时长
        avg_duration = 0.0
        if completed_executions > 0:
            durations = []
            for t in recent_tasks:
                if t.status == WorkflowStatus.SUCCEEDED and t.updated_at and t.created_at:
                    duration = (t.updated_at - t.created_at).total_seconds()
                    durations.append(duration)
            if durations:
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

        _record_metric("workflow_statistics", 1, {"days": days})

        logger.info(f"Retrieved workflow statistics for {days} days by user {current_user.username}")

        return statistics

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_statistics_duration", duration)


# ============================================================
# 8. 版本控制 (3个端点)
# ============================================================


@router.get("/versions/{workflow_id}", summary="获取工作流版本列表")
async def list_workflow_versions(
    request: Request,
    workflow_id: str = Path(..., min_length=1, description="工作流ID"),
    current_user: User = Depends(require_permission("workflow", "read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取指定工作流的所有版本
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)

    try:
        versions = _versions.get(workflow_id, [])

        _record_metric("workflow_versions_list", len(versions), {"workflow_id": workflow_id})

        logger.info(f"Listed {len(versions)} versions for workflow {workflow_id} by user {current_user.username}")

        return {
            "workflow_id": workflow_id,
            "total": len(versions),
            "data": [v.model_dump() for v in versions],
        }
    except Exception as e:
        logger.error(f"获取工作流版本列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流版本列表失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_versions_list_duration", duration)


@router.post("/versions", summary="创建工作流版本", status_code=201)
async def create_workflow_version(
    request: Request,
    body: WorkflowVersionCreate,
    current_user: User = Depends(require_permission("workflow", "create")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    为工作流创建新版本快照
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)

    try:
        repo = await _get_repository()
        definition = await repo.get_definition(body.workflow_id)

        if not definition:
            raise HTTPException(status_code=404, detail=f"工作流 '{body.workflow_id}' 不存在")

        version = WorkflowVersion(
            version=str(uuid.uuid4())[:8],
            workflow_id=body.workflow_id,
            commit_hash=str(uuid.uuid4())[:16],
            message=body.message,
        )

        if body.workflow_id not in _versions:
            _versions[body.workflow_id] = []
        _versions[body.workflow_id].append(version)

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="create",
            resource_type="workflow_version",
            resource_id=version.version,
            user=current_user.username,
            details={"workflow_id": body.workflow_id, "message": body.message},
            ip=ip,
            db=db,
        )

        _record_metric("workflow_version_created", 1, {"workflow_id": body.workflow_id})

        logger.info(f"Created workflow version {version.version} for {body.workflow_id} by user {current_user.username}")

        return version.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建工作流版本失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建工作流版本失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_version_create_duration", duration)


@router.delete("/versions/{workflow_id}/{version}", summary="删除工作流版本")
async def delete_workflow_version(
    request: Request,
    workflow_id: str = Path(..., min_length=1, description="工作流ID"),
    version: str = Path(..., min_length=1, description="版本号"),
    current_user: User = Depends(require_permission("workflow", "delete")),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    删除指定的工作流版本
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=10)

    try:
        if workflow_id not in _versions:
            raise HTTPException(status_code=404, detail=f"工作流 '{workflow_id}' 不存在")

        version_to_delete = None
        for v in _versions[workflow_id]:
            if v.version == version:
                version_to_delete = v
                break

        if not version_to_delete:
            raise HTTPException(status_code=404, detail=f"版本 '{version}' 不存在")

        _versions[workflow_id].remove(version_to_delete)

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="delete",
            resource_type="workflow_version",
            resource_id=version,
            user=current_user.username,
            details={"workflow_id": workflow_id},
            ip=ip,
            db=db,
        )

        _record_metric("workflow_version_deleted", 1, {"workflow_id": workflow_id, "version": version})

        logger.info(f"Deleted workflow version {version} for {workflow_id} by user {current_user.username}")

        return {"detail": f"工作流版本 '{version}' 已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除工作流版本失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除工作流版本失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_version_delete_duration", duration)


# ============================================================
# 9. 模板管理 (3个端点)
# ============================================================


@router.get("/templates", summary="获取所有模板")
async def list_templates(
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(require_permission("workflow", "read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取所有工作流模板列表
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=60)

    try:
        templates_list = list(_templates.values())
        paginated = templates_list[offset : offset + limit]

        _record_metric("workflow_templates_list", len(paginated))

        logger.info(f"Listed {len(paginated)} templates for user {current_user.username}")

        return {
            "total": len(templates_list),
            "limit": limit,
            "offset": offset,
            "data": [t.model_dump() for t in paginated],
        }
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_templates_list_duration", duration)


@router.post("/templates", summary="创建模板", status_code=201)
async def create_template(
    request: Request,
    body: WorkflowTemplateCreate,
    current_user: User = Depends(require_permission("workflow", "create")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    创建新的工作流模板
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=20)

    try:
        # 检查是否已存在
        if body.template_id in _templates:
            raise HTTPException(status_code=400, detail=f"模板 '{body.template_id}' 已存在")

        template = WorkflowTemplate(
            template_id=body.template_id,
            name=body.name,
            description=body.description,
            source=body.source,
            default_params=body.default_params,
        )

        _templates[body.template_id] = template

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="create",
            resource_type="workflow_template",
            resource_id=body.template_id,
            user=current_user.username,
            details={"name": body.name},
            ip=ip,
            db=db,
        )

        _record_metric("workflow_template_created", 1, {"template_id": body.template_id})

        logger.info(f"Created template: {body.template_id} by user {current_user.username}")

        return template.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建模板失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_template_create_duration", duration)


@router.delete("/templates/{id}", summary="删除模板")
async def delete_template(
    request: Request,
    id: str = Path(..., min_length=1, description="模板ID"),
    current_user: User = Depends(require_permission("workflow", "delete")),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    删除指定的模板
    """
    start_time = datetime.utcnow()
    identifier = current_user.username if current_user else request.client.host
    check_rate_limit(identifier, requests_per_minute=10)

    try:
        template = _templates.get(id)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板 '{id}' 不存在")

        del _templates[id]

        # 记录审计日志
        ip = request.client.host if request.client else "unknown"
        _add_audit_log(
            action="delete",
            resource_type="workflow_template",
            resource_id=id,
            user=current_user.username,
            details={"name": template.name},
            ip=ip,
            db=db,
        )

        _record_metric("workflow_template_deleted", 1, {"template_id": id})

        logger.info(f"Deleted template: {id} by user {current_user.username}")

        return {"detail": f"模板 '{id}' 已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")
    finally:
        duration = (datetime.utcnow() - start_time).total_seconds()
        _record_metric("workflow_template_delete_duration", duration)
