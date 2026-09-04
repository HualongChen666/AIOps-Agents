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


class MaturityAssessmentUpdate(BaseModel):
    assessment_name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[AssessmentStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = {"extra": "ignore"}


class MaturityAssessmentPatch(BaseModel):
    assessment_name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[AssessmentStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = {"extra": "ignore"}


class AssessmentCompareRequest(BaseModel):
    compare_with_id: str = Field(..., description="要对比的评估ID")

    model_config = {"extra": "ignore"}


class AssessmentApproveRequest(BaseModel):
    approved: bool = Field(..., description="是否批准")
    comment: Optional[str] = Field(None, max_length=500, description="审批意见")

    model_config = {"extra": "ignore"}


class BatchAssessmentCreate(BaseModel):
    assessments: List[MaturityAssessmentCreate] = Field(..., min_length=1, max_length=10)

    model_config = {"extra": "ignore"}


class BatchAssessmentDelete(BaseModel):
    assessment_ids: List[str] = Field(..., min_length=1, max_length=50)

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


@router.put(
    "/assessments/{id}",
    summary="更新成熟度评估",
    responses={
        (200): {"description": "评估更新成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "评估不存在"},
    },
)
async def update_assessment(
    id: str,
    assessment_update: MaturityAssessmentUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """更新指定的成熟度评估记录"""
    try:
        record = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == id).first()
        if not record:
            return create_error_response(error="Assessment not found")

        # Update fields if provided
        if assessment_update.assessment_name is not None:
            record.assessment_name = assessment_update.assessment_name
        if assessment_update.status is not None:
            record.status = assessment_update.status.value
        if assessment_update.notes is not None:
            record.notes = assessment_update.notes

        db.commit()
        db.refresh(record)

        logger.info(
            f"Maturity assessment updated | assessment_id={id} | user={current_user.username} "
            f"| ip={get_client_ip(request)}"
        )

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
        logger.error(f"更新评估失败: {e}", exc_info=True)
        return create_error_response(error=f"更新评估失败: {str(e)[:200]}")


@router.patch(
    "/assessments/{id}",
    summary="部分更新成熟度评估",
    responses={
        (200): {"description": "评估更新成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "评估不存在"},
    },
)
async def patch_assessment(
    id: str,
    assessment_patch: MaturityAssessmentPatch,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """部分更新指定的成熟度评估记录"""
    try:
        record = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == id).first()
        if not record:
            return create_error_response(error="Assessment not found")

        # Update fields if provided
        if assessment_patch.assessment_name is not None:
            record.assessment_name = assessment_patch.assessment_name
        if assessment_patch.status is not None:
            record.status = assessment_patch.status.value
        if assessment_patch.notes is not None:
            record.notes = assessment_patch.notes

        db.commit()
        db.refresh(record)

        logger.info(
            f"Maturity assessment patched | assessment_id={id} | user={current_user.username} "
            f"| ip={get_client_ip(request)}"
        )

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
        logger.error(f"部分更新评估失败: {e}", exc_info=True)
        return create_error_response(error=f"部分更新评估失败: {str(e)[:200]}")


@router.get(
    "/assessments/{id}/history",
    summary="获取评估历史",
    responses={
        (200): {"description": "评估历史"},
        (401): {"description": "未授权"},
        (404): {"description": "评估不存在"},
    },
)
async def get_assessment_history(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """获取指定评估的历史记录"""
    try:
        record = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == id).first()
        if not record:
            return create_error_response(error="Assessment not found")

        # Get related assessments by same user with similar name
        history_records = (
            db.query(MaturityAssessmentDB)
            .filter(
                MaturityAssessmentDB.assessed_by == record.assessed_by,
                MaturityAssessmentDB.assessed_at <= record.assessed_at,
            )
            .order_by(MaturityAssessmentDB.assessed_at.desc())
            .limit(10)
            .all()
        )

        result = []
        for hist_record in history_records:
            result.append({
                "id": hist_record.id,
                "assessment_name": hist_record.assessment_name,
                "status": hist_record.status,
                "overall_score": hist_record.overall_score,
                "level": hist_record.level,
                "level_name": hist_record.level_name,
                "assessed_at": hist_record.assessed_at.isoformat() if hist_record.assessed_at else None,
                "assessed_by": hist_record.assessed_by,
            })

        logger.info(f"Assessment history retrieved | assessment_id={id} | count={len(result)}")
        return create_success_response(data=result)
    except Exception as e:
        logger.error(f"获取评估历史失败: {e}", exc_info=True)
        return create_error_response(error=f"获取评估历史失败: {str(e)[:200]}")


@router.post(
    "/assessments/{id}/compare",
    summary="对比评估",
    responses={
        (200): {"description": "评估对比结果"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (404): {"description": "评估不存在"},
    },
)
async def compare_assessments(
    id: str,
    compare_request: AssessmentCompareRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """对比两个成熟度评估"""
    try:
        record1 = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == id).first()
        record2 = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == compare_request.compare_with_id).first()

        if not record1:
            return create_error_response(error="Source assessment not found")
        if not record2:
            return create_error_response(error="Target assessment not found")

        # Calculate differences
        score_diff = record2.overall_score - record1.overall_score
        level_diff = record2.level - record1.level

        # Compare dimensions
        dimensions1 = record1.dimensions or []
        dimensions2 = record2.dimensions or []
        dimension_diffs = []
        for dim1 in dimensions1:
            dim2 = next((d for d in dimensions2 if d.get("name") == dim1.get("name")), None)
            if dim2:
                dimension_diffs.append({
                    "name": dim1.get("name"),
                    "score_before": dim1.get("score", 0),
                    "score_after": dim2.get("score", 0),
                    "difference": dim2.get("score", 0) - dim1.get("score", 0),
                })

        result_data = {
            "assessment1": {
                "id": record1.id,
                "assessment_name": record1.assessment_name,
                "overall_score": record1.overall_score,
                "level": record1.level,
                "level_name": record1.level_name,
                "assessed_at": record1.assessed_at.isoformat() if record1.assessed_at else None,
            },
            "assessment2": {
                "id": record2.id,
                "assessment_name": record2.assessment_name,
                "overall_score": record2.overall_score,
                "level": record2.level,
                "level_name": record2.level_name,
                "assessed_at": record2.assessed_at.isoformat() if record2.assessed_at else None,
            },
            "score_difference": score_diff,
            "level_difference": level_diff,
            "dimension_differences": dimension_diffs,
            "improvement": score_diff > 0,
        }

        logger.info(f"Assessment comparison completed | id1={id} | id2={compare_request.compare_with_id}")
        return create_success_response(data=result_data)
    except Exception as e:
        logger.error(f"对比评估失败: {e}", exc_info=True)
        return create_error_response(error=f"对比评估失败: {str(e)[:200]}")


@router.get(
    "/assessments/trends",
    summary="获取成熟度趋势",
    responses={
        (200): {"description": "成熟度趋势数据"},
        (401): {"description": "未授权"},
    },
)
async def get_maturity_trends(
    days: int = 30,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """获取成熟度评估趋势"""
    try:
        if days < 1 or days > 365:
            return create_error_response(error="Days must be between 1 and 365")

        start_date = datetime.now() - timedelta(days=days)

        records = (
            db.query(MaturityAssessmentDB)
            .filter(MaturityAssessmentDB.assessed_at >= start_date)
            .order_by(MaturityAssessmentDB.assessed_at.asc())
            .all()
        )

        trends = []
        for record in records:
            trends.append({
                "id": record.id,
                "assessment_name": record.assessment_name,
                "overall_score": record.overall_score,
                "level": record.level,
                "level_name": record.level_name,
                "assessed_at": record.assessed_at.isoformat() if record.assessed_at else None,
                "assessed_by": record.assessed_by,
            })

        # Calculate trend statistics
        if len(trends) >= 2:
            first_score = trends[0]["overall_score"]
            last_score = trends[-1]["overall_score"]
            trend_direction = "improving" if last_score > first_score else "declining" if last_score < first_score else "stable"
            avg_score = sum(t["overall_score"] for t in trends) / len(trends)
        else:
            trend_direction = "insufficient_data"
            avg_score = 0

        result_data = {
            "trends": trends,
            "statistics": {
                "total_assessments": len(trends),
                "trend_direction": trend_direction,
                "average_score": round(avg_score, 2),
                "first_score": trends[0]["overall_score"] if trends else 0,
                "last_score": trends[-1]["overall_score"] if trends else 0,
            },
        }

        logger.info(f"Maturity trends retrieved | days={days} | count={len(trends)}")
        return create_success_response(data=result_data)
    except Exception as e:
        logger.error(f"获取成熟度趋势失败: {e}", exc_info=True)
        return create_error_response(error="获取成熟度趋势失败")


@router.post(
    "/assessments/{id}/approve",
    summary="审批评估",
    responses={
        (200): {"description": "评估审批成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "评估不存在"},
    },
)
async def approve_assessment(
    id: str,
    approve_request: AssessmentApproveRequest,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """审批指定的成熟度评估"""
    try:
        if current_user.role != "admin":
            return create_error_response(error="Admin privileges required")

        record = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == id).first()
        if not record:
            return create_error_response(error="Assessment not found")

        # Update status based on approval
        if approve_request.approved:
            record.status = AssessmentStatus.COMPLETED.value
        else:
            record.status = AssessmentStatus.FAILED.value

        # Add approval comment to notes
        if approve_request.comment:
            existing_notes = record.notes or ""
            record.notes = f"{existing_notes}\n[Approval by {current_user.username}: {approve_request.comment}]".strip()

        db.commit()
        db.refresh(record)

        logger.info(
            f"Maturity assessment approved | assessment_id={id} | approved={approve_request.approved} "
            f"| user={current_user.username} | ip={get_client_ip(request)}"
        )

        result_data = {
            "id": record.id,
            "assessment_name": record.assessment_name,
            "status": record.status,
            "overall_score": record.overall_score,
            "level": record.level,
            "level_name": record.level_name,
            "notes": record.notes,
        }

        return create_success_response(data=result_data)
    except Exception as e:
        db.rollback()
        logger.error(f"审批评估失败: {e}", exc_info=True)
        return create_error_response(error=f"审批评估失败: {str(e)[:200]}")


@router.get(
    "/assessments/stats",
    summary="获取评估统计",
    responses={
        (200): {"description": "评估统计数据"},
        (401): {"description": "未授权"},
    },
)
async def get_assessment_stats(
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """获取成熟度评估统计信息"""
    try:
        total_assessments = db.query(MaturityAssessmentDB).count()

        # Count by status
        completed_count = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.status == AssessmentStatus.COMPLETED.value).count()
        in_progress_count = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.status == AssessmentStatus.IN_PROGRESS.value).count()
        failed_count = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.status == AssessmentStatus.FAILED.value).count()

        # Calculate average score
        all_records = db.query(MaturityAssessmentDB).all()
        if all_records:
            avg_score = sum(r.overall_score for r in all_records) / len(all_records)
            avg_level = sum(r.level for r in all_records) / len(all_records)
        else:
            avg_score = 0
            avg_level = 0

        # Count by level
        level_counts = {}
        for record in all_records:
            level_counts[record.level] = level_counts.get(record.level, 0) + 1

        result_data = {
            "total_assessments": total_assessments,
            "status_distribution": {
                "completed": completed_count,
                "in_progress": in_progress_count,
                "failed": failed_count,
            },
            "average_score": round(avg_score, 2),
            "average_level": round(avg_level, 2),
            "level_distribution": level_counts,
        }

        logger.info(f"Assessment stats retrieved | total={total_assessments}")
        return create_success_response(data=result_data)
    except Exception as e:
        logger.error(f"获取评估统计失败: {e}", exc_info=True)
        return create_error_response(error="获取评估统计失败")


@router.post(
    "/assessments/batch",
    status_code=status.HTTP_201_CREATED,
    summary="批量创建评估",
    responses={
        (201): {"description": "批量评估创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def batch_create_assessments(
    batch_request: BatchAssessmentCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """批量创建成熟度评估"""
    try:
        created_assessments = []
        failed_assessments = []

        # Process in batches to avoid rate limiting
        batch_size = 5
        for i in range(0, len(batch_request.assessments), batch_size):
            batch = batch_request.assessments[i:i + batch_size]

            for assessment_create in batch:
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
                    created_assessments.append({
                        "id": record.id,
                        "assessment_name": record.assessment_name,
                        "status": record.status,
                    })
                except Exception as e:
                    db.rollback()
                    failed_assessments.append({
                        "assessment_name": assessment_create.assessment_name,
                        "error": str(e)[:200],
                    })

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(batch_request.assessments):
                import asyncio
                await asyncio.sleep(0.1)

        logger.info(
            f"Batch maturity assessments created | created={len(created_assessments)} "
            f"| failed={len(failed_assessments)} | user={current_user.username} "
            f"| ip={get_client_ip(request)}"
        )

        result_data = {
            "created": created_assessments,
            "failed": failed_assessments,
            "total_requested": len(batch_request.assessments),
            "total_created": len(created_assessments),
            "total_failed": len(failed_assessments),
        }

        return create_success_response(data=result_data)
    except Exception as e:
        db.rollback()
        logger.error(f"批量创建评估失败: {e}", exc_info=True)
        return create_error_response(error="批量创建评估失败")


@router.post(
    "/assessments/batch/delete",
    summary="批量删除评估",
    responses={
        (200): {"description": "批量评估删除成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def batch_delete_assessments(
    batch_request: BatchAssessmentDelete,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """批量删除成熟度评估"""
    try:
        if current_user.role != "admin":
            return create_error_response(error="Admin privileges required")

        deleted_assessments = []
        failed_assessments = []

        # Process in batches to avoid rate limiting
        batch_size = 10
        for i in range(0, len(batch_request.assessment_ids), batch_size):
            batch = batch_request.assessment_ids[i:i + batch_size]

            for assessment_id in batch:
                record = db.query(MaturityAssessmentDB).filter(MaturityAssessmentDB.id == assessment_id).first()
                if record:
                    try:
                        db.delete(record)
                        db.commit()
                        deleted_assessments.append(assessment_id)
                    except Exception as e:
                        db.rollback()
                        failed_assessments.append({
                            "assessment_id": assessment_id,
                            "error": str(e)[:200],
                        })
                else:
                    failed_assessments.append({
                        "assessment_id": assessment_id,
                        "error": "Assessment not found",
                    })

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(batch_request.assessment_ids):
                import asyncio
                await asyncio.sleep(0.1)

        logger.info(
            f"Batch maturity assessments deleted | deleted={len(deleted_assessments)} "
            f"| failed={len(failed_assessments)} | user={current_user.username} "
            f"| ip={get_client_ip(request)}"
        )

        result_data = {
            "deleted": deleted_assessments,
            "failed": failed_assessments,
            "total_requested": len(batch_request.assessment_ids),
            "total_deleted": len(deleted_assessments),
            "total_failed": len(failed_assessments),
        }

        return create_success_response(data=result_data)
    except Exception as e:
        db.rollback()
        logger.error(f"批量删除评估失败: {e}", exc_info=True)
        return create_error_response(error=f"批量删除评估失败: {str(e)[:200]}")
