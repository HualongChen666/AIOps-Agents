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


# ============ In-memory data storage ============
_coverage_reports: Dict[str, CoverageReport] = {}


def _init_coverage_reports():
    """初始化默认覆盖率报告"""
    if not _coverage_reports:
        modules = [
            ModuleCoverage(
                module_id="mod-1",
                module_name="core/authentication",
                total_lines=500,
                covered_lines=450,
                coverage_percentage=90.0,
                coverage_level=CoverageLevel.EXCELLENT,
                last_updated=datetime.now() - timedelta(hours=1),
            ),
            ModuleCoverage(
                module_id="mod-2",
                module_name="core/user_service",
                total_lines=800,
                covered_lines=640,
                coverage_percentage=80.0,
                coverage_level=CoverageLevel.GOOD,
                last_updated=datetime.now() - timedelta(hours=1),
            ),
            ModuleCoverage(
                module_id="mod-3",
                module_name="api/routes",
                total_lines=1200,
                covered_lines=840,
                coverage_percentage=70.0,
                coverage_level=CoverageLevel.ADEQUATE,
                last_updated=datetime.now() - timedelta(hours=1),
            ),
            ModuleCoverage(
                module_id="mod-4",
                module_name="utils/helpers",
                total_lines=300,
                covered_lines=150,
                coverage_percentage=50.0,
                coverage_level=CoverageLevel.POOR,
                last_updated=datetime.now() - timedelta(hours=1),
            ),
        ]

        overall_coverage = sum(m.coverage_percentage for m in modules) / len(modules)

        report = CoverageReport(
            id=str(uuid.uuid4()),
            report_name="Latest Coverage Report",
            generated_at=datetime.now(),
            overall_coverage=overall_coverage,
            overall_level=CoverageLevel.GOOD if overall_coverage >= 75 else CoverageLevel.ADEQUATE,
            total_modules=len(modules),
            modules=modules,
            summary={
                "total_lines": sum(m.total_lines for m in modules),
                "covered_lines": sum(m.covered_lines for m in modules),
                "uncovered_lines": sum(m.total_lines - m.covered_lines for m in modules),
                "excellent_count": len([m for m in modules if m.coverage_level == CoverageLevel.EXCELLENT]),
                "good_count": len([m for m in modules if m.coverage_level == CoverageLevel.GOOD]),
                "adequate_count": len([m for m in modules if m.coverage_level == CoverageLevel.ADEQUATE]),
                "poor_count": len([m for m in modules if m.coverage_level == CoverageLevel.POOR]),
            },
            trends={
                "previous_coverage": 72.5,
                "change": overall_coverage - 72.5,
                "trend": "up" if overall_coverage > 72.5 else "down",
            },
        )

        _coverage_reports[report.id] = report


# 初始化数据
_init_coverage_reports()


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
) -> List[CoverageReport]:
    """获取所有覆盖率报告"""
    reports = list(_coverage_reports.values())
    reports.sort(key=lambda x: x.generated_at, reverse=True)
    return reports[offset : offset + limit]


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
) -> CoverageReport:
    """生成新的覆盖率报告"""
    # 获取最新的报告作为基础
    if not _coverage_reports:
        _init_coverage_reports()

    latest_report = list(_coverage_reports.values())[0] if _coverage_reports else None

    # 模拟生成新报告（实际应该从测试框架获取最新数据）
    if latest_report:
        modules = [
            ModuleCoverage(
                module_id=m.module_id,
                module_name=m.module_name,
                total_lines=m.total_lines,
                covered_lines=int(m.covered_lines * (1 + (hash(m.module_id) % 10) / 100)),  # 模拟变化
                coverage_percentage=0,
                coverage_level=CoverageLevel.GOOD,
                last_updated=datetime.now(),
            )
            for m in latest_report.modules
        ]

        # 重新计算覆盖率
        for module in modules:
            module.coverage_percentage = round(
                (module.covered_lines / module.total_lines) * 100, 2
            )
            module.coverage_level = _calculate_coverage_level(module.coverage_percentage)

        overall_coverage = sum(m.coverage_percentage for m in modules) / len(modules)
    else:
        modules = []
        overall_coverage = 0.0

    report_id = str(uuid.uuid4())
    now = datetime.now()

    report = CoverageReport(
        id=report_id,
        report_name=report_create.report_name,
        generated_at=now,
        overall_coverage=overall_coverage,
        overall_level=_calculate_coverage_level(overall_coverage),
        total_modules=len(modules),
        modules=modules,
        summary={
            "total_lines": sum(m.total_lines for m in modules),
            "covered_lines": sum(m.covered_lines for m in modules),
            "uncovered_lines": sum(m.total_lines - m.covered_lines for m in modules),
            "excellent_count": len([m for m in modules if m.coverage_level == CoverageLevel.EXCELLENT]),
            "good_count": len([m for m in modules if m.coverage_level == CoverageLevel.GOOD]),
            "adequate_count": len([m for m in modules if m.coverage_level == CoverageLevel.ADEQUATE]),
            "poor_count": len([m for m in modules if m.coverage_level == CoverageLevel.POOR]),
        },
        trends={
            "previous_coverage": latest_report.overall_coverage if latest_report else 0,
            "change": overall_coverage - (latest_report.overall_coverage if latest_report else 0),
            "trend": "up" if overall_coverage > (latest_report.overall_coverage if latest_report else 0) else "down",
        } if report_create.include_trends and latest_report else None,
    )

    _coverage_reports[report_id] = report

    logger.info(
        f"Coverage report generated | report_id={report_id} | name={report_create.report_name} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )

    return report


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
) -> CoverageReport:
    """获取指定覆盖率报告的详情"""
    if id not in _coverage_reports:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return _coverage_reports[id]


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
) -> None:
    """删除指定的覆盖率报告"""
    if id not in _coverage_reports:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    del _coverage_reports[id]

    logger.info(
        f"Coverage report deleted | report_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
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
) -> Dict[str, Any]:
    """获取最新的覆盖率摘要信息"""
    if not _coverage_reports:
        _init_coverage_reports()

    latest_report = list(_coverage_reports.values())[0] if _coverage_reports else None

    if not latest_report:
        return {
            "overall_coverage": 0.0,
            "overall_level": "poor",
            "total_modules": 0,
            "summary": {},
        }

    return {
        "overall_coverage": latest_report.overall_coverage,
        "overall_level": latest_report.overall_level.value,
        "total_modules": latest_report.total_modules,
        "summary": latest_report.summary,
        "generated_at": latest_report.generated_at.isoformat(),
    }
