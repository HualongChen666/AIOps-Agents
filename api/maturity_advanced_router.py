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
from sqlalchemy.orm import Session

from core.authentication import UserInDB, get_user, verify_token
from core.maturity_engine import assess_maturity
from core.api_response_standard import create_success_response, create_error_response
from core.auth_db import get_session
from core.models import MaturityAssessmentDB

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


# ============ Database-based data storage ============


# ============ Assessment Endpoints ============
@router.get(
    "/assessments",
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
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """获取所有成熟度评估记录"""
    try:
        query = db.query(MaturityAssessmentDB)

        if status:
            query = query.filter(MaturityAssessmentDB.status == status.value)

        records = query.order_by(MaturityAssessmentDB.assessed_at.desc()).offset(offset).limit(limit).all()

        # Convert to response format
        result = []
        for record in records:
            result.append({
                "id": record.id,
                "assessment_name": record.assessment_name,
                "status": record.status,
                "overall_score": record.overall_score,
                "level": record.level,
                "level_name": record.level_name,
                "dimensions": record.dimensions or [],
                "recommendations": record.recommendations or [],
                "assessed_at": record.assessed_at.isoformat() if record.assessed_at else None,
                "assessed_by": record.assessed_by,
                "notes": record.notes,
            })

        return create_success_response(data=result)
    except Exception as e:
        logger.error(f"获取评估列表失败: {e}", exc_info=True)
        return create_error_response(error=f"获取评估列表失败: {str(e)[:200]}")


@router.post(
    "/assessments",
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
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
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

    # Create database record
    record = MaturityAssessmentDB(
        id=assessment_id,
        assessment_name=assessment_create.assessment_name,
        status=status.value,
        overall_score=result.get("overall_score", 0),
        level=result.get("level", 1),
        level_name=result.get("level_name", "Unknown"),
        dimensions=result.get("dimensions", []),
        recommendations=result.get("recommendations", []),
        assessed_at=now,
        assessed_by=current_user.username,
        notes=assessment_create.notes,
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(
            f"Maturity assessment created | assessment_id={assessment_id} "
            f"| name={assessment_create.assessment_name} | user={current_user.username} "
            f"| ip={get_client_ip(request)}"
        )

        # Convert to response format
        result_data = {
            "id": record.id,
            "assessment_name": record.assessment_name,
            "status": record.status,
            "overall_score": record.overall_score,
            "level": record.level,
            "level_name": record.level_name,
            "dimensions": record.dimensions or [],
            "recommendations": record.recommendations or [],
            "assessed_at": record.assessed_at.isoformat() if record.assessed_at else None,
            "assessed_by": record.assessed_by,
            "notes": record.notes,
        }

        return create_success_response(data=result_data)
    except Exception as e:
        db.rollback()
        logger.error(f"创建评估失败: {e}", exc_info=True)
        return create_error_response(error=f"创建评估失败: {str(e)[:200]}")


@router.get(
    "/assessments/{id}",
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
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """获取指定评估的详情"""
    try:
        record = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == id).first()
        if not record:
            return create_error_response(error="Assessment not found")

        # Convert to response format
        result_data = {
            "id": record.id,
            "assessment_name": record.assessment_name,
            "status": record.status,
            "overall_score": record.overall_score,
            "level": record.level,
            "level_name": record.level_name,
            "dimensions": record.dimensions or [],
            "recommendations": record.recommendations or [],
            "assessed_at": record.assessed_at.isoformat() if record.assessed_at else None,
            "assessed_by": record.assessed_by,
            "notes": record.notes,
        }

        return create_success_response(data=result_data)
    except Exception as e:
        logger.error(f"获取评估详情失败: {e}", exc_info=True)
        return create_error_response(error=f"获取评估详情失败: {str(e)[:200]}")


@router.delete(
    "/assessments/{id}",
    summary="删除评估",
    responses={
        (200): {"description": "评估删除成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "评估不存在"},
    },
)
async def delete_assessment(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """删除指定的评估记录"""
    try:
        if current_user.role != "admin":
            return create_error_response(error="Admin privileges required")

        record = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == id).first()
        if not record:
            return create_error_response(error="Assessment not found")

        db.delete(record)
        db.commit()

        logger.info(
            f"Maturity assessment deleted | assessment_id={id} | user={current_user.username} "
            f"| ip={get_client_ip(request)}"
        )

        return create_success_response(message="Assessment deleted successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"删除评估失败: {e}", exc_info=True)
        return create_error_response(error=f"删除评估失败: {str(e)[:200]}")


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
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """导出指定评估的报告"""
    try:
        record = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == id).first()
        if not record:
            return create_error_response(error="Assessment not found")

        if format == "json":
            result_data = {
                "id": record.id,
                "assessment_name": record.assessment_name,
                "status": record.status,
                "overall_score": record.overall_score,
                "level": record.level,
                "level_name": record.level_name,
                "dimensions": record.dimensions or [],
                "recommendations": record.recommendations or [],
                "assessed_at": record.assessed_at.isoformat() if record.assessed_at else None,
                "assessed_by": record.assessed_by,
                "notes": record.notes,
            }
            return create_success_response(data=result_data)
        elif format == "summary":
            result_data = {
                "id": record.id,
                "assessment_name": record.assessment_name,
                "overall_score": record.overall_score,
                "level": record.level,
                "level_name": record.level_name,
                "assessed_at": record.assessed_at.isoformat() if record.assessed_at else None,
                "dimension_count": len(record.dimensions) if record.dimensions else 0,
                "recommendation_count": len(record.recommendations) if record.recommendations else 0,
            }
            return create_success_response(data=result_data)
        else:
            return create_error_response(error=f"Unsupported format: {format}")
    except Exception as e:
        logger.error(f"导出评估失败: {e}", exc_info=True)
        return create_error_response(error=f"导出评估失败: {str(e)[:200]}")
