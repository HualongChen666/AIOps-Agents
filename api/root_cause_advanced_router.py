# -*- coding: utf-8 -*-
"""
Root Cause Advanced API Router
高级根因分析API端点
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import (
    RootCauseConclusion,
    RootCauseEvidence,
    RootCauseExperiment,
    RootCauseHypothesis,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/root-cause", tags=["根因分析"])


# ==================== Pydantic Models ====================


class RootCauseAnalysisRequest(BaseModel):
    """根因分析请求"""

    alert: Dict[str, Any] = Field(..., description="告警信息")
    metrics_data: Dict[str, Any] = Field(..., description="指标数据")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alert": {"id": "ALT-001", "title": "高CPU使用率", "level": "critical"},
                "metrics_data": {"cpu_usage": 95, "memory_usage": 80},
                "context": {"service": "api-service"},
            }
        }
    }


class RootCauseHypothesisCreate(BaseModel):
    """创建根因假设请求"""

    alert_id: str = Field(..., description="告警ID")
    root_cause: str = Field(..., description="根因")
    description: Optional[str] = Field(None, description="描述")
    confidence: float = Field(..., ge=0, le=1, description="置信度 (0-1)")
    impact_score: float = Field(..., ge=0, le=1, description="影响分数 (0-1)")
    evidence: Optional[List[str]] = Field(None, description="证据列表")
    causal_path: Optional[List[str]] = Field(None, description="因果路径")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alert_id": "ALT-001",
                "root_cause": "数据库连接池耗尽",
                "description": "数据库连接数达到上限",
                "confidence": 0.85,
                "impact_score": 0.9,
                "evidence": ["数据库连接数: 100/100", "查询响应时间: 5000ms"],
                "causal_path": ["API服务", "数据库", "连接池"],
            }
        }
    }


class RootCauseHypothesisUpdate(BaseModel):
    """更新根因假设请求"""

    root_cause: Optional[str] = Field(None, description="根因")
    description: Optional[str] = Field(None, description="描述")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="置信度")
    impact_score: Optional[float] = Field(None, ge=0, le=1, description="影响分数")
    evidence: Optional[List[str]] = Field(None, description="证据列表")
    causal_path: Optional[List[str]] = Field(None, description="因果路径")
    verification_status: Optional[str] = Field(None, description="验证状态")
    status: Optional[str] = Field(None, description="假设状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {"extra": "ignore"}


class RootCauseHypothesisResponse(BaseModel):
    """根因假设响应"""

    id: str
    alert_id: str
    root_cause: str
    description: Optional[str]
    confidence: float
    impact_score: float
    evidence: Optional[List[str]]
    causal_path: Optional[List[str]]
    verification_status: str
    verification_timestamp: Optional[str]
    status: str
    created_at: str
    updated_at: str
    created_by: Optional[str]
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class RootCauseExperimentCreate(BaseModel):
    """创建根因实验请求"""

    hypothesis_id: str = Field(..., description="假设ID")
    experiment_type: str = Field(..., description="实验类型 (verification, mitigation)")
    description: Optional[str] = Field(None, description="实验描述")
    parameters: Dict[str, Any] = Field(..., description="实验参数")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "hypothesis_id": "HYP-001",
                "experiment_type": "verification",
                "description": "验证数据库连接池是否为根因",
                "parameters": {"action": "increase_pool_size", "new_size": 200},
            }
        }
    }


class RootCauseExperimentUpdate(BaseModel):
    """更新根因实验请求"""

    experiment_type: Optional[str] = Field(None, description="实验类型")
    description: Optional[str] = Field(None, description="实验描述")
    parameters: Optional[Dict[str, Any]] = Field(None, description="实验参数")
    result: Optional[Dict[str, Any]] = Field(None, description="实验结果")
    success: Optional[bool] = Field(None, description="是否成功")
    conclusion: Optional[str] = Field(None, description="结论")
    status: Optional[str] = Field(None, description="实验状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {"extra": "ignore"}


class RootCauseExperimentResponse(BaseModel):
    """根因实验响应"""

    id: str
    hypothesis_id: str
    experiment_type: str
    description: Optional[str]
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    success: Optional[bool]
    conclusion: Optional[str]
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str
    created_by: Optional[str]
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class RootCauseEvidenceResponse(BaseModel):
    """根因证据响应"""

    id: int
    hypothesis_id: str
    evidence_type: str
    evidence_data: Dict[str, Any]
    description: Optional[str]
    strength: float
    collected_at: str
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class RootCauseConclusionCreate(BaseModel):
    """创建根因结论请求"""

    alert_id: str = Field(..., description="告警ID")
    root_cause: str = Field(..., description="根因")
    summary: str = Field(..., description="总结")
    detailed_analysis: Optional[str] = Field(None, description="详细分析")
    confidence: float = Field(..., ge=0, le=1, description="置信度 (0-1)")
    verified_hypothesis_id: Optional[str] = Field(None, description="已验证的假设ID")
    recommended_actions: Optional[List[str]] = Field(None, description="推荐操作")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alert_id": "ALT-001",
                "root_cause": "数据库连接池耗尽",
                "summary": "数据库连接数达到上限导致API服务响应缓慢",
                "detailed_analysis": "详细分析内容...",
                "confidence": 0.9,
                "verified_hypothesis_id": "HYP-001",
                "recommended_actions": ["增加连接池大小", "优化查询"],
            }
        }
    }


class RootCauseConclusionResponse(BaseModel):
    """根因结论响应"""

    id: str
    alert_id: str
    root_cause: str
    summary: str
    detailed_analysis: Optional[str]
    confidence: float
    verified_hypothesis_id: Optional[str]
    recommended_actions: Optional[List[str]]
    status: str
    created_at: str
    updated_at: str
    created_by: Optional[str]
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


# ==================== API Endpoints ====================


@router.post("/analysis", summary="执行根因分析")
async def analyze_root_cause(request: RootCauseAnalysisRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    执行根因分析

    基于告警信息和指标数据生成根因假设
    """
    try:
        alert_id = request.alert.get("id", "unknown")

        # 简单的根因分析逻辑
        # 在实际应用中，这里应该调用更复杂的分析引擎
        hypotheses = []

        # 根据指标数据生成假设
        metrics = request.metrics_data
        if metrics.get("cpu_usage", 0) > 90:
            hypotheses.append(
                {
                    "root_cause": "CPU使用率过高",
                    "description": "CPU使用率超过90%",
                    "confidence": 0.8,
                    "impact_score": 0.9,
                    "evidence": [f"CPU使用率: {metrics.get('cpu_usage')}%"],
                    "causal_path": ["应用服务", "CPU"],
                }
            )

        if metrics.get("memory_usage", 0) > 90:
            hypotheses.append(
                {
                    "root_cause": "内存使用率过高",
                    "description": "内存使用率超过90%",
                    "confidence": 0.75,
                    "impact_score": 0.85,
                    "evidence": [f"内存使用率: {metrics.get('memory_usage')}%"],
                    "causal_path": ["应用服务", "内存"],
                }
            )

        if metrics.get("response_time", 0) > 5000:
            hypotheses.append(
                {
                    "root_cause": "响应时间过长",
                    "description": "API响应时间超过5秒",
                    "confidence": 0.7,
                    "impact_score": 0.8,
                    "evidence": [f"响应时间: {metrics.get('response_time')}ms"],
                    "causal_path": ["API服务", "数据库", "网络"],
                }
            )

        # 如果没有生成假设，创建一个默认假设
        if not hypotheses:
            hypotheses.append(
                {
                    "root_cause": "未知原因",
                    "description": "无法确定具体根因",
                    "confidence": 0.5,
                    "impact_score": 0.5,
                    "evidence": ["需要进一步调查"],
                    "causal_path": [],
                }
            )

        # 保存假设到数据库
        saved_hypotheses = []
        for hyp in hypotheses:
            hyp_id = f"HYP-{uuid.uuid4().hex[:8].upper()}"
            new_hypothesis = RootCauseHypothesis(
                id=hyp_id,
                alert_id=alert_id,
                root_cause=hyp["root_cause"],
                description=hyp["description"],
                confidence=hyp["confidence"],
                impact_score=hyp["impact_score"],
                evidence=hyp["evidence"],
                causal_path=hyp["causal_path"],
                verification_status="pending",
                status="active",
                meta_data=request.context,
                created_by="system",
            )
            db.add(new_hypothesis)
            saved_hypotheses.append(
                {
                    "hypothesis_id": hyp_id,
                    "root_cause": hyp["root_cause"],
                    "confidence": hyp["confidence"],
                    "evidence": hyp["evidence"],
                    "causal_path": hyp["causal_path"],
                    "impact_score": hyp["impact_score"],
                    "verification_status": "pending",
                    "verification_timestamp": None,
                }
            )

        db.commit()

        logger.info(f"根因分析成功: {alert_id}, 生成 {len(hypotheses)} 个假设")

        return {
            "status": "success",
            "alert_id": alert_id,
            "hypotheses": saved_hypotheses,
            "total_hypotheses": len(hypotheses),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"根因分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"根因分析失败: {str(e)}")


@router.get(
    "/hypotheses", response_model=List[RootCauseHypothesisResponse], summary="获取根因假设列表"
)
async def get_root_cause_hypotheses(
    alert_id: Optional[str] = Query(None, description="按告警ID过滤"),
    verification_status: Optional[str] = Query(None, description="按验证状态过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[RootCauseHypothesisResponse]:
    """
    获取根因假设列表

    支持按告警ID、验证状态和状态过滤
    """
    try:
        query = db.query(RootCauseHypothesis)

        if alert_id is not None:
            query = query.filter(RootCauseHypothesis.alert_id == alert_id)
        if verification_status is not None:
            query = query.filter(RootCauseHypothesis.verification_status == verification_status)
        if status is not None:
            query = query.filter(RootCauseHypothesis.status == status)

        hypotheses = (
            query.order_by(RootCauseHypothesis.created_at.desc()).offset(offset).limit(limit).all()
        )

        return [
            RootCauseHypothesisResponse(
                id=hyp.id,
                alert_id=hyp.alert_id,
                root_cause=hyp.root_cause,
                description=hyp.description,
                confidence=hyp.confidence,
                impact_score=hyp.impact_score,
                evidence=hyp.evidence,
                causal_path=hyp.causal_path,
                verification_status=hyp.verification_status,
                verification_timestamp=(
                    hyp.verification_timestamp.isoformat() if hyp.verification_timestamp else None
                ),
                status=hyp.status,
                created_at=hyp.created_at.isoformat() if hyp.created_at else "",
                updated_at=hyp.updated_at.isoformat() if hyp.updated_at else "",
                created_by=hyp.created_by,
                meta_data=hyp.meta_data,
            )
            for hyp in hypotheses
        ]
    except Exception as e:
        logger.error(f"获取根因假设失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因假设失败: {str(e)}")


@router.post("/hypotheses", response_model=RootCauseHypothesisResponse, summary="创建根因假设")
async def create_root_cause_hypothesis(
    hypothesis: RootCauseHypothesisCreate,
    db: Session = Depends(get_db),
) -> RootCauseHypothesisResponse:
    """
    创建新的根因假设

    假设用于记录可能的根因
    """
    try:
        # 创建假设
        hyp_id = f"HYP-{uuid.uuid4().hex[:8].upper()}"
        new_hypothesis = RootCauseHypothesis(
            id=hyp_id,
            alert_id=hypothesis.alert_id,
            root_cause=hypothesis.root_cause,
            description=hypothesis.description,
            confidence=hypothesis.confidence,
            impact_score=hypothesis.impact_score,
            evidence=hypothesis.evidence,
            causal_path=hypothesis.causal_path,
            verification_status="pending",
            status="active",
            meta_data=hypothesis.meta_data,
            created_by="system",
        )

        db.add(new_hypothesis)
        db.commit()
        db.refresh(new_hypothesis)

        logger.info(f"创建根因假设成功: {hyp_id}")

        return RootCauseHypothesisResponse(
            id=new_hypothesis.id,
            alert_id=new_hypothesis.alert_id,
            root_cause=new_hypothesis.root_cause,
            description=new_hypothesis.description,
            confidence=new_hypothesis.confidence,
            impact_score=new_hypothesis.impact_score,
            evidence=new_hypothesis.evidence,
            causal_path=new_hypothesis.causal_path,
            verification_status=new_hypothesis.verification_status,
            verification_timestamp=(
                new_hypothesis.verification_timestamp.isoformat()
                if new_hypothesis.verification_timestamp
                else None
            ),
            status=new_hypothesis.status,
            created_at=new_hypothesis.created_at.isoformat() if new_hypothesis.created_at else "",
            updated_at=new_hypothesis.updated_at.isoformat() if new_hypothesis.updated_at else "",
            created_by=new_hypothesis.created_by,
            meta_data=new_hypothesis.meta_data,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"创建根因假设失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建根因假设失败: {str(e)}")


@router.get(
    "/hypotheses/{hypothesis_id}",
    response_model=RootCauseHypothesisResponse,
    summary="获取单个根因假设",
)
async def get_root_cause_hypothesis(hypothesis_id: str, db: Session = Depends(get_db)) -> RootCauseHypothesisResponse:
    """
    根据ID获取单个根因假设
    """
    try:
        hypothesis = (
            db.query(RootCauseHypothesis).filter(RootCauseHypothesis.id == hypothesis_id).first()
        )
        if not hypothesis:
            raise HTTPException(status_code=404, detail=f"假设 {hypothesis_id} 不存在")

        return RootCauseHypothesisResponse(
            id=hypothesis.id,
            alert_id=hypothesis.alert_id,
            root_cause=hypothesis.root_cause,
            description=hypothesis.description,
            confidence=hypothesis.confidence,
            impact_score=hypothesis.impact_score,
            evidence=hypothesis.evidence,
            causal_path=hypothesis.causal_path,
            verification_status=hypothesis.verification_status,
            verification_timestamp=(
                hypothesis.verification_timestamp.isoformat()
                if hypothesis.verification_timestamp
                else None
            ),
            status=hypothesis.status,
            created_at=hypothesis.created_at.isoformat() if hypothesis.created_at else "",
            updated_at=hypothesis.updated_at.isoformat() if hypothesis.updated_at else "",
            created_by=hypothesis.created_by,
            meta_data=hypothesis.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取根因假设失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因假设失败: {str(e)}")


@router.patch(
    "/hypotheses/{hypothesis_id}",
    response_model=RootCauseHypothesisResponse,
    summary="更新根因假设",
)
async def update_root_cause_hypothesis(
    hypothesis_id: str, hypothesis_update: RootCauseHypothesisUpdate, db: Session = Depends(get_db)
) -> RootCauseHypothesisResponse:
    """
    更新根因假设

    支持部分更新
    """
    try:
        hypothesis = (
            db.query(RootCauseHypothesis).filter(RootCauseHypothesis.id == hypothesis_id).first()
        )
        if not hypothesis:
            raise HTTPException(status_code=404, detail=f"假设 {hypothesis_id} 不存在")

        # 更新字段
        update_data = hypothesis_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(hypothesis, field, value)

        # 如果验证状态改变，更新验证时间
        if hypothesis_update.verification_status == "verified":
            hypothesis.verification_timestamp = datetime.utcnow()

        db.commit()
        db.refresh(hypothesis)

        logger.info(f"更新根因假设成功: {hypothesis_id}")

        return RootCauseHypothesisResponse(
            id=hypothesis.id,
            alert_id=hypothesis.alert_id,
            root_cause=hypothesis.root_cause,
            description=hypothesis.description,
            confidence=hypothesis.confidence,
            impact_score=hypothesis.impact_score,
            evidence=hypothesis.evidence,
            causal_path=hypothesis.causal_path,
            verification_status=hypothesis.verification_status,
            verification_timestamp=(
                hypothesis.verification_timestamp.isoformat()
                if hypothesis.verification_timestamp
                else None
            ),
            status=hypothesis.status,
            created_at=hypothesis.created_at.isoformat() if hypothesis.created_at else "",
            updated_at=hypothesis.updated_at.isoformat() if hypothesis.updated_at else "",
            created_by=hypothesis.created_by,
            meta_data=hypothesis.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新根因假设失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新根因假设失败: {str(e)}")


@router.delete("/hypotheses/{hypothesis_id}", summary="删除根因假设")
async def delete_root_cause_hypothesis(hypothesis_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    删除根因假设
    """
    try:
        hypothesis = (
            db.query(RootCauseHypothesis).filter(RootCauseHypothesis.id == hypothesis_id).first()
        )
        if not hypothesis:
            raise HTTPException(status_code=404, detail=f"假设 {hypothesis_id} 不存在")

        db.delete(hypothesis)
        db.commit()

        logger.info(f"删除根因假设成功: {hypothesis_id}")

        return {"status": "success", "message": f"假设 {hypothesis_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除根因假设失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除根因假设失败: {str(e)}")


@router.get(
    "/experiments", response_model=List[RootCauseExperimentResponse], summary="获取根因实验列表"
)
async def get_root_cause_experiments(
    hypothesis_id: Optional[str] = Query(None, description="按假设ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[RootCauseExperimentResponse]:
    """
    获取根因实验列表

    支持按假设ID和状态过滤
    """
    try:
        query = db.query(RootCauseExperiment)

        if hypothesis_id is not None:
            query = query.filter(RootCauseExperiment.hypothesis_id == hypothesis_id)
        if status is not None:
            query = query.filter(RootCauseExperiment.status == status)

        experiments = (
            query.order_by(RootCauseExperiment.created_at.desc()).offset(offset).limit(limit).all()
        )

        return [
            RootCauseExperimentResponse(
                id=exp.id,
                hypothesis_id=exp.hypothesis_id,
                experiment_type=exp.experiment_type,
                description=exp.description,
                parameters=exp.parameters,
                result=exp.result,
                success=exp.success,
                conclusion=exp.conclusion,
                status=exp.status,
                started_at=exp.started_at.isoformat() if exp.started_at else None,
                completed_at=exp.completed_at.isoformat() if exp.completed_at else None,
                created_at=exp.created_at.isoformat() if exp.created_at else "",
                updated_at=exp.updated_at.isoformat() if exp.updated_at else "",
                created_by=exp.created_by,
                meta_data=exp.meta_data,
            )
            for exp in experiments
        ]
    except Exception as e:
        logger.error(f"获取根因实验失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因实验失败: {str(e)}")


@router.post("/experiments", response_model=RootCauseExperimentResponse, summary="创建根因实验")
async def create_root_cause_experiment(
    experiment: RootCauseExperimentCreate,
    db: Session = Depends(get_db),
) -> RootCauseExperimentResponse:
    """
    创建新的根因实验

    实验用于验证或缓解根因假设
    """
    try:
        # 验证假设是否存在
        hypothesis = (
            db.query(RootCauseHypothesis)
            .filter(RootCauseHypothesis.id == experiment.hypothesis_id)
            .first()
        )
        if not hypothesis:
            raise HTTPException(status_code=404, detail=f"假设 {experiment.hypothesis_id} 不存在")

        # 验证实验类型
        valid_types = ["verification", "mitigation"]
        if experiment.experiment_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的实验类型: {experiment.experiment_type}, 必须是 {valid_types}",
            )

        # 创建实验
        exp_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"
        new_experiment = RootCauseExperiment(
            id=exp_id,
            hypothesis_id=experiment.hypothesis_id,
            experiment_type=experiment.experiment_type,
            description=experiment.description,
            parameters=experiment.parameters,
            status="pending",
            meta_data=experiment.meta_data,
            created_by="system",
        )

        db.add(new_experiment)
        db.commit()
        db.refresh(new_experiment)

        logger.info(f"创建根因实验成功: {exp_id}")

        return RootCauseExperimentResponse(
            id=new_experiment.id,
            hypothesis_id=new_experiment.hypothesis_id,
            experiment_type=new_experiment.experiment_type,
            description=new_experiment.description,
            parameters=new_experiment.parameters,
            result=new_experiment.result,
            success=new_experiment.success,
            conclusion=new_experiment.conclusion,
            status=new_experiment.status,
            started_at=(
                new_experiment.started_at.isoformat() if new_experiment.started_at else None
            ),
            completed_at=(
                new_experiment.completed_at.isoformat() if new_experiment.completed_at else None
            ),
            created_at=new_experiment.created_at.isoformat() if new_experiment.created_at else "",
            updated_at=new_experiment.updated_at.isoformat() if new_experiment.updated_at else "",
            created_by=new_experiment.created_by,
            meta_data=new_experiment.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建根因实验失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建根因实验失败: {str(e)}")


@router.get(
    "/experiments/{experiment_id}",
    response_model=RootCauseExperimentResponse,
    summary="获取单个根因实验",
)
async def get_root_cause_experiment(experiment_id: str, db: Session = Depends(get_db)) -> RootCauseExperimentResponse:
    """
    根据ID获取单个根因实验
    """
    try:
        experiment = (
            db.query(RootCauseExperiment).filter(RootCauseExperiment.id == experiment_id).first()
        )
        if not experiment:
            raise HTTPException(status_code=404, detail=f"实验 {experiment_id} 不存在")

        return RootCauseExperimentResponse(
            id=experiment.id,
            hypothesis_id=experiment.hypothesis_id,
            experiment_type=experiment.experiment_type,
            description=experiment.description,
            parameters=experiment.parameters,
            result=experiment.result,
            success=experiment.success,
            conclusion=experiment.conclusion,
            status=experiment.status,
            started_at=experiment.started_at.isoformat() if experiment.started_at else None,
            completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
            created_at=experiment.created_at.isoformat() if experiment.created_at else "",
            updated_at=experiment.updated_at.isoformat() if experiment.updated_at else "",
            created_by=experiment.created_by,
            meta_data=experiment.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取根因实验失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因实验失败: {str(e)}")


@router.patch(
    "/experiments/{experiment_id}",
    response_model=RootCauseExperimentResponse,
    summary="更新根因实验",
)
async def update_root_cause_experiment(
    experiment_id: str, experiment_update: RootCauseExperimentUpdate, db: Session = Depends(get_db)
) -> RootCauseExperimentResponse:
    """
    更新根因实验

    支持部分更新
    """
    try:
        experiment = (
            db.query(RootCauseExperiment).filter(RootCauseExperiment.id == experiment_id).first()
        )
        if not experiment:
            raise HTTPException(status_code=404, detail=f"实验 {experiment_id} 不存在")

        # 更新字段
        update_data = experiment_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(experiment, field, value)

        # 如果状态变为running，设置开始时间
        if experiment_update.status == "running" and not experiment.started_at:
            experiment.started_at = datetime.utcnow()

        # 如果状态变为completed或failed，设置完成时间
        if experiment_update.status in ["completed", "failed"] and not experiment.completed_at:
            experiment.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(experiment)

        logger.info(f"更新根因实验成功: {experiment_id}")

        return RootCauseExperimentResponse(
            id=experiment.id,
            hypothesis_id=experiment.hypothesis_id,
            experiment_type=experiment.experiment_type,
            description=experiment.description,
            parameters=experiment.parameters,
            result=experiment.result,
            success=experiment.success,
            conclusion=experiment.conclusion,
            status=experiment.status,
            started_at=experiment.started_at.isoformat() if experiment.started_at else None,
            completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
            created_at=experiment.created_at.isoformat() if experiment.created_at else "",
            updated_at=experiment.updated_at.isoformat() if experiment.updated_at else "",
            created_by=experiment.created_by,
            meta_data=experiment.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新根因实验失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新根因实验失败: {str(e)}")


@router.delete("/experiments/{experiment_id}", summary="删除根因实验")
async def delete_root_cause_experiment(experiment_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    删除根因实验
    """
    try:
        experiment = (
            db.query(RootCauseExperiment).filter(RootCauseExperiment.id == experiment_id).first()
        )
        if not experiment:
            raise HTTPException(status_code=404, detail=f"实验 {experiment_id} 不存在")

        db.delete(experiment)
        db.commit()

        logger.info(f"删除根因实验成功: {experiment_id}")

        return {"status": "success", "message": f"实验 {experiment_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除根因实验失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除根因实验失败: {str(e)}")


@router.get("/evidence", response_model=List[RootCauseEvidenceResponse], summary="获取根因证据列表")
async def get_root_cause_evidence(
    hypothesis_id: Optional[str] = Query(None, description="按假设ID过滤"),
    evidence_type: Optional[str] = Query(None, description="按证据类型过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[RootCauseEvidenceResponse]:
    """
    获取根因证据列表

    支持按假设ID和证据类型过滤
    """
    try:
        query = db.query(RootCauseEvidence)

        if hypothesis_id is not None:
            query = query.filter(RootCauseEvidence.hypothesis_id == hypothesis_id)
        if evidence_type is not None:
            query = query.filter(RootCauseEvidence.evidence_type == evidence_type)

        evidence = (
            query.order_by(RootCauseEvidence.collected_at.desc()).offset(offset).limit(limit).all()
        )

        return [
            RootCauseEvidenceResponse(
                id=ev.id,
                hypothesis_id=ev.hypothesis_id,
                evidence_type=ev.evidence_type,
                evidence_data=ev.evidence_data,
                description=ev.description,
                strength=ev.strength,
                collected_at=ev.collected_at.isoformat() if ev.collected_at else "",
                meta_data=ev.meta_data,
            )
            for ev in evidence
        ]
    except Exception as e:
        logger.error(f"获取根因证据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因证据失败: {str(e)}")


@router.get(
    "/conclusions", response_model=List[RootCauseConclusionResponse], summary="获取根因结论列表"
)
async def get_root_cause_conclusions(
    alert_id: Optional[str] = Query(None, description="按告警ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[RootCauseConclusionResponse]:
    """
    获取根因结论列表

    支持按告警ID和状态过滤
    """
    try:
        query = db.query(RootCauseConclusion)

        if alert_id is not None:
            query = query.filter(RootCauseConclusion.alert_id == alert_id)
        if status is not None:
            query = query.filter(RootCauseConclusion.status == status)

        conclusions = (
            query.order_by(RootCauseConclusion.created_at.desc()).offset(offset).limit(limit).all()
        )

        return [
            RootCauseConclusionResponse(
                id=concl.id,
                alert_id=concl.alert_id,
                root_cause=concl.root_cause,
                summary=concl.summary,
                detailed_analysis=concl.detailed_analysis,
                confidence=concl.confidence,
                verified_hypothesis_id=concl.verified_hypothesis_id,
                recommended_actions=concl.recommended_actions,
                status=concl.status,
                created_at=concl.created_at.isoformat() if concl.created_at else "",
                updated_at=concl.updated_at.isoformat() if concl.updated_at else "",
                created_by=concl.created_by,
                meta_data=concl.meta_data,
            )
            for concl in conclusions
        ]
    except Exception as e:
        logger.error(f"获取根因结论失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因结论失败: {str(e)}")


@router.post("/conclusions", response_model=RootCauseConclusionResponse, summary="创建根因结论")
async def create_root_cause_conclusion(
    conclusion: RootCauseConclusionCreate,
    db: Session = Depends(get_db),
) -> RootCauseConclusionResponse:
    """
    创建新的根因结论

    结论用于记录最终的根因分析结果
    """
    try:
        # 创建结论
        concl_id = f"CON-{uuid.uuid4().hex[:8].upper()}"
        new_conclusion = RootCauseConclusion(
            id=concl_id,
            alert_id=conclusion.alert_id,
            root_cause=conclusion.root_cause,
            summary=conclusion.summary,
            detailed_analysis=conclusion.detailed_analysis,
            confidence=conclusion.confidence,
            verified_hypothesis_id=conclusion.verified_hypothesis_id,
            recommended_actions=conclusion.recommended_actions,
            status="draft",
            meta_data=conclusion.meta_data,
            created_by="system",
        )

        db.add(new_conclusion)
        db.commit()
        db.refresh(new_conclusion)

        logger.info(f"创建根因结论成功: {concl_id}")

        return RootCauseConclusionResponse(
            id=new_conclusion.id,
            alert_id=new_conclusion.alert_id,
            root_cause=new_conclusion.root_cause,
            summary=new_conclusion.summary,
            detailed_analysis=new_conclusion.detailed_analysis,
            confidence=new_conclusion.confidence,
            verified_hypothesis_id=new_conclusion.verified_hypothesis_id,
            recommended_actions=new_conclusion.recommended_actions,
            status=new_conclusion.status,
            created_at=new_conclusion.created_at.isoformat() if new_conclusion.created_at else "",
            updated_at=new_conclusion.updated_at.isoformat() if new_conclusion.updated_at else "",
            created_by=new_conclusion.created_by,
            meta_data=new_conclusion.meta_data,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"创建根因结论失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建根因结论失败: {str(e)}")


@router.get(
    "/conclusions/{conclusion_id}",
    response_model=RootCauseConclusionResponse,
    summary="获取单个根因结论",
)
async def get_root_cause_conclusion(conclusion_id: str, db: Session = Depends(get_db)) -> RootCauseConclusionResponse:
    """
    根据ID获取单个根因结论
    """
    try:
        conclusion = (
            db.query(RootCauseConclusion).filter(RootCauseConclusion.id == conclusion_id).first()
        )
        if not conclusion:
            raise HTTPException(status_code=404, detail=f"结论 {conclusion_id} 不存在")

        return RootCauseConclusionResponse(
            id=conclusion.id,
            alert_id=conclusion.alert_id,
            root_cause=conclusion.root_cause,
            summary=conclusion.summary,
            detailed_analysis=conclusion.detailed_analysis,
            confidence=conclusion.confidence,
            verified_hypothesis_id=conclusion.verified_hypothesis_id,
            recommended_actions=conclusion.recommended_actions,
            status=conclusion.status,
            created_at=conclusion.created_at.isoformat() if conclusion.created_at else "",
            updated_at=conclusion.updated_at.isoformat() if conclusion.updated_at else "",
            created_by=conclusion.created_by,
            meta_data=conclusion.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取根因结论失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因结论失败: {str(e)}")


class RootCauseConclusionUpdate(BaseModel):
    """更新根因结论请求"""

    root_cause: Optional[str] = Field(None, description="根因")
    summary: Optional[str] = Field(None, description="总结")
    detailed_analysis: Optional[str] = Field(None, description="详细分析")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="置信度")
    verified_hypothesis_id: Optional[str] = Field(None, description="已验证的假设ID")
    recommended_actions: Optional[List[str]] = Field(None, description="推荐操作")
    status: Optional[str] = Field(None, description="结论状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {"extra": "ignore"}


@router.patch(
    "/conclusions/{conclusion_id}",
    response_model=RootCauseConclusionResponse,
    summary="更新根因结论",
)
async def update_root_cause_conclusion(
    conclusion_id: str, conclusion_update: RootCauseConclusionUpdate, db: Session = Depends(get_db)
) -> RootCauseConclusionResponse:
    """
    更新根因结论

    支持部分更新
    """
    try:
        conclusion = (
            db.query(RootCauseConclusion).filter(RootCauseConclusion.id == conclusion_id).first()
        )
        if not conclusion:
            raise HTTPException(status_code=404, detail=f"结论 {conclusion_id} 不存在")

        # 更新字段
        update_data = conclusion_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conclusion, field, value)

        db.commit()
        db.refresh(conclusion)

        logger.info(f"更新根因结论成功: {conclusion_id}")

        return RootCauseConclusionResponse(
            id=conclusion.id,
            alert_id=conclusion.alert_id,
            root_cause=conclusion.root_cause,
            summary=conclusion.summary,
            detailed_analysis=conclusion.detailed_analysis,
            confidence=conclusion.confidence,
            verified_hypothesis_id=conclusion.verified_hypothesis_id,
            recommended_actions=conclusion.recommended_actions,
            status=conclusion.status,
            created_at=conclusion.created_at.isoformat() if conclusion.created_at else "",
            updated_at=conclusion.updated_at.isoformat() if conclusion.updated_at else "",
            created_by=conclusion.created_by,
            meta_data=conclusion.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新根因结论失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新根因结论失败: {str(e)}")


@router.delete("/conclusions/{conclusion_id}", summary="删除根因结论")
async def delete_root_cause_conclusion(conclusion_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    删除根因结论
    """
    try:
        conclusion = (
            db.query(RootCauseConclusion).filter(RootCauseConclusion.id == conclusion_id).first()
        )
        if not conclusion:
            raise HTTPException(status_code=404, detail=f"结论 {conclusion_id} 不存在")

        db.delete(conclusion)
        db.commit()

        logger.info(f"删除根因结论成功: {conclusion_id}")

        return {"status": "success", "message": f"结论 {conclusion_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除根因结论失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除根因结论失败: {str(e)}")


class RootCauseEvidenceCreate(BaseModel):
    """创建根因证据请求"""

    hypothesis_id: str = Field(..., description="假设ID")
    evidence_type: str = Field(..., description="证据类型 (metrics, logs, traces, events)")
    evidence_data: Dict[str, Any] = Field(..., description="证据数据")
    description: Optional[str] = Field(None, description="描述")
    strength: float = Field(..., ge=0, le=1, description="证据强度 (0-1)")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "hypothesis_id": "HYP-001",
                "evidence_type": "metrics",
                "evidence_data": {"cpu_usage": 95, "memory_usage": 80},
                "description": "CPU和内存使用率异常",
                "strength": 0.9,
            }
        }
    }


@router.post("/evidence", response_model=RootCauseEvidenceResponse, summary="创建根因证据")
async def create_root_cause_evidence(
    evidence: RootCauseEvidenceCreate, db: Session = Depends(get_db)
) -> RootCauseEvidenceResponse:
    """
    创建新的根因证据

    证据用于支持根因假设
    """
    try:
        # 验证假设是否存在
        hypothesis = (
            db.query(RootCauseHypothesis).filter(RootCauseHypothesis.id == evidence.hypothesis_id).first()
        )
        if not hypothesis:
            raise HTTPException(status_code=404, detail=f"假设 {evidence.hypothesis_id} 不存在")

        # 验证证据类型
        valid_types = ["metrics", "logs", "traces", "events", "config", "network"]
        if evidence.evidence_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的证据类型: {evidence.evidence_type}, 必须是 {valid_types}",
            )

        # 创建证据
        new_evidence = RootCauseEvidence(
            hypothesis_id=evidence.hypothesis_id,
            evidence_type=evidence.evidence_type,
            evidence_data=evidence.evidence_data,
            description=evidence.description,
            strength=evidence.strength,
            meta_data=evidence.meta_data,
        )

        db.add(new_evidence)
        db.commit()
        db.refresh(new_evidence)

        logger.info(f"创建根因证据成功: {new_evidence.id}")

        return RootCauseEvidenceResponse(
            id=new_evidence.id,
            hypothesis_id=new_evidence.hypothesis_id,
            evidence_type=new_evidence.evidence_type,
            evidence_data=new_evidence.evidence_data,
            description=new_evidence.description,
            strength=new_evidence.strength,
            collected_at=new_evidence.collected_at.isoformat() if new_evidence.collected_at else "",
            meta_data=new_evidence.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建根因证据失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建根因证据失败: {str(e)}")


@router.get(
    "/evidence/{evidence_id}",
    response_model=RootCauseEvidenceResponse,
    summary="获取单个根因证据",
)
async def get_root_cause_evidence(evidence_id: int, db: Session = Depends(get_db)) -> RootCauseEvidenceResponse:
    """
    根据ID获取单个根因证据
    """
    try:
        evidence = (
            db.query(RootCauseEvidence).filter(RootCauseEvidence.id == evidence_id).first()
        )
        if not evidence:
            raise HTTPException(status_code=404, detail=f"证据 {evidence_id} 不存在")

        return RootCauseEvidenceResponse(
            id=evidence.id,
            hypothesis_id=evidence.hypothesis_id,
            evidence_type=evidence.evidence_type,
            evidence_data=evidence.evidence_data,
            description=evidence.description,
            strength=evidence.strength,
            collected_at=evidence.collected_at.isoformat() if evidence.collected_at else "",
            meta_data=evidence.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取根因证据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因证据失败: {str(e)}")


@router.delete("/evidence/{evidence_id}", summary="删除根因证据")
async def delete_root_cause_evidence(evidence_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    删除根因证据
    """
    try:
        evidence = (
            db.query(RootCauseEvidence).filter(RootCauseEvidence.id == evidence_id).first()
        )
        if not evidence:
            raise HTTPException(status_code=404, detail=f"证据 {evidence_id} 不存在")

        db.delete(evidence)
        db.commit()

        logger.info(f"删除根因证据成功: {evidence_id}")

        return {"status": "success", "message": f"证据 {evidence_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除根因证据失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除根因证据失败: {str(e)}")


class BatchAnalysisRequest(BaseModel):
    """批量根因分析请求"""

    alerts: List[Dict[str, Any]] = Field(..., description="告警列表")
    batch_size: int = Field(default=10, ge=1, le=50, description="批处理大小")
    timeout: int = Field(default=300, ge=60, le=600, description="超时时间（秒）")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alerts": [
                    {"id": "ALT-001", "title": "高CPU使用率", "level": "critical"},
                    {"id": "ALT-002", "title": "高内存使用率", "level": "warning"},
                ],
                "batch_size": 10,
                "timeout": 300,
            }
        }
    }


@router.post("/batch-analyze", summary="批量根因分析")
async def batch_analyze_root_causes(
    request: BatchAnalysisRequest, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    批量执行根因分析

    支持对多个告警进行批量根因分析，自动分批处理以避免速率限制
    """
    try:
        alerts = request.alerts
        batch_size = request.batch_size
        total_alerts = len(alerts)
        results = []
        errors = []

        logger.info(f"开始批量根因分析: {total_alerts} 个告警, 批大小: {batch_size}")

        # 分批处理
        for i in range(0, total_alerts, batch_size):
            batch = alerts[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_alerts + batch_size - 1) // batch_size

            logger.info(f"处理批次 {batch_num}/{total_batches}, 大小: {len(batch)}")

            for alert in batch:
                try:
                    alert_id = alert.get("id", f"unknown-{i}")
                    metrics_data = alert.get("metrics_data", {})
                    context = alert.get("context", {})

                    # 简单的根因分析逻辑
                    hypotheses = []
                    if metrics_data.get("cpu_usage", 0) > 90:
                        hypotheses.append(
                            {
                                "root_cause": "CPU使用率过高",
                                "description": "CPU使用率超过90%",
                                "confidence": 0.8,
                                "impact_score": 0.9,
                                "evidence": [f"CPU使用率: {metrics_data.get('cpu_usage')}%"],
                                "causal_path": ["应用服务", "CPU"],
                            }
                        )

                    if metrics_data.get("memory_usage", 0) > 90:
                        hypotheses.append(
                            {
                                "root_cause": "内存使用率过高",
                                "description": "内存使用率超过90%",
                                "confidence": 0.75,
                                "impact_score": 0.85,
                                "evidence": [f"内存使用率: {metrics_data.get('memory_usage')}%"],
                                "causal_path": ["应用服务", "内存"],
                            }
                        )

                    # 保存假设到数据库
                    saved_hypotheses = []
                    for hyp in hypotheses:
                        hyp_id = f"HYP-{uuid.uuid4().hex[:8].upper()}"
                        new_hypothesis = RootCauseHypothesis(
                            id=hyp_id,
                            alert_id=alert_id,
                            root_cause=hyp["root_cause"],
                            description=hyp["description"],
                            confidence=hyp["confidence"],
                            impact_score=hyp["impact_score"],
                            evidence=hyp["evidence"],
                            causal_path=hyp["causal_path"],
                            verification_status="pending",
                            status="active",
                            meta_data=request.meta_data,
                            created_by="system",
                        )
                        db.add(new_hypothesis)
                        saved_hypotheses.append(
                            {
                                "hypothesis_id": hyp_id,
                                "root_cause": hyp["root_cause"],
                                "confidence": hyp["confidence"],
                            }
                        )

                    results.append(
                        {
                            "alert_id": alert_id,
                            "status": "success",
                            "hypotheses": saved_hypotheses,
                            "total_hypotheses": len(hypotheses),
                        }
                    )
                except Exception as e:
                    logger.error(f"分析告警 {alert.get('id', 'unknown')} 失败: {e}")
                    errors.append({"alert_id": alert.get("id", "unknown"), "error": str(e)})

            # 每批次后提交，避免事务过大
            db.commit()

        logger.info(f"批量根因分析完成: 成功 {len(results)}, 失败 {len(errors)}")

        return {
            "status": "success",
            "total_alerts": total_alerts,
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"批量根因分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量根因分析失败: {str(e)}")


@router.get("/trends", summary="获取根因趋势分析")
async def get_root_cause_trends(
    days: int = Query(default=30, ge=1, le=365, description="分析天数"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取根因趋势分析

    基于历史数据分析根因出现频率和趋势
    """
    try:
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        # 查询指定时间范围内的结论
        conclusions = (
            db.query(RootCauseConclusion)
            .filter(RootCauseConclusion.created_at >= start_date)
            .all()
        )

        # 统计根因频率
        root_cause_counts: Dict[str, int] = {}
        for conclusion in conclusions:
            root_cause = conclusion.root_cause
            root_cause_counts[root_cause] = root_cause_counts.get(root_cause, 0) + 1

        # 按频率排序
        sorted_root_causes = sorted(
            root_cause_counts.items(), key=lambda x: x[1], reverse=True
        )[:limit]

        # 计算趋势
        trends = []
        for root_cause, count in sorted_root_causes:
            # 获取该根因的结论
            related_conclusions = [
                c for c in conclusions if c.root_cause == root_cause
            ]

            # 计算平均置信度
            avg_confidence = sum(c.confidence for c in related_conclusions) / len(
                related_conclusions
            ) if related_conclusions else 0

            trends.append(
                {
                    "root_cause": root_cause,
                    "frequency": count,
                    "percentage": (count / len(conclusions) * 100) if conclusions else 0,
                    "avg_confidence": round(avg_confidence, 2),
                    "total_conclusions": len(related_conclusions),
                }
            )

        logger.info(f"根因趋势分析完成: {len(trends)} 个趋势, 时间范围: {days} 天")

        return {
            "status": "success",
            "analysis_period_days": days,
            "total_conclusions": len(conclusions),
            "trends": trends,
        }
    except Exception as e:
        logger.error(f"获取根因趋势失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取根因趋势失败: {str(e)}")
