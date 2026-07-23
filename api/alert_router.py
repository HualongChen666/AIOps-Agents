# -*- coding: utf-8 -*-
"""
Alert Router Module
===================

Provides API endpoints for alert management.
Supports alert creation, retrieval, and status updates.

Endpoints:
- GET /api/v1/alerts - Get all alerts
- POST /api/v1/alerts - Create new alert
- GET /api/v1/alerts/{id} - Get alert by ID
- PUT /api/v1/alerts/{id} - Update alert
- DELETE /api/v1/alerts/{id} - Delete alert
"""

import logging
from datetime import datetime
from typing import Any, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from core.alert_service import alert_service

try:
    from core.alert_intelligence import alert_intelligence_engine

    ALERT_INTELLIGENCE_AVAILABLE = True
except ImportError:
    ALERT_INTELLIGENCE_AVAILABLE = False
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["告警管理"])


class RoutingRule(BaseModel):
    """告警路由规则"""

    conditions: dict[str, Any]
    destination: str
    description: Optional[str] = None
    priority: int = 0

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"conditions": {}},
            "destination": "example",
            "description": "example",
            "priority": 0,
        },
    }


class SuppressionRule(BaseModel):
    """告警抑制规则"""

    pattern: str
    reason: str
    suppression_window: int = 300
    enabled: bool = True

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "pattern": "example",
                "reason": "example",
                "suppression_window": 0,
                "enabled": True,
            }
        },
    }


class TrendPredictionRequest(BaseModel):
    """趋势预测请求"""

    metric_name: str
    horizon_hours: int = 24

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"metric_name": "example", "horizon_hours": 0}},
    }


@router.get(
    "/",
    summary="获取告警历史列表",
    responses={
        (200): {
            "description": "告警列表",
            "content": {
                "application/json": {
                    "example": {
                        "alerts": [
                            {
                                "level": "warning",
                                "title": "CPU使用率过高",
                                "desc": "CPU使用率达到85%",
                                "raw_time": "10:30:00",
                                "metric": "cpu",
                                "value": 85.0,
                            }
                        ]
                    }
                }
            },
        },
        (422): {
            "description": "参数校验失败",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Validation failed for limit parameter",
                        "error_code": "VALIDATION_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_alerts(
    limit: int = Query(default=20, ge=1, le=500, description="返回的告警最大条数,范围 1-500")
) -> dict[str, Any]:
    """
    返回最新告警列表(时间倒序,最新在前)
    对应前端:右侧"最新告警事件"面板
    """
    return alert_service.get_alerts(limit)


@router.delete(
    "/",
    summary="清空告警历史(高危操作)",
    responses={
        (200): {
            "description": "清空成功",
            "content": {
                "application/json": {"example": {"status": "success", "cleared_count": 42}}
            },
        },
        (401): {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Authentication required",
                        "error_code": "AUTHENTICATION_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
        (403): {
            "description": "权限不足",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Insufficient privileges to clear alerts",
                        "error_code": "PERMISSION_DENIED",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def clear_alerts_endpoint(request: Request) -> dict[str, Any]:
    """
    清空所有告警记录(内存 + SQLite 双清)

    ⚠️ 高危操作:清空后数据不可恢复,操作将被完整记录到日志
    """
    operator_ip = request.client.host if request.client else "unknown"
    return alert_service.clear_alerts(operator_ip)


@router.get(
    "/intelligence/statistics",
    summary="获取智能告警统计信息",
    responses={
        (200): {
            "description": "统计信息",
            "content": {
                "application/json": {
                    "example": {
                        "total_patterns": 150,
                        "noise_patterns": 25,
                        "cluster_count": 8,
                        "last_updated": "2026-07-02T10:30:00Z",
                    }
                }
            },
        },
        (503): {
            "description": "智能告警引擎不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Alert intelligence engine is not available",
                        "error_code": "ALERT_INTELLIGENCE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_intelligence_statistics() -> dict[str, Any]:
    """
    获取智能告警引擎的统计信息，包括模式数量、噪声模式、集群数量等
    """
    if not ALERT_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="智能告警引擎不可用")
    return alert_intelligence_engine.get_alert_statistics()


@router.get(
    "/intelligence/patterns",
    summary="获取告警模式列表",
    responses={
        (200): {
            "description": "告警模式列表",
            "content": {
                "application/json": {
                    "example": {
                        "total": 150,
                        "patterns": [
                            {
                                "pattern_id": "pattern_001",
                                "signature": "cpu_high",
                                "frequency": 42,
                                "last_seen": "2026-07-02T10:30:00Z",
                                "is_noise": False,
                                "noise_reason": None,
                            }
                        ],
                    }
                }
            },
        },
        (503): {
            "description": "智能告警引擎不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Alert intelligence engine is not available",
                        "error_code": "ALERT_INTELLIGENCE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_alert_patterns(
    limit: int = Query(default=50, ge=1, le=200), include_noise: bool = Query(default=False)
) -> dict[str, Any]:
    """
    获取历史告警模式，用于噪声分析和趋势识别
    """
    if not ALERT_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="智能告警引擎不可用")
    patterns = alert_intelligence_engine.patterns
    filtered_patterns: List[dict[str, Any]] = []
    for pattern_id, pattern in patterns.items():
        if include_noise or not pattern.is_noise:
            filtered_patterns.append(
                {
                    "pattern_id": pattern.pattern_id,
                    "signature": pattern.signature,
                    "frequency": pattern.frequency,
                    "last_seen": pattern.last_seen.isoformat(),
                    "is_noise": pattern.is_noise,
                    "noise_reason": pattern.noise_reason,
                }
            )
    filtered_patterns.sort(key=lambda x: x["frequency"], reverse=True)
    return {"total": len(filtered_patterns), "patterns": filtered_patterns[:limit]}


@router.post(
    "/intelligence/predict",
    summary="预测告警趋势",
    responses={
        (200): {
            "description": "预测结果",
            "content": {
                "application/json": {
                    "example": {
                        "metric_name": "cpu_usage",
                        "predicted_values": [45.2, 48.1, 52.3, 55.8, 49.2],
                        "predicted_anomalies": [{"time": "2026-07-02T12:00:00Z", "value": 85.0}],
                        "confidence": 0.87,
                        "prediction_horizon": 24,
                        "model_used": "prophet",
                    }
                }
            },
        },
        (400): {"description": "历史数据不足或参数错误"},
        (503): {
            "description": "智能告警引擎不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Alert intelligence engine is not available",
                        "error_code": "ALERT_INTELLIGENCE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def predict_alert_trend(request: TrendPredictionRequest) -> dict[str, Any]:
    """
    基于历史数据预测告警趋势，使用Prophet或规则基算法
    """
    if not ALERT_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="智能告警引擎不可用")
    from core.metrics_history import metrics_history

    historical_data: List[Tuple[datetime, float]] = []
    history_dict = metrics_history.to_dict()
    timestamps = history_dict.get("timestamps", [])
    values = history_dict.get(request.metric_name, [])
    if len(timestamps) != len(values):
        raise HTTPException(status_code=400, detail=f"指标 {request.metric_name} 数据不完整")
    for ts, val in zip(timestamps, values):
        try:
            dt = datetime.strptime(ts, "%H:%M:%S")
            historical_data.append((dt, float(val)))
        except (ValueError, TypeError):
            continue
    if len(historical_data) < 10:
        raise HTTPException(status_code=400, detail="历史数据不足，至少需要10个数据点")
    prediction = await alert_intelligence_engine.predict_alert_trends(
        request.metric_name, historical_data, request.horizon_hours
    )
    return {
        "metric_name": prediction.metric_name,
        "predicted_values": prediction.predicted_values,
        "predicted_anomalies": [
            {"time": anom[0].isoformat(), "value": anom[1]}
            for anom in prediction.predicted_anomalies
        ],
        "confidence": prediction.confidence,
        "prediction_horizon": prediction.prediction_horizon,
        "model_used": prediction.model_used,
    }


@router.get(
    "/intelligence/topology",
    summary="获取拓扑上下文",
    responses={
        (200): {
            "description": "拓扑上下文",
            "content": {
                "application/json": {
                    "example": {
                        "nodes": ["web_server", "database", "cache"],
                        "edges": [
                            {"source": "web_server", "target": "database", "type": "query"},
                            {"source": "web_server", "target": "cache", "type": "read"},
                        ],
                    }
                }
            },
        },
        (503): {
            "description": "智能告警引擎不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Alert intelligence engine is not available",
                        "error_code": "ALERT_INTELLIGENCE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_topology_context() -> dict[str, Any]:
    """
    获取当前告警的拓扑上下文，包括节点关系和组件依赖
    """
    if not ALERT_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="智能告警引擎不可用")
    from core.alert_engine import alert_history

    alerts: List[Any] = list(alert_history)[:100]
    topology: dict[str, Any] = alert_intelligence_engine.build_topology_context(alerts)
    return topology


@router.post(
    "/intelligence/routing-rules",
    summary="添加告警路由规则",
    responses={
        (200): {
            "description": "规则添加成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "路由规则已添加",
                        "rule": {
                            "conditions": {"level": "critical"},
                            "destination": "oncall",
                            "description": "紧急告警通知值班人员",
                            "priority": 1,
                        },
                    }
                }
            },
        },
        (503): {
            "description": "智能告警引擎不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Alert intelligence engine is not available",
                        "error_code": "ALERT_INTELLIGENCE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def add_routing_rule(rule: RoutingRule) -> dict[str, Any]:
    """
    添加自定义告警路由规则，实现智能告警分发
    """
    if not ALERT_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="智能告警引擎不可用")
    alert_intelligence_engine.add_routing_rule(rule.dict())
    return {"status": "success", "message": "路由规则已添加", "rule": rule.dict()}


@router.post(
    "/intelligence/suppression-rules",
    summary="添加告警抑制规则",
    responses={
        (200): {
            "description": "规则添加成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "抑制规则已添加",
                        "rule": {
                            "pattern": "cpu_normal",
                            "reason": "正常CPU波动，无需告警",
                            "suppression_window": 300,
                            "enabled": True,
                        },
                    }
                }
            },
        },
        (503): {
            "description": "智能告警引擎不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Alert intelligence engine is not available",
                        "error_code": "ALERT_INTELLIGENCE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def add_suppression_rule(rule: SuppressionRule) -> dict[str, Any]:
    """
    添加告警抑制规则，实现精细化噪声控制
    """
    if not ALERT_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="智能告警引擎不可用")
    alert_intelligence_engine.add_suppression_rule(rule.dict())
    return {"status": "success", "message": "抑制规则已添加", "rule": rule.dict()}


@router.post(
    "/intelligence/route-alerts",
    summary="智能路由告警",
    responses={
        (200): {
            "description": "路由结果",
            "content": {
                "application/json": {
                    "example": {
                        "total_alerts": 50,
                        "routes": {"oncall": 5, "slack": 10, "email": 35},
                        "detailed_routing": {
                            "oncall": [{"level": "critical", "title": "数据库连接失败"}],
                            "slack": [{"level": "warning", "title": "CPU使用率过高"}],
                        },
                    }
                }
            },
        },
        (503): {
            "description": "智能告警引擎不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Alert intelligence engine is not available",
                        "error_code": "ALERT_INTELLIGENCE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def route_alerts_intelligently() -> dict[str, Any]:
    """
    对当前告警进行智能路由，基于拓扑和规则引擎
    """
    if not ALERT_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="智能告警引擎不可用")
    from core.alert_engine import alert_history

    alerts: List[Any] = list(alert_history)[:50]
    routed_alerts: dict[str, List[Any]] = (
        await alert_intelligence_engine.route_alerts_intelligently(alerts)
    )
    return {
        "total_alerts": len(alerts),
        "routes": {route: len(alerts_list) for route, alerts_list in routed_alerts.items()},
        "detailed_routing": routed_alerts,
    }
