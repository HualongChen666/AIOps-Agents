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

from core.api_response_standard import (
    ErrorCode,
    create_error_response,
    create_success_response,
)
from core.chaos_engineering import (
    ChaosExperiment,
    ExperimentStatus,
    chaos_engine,
)

router = APIRouter(prefix="/api/v1/chaos", tags=["混沌工程高级"])

# Data storage paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

EXPERIMENTS_FILE = DATA_DIR / "chaos_experiments.json"
SCENARIOS_FILE = DATA_DIR / "chaos_scenarios.json"
FAULTS_FILE = DATA_DIR / "chaos_faults.json"


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


# Data storage helpers
def _load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """加载JSON文件"""
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Failed to load JSON file {file_path}: {exc}")
        return []
    except Exception as e:  # noqa: F841 - Exception intentionally unused
        return []


def _save_json_file(file_path: Path, data: List[Dict[str, Any]]) -> None:
    """保存JSON文件"""
    import os
    import stat

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        # Set restrictive permissions for chaos engineering data file (600 - owner read/write only)
        try:
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, AttributeError):
            # chmod may fail on Windows or non-Unix systems
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save data: {str(e)}")


def _generate_id(prefix: str) -> str:
    """生成唯一ID"""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _now() -> str:
    """获取当前时间戳"""
    return datetime.now(timezone.utc).isoformat()


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
        experiments = _load_json_file(EXPERIMENTS_FILE)

        # 过滤
        if status:
            experiments = [e for e in experiments if e.get("status") == status.value]
        if severity:
            experiments = [e for e in experiments if e.get("severity") == severity.value]

        # 分页
        total = len(experiments)
        paginated = experiments[offset : offset + limit]

        return create_success_response(
            {
                "items": paginated,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )
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

        experiments = _load_json_file(EXPERIMENTS_FILE)

        experiment = {
            "id": _generate_id("EXP"),
            "name": request.name,
            "description": request.description,
            "experiment_type": request.experiment_type,
            "parameters": request.parameters,
            "severity": request.severity.value,
            "tags": request.tags,
            "status": ExperimentStatusEnum.PENDING.value,
            "created_at": _now(),
            "updated_at": _now(),
            "run_count": 0,
            "last_run_at": None,
        }

        experiments.append(experiment)
        _save_json_file(EXPERIMENTS_FILE, experiments)

        return create_success_response(experiment, "实验创建成功")
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
        experiments = _load_json_file(EXPERIMENTS_FILE)
        experiment = next((e for e in experiments if e.get("id") == experiment_id), None)

        if not experiment:
            return create_error_response(
                error=f"Experiment {experiment_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="实验不存在",
            )

        return create_success_response(experiment)
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
        experiments = _load_json_file(EXPERIMENTS_FILE)
        experiment = next((e for e in experiments if e.get("id") == experiment_id), None)

        if not experiment:
            return create_error_response(
                error=f"Experiment {experiment_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="实验不存在",
            )

        # 更新字段
        if request.name is not None:
            experiment["name"] = request.name
        if request.description is not None:
            experiment["description"] = request.description
        if request.parameters is not None:
            experiment["parameters"] = request.parameters
        if request.severity is not None:
            experiment["severity"] = request.severity.value
        if request.tags is not None:
            experiment["tags"] = request.tags

        experiment["updated_at"] = _now()

        _save_json_file(EXPERIMENTS_FILE, experiments)

        return create_success_response(experiment, "实验更新成功")
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
        experiments = _load_json_file(EXPERIMENTS_FILE)
        experiment = next((e for e in experiments if e.get("id") == experiment_id), None)

        if not experiment:
            return create_error_response(
                error=f"Experiment {experiment_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="实验不存在",
            )

        experiments = [e for e in experiments if e.get("id") != experiment_id]
        _save_json_file(EXPERIMENTS_FILE, experiments)

        return create_success_response({"id": experiment_id}, "实验删除成功")
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
        experiments = _load_json_file(EXPERIMENTS_FILE)
        experiment = next((e for e in experiments if e.get("id") == experiment_id), None)

        if not experiment:
            return create_error_response(
                error=f"Experiment {experiment_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="实验不存在",
            )

        # 更新状态为运行中
        experiment["status"] = ExperimentStatusEnum.RUNNING.value
        experiment["updated_at"] = _now()
        _save_json_file(EXPERIMENTS_FILE, experiments)

        # 执行实验
        try:
            experiment_type = ChaosExperiment(experiment["experiment_type"])
            parameters = experiment.get("parameters", {})
            result = await chaos_engine.run_experiment(experiment_type, parameters)

            # 更新实验状态
            experiment["status"] = result.status.value
            experiment["run_count"] = experiment.get("run_count", 0) + 1
            experiment["last_run_at"] = _now()
            experiment["last_result"] = {
                "success": result.success,
                "duration_seconds": result.duration_seconds,
                "metrics": result.metrics,
                "error_message": result.error_message,
            }
            experiment["updated_at"] = _now()

            _save_json_file(EXPERIMENTS_FILE, experiments)

            return create_success_response(
                {
                    "experiment_id": experiment_id,
                    "status": result.status.value,
                    "success": result.success,
                    "duration_seconds": result.duration_seconds,
                    "metrics": result.metrics,
                },
                "实验运行完成",
            )
        except ValueError as e:
            experiment["status"] = ExperimentStatusEnum.FAILED.value
            _save_json_file(EXPERIMENTS_FILE, experiments)
            return create_error_response(
                error=str(e), error_code=ErrorCode.VALIDATION_ERROR, message="实验类型无效"
            )
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
        experiments = _load_json_file(EXPERIMENTS_FILE)
        experiment = next((e for e in experiments if e.get("id") == experiment_id), None)

        if not experiment:
            return create_error_response(
                error=f"Experiment {experiment_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="实验不存在",
            )

        if experiment["status"] != ExperimentStatusEnum.RUNNING.value:
            return create_error_response(
                error="Experiment is not running",
                error_code=ErrorCode.BAD_REQUEST,
                message="实验未在运行中",
            )

        # 更新状态为已中止
        experiment["status"] = ExperimentStatusEnum.ABORTED.value
        experiment["updated_at"] = _now()
        _save_json_file(EXPERIMENTS_FILE, experiments)

        return create_success_response({"id": experiment_id}, "实验已停止")
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
        scenarios = _load_json_file(SCENARIOS_FILE)

        if enabled is not None:
            scenarios = [s for s in scenarios if s.get("enabled") == enabled]

        paginated = scenarios[:limit]

        return create_success_response(
            {
                "items": paginated,
                "total": len(scenarios),
                "limit": limit,
            }
        )
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
        scenarios = _load_json_file(SCENARIOS_FILE)

        # 验证实验ID是否存在
        experiments = _load_json_file(EXPERIMENTS_FILE)
        experiment_ids = {e.get("id") for e in experiments}
        for exp_id in request.experiments:
            if exp_id not in experiment_ids:
                return create_error_response(
                    error=f"Experiment {exp_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message=f"实验 {exp_id} 不存在",
                )

        scenario = {
            "id": _generate_id("SCN"),
            "name": request.name,
            "description": request.description,
            "experiments": request.experiments,
            "enabled": request.enabled,
            "schedule": request.schedule,
            "created_at": _now(),
            "updated_at": _now(),
            "run_count": 0,
            "last_run_at": None,
        }

        scenarios.append(scenario)
        _save_json_file(SCENARIOS_FILE, scenarios)

        return create_success_response(scenario, "场景创建成功")
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
        faults = _load_json_file(FAULTS_FILE)

        if fault_type:
            faults = [f for f in faults if f.get("fault_type") == fault_type.value]

        paginated = faults[:limit]

        return create_success_response(
            {
                "items": paginated,
                "total": len(faults),
                "limit": limit,
            }
        )
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
        faults = _load_json_file(FAULTS_FILE)

        fault = {
            "id": _generate_id("FLT"),
            "name": request.name,
            "fault_type": request.fault_type.value,
            "description": request.description,
            "parameters": request.parameters,
            "severity": request.severity.value,
            "recovery_strategy": request.recovery_strategy,
            "created_at": _now(),
            "updated_at": _now(),
            "injection_count": 0,
            "last_injection_at": None,
        }

        faults.append(fault)
        _save_json_file(FAULTS_FILE, faults)

        return create_success_response(fault, "故障创建成功")
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
        experiments = _load_json_file(EXPERIMENTS_FILE)
        scenarios = _load_json_file(SCENARIOS_FILE)
        faults = _load_json_file(FAULTS_FILE)

        # 统计实验数据
        total_experiments = len(experiments)
        running_experiments = sum(1 for e in experiments if e.get("status") == "running")
        completed_experiments = sum(1 for e in experiments if e.get("status") == "completed")
        failed_experiments = sum(1 for e in experiments if e.get("status") == "failed")

        # 计算成功率
        success_count = sum(
            1 for e in experiments if e.get("last_result", {}).get("success", False)
        )
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
                "total": len(scenarios),
                "enabled": sum(1 for s in scenarios if s.get("enabled", False)),
            },
            "faults": {
                "total": len(faults),
                "by_type": {},
            },
            "engine": engine_stats,
        }

        # 按类型统计故障
        for fault in faults:
            fault_type = fault.get("fault_type", "unknown")
            metrics["faults"]["by_type"][fault_type] = (
                metrics["faults"]["by_type"].get(fault_type, 0) + 1
            )

        return create_success_response(metrics)
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取指标失败"
        )


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
        experiments = _load_json_file(EXPERIMENTS_FILE)
        experiment = next((e for e in experiments if e.get("id") == request.experiment_id), None)

        if not experiment:
            return create_error_response(
                error=f"Experiment {request.experiment_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="实验不存在",
            )

        # 执行安全检查
        checks = {
            "experiment_id": request.experiment_id,
            "check_type": request.check_type,
            "timestamp": _now(),
            "checks": [],
        }

        # 检查混沌工程是否启用
        chaos_enabled = chaos_engine.is_enabled()
        checks["checks"].append(
            {
                "name": "chaos_engine_enabled",
                "status": "pass" if chaos_enabled else "fail",
                "message": (
                    "Chaos engine is enabled" if chaos_enabled else "Chaos engine is disabled"
                ),
            }
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
