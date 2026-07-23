# -*- coding: utf-8 -*-
"""
Root Cause Analysis Router
=========================

API endpoints for advanced root cause analysis including:
- Real-time topology discovery
- Cross-layer tracking
- Historical pattern matching
- Root cause prediction
- Automated verification
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/root-cause", tags=["根因分析"])
try:
    from core.root_cause_intelligence import root_cause_intelligence_engine

    ROOT_CAUSE_INTELLIGENCE_AVAILABLE = True
except ImportError:
    ROOT_CAUSE_INTELLIGENCE_AVAILABLE = False
    logger.warning("Root cause intelligence engine not available")


class TopologyDiscoveryRequest(BaseModel):
    """Request for topology discovery"""

    metrics_data: dict[str, Any]
    include_dependencies: bool = True

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"metrics_data": {}}, "include_dependencies": True},
    }


class SymptomMatchingRequest(BaseModel):
    """Request for symptom matching"""

    symptoms: dict[str, Any]
    similarity_threshold: float = 0.5

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"symptoms": {}}, "similarity_threshold": 0.0},
    }


class RootCauseAnalysisRequest(BaseModel):
    """Request for root cause analysis"""

    alert: dict[str, Any]
    metrics_data: dict[str, Any]
    context: Optional[dict[str, Any]] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"alert": {}}, "metrics_data": {}, "context": "example"},
    }


class RootCausePredictionRequest(BaseModel):
    """Request for root cause prediction"""

    current_state: dict[str, Any]
    prediction_horizon: int = 60

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"current_state": {}}, "prediction_horizon": 0},
    }


class VerificationRequest(BaseModel):
    """Request for hypothesis verification"""

    hypothesis_id: str
    verification_data: dict[str, Any]

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"hypothesis_id": "example", "verification_data": {}}},
    }


class PatternLearningRequest(BaseModel):
    """Request for pattern learning"""

    symptoms: dict[str, Any]
    root_cause: str
    resolution_time: float
    effectiveness: float

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"symptoms": {}},
            "root_cause": "example",
            "resolution_time": 0.0,
            "effectiveness": 0.0,
        },
    }


@router.get(
    "/topology",
    summary="获取当前拓扑结构",
    responses={(200): {"description": "拓扑结构"}, (503): {"description": "根因智能引擎不可用"}},
)
async def get_topology_structure() -> dict[str, Any]:
    """
    获取当前系统拓扑结构，包括节点、层级和依赖关系
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    topology_summary: dict[str, Any] = root_cause_intelligence_engine._get_topology_summary()
    return {
        "status": "success",
        "topology": topology_summary,
        "nodes": {
            node_id: {
                "name": node.name,
                "layer": node.layer.value,
                "health_status": node.health_status,
                "dependencies": list(node.dependencies),
                "dependents": list(node.dependents),
                "last_updated": node.last_updated.isoformat(),
            }
            for node_id, node in root_cause_intelligence_engine.topology_graph.items()
        },
    }


@router.post(
    "/topology/discover",
    summary="实时拓扑发现",
    responses={
        (200): {"description": "拓扑发现结果"},
        (503): {"description": "根因智能引擎不可用"},
    },
)
async def discover_topology_realtime(request: TopologyDiscoveryRequest) -> dict[str, Any]:
    """
    基于当前指标数据执行实时拓扑发现
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    discovery_result: dict[str, Any] = (
        await root_cause_intelligence_engine.discover_topology_realtime(request.metrics_data)
    )
    return {"status": "success", "discovery_result": discovery_result}


@router.post(
    "/cross-layer-track",
    summary="跨层级追踪",
    responses={(200): {"description": "因果路径"}, (503): {"description": "根因智能引擎不可用"}},
)
async def perform_cross_layer_tracking(
    alert: dict[str, Any], max_depth: int = Query(default=5, ge=1, le=10)
) -> dict[str, Any]:
    """
    执行跨层级追踪，找到完整的因果路径
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    causal_path: List[str] = await root_cause_intelligence_engine.perform_cross_layer_tracking(
        alert, max_depth
    )
    return {
        "status": "success",
        "causal_path": causal_path,
        "path_length": len(causal_path),
        "alert_id": alert.get("id", "unknown"),
    }


@router.post(
    "/patterns/match",
    summary="历史模式匹配",
    responses={(200): {"description": "匹配结果"}, (503): {"description": "根因智能引擎不可用"}},
)
async def match_historical_patterns(request: SymptomMatchingRequest) -> dict[str, Any]:
    """
    将当前症状与历史模式进行匹配
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    matched_patterns: List[Any] = await root_cause_intelligence_engine.match_historical_patterns(
        request.symptoms
    )
    filtered_patterns: List[Any] = [
        pattern
        for pattern in matched_patterns
        if pattern.confidence >= request.similarity_threshold
    ]
    return {
        "status": "success",
        "matched_patterns": [
            {
                "pattern_id": pattern.pattern_id,
                "root_cause": pattern.root_cause,
                "confidence": pattern.confidence,
                "frequency": pattern.frequency,
                "last_occurrence": pattern.last_occurrence.isoformat(),
                "resolution_time_avg": pattern.resolution_time_avg,
                "effectiveness_score": pattern.effectiveness_score,
            }
            for pattern in filtered_patterns
        ],
        "total_matches": len(filtered_patterns),
    }


@router.post("/patterns/learn", summary="学习历史模式")
async def learn_historical_pattern(request: PatternLearningRequest) -> dict[str, Any]:
    """
    从已解决的故障中学习新的历史模式
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    root_cause_intelligence_engine.learn_historical_pattern(
        request.symptoms, request.root_cause, request.resolution_time, request.effectiveness
    )
    return {"status": "success", "message": "历史模式已学习", "root_cause": request.root_cause}


@router.get("/patterns", summary="获取历史模式列表")
async def get_historical_patterns(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """
    获取所有历史模式，用于分析和学习
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    patterns: List[Any] = list(root_cause_intelligence_engine.historical_patterns.values())
    patterns.sort(key=lambda p: (p.frequency, p.confidence), reverse=True)
    return {
        "status": "success",
        "total_patterns": len(patterns),
        "patterns": [
            {
                "pattern_id": pattern.pattern_id,
                "root_cause": pattern.root_cause,
                "confidence": pattern.confidence,
                "frequency": pattern.frequency,
                "last_occurrence": pattern.last_occurrence.isoformat(),
                "resolution_time_avg": pattern.resolution_time_avg,
                "effectiveness_score": pattern.effectiveness_score,
            }
            for pattern in patterns[:limit]
        ],
    }


@router.post("/analyze", summary="增强根因分析")
async def analyze_root_causes_enhanced(request: RootCauseAnalysisRequest) -> dict[str, Any]:
    """
    执行增强的根因分析，结合多种算法
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    hypotheses: List[Any] = await root_cause_intelligence_engine.analyze_root_causes_enhanced(
        request.alert, request.metrics_data, request.context
    )
    return {
        "status": "success",
        "alert_id": request.alert.get("id", "unknown"),
        "hypotheses": [
            {
                "hypothesis_id": h.hypothesis_id,
                "root_cause": h.root_cause,
                "confidence": h.confidence,
                "evidence": h.evidence,
                "causal_path": h.causal_path,
                "impact_score": h.impact_score,
                "verification_status": h.verification_status,
                "verification_timestamp": (
                    h.verification_timestamp.isoformat() if h.verification_timestamp else None
                ),
            }
            for h in hypotheses
        ],
        "total_hypotheses": len(hypotheses),
    }


@router.post("/predict", summary="根因预测")
async def predict_root_causes(request: RootCausePredictionRequest) -> dict[str, Any]:
    """
    预测未来可能出现的根因
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    predictions: dict[str, Any] = await root_cause_intelligence_engine.predict_root_causes(
        request.current_state, request.prediction_horizon
    )
    return {"status": "success", "predictions": predictions}


@router.post("/verify", summary="验证根因假设")
async def verify_root_cause_hypothesis(request: VerificationRequest) -> dict[str, Any]:
    """
    自动验证根因假设
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    hypothesis = root_cause_intelligence_engine.active_hypotheses.get(request.hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail=f"假设 {request.hypothesis_id} 不存在")
    verification_result: dict[str, Any] = await root_cause_intelligence_engine.verify_root_cause(
        hypothesis, request.verification_data
    )
    return {"status": "success", "verification_result": verification_result}


@router.get("/statistics", summary="获取根因分析统计信息")
async def get_root_cause_statistics() -> dict[str, Any]:
    """
    获取根因分析的统计信息和性能指标
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    statistics: dict[str, Any] = root_cause_intelligence_engine.get_analysis_statistics()
    return {"status": "success", "statistics": statistics}


@router.get("/hypotheses", summary="获取活跃假设列表")
async def get_active_hypotheses(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    """
    获取当前活跃的根因假设
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    hypotheses: List[Any] = list(root_cause_intelligence_engine.active_hypotheses.values())
    hypotheses.sort(key=lambda h: h.confidence, reverse=True)
    return {
        "status": "success",
        "total_hypotheses": len(hypotheses),
        "hypotheses": [
            {
                "hypothesis_id": h.hypothesis_id,
                "root_cause": h.root_cause,
                "confidence": h.confidence,
                "evidence": h.evidence,
                "causal_path": h.causal_path,
                "impact_score": h.impact_score,
                "verification_status": h.verification_status,
                "verification_timestamp": (
                    h.verification_timestamp.isoformat() if h.verification_timestamp else None
                ),
            }
            for h in hypotheses[:limit]
        ],
    }


@router.delete("/hypotheses/{hypothesis_id}", summary="删除根因假设")
async def delete_hypothesis(hypothesis_id: str) -> dict[str, Any]:
    """
    删除指定的根因假设
    """
    if not ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="根因智能引擎不可用")
    if hypothesis_id not in root_cause_intelligence_engine.active_hypotheses:
        raise HTTPException(status_code=404, detail=f"假设 {hypothesis_id} 不存在")
    hypothesis = root_cause_intelligence_engine.active_hypotheses.pop(hypothesis_id)
    root_cause_intelligence_engine.hypothesis_history.append(hypothesis)
    return {"status": "success", "message": f"假设 {hypothesis_id} 已删除并移至历史记录"}
