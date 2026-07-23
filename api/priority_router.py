# -*- coding: utf-8 -*-
"""
Priority API Router
Phase 4 集成: 业务影响优先级路由
"""

import logging
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/priority", tags=["priority"])

# Phase 4 集成: 业务影响优先级
try:
    from core.priority import (
        BusinessImpactAssessor,
        PriorityRanker,
        ResourceAllocator,
        SLAAwareScheduler,
    )

    PRIORITY_AVAILABLE = True
except ImportError:
    PRIORITY_AVAILABLE = False
    logger.warning("Phase 4 priority not available")


_assessor: Optional[BusinessImpactAssessor] = None
_ranker: Optional[PriorityRanker] = None
_sla_scheduler: Optional[SLAAwareScheduler] = None
_resource_allocator: Optional[ResourceAllocator] = None

if PRIORITY_AVAILABLE:
    try:
        _assessor = BusinessImpactAssessor()
        _ranker = PriorityRanker(_assessor)
        _sla_scheduler = SLAAwareScheduler()
        _resource_allocator = ResourceAllocator()
        logger.info("Phase 4 priority components initialized")
    except Exception as e:
        logger.error(f"Failed to initialize priority components: {e}")
        PRIORITY_AVAILABLE = False


@router.get(
    "/health",
    summary="优先级服务健康检查",
    responses={
        200: {
            "description": "健康状态",
            "content": {
                "application/json": {"example": {"status": "healthy", "priority_available": True}}
            },
        },
        503: {"description": "优先级服务不可用"},
    },
)
async def priority_health() -> Dict[str, Any]:
    """Priority health check endpoint"""
    return {
        "status": "healthy" if PRIORITY_AVAILABLE else "degraded",
        "priority_available": PRIORITY_AVAILABLE,
    }


@router.post(
    "/assess",
    summary="评估告警业务影响",
    responses={
        200: {
            "description": "影响评估结果",
            "content": {
                "application/json": {
                    "example": {
                        "service": "api-service",
                        "impact_level": "high",
                        "affected_users": 1000,
                        "revenue_impact": 500.0,
                    }
                }
            },
        },
        503: {"description": "优先级服务不可用"},
        500: {"description": "评估失败"},
    },
)
async def assess_impact(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Assess business impact of an alert"""
    if not PRIORITY_AVAILABLE or not _assessor:
        raise HTTPException(status_code=503, detail="Priority not available")

    try:
        impact = _assessor.assess(
            service=alert.get("service", "unknown"),
            affected_users=alert.get("affected_users", 0),
            revenue_per_minute=alert.get("revenue_per_minute", 0.0),
            sla_violation=alert.get("sla_violation", False),
            context=alert.get("context"),
        )
        # Convert impact object to dict
        if hasattr(impact, "to_dict"):
            return cast(Dict[str, Any], impact.to_dict())
        else:
            return vars(impact)  # type: ignore[return-value]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


@router.post(
    "/rank",
    summary="按优先级排序告警",
    responses={
        200: {
            "description": "排序后的告警列表",
            "content": {
                "application/json": {
                    "example": [
                        {"alert_id": "1", "priority": 1, "score": 0.95},
                        {"alert_id": "2", "priority": 2, "score": 0.85},
                    ]
                }
            },
        },
        503: {"description": "优先级服务不可用"},
        500: {"description": "排序失败"},
    },
)
async def rank_alerts(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank alerts by priority"""
    if not PRIORITY_AVAILABLE or not _ranker:
        raise HTTPException(status_code=503, detail="Priority not available")

    try:
        ranks = _ranker.rank_alerts(alerts)
        return [r.__dict__ for r in ranks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ranking failed: {str(e)}")


@router.get(
    "/sla/status",
    summary="获取服务SLA状态",
    responses={
        200: {
            "description": "SLA状态",
            "content": {
                "application/json": {
                    "example": {
                        "service": "api-service",
                        "sla_compliance": 0.98,
                        "violations": 2,
                        "next_breach": "2026-07-03T10:00:00Z",
                    }
                }
            },
        },
        503: {"description": "优先级服务不可用"},
        500: {"description": "SLA状态检查失败"},
    },
)
async def get_sla_status(service: str) -> Dict[str, Any]:
    """Get SLA status for a service"""
    if not PRIORITY_AVAILABLE or not _sla_scheduler:
        raise HTTPException(status_code=503, detail="Priority not available")

    try:
        return _sla_scheduler.get_sla_status(service)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SLA status check failed: {str(e)}")
