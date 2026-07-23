# -*- coding: utf-8 -*-
"""
Advanced AI Capabilities Router
================================

API endpoints for advanced AI capabilities including:
- Predictive analysis
- Adaptive learning
- Natural language interaction
- Explainable AI
- Continuous knowledge learning
"""

import logging
from datetime import datetime
from typing import Any, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai-advanced", tags=["高级AI能力"])
try:
    from core.advanced_ai_capabilities import LearningMode, PredictionType, advanced_ai_capabilities

    ADVANCED_AI_AVAILABLE = True
except ImportError:
    ADVANCED_AI_AVAILABLE = False
    logger.warning("Advanced AI capabilities not available")


class TimeSeriesPredictionRequest(BaseModel):
    """Request for time series prediction"""

    historical_data: list[dict[str, Any]]
    prediction_horizon: int = 24

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"historical_data": [], "prediction_horizon": 0}},
    }


class AnomalyPredictionRequest(BaseModel):
    """Request for anomaly prediction"""

    current_data: dict[str, float]
    historical_baseline: dict[str, list[float]]
    threshold_std: float = 2.0

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"current_data": {}},
            "historical_baseline": {},
            "threshold_std": 0.0,
        },
    }


class AdaptiveLearningRequest(BaseModel):
    """Request for adaptive learning update"""

    new_data: dict[str, Any]
    feedback: dict[str, float]
    learning_mode: str = "online"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"new_data": {}},
            "feedback": {},
            "learning_mode": "example",
        },
    }


class NaturalLanguageRequest(BaseModel):
    """Request for natural language interaction"""

    user_input: str
    conversation_id: str
    user_id: str

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"user_input": "example", "conversation_id": "example", "user_id": "example"}
        },
    }


class DecisionExplanationRequest(BaseModel):
    """Request for decision explanation"""

    decision: str
    decision_context: dict[str, Any]
    decision_type: str = "default"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"decision": "example", "decision_context": {}},
            "decision_type": "example",
        },
    }


class KnowledgeLearningRequest(BaseModel):
    """Request for continuous knowledge learning"""

    experience_data: dict[str, Any]
    outcome: str

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"experience_data": {}}, "outcome": "example"},
    }


@router.post(
    "/predict/time-series",
    summary="时序预测",
    responses={
        (200): {
            "description": "时序预测结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "predictions": [{"timestamp": "2026-07-04T00:00:00Z", "value": 75.5}],
                        "confidence": 0.95,
                    }
                }
            },
        },
        (400): {
            "description": "历史数据不足",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Insufficient historical data, at least 10 data points required",
                        "error_code": "VALIDATION_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def predict_time_series(request: TimeSeriesPredictionRequest) -> dict[str, Any]:
    """
    执行时序预测分析
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    historical_tuples: List[Tuple[datetime, float]] = []
    for item in request.historical_data:
        try:
            timestamp = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
            value = float(item["value"])
            historical_tuples.append((timestamp, value))
        except (ValueError, KeyError) as e:
            logger.warning(f"Skipping invalid historical data point: {e}")
    if len(historical_tuples) < 10:
        raise HTTPException(status_code=400, detail="历史数据不足，至少需要10个数据点")
    prediction = await advanced_ai_capabilities.predict_time_series(
        historical_tuples, request.prediction_horizon
    )
    return {
        "status": "success",
        "prediction": {
            "type": prediction.prediction_type.value,
            "predicted_values": prediction.predicted_values,
            "confidence": prediction.confidence,
            "model_used": prediction.model_used,
            "prediction_timestamp": prediction.prediction_timestamp.isoformat(),
            "metadata": prediction.metadata,
        },
    }


@router.post(
    "/predict/anomalies",
    summary="异常预测",
    responses={
        (200): {
            "description": "异常预测结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "prediction": {
                            "type": "anomaly_detection",
                            "confidence": 0.92,
                            "anomalies": [
                                {"metric": "cpu_usage", "value": 95.5, "is_anomaly": True}
                            ],
                            "total_metrics_analyzed": 10,
                        },
                    }
                }
            },
        },
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def predict_anomalies(request: AnomalyPredictionRequest) -> dict[str, Any]:
    """
    基于统计分析预测异常
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    prediction = await advanced_ai_capabilities.predict_anomalies(
        request.current_data, request.historical_baseline, request.threshold_std
    )
    return {
        "status": "success",
        "prediction": {
            "type": prediction.prediction_type.value,
            "confidence": prediction.confidence,
            "model_used": prediction.model_used,
            "anomalies": prediction.metadata.get("anomalies", []),
            "anomaly_scores": prediction.metadata.get("anomaly_scores", {}),
            "total_metrics_analyzed": prediction.metadata.get("total_metrics", 0),
        },
    }


@router.post(
    "/learning/update",
    summary="自适应学习更新",
    responses={
        (200): {
            "description": "学习更新结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "learning_update": {
                            "update_id": "update-123",
                            "learning_mode": "online",
                            "performance_improvement": 0.15,
                            "new_samples": 100,
                            "model_version": "v2.1",
                        },
                    }
                }
            },
        },
        (400): {
            "description": "无效的学习模式",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Invalid learning mode specified",
                        "error_code": "VALIDATION_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def adaptive_learning_update(request: AdaptiveLearningRequest) -> dict[str, Any]:
    """
    执行自适应学习更新
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    try:
        learning_mode: LearningMode = LearningMode(request.learning_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的学习模式: {request.learning_mode}")
    update = await advanced_ai_capabilities.adaptive_learning_update(
        request.new_data, request.feedback, learning_mode
    )
    return {
        "status": "success",
        "learning_update": {
            "update_id": update.update_id,
            "learning_mode": update.learning_mode.value,
            "performance_improvement": update.performance_improvement,
            "new_samples": update.new_samples,
            "model_version": update.model_version,
            "update_timestamp": update.update_timestamp.isoformat(),
            "metadata": update.metadata,
        },
    }


@router.post(
    "/conversation",
    summary="自然语言交互",
    responses={
        (200): {
            "description": "自然语言响应",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "response": {
                            "conversation_id": "conv-123",
                            "user_message": "系统状态如何？",
                            "ai_response": "系统运行正常，所有服务健康",
                            "intent": "status_query",
                        },
                    }
                }
            },
        },
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def natural_language_interaction(request: NaturalLanguageRequest) -> dict[str, Any]:
    """
    处理自然语言交互，实现对话式运维
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    response: dict[str, Any] = await advanced_ai_capabilities.natural_language_interaction(
        request.user_input, request.conversation_id, request.user_id
    )
    return {"status": "success", "response": response}


@router.get(
    "/conversation/{conversation_id}",
    summary="获取对话上下文",
    responses={
        (200): {
            "description": "对话上下文",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "conversation": {
                            "conversation_id": "conv-123",
                            "user_id": "user-456",
                            "current_intent": "status_query",
                            "message_count": 5,
                            "started_at": "2026-07-03T09:00:00Z",
                            "last_activity": "2026-07-03T09:05:00Z",
                        },
                    }
                }
            },
        },
        (404): {"description": "对话不存在"},
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_conversation_context(conversation_id: str) -> dict[str, Any]:
    """
    获取指定对话的上下文信息
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    if conversation_id not in advanced_ai_capabilities.conversation_contexts:
        raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")
    context = advanced_ai_capabilities.conversation_contexts[conversation_id]
    return {
        "status": "success",
        "conversation": {
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "current_intent": context.current_intent,
            "message_count": len(context.messages),
            "started_at": context.started_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
            "context_variables": context.context_variables,
        },
    }


@router.post(
    "/explain",
    summary="AI决策解释",
    responses={
        (200): {
            "description": "决策解释",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "explanation": {
                            "decision_id": "decision-123",
                            "decision": "restart_service",
                            "confidence": 0.88,
                            "reasoning": "服务响应时间超过阈值，重启可恢复正常",
                            "feature_importance": {"response_time": 0.6, "error_rate": 0.4},
                            "alternative_options": ["scale_up", "optimize"],
                        },
                    }
                }
            },
        },
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def explain_decision(request: DecisionExplanationRequest) -> dict[str, Any]:
    """
    生成AI决策的解释，提供可解释性
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    explanation = await advanced_ai_capabilities.explain_decision(
        request.decision, request.decision_context, request.decision_type
    )
    return {
        "status": "success",
        "explanation": {
            "decision_id": explanation.decision_id,
            "decision": explanation.decision,
            "confidence": explanation.confidence,
            "reasoning": explanation.reasoning,
            "feature_importance": explanation.feature_importance,
            "alternative_options": explanation.alternative_options,
            "decision_timestamp": explanation.decision_timestamp.isoformat(),
        },
    }


@router.post(
    "/knowledge/learn",
    summary="持续知识学习",
    responses={
        (200): {
            "description": "知识学习结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "learning_result": {
                            "knowledge_id": "knowledge-123",
                            "experience_type": "repair_success",
                            "lessons_learned": ["重启服务可解决响应慢问题"],
                            "confidence_score": 0.85,
                            "applied_to_future": True,
                        },
                    }
                }
            },
        },
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def continuous_knowledge_learning(request: KnowledgeLearningRequest) -> dict[str, Any]:
    """
    从经验中持续学习和积累知识
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    result: dict[str, Any] = await advanced_ai_capabilities.continuous_knowledge_learning(
        request.experience_data, request.outcome
    )
    return {"status": "success", "learning_result": result}


@router.get(
    "/knowledge",
    summary="获取知识库内容",
    responses={
        (200): {"description": "知识库内容"},
        (404): {
            "description": "知识类别不存在",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Knowledge category not found",
                        "error_code": "RESOURCE_NOT_FOUND",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_knowledge_base(
    category: Optional[str] = None, limit: int = Query(default=50, ge=1, le=200)
) -> dict[str, Any]:
    """
    获取知识库内容
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    knowledge_base: dict[str, List[dict[str, Any]]] = advanced_ai_capabilities.knowledge_base
    if category:
        if category not in knowledge_base:
            raise HTTPException(status_code=404, detail=f"知识类别 {category} 不存在")
        items = knowledge_base[category][-limit:]
    else:
        all_items: List[dict[str, Any]] = []
        for cat_items in knowledge_base.values():
            all_items.extend(cat_items[-limit:])
        all_items.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
        items = all_items[:limit]
    return {"status": "success", "category": category, "items_count": len(items), "items": items}


@router.get(
    "/statistics",
    summary="获取AI能力统计信息",
    responses={
        (200): {"description": "AI能力统计信息"},
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_ai_statistics() -> dict[str, Any]:
    """
    获取高级AI能力的统计信息
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    summary: dict[str, Any] = advanced_ai_capabilities.get_capabilities_summary()
    return {"status": "success", "capabilities_summary": summary}


@router.get(
    "/learning/history",
    summary="获取学习历史",
    responses={
        (200): {"description": "学习历史记录"},
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_learning_history(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    """
    获取自适应学习的历史记录
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    history = advanced_ai_capabilities.learning_updates[-limit:]
    return {
        "status": "success",
        "total_updates": len(advanced_ai_capabilities.learning_updates),
        "recent_updates": [
            {
                "update_id": update.update_id,
                "learning_mode": update.learning_mode.value,
                "performance_improvement": update.performance_improvement,
                "new_samples": update.new_samples,
                "model_version": update.model_version,
                "update_timestamp": update.update_timestamp.isoformat(),
            }
            for update in history
        ],
    }


@router.get(
    "/predictions/history",
    summary="获取预测历史",
    responses={
        (200): {"description": "预测历史记录"},
        (400): {
            "description": "无效的预测类型",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Invalid prediction type specified",
                        "error_code": "VALIDATION_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_prediction_history(
    prediction_type: Optional[str] = None, limit: int = Query(default=20, ge=1, le=100)
) -> dict[str, Any]:
    """
    获取预测分析的历史记录
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    history: List[Any] = advanced_ai_capabilities.prediction_history
    if prediction_type:
        try:
            pred_type = PredictionType(prediction_type)
            filtered_history: List[Any] = [p for p in history if p.prediction_type == pred_type]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的预测类型: {prediction_type}")
    else:
        filtered_history = history
    recent_predictions: List[Any] = filtered_history[-limit:]
    return {
        "status": "success",
        "total_predictions": len(history),
        "filtered_count": len(filtered_history),
        "recent_predictions": [
            {
                "prediction_type": pred.prediction_type.value,
                "confidence": pred.confidence,
                "model_used": pred.model_used,
                "prediction_timestamp": pred.prediction_timestamp.isoformat(),
                "metadata": pred.metadata,
            }
            for pred in recent_predictions
        ],
    }


@router.delete(
    "/conversation/{conversation_id}",
    summary="删除对话上下文",
    responses={
        (200): {"description": "删除成功"},
        (404): {"description": "对话不存在"},
        (503): {
            "description": "高级AI能力不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Advanced AI capabilities not available",
                        "error_code": "AI_ENGINE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def delete_conversation(conversation_id: str) -> dict[str, Any]:
    """
    删除指定的对话上下文
    """
    if not ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="高级AI能力不可用")
    if conversation_id not in advanced_ai_capabilities.conversation_contexts:
        raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")
    del advanced_ai_capabilities.conversation_contexts[conversation_id]
    return {"status": "success", "message": f"对话 {conversation_id} 已删除"}
