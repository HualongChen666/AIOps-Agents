# -*- coding: utf-8 -*-
"""SRE maturity assessment REST API."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.maturity_engine import assess_maturity, get_dimension_metadata

router = APIRouter(prefix="/api/v1/maturity", tags=["SRE成熟度评估"])


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
