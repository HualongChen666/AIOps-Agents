# -*- coding: utf-8 -*-
"""
Business Impact Advanced Router
业务影响高级路由

提供完整的业务影响分析API端点，包括分析、指标、依赖关系、报告等功能。
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
from core.business_impact_engine import (
    assess_business_impact,
    list_business_impact_services,
    list_business_impact_ux_metrics,
)
from core.models import (
    BusinessImpactAnalysisDB,
    BusinessImpactDependencyDB,
    BusinessImpactReportDB,
)
from core.cache_manager import cache_manager, cache_key_generator

router = APIRouter(prefix="/api/v1/business-impact", tags=["业务影响高级"])

# Data storage paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ANALYSIS_FILE = DATA_DIR / "business_impact_analysis.json"
DEPENDENCIES_FILE = DATA_DIR / "business_impact_dependencies.json"
REPORTS_FILE = DATA_DIR / "business_impact_reports.json"


# Pydantic Models
class ImpactSeverityEnum(str, Enum):
    """影响严重程度枚举"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisStatusEnum(str, Enum):
    """分析状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CreateAnalysisRequest(BaseModel):
    """创建分析请求"""

    service_name: str = Field(..., min_length=1, max_length=200, description="服务名称")
    analysis_type: str = Field(default="full", description="分析类型")
    time_range: str = Field(default="1h", description="时间范围")
    include_dependencies: bool = Field(default=True, description="是否包含依赖分析")
    include_ux_metrics: bool = Field(default=True, description="是否包含用户体验指标")

    model_config = {
        "json_schema_extra": {
            "example": {
                "service_name": "payment-service",
                "analysis_type": "full",
                "time_range": "1h",
                "include_dependencies": True,
                "include_ux_metrics": True,
            }
        }
    }


class UpdateAnalysisRequest(BaseModel):
    """更新分析请求"""

    status: Optional[AnalysisStatusEnum] = Field(None, description="分析状态")
    result: Optional[Dict[str, Any]] = Field(None, description="分析结果")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "completed",
                "result": {"impact_score": 8.5, "affected_users": 1000},
            }
        }
    }


class CreateDependencyRequest(BaseModel):
    """创建依赖关系请求"""

    source_service: str = Field(..., min_length=1, max_length=200, description="源服务")
    target_service: str = Field(..., min_length=1, max_length=200, description="目标服务")
    dependency_type: str = Field(default="api_call", description="依赖类型")
    criticality: ImpactSeverityEnum = Field(
        default=ImpactSeverityEnum.MEDIUM, description="关键程度"
    )
    description: Optional[str] = Field(None, max_length=500, description="描述")

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_service": "api-service",
                "target_service": "database-service",
                "dependency_type": "api_call",
                "criticality": "high",
                "description": "API服务依赖数据库服务",
            }
        }
    }


class CreateReportRequest(BaseModel):
    """创建报告请求"""

    title: str = Field(..., min_length=1, max_length=200, description="报告标题")
    service_names: List[str] = Field(..., min_items=1, description="服务名称列表")
    time_range: str = Field(default="24h", description="时间范围")
    include_recommendations: bool = Field(default=True, description="是否包含建议")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "周度业务影响报告",
                "service_names": ["payment-service", "api-service"],
                "time_range": "24h",
                "include_recommendations": True,
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
    except Exception as e:  # noqa: F841 - Exception intentionally unused
        return []


def _save_json_file(file_path: Path, data: List[Dict[str, Any]]) -> None:
    """保存JSON文件"""
    import os
    import stat

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        # Set restrictive permissions for business impact data file (600 - owner read/write only)
        try:
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, AttributeError):
            # chmod may fail on Windows or non-Unix systems
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save data: {str(e)}")


# Dual-write functions for database migration
def _save_analysis_to_db(db: Session, analysis: Dict[str, Any]) -> None:
    """保存分析到数据库"""
    try:
        db_analysis = BusinessImpactAnalysisDB(
            id=analysis["id"],
            service_name=analysis["service_name"],
            analysis_type=analysis["analysis_type"],
            time_range=analysis["time_range"],
            include_dependencies=analysis["include_dependencies"],
            include_ux_metrics=analysis["include_ux_metrics"],
            status=analysis["status"],
            result=analysis.get("result"),
            error=analysis.get("error"),
            created_at=datetime.fromisoformat(analysis["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(analysis["updated_at"].replace("Z", "+00:00")),
        )
        db.merge(db_analysis)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save analysis to database: {str(e)}")


def _save_dependency_to_db(db: Session, dependency: Dict[str, Any]) -> None:
    """保存依赖关系到数据库"""
    try:
        db_dependency = BusinessImpactDependencyDB(
            id=dependency["id"],
            source_service=dependency["source_service"],
            target_service=dependency["target_service"],
            dependency_type=dependency["dependency_type"],
            criticality=dependency["criticality"],
            description=dependency.get("description"),
            created_at=datetime.fromisoformat(dependency["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(dependency["updated_at"].replace("Z", "+00:00")),
        )
        db.merge(db_dependency)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save dependency to database: {str(e)}")


def _save_report_to_db(db: Session, report: Dict[str, Any]) -> None:
    """保存报告到数据库"""
    try:
        db_report = BusinessImpactReportDB(
            id=report["id"],
            title=report["title"],
            service_names=report["service_names"],
            time_range=report["time_range"],
            include_recommendations=report["include_recommendations"],
            summary=report.get("summary"),
            service_data=report.get("service_data"),
            recommendations=report.get("recommendations"),
            created_at=datetime.fromisoformat(report["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(report["updated_at"].replace("Z", "+00:00")),
        )
        db.merge(db_report)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save report to database: {str(e)}")


def _generate_id(prefix: str) -> str:
    """生成唯一ID"""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _now() -> str:
    """获取当前时间戳"""
    return datetime.now(timezone.utc).isoformat()


# Analysis endpoints
@router.get(
    "/analysis",
    summary="获取分析列表",
    responses={
        200: {"description": "分析列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_analysis_list(
    service_name: Optional[str] = Query(None, description="按服务名称筛选"),
    status: Optional[AnalysisStatusEnum] = Query(None, description="按状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取业务影响分析列表

    支持按服务名称和状态筛选，支持分页。
    """
    try:
        # 生成缓存键
        cache_key = cache_key_generator(
            "business_impact_analysis_list",
            service_name,
            status.value if status else None,
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
            query = db.query(BusinessImpactAnalysisDB)
            
            # 过滤
            if service_name:
                query = query.filter(BusinessImpactAnalysisDB.service_name == service_name)
            if status:
                query = query.filter(BusinessImpactAnalysisDB.status == status.value)
            
            # 分页
            total = query.count()
            results = query.offset(offset).limit(limit).all()
            
            # 转换为字典格式
            items = []
            for result in results:
                items.append({
                    "id": result.id,
                    "service_name": result.service_name,
                    "analysis_type": result.analysis_type,
                    "time_range": result.time_range,
                    "include_dependencies": result.include_dependencies,
                    "include_ux_metrics": result.include_ux_metrics,
                    "status": result.status,
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
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取分析列表失败"
        )


@router.post(
    "/analysis",
    summary="创建分析",
    status_code=201,
    responses={
        201: {"description": "分析创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_analysis(request: CreateAnalysisRequest) -> Dict[str, Any]:
    """
    创建新的业务影响分析

    对指定服务进行业务影响分析，包括依赖关系、用户体验指标等。
    """
    try:
        analyses = _load_json_file(ANALYSIS_FILE)

        analysis = {
            "id": _generate_id("BIA"),
            "service_name": request.service_name,
            "analysis_type": request.analysis_type,
            "time_range": request.time_range,
            "include_dependencies": request.include_dependencies,
            "include_ux_metrics": request.include_ux_metrics,
            "status": AnalysisStatusEnum.RUNNING.value,
            "created_at": _now(),
            "updated_at": _now(),
            "result": None,
        }

        analyses.append(analysis)
        _save_json_file(ANALYSIS_FILE, analyses)

        # Dual-write to database
        db = get_session()
        try:
            _save_analysis_to_db(db, analysis)
        except Exception as e:
            # Log database error but continue with JSON storage
            pass
        finally:
            db.close()

        # Invalidate cache for analysis list
        cache_manager.delete_pattern("business_impact_analysis_list:*")

        # 异步执行分析
        try:
            # 获取业务影响评估
            impact_assessment = await assess_business_impact(request.service_name)

            # 如果需要，获取依赖关系
            dependencies = []
            if request.include_dependencies:
                deps = _load_json_file(DEPENDENCIES_FILE)
                dependencies = [
                    d
                    for d in deps
                    if d.get("source_service") == request.service_name
                    or d.get("target_service") == request.service_name
                ]

            # 如果需要，获取UX指标
            ux_metrics = []
            if request.include_ux_metrics:
                ux_metrics = await list_business_impact_ux_metrics()

            # 更新分析结果
            analysis["status"] = AnalysisStatusEnum.COMPLETED.value
            analysis["result"] = {
                "impact_assessment": impact_assessment,
                "dependencies": dependencies,
                "ux_metrics": ux_metrics,
            }
            analysis["updated_at"] = _now()

            _save_json_file(ANALYSIS_FILE, analyses)

            # Dual-write to database
            db = get_session()
            try:
                _save_analysis_to_db(db, analysis)
            except Exception as e:
                # Log database error but continue with JSON storage
                pass
            finally:
                db.close()

            # Invalidate cache for analysis list
            cache_manager.delete_pattern("business_impact_analysis_list:*")

            return create_success_response(analysis, "分析创建成功")
        except Exception as e:
            analysis["status"] = AnalysisStatusEnum.FAILED.value
            analysis["error"] = str(e)
            analysis["updated_at"] = _now()
            _save_json_file(ANALYSIS_FILE, analyses)

            # Dual-write to database
            db = get_session()
            try:
                _save_analysis_to_db(db, analysis)
            except Exception as e:
                # Log database error but continue with JSON storage
                pass
            finally:
                db.close()

            # Invalidate cache for analysis list
            cache_manager.delete_pattern("business_impact_analysis_list:*")

            return create_error_response(
                error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="分析执行失败"
            )
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建分析失败"
        )


# Metrics endpoint
@router.get(
    "/metrics",
    summary="获取业务影响指标",
    responses={
        200: {"description": "业务影响指标"},
        500: {"description": "服务器错误"},
    },
)
async def get_business_impact_metrics(
    service_name: Optional[str] = Query(None, description="服务名称"),
    time_range: str = Query("1h", description="时间范围"),
) -> Dict[str, Any]:
    """
    获取业务影响指标

    返回指定服务或整体系统的业务影响指标。
    """
    try:
        # 获取服务列表
        services = await list_business_impact_services()

        # 如果指定了服务名称，筛选该服务
        if service_name:
            services = [s for s in services if s.get("name") == service_name]
            if not services:
                return create_error_response(
                    error=f"Service {service_name} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="服务不存在",
                )

        # 获取UX指标
        ux_metrics = await list_business_impact_ux_metrics()

        # 计算聚合指标
        total_services = len(services)
        down_services = sum(1 for s in services if s.get("status") == "down")
        degraded_services = sum(1 for s in services if s.get("status") == "degraded")
        healthy_services = sum(1 for s in services if s.get("status") == "healthy")

        total_revenue_impact = sum(s.get("revenueImpact", 0) for s in services)
        total_affected_users = sum(s.get("affectedUsers", 0) for s in services)

        avg_impact_score = (
            sum(s.get("impactScore", 0) for s in services) / total_services
            if total_services > 0
            else 0
        )

        metrics = {
            "summary": {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "degraded_services": degraded_services,
                "down_services": down_services,
                "total_revenue_impact": total_revenue_impact,
                "total_affected_users": total_affected_users,
                "avg_impact_score": round(avg_impact_score, 2),
            },
            "services": services,
            "ux_metrics": ux_metrics,
            "time_range": time_range,
            "timestamp": _now(),
        }

        return create_success_response(metrics)
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取指标失败"
        )


# Dependencies endpoints
@router.get(
    "/dependencies",
    summary="获取依赖关系列表",
    responses={
        200: {"description": "依赖关系列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_dependencies(
    source_service: Optional[str] = Query(None, description="源服务名称"),
    target_service: Optional[str] = Query(None, description="目标服务名称"),
    criticality: Optional[ImpactSeverityEnum] = Query(None, description="关键程度"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
) -> Dict[str, Any]:
    """
    获取服务依赖关系列表

    支持按源服务、目标服务和关键程度筛选。
    """
    try:
        dependencies = _load_json_file(DEPENDENCIES_FILE)

        # 过滤
        if source_service:
            dependencies = [d for d in dependencies if d.get("source_service") == source_service]
        if target_service:
            dependencies = [d for d in dependencies if d.get("target_service") == target_service]
        if criticality:
            dependencies = [d for d in dependencies if d.get("criticality") == criticality.value]

        paginated = dependencies[:limit]

        return create_success_response(
            {
                "items": paginated,
                "total": len(dependencies),
                "limit": limit,
            }
        )
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取依赖关系失败"
        )


@router.post(
    "/dependencies",
    summary="创建依赖关系",
    status_code=201,
    responses={
        201: {"description": "依赖关系创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_dependency(request: CreateDependencyRequest) -> Dict[str, Any]:
    """
    创建新的服务依赖关系

    定义服务之间的依赖关系和关键程度。
    """
    try:
        dependencies = _load_json_file(DEPENDENCIES_FILE)

        # 检查是否已存在
        for dep in dependencies:
            if (
                dep.get("source_service") == request.source_service
                and dep.get("target_service") == request.target_service
            ):
                return create_error_response(
                    error="Dependency already exists",
                    error_code=ErrorCode.BAD_REQUEST,
                    message="依赖关系已存在",
                )

        dependency = {
            "id": _generate_id("DEP"),
            "source_service": request.source_service,
            "target_service": request.target_service,
            "dependency_type": request.dependency_type,
            "criticality": request.criticality.value,
            "description": request.description,
            "created_at": _now(),
            "updated_at": _now(),
        }

        dependencies.append(dependency)
        _save_json_file(DEPENDENCIES_FILE, dependencies)

        # Dual-write to database
        db = get_session()
        try:
            _save_dependency_to_db(db, dependency)
        except Exception as e:
            # Log database error but continue with JSON storage
            pass
        finally:
            db.close()

        return create_success_response(dependency, "依赖关系创建成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建依赖关系失败"
        )


# Reports endpoints
@router.get(
    "/reports",
    summary="获取报告列表",
    responses={
        200: {"description": "报告列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_reports(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取业务影响报告列表

    支持分页查询。
    """
    try:
        reports = _load_json_file(REPORTS_FILE)

        # 分页
        total = len(reports)
        paginated = reports[offset : offset + limit]

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
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取报告列表失败"
        )


@router.post(
    "/reports",
    summary="创建报告",
    status_code=201,
    responses={
        201: {"description": "报告创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_report(request: CreateReportRequest) -> Dict[str, Any]:
    """
    创建新的业务影响报告

    生成包含多个服务业务影响分析的报告。
    """
    try:
        reports = _load_json_file(REPORTS_FILE)

        # 收集所有服务的业务影响数据
        service_data = []
        for service_name in request.service_names:
            try:
                impact = await assess_business_impact(service_name)
                service_data.append(impact)
            except Exception as e:  # noqa: F841 - Exception intentionally unused
                # 跳过失败的服务
                continue

        # 计算汇总统计
        total_revenue_impact = sum(s.get("revenueImpact", 0) for s in service_data)
        total_affected_users = sum(s.get("affectedUsers", 0) for s in service_data)
        avg_impact_score = (
            sum(s.get("impactScore", 0) for s in service_data) / len(service_data)
            if service_data
            else 0
        )

        # 生成建议
        recommendations = []
        if request.include_recommendations:
            high_impact_services = [s for s in service_data if s.get("impactScore", 0) > 7]
            for service in high_impact_services:
                recommendations.append(
                    {
                        "service": service.get("name"),
                        "priority": "high",
                        "action": f"Monitor {service.get('name')} closely due to high impact score",
                    }
                )

        report = {
            "id": _generate_id("RPT"),
            "title": request.title,
            "service_names": request.service_names,
            "time_range": request.time_range,
            "include_recommendations": request.include_recommendations,
            "created_at": _now(),
            "updated_at": _now(),
            "summary": {
                "total_services": len(service_data),
                "total_revenue_impact": total_revenue_impact,
                "total_affected_users": total_affected_users,
                "avg_impact_score": round(avg_impact_score, 2),
            },
            "service_data": service_data,
            "recommendations": recommendations,
        }

        reports.append(report)
        _save_json_file(REPORTS_FILE, reports)

        # Dual-write to database
        db = get_session()
        try:
            _save_report_to_db(db, report)
        except Exception as e:
            # Log database error but continue with JSON storage
            pass
        finally:
            db.close()

        return create_success_response(report, "报告创建成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建报告失败"
        )


# Impact scores endpoint
@router.get(
    "/impact-scores",
    summary="获取影响分数",
    responses={
        200: {"description": "影响分数"},
        500: {"description": "服务器错误"},
    },
)
async def get_impact_scores(
    service_name: Optional[str] = Query(None, description="服务名称"),
    threshold: Optional[float] = Query(None, ge=0, le=10, description="分数阈值"),
) -> Dict[str, Any]:
    """
    获取服务业务影响分数

    返回所有服务或指定服务的影响分数，支持按阈值筛选。
    """
    try:
        services = await list_business_impact_services()

        # 提取影响分数
        impact_scores = [
            {
                "service_id": s.get("id"),
                "service_name": s.get("name"),
                "impact_score": s.get("impactScore"),
                "category": s.get("category"),
                "status": s.get("status"),
            }
            for s in services
        ]

        # 按服务名称筛选
        if service_name:
            impact_scores = [s for s in impact_scores if s["service_name"] == service_name]

        # 按阈值筛选
        if threshold is not None:
            impact_scores = [s for s in impact_scores if s["impact_score"] >= threshold]

        # 按影响分数排序
        impact_scores.sort(key=lambda x: x["impact_score"], reverse=True)

        # 计算统计信息
        if impact_scores:
            avg_score = sum(s["impact_score"] for s in impact_scores) / len(impact_scores)
            max_score = max(s["impact_score"] for s in impact_scores)
            min_score = min(s["impact_score"] for s in impact_scores)
        else:
            avg_score = max_score = min_score = 0

        result = {
            "impact_scores": impact_scores,
            "statistics": {
                "count": len(impact_scores),
                "average": round(avg_score, 2),
                "max": round(max_score, 2),
                "min": round(min_score, 2),
            },
            "timestamp": _now(),
        }

        return create_success_response(result)
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取影响分数失败"
        )
