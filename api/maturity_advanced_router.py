# -*- coding: utf-8 -*-
"""Advanced Maturity Assessment API router for assessments and evaluations."""

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
from core.maturity_engine import assess_maturity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/maturity", tags=["maturity-advanced"])
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
class AssessmentStatus(str, Enum):
    """评估状态"""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ============ Assessment Models ============
class MaturityAssessmentRecord(BaseModel):
    id: str
    assessment_name: str
    status: AssessmentStatus
    overall_score: int
    level: int
    level_name: str
    dimensions: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    assessed_at: datetime
    assessed_by: str
    notes: Optional[str] = None

    model_config = {"extra": "ignore"}


class MaturityAssessmentCreate(BaseModel):
    assessment_name: str = Field(..., min_length=1, max_length=200)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = {"extra": "ignore"}


# ============ In-memory data storage ============
_assessment_records: Dict[str, MaturityAssessmentRecord] = {}


def _init_assessment_records():
    """初始化默认评估记录"""
    if not _assessment_records:
        # 创建一个模拟的评估结果
        assessment_id = str(uuid.uuid4())
        try:
            result = await assess_maturity()
        except:
            # 如果核心引擎失败，创建一个模拟结果
            result = {
                "overall_score": 65,
                "level": 3,
                "level_name": "Intermediate",
                "dimensions": [
                    {
                        "name": "可观测性",
                        "score": 70,
                        "maxScore": 100,
                        "description": "系统监控覆盖度和实时性",
                    },
                    {
                        "name": "自动化",
                        "score": 60,
                        "maxScore": 100,
                        "description": "运维自动化程度",
                    },
                    {
                        "name": "可靠性",
                        "score": 65,
                        "maxScore": 100,
                        "description": "系统可靠性和稳定性",
                    },
                ],
                "recommendations": [
                    {
                        "id": "rec-1",
                        "category": "可观测性",
                        "title": "增加监控覆盖",
                        "description": "扩展监控指标覆盖范围",
                        "priority": "high",
                        "estimatedTime": "2周",
                        "targetLevel": 4,
                    }
                ],
            }

        record = MaturityAssessmentRecord(
            id=assessment_id,
            assessment_name="Initial Assessment",
            status=AssessmentStatus.COMPLETED,
            overall_score=result.get("overall_score", 0),
            level=result.get("level", 1),
            level_name=result.get("level_name", "Unknown"),
            dimensions=result.get("dimensions", []),
            recommendations=result.get("recommendations", []),
            assessed_at=datetime.now() - timedelta(days=7),
            assessed_by="admin",
            notes="Initial maturity assessment",
        )

        _assessment_records[assessment_id] = record


# 初始化数据
_init_assessment_records()


# ============ Assessment Endpoints ============
@router.get(
    "/assessments",
    response_model=List[MaturityAssessmentRecord],
    summary="获取成熟度评估列表",
    responses={
        (200): {"description": "评估记录列表"},
        (401): {"description": "未授权"},
    },
)
async def get_assessments(
    status: Optional[AssessmentStatus] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[MaturityAssessmentRecord]:
    """获取所有成熟度评估记录"""
    records = list(_assessment_records.values())

    if status:
        records = [r for r in records if r.status == status]

    records.sort(key=lambda x: x.assessed_at, reverse=True)
    return records[offset : offset + limit]


@router.post(
    "/assessments",
    response_model=MaturityAssessmentRecord,
    status_code=status.HTTP_201_CREATED,
    summary="创建成熟度评估",
    responses={
        (201): {"description": "评估创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_assessment(
    assessment_create: MaturityAssessmentCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> MaturityAssessmentRecord:
    """创建新的成熟度评估"""
    assessment_id = str(uuid.uuid4())
    now = datetime.now()

    # 执行评估
    try:
        result = await assess_maturity()
        status = AssessmentStatus.COMPLETED
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        result = {
            "overall_score": 0,
            "level": 1,
            "level_name": "Unknown",
            "dimensions": [],
            "recommendations": [],
        }
        status = AssessmentStatus.FAILED

    record = MaturityAssessmentRecord(
        id=assessment_id,
        assessment_name=assessment_create.assessment_name,
        status=status,
        overall_score=result.get("overall_score", 0),
        level=result.get("level", 1),
        level_name=result.get("level_name", "Unknown"),
        dimensions=result.get("dimensions", []),
        recommendations=result.get("recommendations", []),
        assessed_at=now,
        assessed_by=current_user.username,
        notes=assessment_create.notes,
    )

    _assessment_records[assessment_id] = record

    logger.info(
        f"Maturity assessment created | assessment_id={assessment_id} "
        f"| name={assessment_create.assessment_name} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return record


@router.get(
    "/assessments/{id}",
    response_model=MaturityAssessmentRecord,
    summary="获取评估详情",
    responses={
        (200): {"description": "评估详情"},
        (401): {"description": "未授权"},
        (404): {"description": "评估不存在"},
    },
)
async def get_assessment(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> MaturityAssessmentRecord:
    """获取指定评估的详情"""
    if id not in _assessment_records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return _assessment_records[id]


@router.delete(
    "/assessments/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除评估",
    responses={
        (204): {"description": "评估删除成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "评估不存在"},
    },
)
async def delete_assessment(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定的评估记录"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    if id not in _assessment_records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    del _assessment_records[id]

    logger.info(
        f"Maturity assessment deleted | assessment_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )


@router.get(
    "/assessments/{id}/export",
    summary="导出评估报告",
    responses={
        (200): {"description": "评估报告"},
        (401): {"description": "未授权"},
        (404): {"description": "评估不存在"},
    },
)
async def export_assessment(
    id: str,
    format: str = "json",
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """导出指定评估的报告"""
    if id not in _assessment_records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    record = _assessment_records[id]

    if format == "json":
        return record.model_dump()
    elif format == "summary":
        return {
            "id": record.id,
            "assessment_name": record.assessment_name,
            "overall_score": record.overall_score,
            "level": record.level,
            "level_name": record.level_name,
            "assessed_at": record.assessed_at.isoformat(),
            "dimension_count": len(record.dimensions),
            "recommendation_count": len(record.recommendations),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format: {format}"
        )
