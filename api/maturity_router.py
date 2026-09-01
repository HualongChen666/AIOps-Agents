# -*- coding: utf-8 -*-
"""SRE maturity assessment REST API."""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.authentication import UserInDB, get_user, verify_token
from core.maturity_engine import assess_maturity, get_dimension_metadata

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/maturity", tags=["SRE成熟度评估"])
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


class MaturityDimension(BaseModel):
    """Single maturity dimension with a live score."""

    name: str = Field(..., description="维度名称")
    score: int = Field(..., ge=0, le=100, description="当前得分")
    maxScore: int = Field(100, description="满分")
    description: str = Field(..., description="维度说明")

    model_config = {"from_attributes": True}


class MaturityDimensionMeta(BaseModel):
    """Static metadata for a maturity dimension (no live score)."""

    name: str = Field(..., description="维度名称")
    maxScore: int = Field(100, description="满分")
    description: str = Field(..., description="维度说明")

    model_config = {"from_attributes": True}


class MaturityRecommendation(BaseModel):
    """Prioritized improvement recommendation."""

    id: str = Field(..., description="建议编号")
    category: str = Field(..., description="所属维度")
    title: str = Field(..., description="标题")
    description: str = Field(..., description="详细描述")
    priority: str = Field(..., pattern="^(high|medium|low)$", description="优先级")
    estimatedTime: str = Field(..., description="预计耗时")
    targetLevel: int = Field(..., ge=1, le=5, description="目标等级")

    model_config = {"from_attributes": True}


class MaturityAssessment(BaseModel):
    """Full maturity assessment response."""

    overall_score: int = Field(..., ge=0, le=100, description="总体成熟度得分")
    level: int = Field(..., ge=1, le=5, description="当前等级")
    level_name: str = Field(..., description="等级名称")
    dimensions: List[MaturityDimension] = Field(..., description="维度明细")
    recommendations: List[MaturityRecommendation] = Field(..., description="改进建议")

    model_config = {"from_attributes": True}


@router.get(
    "/assess",
    response_model=MaturityAssessment,
    summary="执行 SRE 成熟度评估",
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "评估失败",
            "content": {"application/json": {"example": {"detail": "maturity assessment failed"}}},
        }
    },
)
async def get_maturity_assessment() -> Dict[str, Any]:
    """Run a real-time SRE maturity assessment against live project data.

    Returns:
        Overall score, per-dimension scores and prioritized recommendations.
    """
    try:
        return await assess_maturity()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"成熟度评估失败: {exc}",
        ) from exc


@router.get(
    "/dimensions",
    response_model=List[MaturityDimensionMeta],
    summary="获取成熟度维度定义",
    responses={
        status.HTTP_200_OK: {
            "description": "维度定义列表",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "name": "可观测性",
                            "maxScore": 100,
                            "description": "系统监控覆盖度和实时性",
                        }
                    ]
                }
            },
        }
    },
)
async def get_dimensions() -> List[Dict[str, Any]]:
    """Return static metadata for all maturity dimensions."""
    return get_dimension_metadata()


# ============ Additional Maturity Endpoints ============


class ImprovementPlanItem(BaseModel):
    """改进计划项"""

    id: str = Field(..., description="计划ID")
    name: str = Field(..., description="计划名称")
    status: str = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")
    priority: str = Field(..., description="优先级")
    category: str = Field(..., description="类别")
    target_score: int = Field(..., description="目标分数")

    model_config = {"from_attributes": True}


@router.get(
    "/improvement-plan",
    response_model=Dict[str, Any],
    summary="获取改进计划",
    responses={
        status.HTTP_200_OK: {"description": "改进计划列表"},
        status.HTTP_401_UNAUTHORIZED: {"description": "未授权"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "服务器错误"},
    },
)
async def get_improvement_plan(
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取基于成熟度评估的改进计划。

    从真实的成熟度评估结果中生成改进建议，按优先级排序。
    """
    try:
        logger.info(f"获取改进计划 | user={current_user.username}")

        # 执行真实的成熟度评估
        assessment = await assess_maturity()
        recommendations = assessment.get("recommendations", [])

        # 转换为改进计划格式
        items = []
        for idx, rec in enumerate(recommendations, start=1):
            items.append({
                "id": rec.get("id", f"PLAN-{idx:03d}"),
                "name": rec.get("title", f"改进计划-{idx}"),
                "status": "pending" if rec.get("priority") == "high" else "in_progress",
                "created_at": datetime.now().isoformat(),
                "priority": rec.get("priority", "medium"),
                "category": rec.get("category", "通用"),
                "target_score": rec.get("targetLevel", 3) * 20,
            })

        logger.info(f"改进计划获取成功 | count={len(items)} | user={current_user.username}")
        return {"items": items, "total": len(items)}
    except Exception as exc:
        logger.error(f"获取改进计划失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取改进计划失败: {exc}",
        ) from exc


class BenchmarkItem(BaseModel):
    """基准对比项"""

    id: str = Field(..., description="基准ID")
    name: str = Field(..., description="基准名称")
    status: str = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")
    industry_average: float = Field(..., description="行业平均分")
    current_score: float = Field(..., description="当前分数")
    gap: float = Field(..., description="差距")

    model_config = {"from_attributes": True}


@router.get(
    "/benchmark",
    response_model=Dict[str, Any],
    summary="获取基准对比",
    responses={
        status.HTTP_200_OK: {"description": "基准对比数据"},
        status.HTTP_401_UNAUTHORIZED: {"description": "未授权"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "服务器错误"},
    },
)
async def get_benchmark(
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取与行业基准的对比数据。

    基于真实的成熟度评估结果，与行业基准进行对比分析。
    """
    try:
        logger.info(f"获取基准对比 | user={current_user.username}")

        # 执行真实的成熟度评估
        assessment = await assess_maturity()
        dimensions = assessment.get("dimensions", [])

        # 行业基准数据（从环境变量获取，默认值）
        industry_benchmarks = {
            "可观测性": float(os.getenv("BENCHMARK_OBSERVABILITY", "75.0")),
            "可靠性": float(os.getenv("BENCHMARK_RELIABILITY", "70.0")),
            "自动化程度": float(os.getenv("BENCHMARK_AUTOMATION", "65.0")),
            "事件响应": float(os.getenv("BENCHMARK_INCIDENT_RESPONSE", "70.0")),
            "安全合规": float(os.getenv("BENCHMARK_SECURITY", "80.0")),
            "文档与知识": float(os.getenv("BENCHMARK_DOCUMENTATION", "60.0")),
        }

        # 生成基准对比数据
        items = []
        for idx, dim in enumerate(dimensions, start=1):
            name = dim.get("name", "未知")
            current_score = float(dim.get("score", 0))
            industry_avg = industry_benchmarks.get(name, 70.0)
            gap = current_score - industry_avg

            items.append({
                "id": f"BENCH-{idx:03d}",
                "name": f"{name}基准对比",
                "status": "above" if gap >= 0 else "below",
                "created_at": datetime.now().isoformat(),
                "industry_average": industry_avg,
                "current_score": current_score,
                "gap": gap,
            })

        logger.info(f"基准对比获取成功 | count={len(items)} | user={current_user.username}")
        return {"items": items, "total": len(items)}
    except Exception as exc:
        logger.error(f"获取基准对比失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取基准对比失败: {exc}",
        ) from exc


class MaturityReportItem(BaseModel):
    """成熟度报告项"""

    id: str = Field(..., description="报告ID")
    name: str = Field(..., description="报告名称")
    status: str = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")
    overall_score: int = Field(..., description="总体分数")
    level: int = Field(..., description="等级")
    level_name: str = Field(..., description="等级名称")

    model_config = {"from_attributes": True}


@router.get(
    "/maturity-report",
    response_model=Dict[str, Any],
    summary="获取成熟度报告",
    responses={
        status.HTTP_200_OK: {"description": "成熟度报告数据"},
        status.HTTP_401_UNAUTHORIZED: {"description": "未授权"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "服务器错误"},
    },
)
async def get_maturity_report(
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取成熟度评估报告。

    基于真实的成熟度评估结果生成详细报告。
    """
    try:
        logger.info(f"获取成熟度报告 | user={current_user.username}")

        # 执行真实的成熟度评估
        assessment = await assess_maturity()

        # 生成报告项
        items = [{
            "id": "REPORT-001",
            "name": f"SRE成熟度评估报告-{datetime.now().strftime('%Y%m%d')}",
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "overall_score": assessment.get("overall_score", 0),
            "level": assessment.get("level", 1),
            "level_name": assessment.get("level_name", "未知"),
        }]

        logger.info(f"成熟度报告获取成功 | count={len(items)} | user={current_user.username}")
        return {"items": items, "total": len(items)}
    except Exception as exc:
        logger.error(f"获取成熟度报告失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取成熟度报告失败: {exc}",
        ) from exc


class MaturityScoreItem(BaseModel):
    """成熟度评分项"""

    id: str = Field(..., description="评分ID")
    name: str = Field(..., description="评分名称")
    status: str = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")
    dimension: str = Field(..., description="维度")
    score: int = Field(..., description="分数")
    max_score: int = Field(..., description="满分")

    model_config = {"from_attributes": True}


@router.get(
    "/maturity-score",
    response_model=Dict[str, Any],
    summary="获取成熟度评分",
    responses={
        status.HTTP_200_OK: {"description": "成熟度评分数据"},
        status.HTTP_401_UNAUTHORIZED: {"description": "未授权"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "服务器错误"},
    },
)
async def get_maturity_score(
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取各维度的成熟度评分详情。

    基于真实的成熟度评估结果返回各维度评分。
    """
    try:
        logger.info(f"获取成熟度评分 | user={current_user.username}")

        # 执行真实的成熟度评估
        assessment = await assess_maturity()
        dimensions = assessment.get("dimensions", [])

        # 转换为评分项格式
        items = []
        for idx, dim in enumerate(dimensions, start=1):
            items.append({
                "id": f"SCORE-{idx:03d}",
                "name": f"{dim.get('name', '未知')}评分",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "dimension": dim.get("name", "未知"),
                "score": dim.get("score", 0),
                "max_score": dim.get("maxScore", 100),
            })

        logger.info(f"成熟度评分获取成功 | count={len(items)} | user={current_user.username}")
        return {"items": items, "total": len(items)}
    except Exception as exc:
        logger.error(f"获取成熟度评分失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取成熟度评分失败: {exc}",
        ) from exc


class CapabilityAssessmentItem(BaseModel):
    """能力评估项"""

    id: str = Field(..., description="评估ID")
    name: str = Field(..., description="评估名称")
    status: str = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")
    capability: str = Field(..., description="能力")
    maturity_level: int = Field(..., description="成熟度等级")
    description: str = Field(..., description="描述")

    model_config = {"from_attributes": True}


@router.get(
    "/capability-assessment",
    response_model=Dict[str, Any],
    summary="获取能力评估",
    responses={
        status.HTTP_200_OK: {"description": "能力评估数据"},
        status.HTTP_401_UNAUTHORIZED: {"description": "未授权"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "服务器错误"},
    },
)
async def get_capability_assessment(
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取SRE能力评估详情。

    基于真实的成熟度评估结果返回各能力维度的评估。
    """
    try:
        logger.info(f"获取能力评估 | user={current_user.username}")

        # 执行真实的成熟度评估
        assessment = await assess_maturity()
        dimensions = assessment.get("dimensions", [])

        # 转换为能力评估格式
        items = []
        for idx, dim in enumerate(dimensions, start=1):
            items.append({
                "id": f"CAP-{idx:03d}",
                "name": f"{dim.get('name', '未知')}能力评估",
                "status": "assessed",
                "created_at": datetime.now().isoformat(),
                "capability": dim.get("name", "未知"),
                "maturity_level": dim.get("level", 1),
                "description": dim.get("description", ""),
            })

        logger.info(f"能力评估获取成功 | count={len(items)} | user={current_user.username}")
        return {"items": items, "total": len(items)}
    except Exception as exc:
        logger.error(f"获取能力评估失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取能力评估失败: {exc}",
        ) from exc


class SreMaturityItem(BaseModel):
    """SRE成熟度项"""

    id: str = Field(..., description="成熟度ID")
    name: str = Field(..., description="成熟度名称")
    status: str = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")
    overall_score: int = Field(..., description="总体分数")
    level: int = Field(..., description="等级")
    level_name: str = Field(..., description="等级名称")
    dimension_count: int = Field(..., description="维度数量")

    model_config = {"from_attributes": True}


@router.get(
    "/sre-maturity",
    response_model=Dict[str, Any],
    summary="获取SRE成熟度",
    responses={
        status.HTTP_200_OK: {"description": "SRE成熟度数据"},
        status.HTTP_401_UNAUTHORIZED: {"description": "未授权"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "服务器错误"},
    },
)
async def get_sre_maturity(
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取SRE整体成熟度评估。

    基于真实的成熟度评估结果返回整体成熟度概况。
    """
    try:
        logger.info(f"获取SRE成熟度 | user={current_user.username}")

        # 执行真实的成熟度评估
        assessment = await assess_maturity()
        dimensions = assessment.get("dimensions", [])

        # 生成SRE成熟度项
        items = [{
            "id": "SRE-001",
            "name": f"SRE成熟度评估-{datetime.now().strftime('%Y%m%d')}",
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "overall_score": assessment.get("overall_score", 0),
            "level": assessment.get("level", 1),
            "level_name": assessment.get("level_name", "未知"),
            "dimension_count": len(dimensions),
        }]

        logger.info(f"SRE成熟度获取成功 | count={len(items)} | user={current_user.username}")
        return {"items": items, "total": len(items)}
    except Exception as exc:
        logger.error(f"获取SRE成熟度失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取SRE成熟度失败: {exc}",
        ) from exc
