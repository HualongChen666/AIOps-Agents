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
from core.models import TestCoverageReportDB
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
