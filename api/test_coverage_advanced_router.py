# -*- coding: utf-8 -*-
"""Advanced Test Coverage API router for reports and metrics."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.authentication import UserInDB, get_user, verify_token
from core.database import get_db
from core.models import TestCoverageReportDB, TestCoverageTargetDB, TestCoverageComparisonDB
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/test-coverage", tags=["test-coverage-advanced"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

# 开发环境占位
FAKE_ADMIN = UserInDB(
    username="dev-admin",
    full_name="Dev Admin",
    email="dev@example.com",
    role="admin",
    disabled=False,
    hashed_password="",
)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserInDB:
    """获取当前用户；无 token 时返回开发占位 admin。"""
    if not token:
        return FAKE_ADMIN
    payload = verify_token(token)
    if not payload:
        return FAKE_ADMIN
    username = payload.get("sub")
    if not username:
        return FAKE_ADMIN
    user = await get_user(username)
    if not user:
        return FAKE_ADMIN
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )
    return user


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ============ Enums ============
class CoverageLevel(str, Enum):
    """覆盖率等级"""

    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    POOR = "poor"


# ============ Report Models ============
class ModuleCoverage(BaseModel):
    module_id: str
    module_name: str
    total_lines: int
    covered_lines: int
    coverage_percentage: float
    coverage_level: CoverageLevel
    last_updated: datetime

    model_config = {"extra": "ignore"}


class CoverageReport(BaseModel):
    id: str
    report_name: str
    generated_at: datetime
    overall_coverage: float
    overall_level: CoverageLevel
    total_modules: int
    modules: List[ModuleCoverage]
    summary: Dict[str, Any]
    trends: Optional[Dict[str, Any]] = None

    model_config = {"extra": "ignore"}


class CoverageReportCreate(BaseModel):
    report_name: str = Field(..., min_length=1, max_length=200)
    include_trends: bool = False

    model_config = {"extra": "ignore"}


# ============ Database Helper Functions ============
def _db_to_report(report_db: TestCoverageReportDB) -> CoverageReport:
    """Convert database model to API model"""
    # Convert modules from JSON to ModuleCoverage objects
    modules_data = report_db.modules or []
    modules = [
        ModuleCoverage(
            module_id=m.get("module_id", f"mod-{i}"),
            module_name=m.get("module_name", "unknown"),
            total_lines=m.get("total_lines", 0),
            covered_lines=m.get("covered_lines", 0),
            coverage_percentage=m.get("coverage_percentage", 0.0),
            coverage_level=CoverageLevel(m.get("coverage_level", "poor")),
            last_updated=datetime.now(),
        )
        for i, m in enumerate(modules_data)
    ]
    
    return CoverageReport(
        id=report_db.id,
        report_name=report_db.report_name,
        generated_at=report_db.generated_at or datetime.now(),
        overall_coverage=report_db.overall_coverage,
        overall_level=CoverageLevel(report_db.overall_level),
        total_modules=report_db.total_modules,
        modules=modules,
        summary=report_db.summary or {},
        trends=report_db.trends,
    )


# ============ Trend Analysis Models ============
class CoverageTrendPoint(BaseModel):
    """覆盖率趋势数据点"""
    date: str
    coverage: float
    report_id: str
    report_name: str

    model_config = {"extra": "ignore"}


class CoverageTrendAnalysis(BaseModel):
    """覆盖率趋势分析"""
    period_start: str
    period_end: str
    trend_points: List[CoverageTrendPoint]
    average_coverage: float
    min_coverage: float
    max_coverage: float
    trend_direction: str  # "up", "down", "stable"
    trend_percentage: float
    improvement_rate: float

    model_config = {"extra": "ignore"}


# ============ Target Management Models ============
class CoverageTarget(BaseModel):
    """覆盖率目标"""
    target_id: str
    target_name: str
    module_id: Optional[str] = None
    module_name: Optional[str] = None
    target_percentage: float
    current_percentage: float
    status: str  # "met", "not_met", "in_progress"
    deadline: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"extra": "ignore"}


class CoverageTargetCreate(BaseModel):
    """创建覆盖率目标"""
    target_name: str = Field(..., min_length=1, max_length=200)
    module_id: Optional[str] = None
    module_name: Optional[str] = None
    target_percentage: float = Field(..., ge=0, le=100)
    deadline: Optional[str] = None

    model_config = {"extra": "ignore"}


class CoverageTargetUpdate(BaseModel):
    """更新覆盖率目标"""
    target_name: Optional[str] = Field(None, min_length=1, max_length=200)
    target_percentage: Optional[float] = Field(None, ge=0, le=100)
    deadline: Optional[str] = None

    model_config = {"extra": "ignore"}


# ============ Comparison Analysis Models ============
class CoverageComparison(BaseModel):
    """覆盖率对比"""
    comparison_id: str
    report_a_id: str
    report_a_name: str
    report_b_id: str
    report_b_name: str
    comparison_date: str
    overall_change: float
    module_changes: List[Dict[str, Any]]
    summary: Dict[str, Any]

    model_config = {"extra": "ignore"}


class CoverageComparisonRequest(BaseModel):
    """覆盖率对比请求"""
    report_a_id: str
    report_b_id: str

    model_config = {"extra": "ignore"}


def _calculate_coverage_level(percentage: float) -> CoverageLevel:
    """根据覆盖率百分比计算等级"""
    if percentage >= 90:
        return CoverageLevel.EXCELLENT
    elif percentage >= 75:
        return CoverageLevel.GOOD
    elif percentage >= 60:
        return CoverageLevel.ADEQUATE
    else:
        return CoverageLevel.POOR


# ============ Report Endpoints ============
@router.get(
    "/reports",
    response_model=List[CoverageReport],
    summary="获取覆盖率报告列表",
    responses={
        (200): {"description": "覆盖率报告列表"},
        (401): {"description": "未授权"},
    },
)
async def get_coverage_reports(
    limit: int = 50,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CoverageReport]:
    """获取所有覆盖率报告"""
    reports_db = db.query(TestCoverageReportDB).order_by(
        TestCoverageReportDB.generated_at.desc()
    ).offset(offset).limit(limit).all()
    
    return [_db_to_report(report) for report in reports_db]


@router.post(
    "/reports",
    response_model=CoverageReport,
    status_code=status.HTTP_201_CREATED,
    summary="生成覆盖率报告",
    responses={
        (201): {"description": "覆盖率报告生成成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_coverage_report(
    report_create: CoverageReportCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageReport:
    """生成新的覆盖率报告"""
    # 获取最新的报告作为基础
    latest_report_db = db.query(TestCoverageReportDB).order_by(
        TestCoverageReportDB.generated_at.desc()
    ).first()

    # 模拟生成新报告（实际应该从测试框架获取最新数据）
    if latest_report_db:
        modules_data = latest_report_db.modules or []
        modules = []
        for m in modules_data:
            covered_lines = int(m.get("covered_lines", 0) * (1 + (hash(m.get("module_id", "")) % 10) / 100))
            coverage_percentage = round((covered_lines / m.get("total_lines", 1)) * 100, 2)
            modules.append({
                "module_id": m.get("module_id", ""),
                "module_name": m.get("module_name", ""),
                "total_lines": m.get("total_lines", 0),
                "covered_lines": covered_lines,
                "coverage_percentage": coverage_percentage,
                "coverage_level": _calculate_coverage_level(coverage_percentage).value,
            })

        overall_coverage = sum(m["coverage_percentage"] for m in modules) / len(modules) if modules else 0.0
    else:
        modules = []
        overall_coverage = 0.0

    report_id = str(uuid.uuid4())
    now = datetime.now()

    summary = {
        "total_lines": sum(m["total_lines"] for m in modules),
        "covered_lines": sum(m["covered_lines"] for m in modules),
        "uncovered_lines": sum(m["total_lines"] - m["covered_lines"] for m in modules),
        "excellent_count": len([m for m in modules if m["coverage_level"] == "excellent"]),
        "good_count": len([m for m in modules if m["coverage_level"] == "good"]),
        "adequate_count": len([m for m in modules if m["coverage_level"] == "adequate"]),
        "poor_count": len([m for m in modules if m["coverage_level"] == "poor"]),
    }

    trends = None
    if report_create.include_trends and latest_report_db:
        trends = {
            "previous_coverage": latest_report_db.overall_coverage,
            "change": overall_coverage - latest_report_db.overall_coverage,
            "trend": "up" if overall_coverage > latest_report_db.overall_coverage else "down",
        }

    report_db = TestCoverageReportDB(
        id=report_id,
        report_name=report_create.report_name,
        generated_at=now,
        overall_coverage=overall_coverage,
        overall_level=_calculate_coverage_level(overall_coverage).value,
        total_modules=len(modules),
        summary=summary,
        modules=modules,
        trends=trends,
    )
    
    db.add(report_db)
    db.commit()

    logger.info(
        f"Coverage report generated | report_id={report_id} | name={report_create.report_name} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )

    return _db_to_report(report_db)


@router.get(
    "/reports/{id}",
    response_model=CoverageReport,
    summary="获取覆盖率报告详情",
    responses={
        (200): {"description": "覆盖率报告详情"},
        (401): {"description": "未授权"},
        (404): {"description": "报告不存在"},
    },
)
async def get_coverage_report(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageReport:
    """获取指定覆盖率报告的详情"""
    report_db = db.query(TestCoverageReportDB).filter(TestCoverageReportDB.id == id).first()
    
    if not report_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    return _db_to_report(report_db)


@router.delete(
    "/reports/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除覆盖率报告",
    responses={
        (204): {"description": "报告删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "报告不存在"},
    },
)
async def delete_coverage_report(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """删除指定的覆盖率报告"""
    report_db = db.query(TestCoverageReportDB).filter(TestCoverageReportDB.id == id).first()
    
    if not report_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    db.delete(report_db)
    db.commit()

    logger.info(
        f"Coverage report deleted | report_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )


@router.get(
    "/summary",
    summary="获取覆盖率摘要",
    responses={
        (200): {"description": "覆盖率摘要"},
        (401): {"description": "未授权"},
    },
)
async def get_coverage_summary(
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """获取最新的覆盖率摘要信息"""
    latest_report_db = db.query(TestCoverageReportDB).order_by(
        TestCoverageReportDB.generated_at.desc()
    ).first()

    if not latest_report_db:
        return {
            "overall_coverage": 0.0,
            "overall_level": "poor",
            "total_modules": 0,
            "summary": {},
        }

    return {
        "overall_coverage": latest_report_db.overall_coverage,
        "overall_level": latest_report_db.overall_level,
        "total_modules": latest_report_db.total_modules,
        "summary": latest_report_db.summary or {},
        "generated_at": latest_report_db.generated_at.isoformat() if latest_report_db.generated_at else None,
    }


# ============ Trend Analysis Endpoints ============
@router.get(
    "/trends",
    response_model=CoverageTrendAnalysis,
    summary="获取覆盖率趋势分析",
    responses={
        (200): {"description": "覆盖率趋势分析"},
        (401): {"description": "未授权"},
    },
)
async def get_coverage_trends(
    days: int = 30,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageTrendAnalysis:
    """获取指定时间段的覆盖率趋势分析"""
    start_date = datetime.now() - timedelta(days=days)
    
    reports_db = db.query(TestCoverageReportDB).filter(
        TestCoverageReportDB.generated_at >= start_date
    ).order_by(TestCoverageReportDB.generated_at.asc()).all()
    
    if not reports_db:
        return CoverageTrendAnalysis(
            period_start=start_date.isoformat(),
            period_end=datetime.now().isoformat(),
            trend_points=[],
            average_coverage=0.0,
            min_coverage=0.0,
            max_coverage=0.0,
            trend_direction="stable",
            trend_percentage=0.0,
            improvement_rate=0.0,
        )
    
    trend_points = [
        CoverageTrendPoint(
            date=report.generated_at.isoformat() if report.generated_at else "",
            coverage=report.overall_coverage,
            report_id=report.id,
            report_name=report.report_name,
        )
        for report in reports_db
    ]
    
    coverages = [point.coverage for point in trend_points]
    average_coverage = sum(coverages) / len(coverages) if coverages else 0.0
    min_coverage = min(coverages) if coverages else 0.0
    max_coverage = max(coverages) if coverages else 0.0
    
    # Calculate trend direction
    if len(coverages) >= 2:
        first_coverage = coverages[0]
        last_coverage = coverages[-1]
        trend_percentage = ((last_coverage - first_coverage) / first_coverage * 100) if first_coverage > 0 else 0.0
        
        if trend_percentage > 1.0:
            trend_direction = "up"
        elif trend_percentage < -1.0:
            trend_direction = "down"
        else:
            trend_direction = "stable"
    else:
        trend_percentage = 0.0
        trend_direction = "stable"
    
    # Calculate improvement rate (percentage points per day)
    if len(trend_points) >= 2:
        time_span_days = (datetime.now() - start_date).days
        improvement_rate = (coverages[-1] - coverages[0]) / time_span_days if time_span_days > 0 else 0.0
    else:
        improvement_rate = 0.0
    
    logger.info(
        f"Coverage trend analysis requested | days={days} | points={len(trend_points)} | "
        f"trend={trend_direction} | user={current_user.username}"
    )
    
    return CoverageTrendAnalysis(
        period_start=start_date.isoformat(),
        period_end=datetime.now().isoformat(),
        trend_points=trend_points,
        average_coverage=average_coverage,
        min_coverage=min_coverage,
        max_coverage=max_coverage,
        trend_direction=trend_direction,
        trend_percentage=trend_percentage,
        improvement_rate=improvement_rate,
    )


# ============ Target Management Endpoints ============
@router.get(
    "/targets",
    response_model=List[CoverageTarget],
    summary="获取覆盖率目标列表",
    responses={
        (200): {"description": "覆盖率目标列表"},
        (401): {"description": "未授权"},
    },
)
async def get_coverage_targets(
    limit: int = 50,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CoverageTarget]:
    """获取所有覆盖率目标"""
    targets_db = db.query(TestCoverageTargetDB).order_by(
        TestCoverageTargetDB.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return [
        CoverageTarget(
            target_id=target.id,
            target_name=target.target_name,
            module_id=target.module_id,
            module_name=target.module_name,
            target_percentage=target.target_percentage,
            current_percentage=target.current_percentage,
            status=target.status,
            deadline=target.deadline.isoformat() if target.deadline else None,
            created_at=target.created_at.isoformat() if target.created_at else "",
            updated_at=target.updated_at.isoformat() if target.updated_at else "",
        )
        for target in targets_db
    ]


@router.post(
    "/targets",
    response_model=CoverageTarget,
    status_code=status.HTTP_201_CREATED,
    summary="创建覆盖率目标",
    responses={
        (201): {"description": "覆盖率目标创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_coverage_target(
    target_create: CoverageTargetCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageTarget:
    """创建新的覆盖率目标"""
    target_id = str(uuid.uuid4())
    now = datetime.now()
    
    # Parse deadline if provided
    deadline = None
    if target_create.deadline:
        try:
            deadline = datetime.fromisoformat(target_create.deadline)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid deadline format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    # Get current coverage for the module if specified
    current_percentage = 0.0
    if target_create.module_id:
        latest_report = db.query(TestCoverageReportDB).order_by(
            TestCoverageReportDB.generated_at.desc()
        ).first()
        if latest_report and latest_report.modules:
            for module in latest_report.modules:
                if module.get("module_id") == target_create.module_id:
                    current_percentage = module.get("coverage_percentage", 0.0)
                    break
    
    # Determine initial status
    status = "met" if current_percentage >= target_create.target_percentage else "not_met"
    
    target_db = TestCoverageTargetDB(
        id=target_id,
        target_name=target_create.target_name,
        module_id=target_create.module_id,
        module_name=target_create.module_name,
        target_percentage=target_create.target_percentage,
        current_percentage=current_percentage,
        status=status,
        deadline=deadline,
    )
    
    db.add(target_db)
    db.commit()
    
    logger.info(
        f"Coverage target created | target_id={target_id} | name={target_create.target_name} | "
        f"target={target_create.target_percentage}% | user={current_user.username} | ip={get_client_ip(request)}"
    )
    
    return CoverageTarget(
        target_id=target_db.id,
        target_name=target_db.target_name,
        module_id=target_db.module_id,
        module_name=target_db.module_name,
        target_percentage=target_db.target_percentage,
        current_percentage=target_db.current_percentage,
        status=target_db.status,
        deadline=target_db.deadline.isoformat() if target_db.deadline else None,
        created_at=target_db.created_at.isoformat() if target_db.created_at else "",
        updated_at=target_db.updated_at.isoformat() if target_db.updated_at else "",
    )


@router.put(
    "/targets/{target_id}",
    response_model=CoverageTarget,
    summary="更新覆盖率目标",
    responses={
        (200): {"description": "覆盖率目标更新成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (404): {"description": "目标不存在"},
    },
)
async def update_coverage_target(
    target_id: str,
    target_update: CoverageTargetUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageTarget:
    """更新指定的覆盖率目标"""
    target_db = db.query(TestCoverageTargetDB).filter(
        TestCoverageTargetDB.id == target_id
    ).first()
    
    if not target_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found"
        )
    
    # Update fields if provided
    if target_update.target_name is not None:
        target_db.target_name = target_update.target_name
    if target_update.target_percentage is not None:
        target_db.target_percentage = target_update.target_percentage
        # Recalculate status
        target_db.status = "met" if target_db.current_percentage >= target_db.target_percentage else "not_met"
    if target_update.deadline is not None:
        try:
            target_db.deadline = datetime.fromisoformat(target_update.deadline)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid deadline format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    db.commit()
    
    logger.info(
        f"Coverage target updated | target_id={target_id} | user={current_user.username} | ip={get_client_ip(request)}"
    )
    
    return CoverageTarget(
        target_id=target_db.id,
        target_name=target_db.target_name,
        module_id=target_db.module_id,
        module_name=target_db.module_name,
        target_percentage=target_db.target_percentage,
        current_percentage=target_db.current_percentage,
        status=target_db.status,
        deadline=target_db.deadline.isoformat() if target_db.deadline else None,
        created_at=target_db.created_at.isoformat() if target_db.created_at else "",
        updated_at=target_db.updated_at.isoformat() if target_db.updated_at else "",
    )


@router.delete(
    "/targets/{target_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除覆盖率目标",
    responses={
        (204): {"description": "目标删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "目标不存在"},
    },
)
async def delete_coverage_target(
    target_id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """删除指定的覆盖率目标"""
    target_db = db.query(TestCoverageTargetDB).filter(
        TestCoverageTargetDB.id == target_id
    ).first()
    
    if not target_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found"
        )
    
    db.delete(target_db)
    db.commit()
    
    logger.info(
        f"Coverage target deleted | target_id={target_id} | user={current_user.username} | ip={get_client_ip(request)}"
    )


@router.post(
    "/targets/{target_id}/refresh",
    response_model=CoverageTarget,
    summary="刷新目标状态",
    responses={
        (200): {"description": "目标状态刷新成功"},
        (401): {"description": "未授权"},
        (404): {"description": "目标不存在"},
    },
)
async def refresh_coverage_target(
    target_id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageTarget:
    """刷新指定目标的当前覆盖率状态"""
    target_db = db.query(TestCoverageTargetDB).filter(
        TestCoverageTargetDB.id == target_id
    ).first()
    
    if not target_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found"
        )
    
    # Get latest coverage for the module
    current_percentage = 0.0
    if target_db.module_id:
        latest_report = db.query(TestCoverageReportDB).order_by(
            TestCoverageReportDB.generated_at.desc()
        ).first()
        if latest_report and latest_report.modules:
            for module in latest_report.modules:
                if module.get("module_id") == target_db.module_id:
                    current_percentage = module.get("coverage_percentage", 0.0)
                    break
    
    target_db.current_percentage = current_percentage
    target_db.status = "met" if current_percentage >= target_db.target_percentage else "not_met"
    
    db.commit()
    
    logger.info(
        f"Coverage target refreshed | target_id={target_id} | current={current_percentage}% | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )
    
    return CoverageTarget(
        target_id=target_db.id,
        target_name=target_db.target_name,
        module_id=target_db.module_id,
        module_name=target_db.module_name,
        target_percentage=target_db.target_percentage,
        current_percentage=target_db.current_percentage,
        status=target_db.status,
        deadline=target_db.deadline.isoformat() if target_db.deadline else None,
        created_at=target_db.created_at.isoformat() if target_db.created_at else "",
        updated_at=target_db.updated_at.isoformat() if target_db.updated_at else "",
    )


# ============ Comparison Analysis Endpoints ============
@router.post(
    "/comparisons",
    response_model=CoverageComparison,
    status_code=status.HTTP_201_CREATED,
    summary="创建覆盖率对比",
    responses={
        (201): {"description": "覆盖率对比创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_coverage_comparison(
    comparison_request: CoverageComparisonRequest,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageComparison:
    """创建两个覆盖率报告之间的对比分析"""
    # Get both reports
    report_a = db.query(TestCoverageReportDB).filter(
        TestCoverageReportDB.id == comparison_request.report_a_id
    ).first()
    
    report_b = db.query(TestCoverageReportDB).filter(
        TestCoverageReportDB.id == comparison_request.report_b_id
    ).first()
    
    if not report_a or not report_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both reports not found"
        )
    
    # Calculate overall change
    overall_change = report_b.overall_coverage - report_a.overall_coverage
    
    # Calculate module-level changes
    module_changes = []
    modules_a = {m.get("module_id"): m for m in (report_a.modules or [])}
    modules_b = {m.get("module_id"): m for m in (report_b.modules or [])}
    
    all_module_ids = set(modules_a.keys()) | set(modules_b.keys())
    
    for module_id in all_module_ids:
        mod_a = modules_a.get(module_id, {})
        mod_b = modules_b.get(module_id, {})
        
        change = mod_b.get("coverage_percentage", 0.0) - mod_a.get("coverage_percentage", 0.0)
        
        module_changes.append({
            "module_id": module_id,
            "module_name": mod_b.get("module_name", mod_a.get("module_name", "unknown")),
            "coverage_a": mod_a.get("coverage_percentage", 0.0),
            "coverage_b": mod_b.get("coverage_percentage", 0.0),
            "change": change,
            "change_percentage": ((change / mod_a.get("coverage_percentage", 1)) * 100) if mod_a.get("coverage_percentage", 0) > 0 else 0.0,
        })
    
    # Sort by absolute change
    module_changes.sort(key=lambda x: abs(x["change"]), reverse=True)
    
    # Create summary
    summary = {
        "improved_modules": len([m for m in module_changes if m["change"] > 0]),
        "degraded_modules": len([m for m in module_changes if m["change"] < 0]),
        "unchanged_modules": len([m for m in module_changes if m["change"] == 0]),
        "max_improvement": max([m["change"] for m in module_changes]) if module_changes else 0.0,
        "max_degradation": min([m["change"] for m in module_changes]) if module_changes else 0.0,
    }
    
    comparison_id = str(uuid.uuid4())
    now = datetime.now()
    
    comparison_db = TestCoverageComparisonDB(
        id=comparison_id,
        report_a_id=report_a.id,
        report_a_name=report_a.report_name,
        report_b_id=report_b.id,
        report_b_name=report_b.report_name,
        overall_change=overall_change,
        module_changes=module_changes,
        summary=summary,
        comparison_date=now,
    )
    
    db.add(comparison_db)
    db.commit()
    
    logger.info(
        f"Coverage comparison created | comparison_id={comparison_id} | change={overall_change}% | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )
    
    return CoverageComparison(
        comparison_id=comparison_db.id,
        report_a_id=comparison_db.report_a_id,
        report_a_name=comparison_db.report_a_name,
        report_b_id=comparison_db.report_b_id,
        report_b_name=comparison_db.report_b_name,
        comparison_date=comparison_db.comparison_date.isoformat() if comparison_db.comparison_date else "",
        overall_change=comparison_db.overall_change,
        module_changes=comparison_db.module_changes or [],
        summary=comparison_db.summary or {},
    )


@router.get(
    "/comparisons",
    response_model=List[CoverageComparison],
    summary="获取覆盖率对比列表",
    responses={
        (200): {"description": "覆盖率对比列表"},
        (401): {"description": "未授权"},
    },
)
async def get_coverage_comparisons(
    limit: int = 50,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CoverageComparison]:
    """获取所有覆盖率对比"""
    comparisons_db = db.query(TestCoverageComparisonDB).order_by(
        TestCoverageComparisonDB.comparison_date.desc()
    ).offset(offset).limit(limit).all()
    
    return [
        CoverageComparison(
            comparison_id=comp.id,
            report_a_id=comp.report_a_id,
            report_a_name=comp.report_a_name,
            report_b_id=comp.report_b_id,
            report_b_name=comp.report_b_name,
            comparison_date=comp.comparison_date.isoformat() if comp.comparison_date else "",
            overall_change=comp.overall_change,
            module_changes=comp.module_changes or [],
            summary=comp.summary or {},
        )
        for comp in comparisons_db
    ]


@router.get(
    "/comparisons/{comparison_id}",
    response_model=CoverageComparison,
    summary="获取覆盖率对比详情",
    responses={
        (200): {"description": "覆盖率对比详情"},
        (401): {"description": "未授权"},
        (404): {"description": "对比不存在"},
    },
)
async def get_coverage_comparison(
    comparison_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageComparison:
    """获取指定覆盖率对比的详情"""
    comparison_db = db.query(TestCoverageComparisonDB).filter(
        TestCoverageComparisonDB.id == comparison_id
    ).first()
    
    if not comparison_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found"
        )
    
    return CoverageComparison(
        comparison_id=comparison_db.id,
        report_a_id=comparison_db.report_a_id,
        report_a_name=comparison_db.report_a_name,
        report_b_id=comparison_db.report_b_id,
        report_b_name=comparison_db.report_b_name,
        comparison_date=comparison_db.comparison_date.isoformat() if comparison_db.comparison_date else "",
        overall_change=comparison_db.overall_change,
        module_changes=comparison_db.module_changes or [],
        summary=comparison_db.summary or {},
    )
