# -*- coding: utf-8 -*-
"""
Chaos Engineering Advanced Router
混沌工程高级路由

提供完整的混沌工程实验管理API端点，包括实验、场景、故障注入等功能。
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.api_response_standard import (
    ErrorCode,
    create_error_response,
    create_success_response,
)
from core.auth_db import get_session
from core.chaos_engineering import (
    ChaosExperiment,
    ExperimentStatus,
    chaos_engine,
)
from core.models import (
    ChaosExperimentDB,
    ChaosScenarioDB,
    ChaosFaultDB,
)
from core.cache_manager import cache_manager, cache_key_generator
from core.models import (
    ChaosExperimentDB,
    ChaosScenarioDB,
    ChaosFaultDB,
)

router = APIRouter(prefix="/api/v1/chaos", tags=["混沌工程高级"])


# Pydantic Models
class ExperimentStatusEnum(str, Enum):
    """实验状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class SeverityEnum(str, Enum):
    """严重程度枚举"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FaultTypeEnum(str, Enum):
    """故障类型枚举"""

    NETWORK_LATENCY = "network_latency"
    DISK_FAILURE = "disk_failure"
    CPU_OVERLOAD = "cpu_overload"
    MEMORY_LEAK = "memory_leak"
    SERVICE_CRASH = "service_crash"
    DATABASE_ERROR = "database_error"
    CACHE_FAILURE = "cache_failure"
    NETWORK_PARTITION = "network_partition"


class CreateExperimentRequest(BaseModel):
    """创建实验请求"""

    name: str = Field(..., min_length=1, max_length=200, description="实验名称")
    description: Optional[str] = Field(None, max_length=1000, description="实验描述")
    experiment_type: str = Field(..., description="实验类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="实验参数")
    severity: SeverityEnum = Field(default=SeverityEnum.MEDIUM, description="严重程度")
    tags: List[str] = Field(default_factory=list, description="标签")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "API延迟注入测试",
                "description": "测试API服务在网络延迟下的表现",
                "experiment_type": "latency_injection",
                "parameters": {"delay_ms": 500, "target": "api-service"},
                "severity": "medium",
                "tags": ["network", "resilience"],
            }
        }
    }


class UpdateExperimentRequest(BaseModel):
    """更新实验请求"""

    name: Optional[str] = Field(None, max_length=200, description="实验名称")
    description: Optional[str] = Field(None, max_length=1000, description="实验描述")
    parameters: Optional[Dict[str, Any]] = Field(None, description="实验参数")
    severity: Optional[SeverityEnum] = Field(None, description="严重程度")
    tags: Optional[List[str]] = Field(None, description="标签")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "API延迟注入测试（更新）",
                "parameters": {"delay_ms": 1000, "target": "api-service"},
            }
        }
    }


class CreateScenarioRequest(BaseModel):
    """创建场景请求"""

    name: str = Field(..., min_length=1, max_length=200, description="场景名称")
    description: Optional[str] = Field(None, max_length=1000, description="场景描述")
    experiments: List[str] = Field(..., min_items=1, description="包含的实验ID列表")
    enabled: bool = Field(default=True, description="是否启用")
    schedule: Optional[str] = Field(None, description="调度配置（cron表达式）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "生产环境压力测试场景",
                "description": "模拟生产环境高负载情况",
                "experiments": ["exp-001", "exp-002"],
                "enabled": True,
                "schedule": "0 2 * * *",
            }
        }
    }


class CreateFaultRequest(BaseModel):
    """创建故障请求"""

    name: str = Field(..., min_length=1, max_length=200, description="故障名称")
    fault_type: FaultTypeEnum = Field(..., description="故障类型")
    description: Optional[str] = Field(None, max_length=1000, description="故障描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="故障参数")
    severity: SeverityEnum = Field(default=SeverityEnum.HIGH, description="严重程度")
    recovery_strategy: Optional[str] = Field(None, description="恢复策略")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "数据库连接超时",
                "fault_type": "database_error",
                "description": "模拟数据库连接超时",
                "parameters": {"timeout_ms": 30000},
                "severity": "high",
                "recovery_strategy": "retry_with_backoff",
            }
        }
    }


class SafetyCheckRequest(BaseModel):
    """安全检查请求"""

    experiment_id: str = Field(..., description="实验ID")
    check_type: str = Field(..., description="检查类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="检查参数")

    model_config = {
        "json_schema_extra": {
            "example": {
                "experiment_id": "exp-001",
                "check_type": "pre_execution",
                "parameters": {"check_dependencies": True, "check_resources": True},
            }
        }
    }



def _generate_id(prefix: str) -> str:
    """生成唯一ID"""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _now() -> str:
    """获取当前时间戳"""
    return datetime.now(timezone.utc).isoformat()

    try:
        db_fault = ChaosFaultDB(
            id=fault["id"],
            fault_type=fault["fault_type"],
            target=fault["target"],
            parameters=fault.get("parameters"),
            severity=fault.get("severity"),
            status=fault.get("status"),
            result=fault.get("result"),
            created_at=datetime.fromisoformat(fault["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(fault["updated_at"].replace("Z", "+00:00")),
        )
        db.merge(db_fault)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save fault to database: {str(e)}")


# Experiment endpoints
@router.get(
    "/experiments",
    summary="获取实验列表",
    responses={
        200: {"description": "实验列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_experiments(
    status: Optional[ExperimentStatusEnum] = Query(None, description="按状态筛选"),
    severity: Optional[SeverityEnum] = Query(None, description="按严重程度筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取混沌实验列表

    支持按状态和严重程度筛选，支持分页。
    """
    try:
        # 生成缓存键
        cache_key = cache_key_generator(
            "chaos_experiments_list",
            status.value if status else None,
            severity.value if severity else None,
            limit,
            offset
        )
        
        # 尝试从缓存获取
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            return create_success_response(cached_result)
        
        # 从数据库获取数据
        db = get_session()
        try:
            query = db.query(ChaosExperimentDB)
            
            # 过滤
            if status:
                query = query.filter(ChaosExperimentDB.status == status.value)
            if severity:
                query = query.filter(ChaosExperimentDB.severity == severity.value)
            
            # 分页
            total = query.count()
            results = query.offset(offset).limit(limit).all()
            
            # 转换为字典格式
            items = []
            for result in results:
                items.append({
                    "id": result.id,
                    "name": result.name,
                    "description": result.description,
                    "experiment_type": result.experiment_type,
                    "parameters": result.parameters,
                    "severity": result.severity,
                    "status": result.status,
                    "tags": result.tags,
                    "result": result.result,
                    "error": result.error,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                    "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                })
            
            response_data = {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
            
            # 设置缓存，TTL为5分钟
            cache_manager.set(cache_key, response_data, ttl=300)
            
            return create_success_response(response_data)
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取实验列表失败"
        )


@router.post(
    "/experiments",
    summary="创建实验",
    status_code=201,
    responses={
        201: {"description": "实验创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_experiment(request: CreateExperimentRequest) -> Dict[str, Any]:
    """
    创建新的混沌实验

    创建一个新的混沌实验配置，包含实验类型、参数、严重程度等信息。
    """
    try:
        # 验证实验类型
        try:
            ChaosExperiment(request.experiment_type)
        except ValueError:
            return create_error_response(
                error=f"Invalid experiment type: {request.experiment_type}",
                error_code=ErrorCode.VALIDATION_ERROR,
                message="无效的实验类型",
            )

        # 直接保存到数据库
        db = get_session()
        try:
            experiment = ChaosExperimentDB(
                id=_generate_id("EXP"),
                name=request.name,
                description=request.description,
                experiment_type=request.experiment_type,
                parameters=request.parameters,
                severity=request.severity.value,
                tags=request.tags,
                status=ExperimentStatusEnum.PENDING.value,
            )
            db.add(experiment)
            db.commit()
            
            response_data = {
                "id": experiment.id,
                "name": experiment.name,
                "description": experiment.description,
                "experiment_type": experiment.experiment_type,
                "parameters": experiment.parameters,
                "severity": experiment.severity,
                "tags": experiment.tags,
                "status": experiment.status,
                "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
                "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None,
            }
            
            # Invalidate cache
            cache_manager.delete_pattern("chaos_experiments_list:*")
            
            return create_success_response(response_data, "实验创建成功")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save experiment to database: {str(e)}")
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建实验失败"
        )


@router.get(
    "/experiments/{experiment_id}",
    summary="获取实验详情",
    responses={
        200: {"description": "实验详情"},
        404: {"description": "实验不存在"},
        500: {"description": "服务器错误"},
    },
)
async def get_experiment(experiment_id: str) -> Dict[str, Any]:
    """
    获取指定实验的详细信息

    根据实验ID获取实验的完整配置和运行历史。
    """
    try:
        db = get_session()
        try:
            experiment = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == experiment_id
            ).first()
            
            if not experiment:
                return create_error_response(
                    error=f"Experiment {experiment_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="实验不存在",
                )
            
            response_data = {
                "id": experiment.id,
                "name": experiment.name,
                "description": experiment.description,
                "experiment_type": experiment.experiment_type,
                "parameters": experiment.parameters,
                "severity": experiment.severity,
                "status": experiment.status,
                "tags": experiment.tags,
                "result": experiment.result,
                "error": experiment.error,
                "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
                "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None,
            }
            
            return create_success_response(response_data)
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取实验详情失败"
        )


@router.patch(
    "/experiments/{experiment_id}",
    summary="更新实验",
    responses={
        200: {"description": "实验更新成功"},
        404: {"description": "实验不存在"},
        500: {"description": "服务器错误"},
    },
)
async def update_experiment(experiment_id: str, request: UpdateExperimentRequest) -> Dict[str, Any]:
    """
    更新实验配置

    更新实验的名称、描述、参数、严重程度等信息。
    """
    try:
        db = get_session()
        try:
            experiment = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == experiment_id
            ).first()
            
            if not experiment:
                return create_error_response(
                    error=f"Experiment {experiment_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="实验不存在",
                )
            
            # 更新字段
            if request.name is not None:
                experiment.name = request.name
            if request.description is not None:
                experiment.description = request.description
            if request.parameters is not None:
                experiment.parameters = request.parameters
            if request.severity is not None:
                experiment.severity = request.severity.value
            if request.tags is not None:
                experiment.tags = request.tags
            
            experiment.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            # Invalidate cache
            cache_manager.delete_pattern("chaos_experiments_list:*")
            
            response_data = {
                "id": experiment.id,
                "name": experiment.name,
                "description": experiment.description,
                "experiment_type": experiment.experiment_type,
                "parameters": experiment.parameters,
                "severity": experiment.severity,
                "tags": experiment.tags,
                "status": experiment.status,
                "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None,
            }
            
            return create_success_response(response_data, "实验更新成功")
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="更新实验失败"
        )


@router.delete(
    "/experiments/{experiment_id}",
    summary="删除实验",
    responses={
        200: {"description": "实验删除成功"},
        404: {"description": "实验不存在"},
        500: {"description": "服务器错误"},
    },
)
async def delete_experiment(experiment_id: str) -> Dict[str, Any]:
    """
    删除实验

    根据实验ID删除实验配置。
    """
    try:
        db = get_session()
        try:
            experiment = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == experiment_id
            ).first()
            
            if not experiment:
                return create_error_response(
                    error=f"Experiment {experiment_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="实验不存在",
                )
            
            db.delete(experiment)
            db.commit()
            
            # Invalidate cache
            cache_manager.delete_pattern("chaos_experiments_list:*")
            
            return create_success_response({"id": experiment_id}, "实验删除成功")
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="删除实验失败"
        )


@router.post(
    "/experiments/{experiment_id}/run",
    summary="运行实验",
    responses={
        200: {"description": "实验运行成功"},
        404: {"description": "实验不存在"},
        500: {"description": "服务器错误"},
    },
)
async def run_experiment(experiment_id: str) -> Dict[str, Any]:
    """
    运行指定的混沌实验

    执行实验并返回运行结果。
    """
    try:
        db = get_session()
        try:
            experiment = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == experiment_id
            ).first()
            
            if not experiment:
                return create_error_response(
                    error=f"Experiment {experiment_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="实验不存在",
                )
            
            # 更新状态为运行中
            experiment.status = ExperimentStatusEnum.RUNNING.value
            experiment.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            # Invalidate cache
            cache_manager.delete_pattern("chaos_experiments_list:*")
            
            response_data = {
                "id": experiment.id,
                "status": experiment.status,
                "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None,
            }
            
            return create_success_response(response_data, "实验开始运行")
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="运行实验失败"
        )


@router.post(
    "/experiments/{experiment_id}/stop",
    summary="停止实验",
    responses={
        200: {"description": "实验停止成功"},
        404: {"description": "实验不存在"},
        500: {"description": "服务器错误"},
    },
)
async def stop_experiment(experiment_id: str) -> Dict[str, Any]:
    """
    停止正在运行的实验

    中止当前正在执行的混沌实验。
    """
    try:
        db = get_session()
        try:
            experiment = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == experiment_id
            ).first()
            
            if not experiment:
                return create_error_response(
                    error=f"Experiment {experiment_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="实验不存在",
                )
            
            # 更新状态为已停止
            experiment.status = ExperimentStatusEnum.ABORTED.value
            experiment.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            # Invalidate cache
            cache_manager.delete_pattern("chaos_experiments_list:*")
            
            response_data = {
                "id": experiment.id,
                "status": experiment.status,
                "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None,
            }
            
            return create_success_response(response_data, "实验已停止")
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="停止实验失败"
        )


# Scenario endpoints
@router.get(
    "/scenarios",
    summary="获取场景列表",
    responses={
        200: {"description": "场景列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_scenarios(
    enabled: Optional[bool] = Query(None, description="按启用状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
) -> Dict[str, Any]:
    """
    获取混沌场景列表

    场景是多个实验的组合，可以批量执行。
    """
    try:
        db = get_session()
        try:
            query = db.query(ChaosScenarioDB)
            
            if enabled is not None:
                query = query.filter(ChaosScenarioDB.enabled == enabled)
            
            total = query.count()
            scenarios = query.limit(limit).all()
            
            items = []
            for scenario in scenarios:
                items.append({
                    "id": scenario.id,
                    "name": scenario.name,
                    "description": scenario.description,
                    "experiments": scenario.experiments,
                    "enabled": scenario.enabled,
                    "schedule": scenario.schedule,
                    "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
                    "updated_at": scenario.updated_at.isoformat() if scenario.updated_at else None,
                })
            
            return create_success_response({
                "items": items,
                "total": total,
                "limit": limit,
            })
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取场景列表失败"
        )


@router.post(
    "/scenarios",
    summary="创建场景",
    status_code=201,
    responses={
        201: {"description": "场景创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_scenario(request: CreateScenarioRequest) -> Dict[str, Any]:
    """
    创建新的混沌场景

    场景可以包含多个实验，支持批量执行和调度。
    """
    try:
        db = get_session()
        try:
            # 验证实验ID是否存在
            experiment_ids = {e.id for e in db.query(ChaosExperimentDB.id).all()}
            for exp_id in request.experiments:
                if exp_id not in experiment_ids:
                    return create_error_response(
                        error=f"Experiment {exp_id} not found",
                        error_code=ErrorCode.RESOURCE_NOT_FOUND,
                        message=f"实验 {exp_id} 不存在",
                    )
            
            scenario = ChaosScenarioDB(
                id=_generate_id("SCN"),
                name=request.name,
                description=request.description,
                experiments=request.experiments,
                enabled=request.enabled,
                schedule=request.schedule,
            )
            db.add(scenario)
            db.commit()
            
            response_data = {
                "id": scenario.id,
                "name": scenario.name,
                "description": scenario.description,
                "experiments": scenario.experiments,
                "enabled": scenario.enabled,
                "schedule": scenario.schedule,
                "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
                "updated_at": scenario.updated_at.isoformat() if scenario.updated_at else None,
            }
            
            return create_success_response(response_data, "场景创建成功")
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建场景失败"
        )


# Fault endpoints
@router.get(
    "/faults",
    summary="获取故障列表",
    responses={
        200: {"description": "故障列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_faults(
    fault_type: Optional[FaultTypeEnum] = Query(None, description="按故障类型筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
) -> Dict[str, Any]:
    """
    获取故障注入列表

    故障注入是混沌工程的核心功能，用于模拟各种系统故障。
    """
    try:
        db = get_session()
        try:
            query = db.query(ChaosFaultDB)
            
            if fault_type:
                query = query.filter(ChaosFaultDB.fault_type == fault_type.value)
            
            total = query.count()
            faults = query.limit(limit).all()
            
            items = []
            for fault in faults:
                items.append({
                    "id": fault.id,
                    "name": fault.name,
                    "description": fault.description,
                    "fault_type": fault.fault_type,
                    "target": fault.target,
                    "parameters": fault.parameters,
                    "severity": fault.severity,
                    "status": fault.status,
                    "result": fault.result,
                    "created_at": fault.created_at.isoformat() if fault.created_at else None,
                    "updated_at": fault.updated_at.isoformat() if fault.updated_at else None,
                })
            
            return create_success_response({
                "items": items,
                "total": total,
                "limit": limit,
            })
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取故障列表失败"
        )


@router.post(
    "/faults",
    summary="创建故障",
    status_code=201,
    responses={
        201: {"description": "故障创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_fault(request: CreateFaultRequest) -> Dict[str, Any]:
    """
    创建新的故障注入配置

    定义故障类型、参数、严重程度和恢复策略。
    """
    try:
        db = get_session()
        try:
            fault = ChaosFaultDB(
                id=_generate_id("FLT"),
                name=request.name,
                fault_type=request.fault_type.value,
                description=request.description,
                parameters=request.parameters,
                target=request.parameters.get("target", "unknown"),
                severity=request.severity.value,
                recovery_strategy=request.recovery_strategy,
            )
            db.add(fault)
            db.commit()
            
            response_data = {
                "id": fault.id,
                "name": fault.name,
                "description": fault.description,
                "fault_type": fault.fault_type,
                "target": fault.target,
                "parameters": fault.parameters,
                "severity": fault.severity,
                "recovery_strategy": fault.recovery_strategy,
                "status": fault.status,
                "created_at": fault.created_at.isoformat() if fault.created_at else None,
                "updated_at": fault.updated_at.isoformat() if fault.updated_at else None,
            }
            
            return create_success_response(response_data, "故障创建成功")
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建故障失败"
        )


# Metrics endpoint
@router.get(
    "/metrics",
    summary="获取混沌工程指标",
    responses={
        200: {"description": "混沌工程指标"},
        500: {"description": "服务器错误"},
    },
)
async def get_chaos_metrics() -> Dict[str, Any]:
    """
    获取混沌工程的整体指标

    包括实验总数、成功率、平均执行时间等统计信息。
    """
    try:
        db = get_session()
        # 统计实验数据
        total_experiments = db.query(ChaosExperimentDB).count()
        running_experiments = db.query(ChaosExperimentDB).filter(
            ChaosExperimentDB.status == "running"
        ).count()
        completed_experiments = db.query(ChaosExperimentDB).filter(
            ChaosExperimentDB.status == "completed"
        ).count()
        failed_experiments = db.query(ChaosExperimentDB).filter(
            ChaosExperimentDB.status == "failed"
        ).count()
        
        # 统计场景数据
        total_scenarios = db.query(ChaosScenarioDB).count()
        enabled_scenarios = db.query(ChaosScenarioDB).filter(
            ChaosScenarioDB.enabled == True
        ).count()
        
        # 统计故障数据
        total_faults = db.query(ChaosFaultDB).count()
        
        # 计算成功率
        success_count = db.query(ChaosExperimentDB).filter(
            ChaosExperimentDB.status == "completed"
        ).count()
        success_rate = (
            (success_count / completed_experiments * 100) if completed_experiments > 0 else 0
        )
        
        # 获取引擎统计
        engine_stats = chaos_engine.get_experiment_stats()
        
        metrics = {
        "experiments": {
            "total": total_experiments,
            "running": running_experiments,
            "completed": completed_experiments,
            "failed": failed_experiments,
            "success_rate": round(success_rate, 2),
        },
        "scenarios": {
            "total": total_scenarios,
            "enabled": enabled_scenarios,
        },
        "faults": {
            "total": total_faults,
            "by_type": {},
        },
        "engine": engine_stats,
    }

        # 按类型统计故障
        fault_types = db.query(ChaosFaultDB.fault_type).all()
        for fault_type in fault_types:
            type_name = fault_type[0]
            count = db.query(ChaosFaultDB).filter(
                ChaosFaultDB.fault_type == type_name
            ).count()
            metrics["faults"]["by_type"][type_name] = count

        return create_success_response(metrics)
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取指标失败"
        )
    finally:
        db.close()


# Safety check endpoint
@router.post(
    "/safety-checks",
    summary="执行安全检查",
    responses={
        200: {"description": "安全检查结果"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def perform_safety_check(request: SafetyCheckRequest) -> Dict[str, Any]:
    """
    执行实验前的安全检查

    检查系统状态、资源可用性、依赖关系等，确保实验安全执行。
    """
    try:
        db = get_session()
        try:
            experiment = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == request.experiment_id
            ).first()
            
            if not experiment:
                return create_error_response(
                    error=f"Experiment {request.experiment_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="实验不存在",
                )
            
            # 执行安全检查
            check_result = chaos_engine.perform_safety_check(
                experiment_id=request.experiment_id,
                check_type=request.check_type,
                parameters=request.parameters,
            )
            
            return create_success_response(check_result, "安全检查完成")
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="安全检查失败"
        )

        # 检查是否有正在运行的实验
        history = chaos_engine.get_experiment_history()
        has_running = any(exp.status == ExperimentStatus.RUNNING for exp in history)
        checks["checks"].append(
            {
                "name": "no_running_experiments",
                "status": "pass" if not has_running else "warning",
                "message": (
                    "No running experiments" if not has_running else "Another experiment is running"
                ),
            }
        )

        # 检查依赖关系
        if request.parameters.get("check_dependencies", False):
            checks["checks"].append(
                {
                    "name": "dependencies_check",
                    "status": "pass",
                    "message": "Dependencies verified",
                }
            )

        # 检查资源
        if request.parameters.get("check_resources", False):
            checks["checks"].append(
                {
                    "name": "resources_check",
                    "status": "pass",
                    "message": "Resources available",
                }
            )

        # 计算总体状态
        failed_checks = [c for c in checks["checks"] if c["status"] == "fail"]
        overall_status = "pass" if not failed_checks else "fail"

        checks["overall_status"] = overall_status
        checks["can_proceed"] = overall_status == "pass"

        return create_success_response(checks, "安全检查完成")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="安全检查失败"
        )
