# -*- coding: utf-8 -*-
"""
Business Impact API Router
==========================

Exposes real business-impact endpoints backed by the
``core.business_impact_engine`` engine.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from loguru import logger

from core.business_impact_engine import (
    assess_business_impact,
    list_business_impact_services,
    list_business_impact_ux_metrics,
)

router = APIRouter(
    prefix="/api/v1/business-impact",
    tags=["Business Impact"],
)

_VALID_SERVICE_PATTERN = re.compile(r"^[a-zA-Z0-9._\-]+$")


def _validate_service_name(service_name: str) -> str:
    """Validate path parameter service_name to avoid traversal/illegal input."""
    if not service_name or not isinstance(service_name, str):
        raise HTTPException(status_code=422, detail="service_name is required")
    cleaned = service_name.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="service_name cannot be empty")
    if len(cleaned) > 128:
        raise HTTPException(status_code=422, detail="service_name too long")
    if not _VALID_SERVICE_PATTERN.match(cleaned):
        raise HTTPException(
            status_code=422,
            detail="service_name may only contain letters, numbers, dots, underscores and hyphens",
        )
    return cleaned


@router.get(
    "/services",
    summary="List services with business impact fields",
    responses={
        200: {
            "description": "List of business impact services",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {
                                "id": "SVC-001",
                                "name": "payment-service",
                                "category": "核心业务",
                                "impactScore": 9.0,
                                "status": "down",
                            }
                        ],
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_business_impact_services() -> Dict[str, Any]:
    """Return all services with real business impact metrics."""
    try:
        services = await list_business_impact_services()
        return {
            "status": "success",
            "data": services,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Error listing business impact services: {exc}")
        raise HTTPException(status_code=500, detail=f"Business impact listing failed: {str(exc)}")


@router.get(
    "/ux-metrics",
    summary="Get real user experience metrics",
    responses={
        200: {
            "description": "User experience metrics",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {
                                "id": "UX-001",
                                "name": "页面加载时间",
                                "value": 2.5,
                                "change": -5.0,
                                "status": "good",
                            }
                        ],
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_business_ux_metrics() -> Dict[str, Any]:
    """Return real user experience metrics derived from project data."""
    try:
        metrics = await list_business_impact_ux_metrics()
        return {
            "status": "success",
            "data": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Error getting UX metrics: {exc}")
        raise HTTPException(status_code=500, detail=f"UX metrics failed: {str(exc)}")


@router.get(
    "/assess/{service_name}",
    summary="Assess business impact for a single service",
    responses={
        200: {
            "description": "Per-service business impact assessment",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "name": "payment-service",
                            "impactScore": 9.0,
                            "status": "down",
                            "affectedUsers": 8500,
                            "revenueImpact": 120000,
                        },
                    }
                }
            },
        },
        422: {"description": "Invalid service_name"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_business_impact_assessment(service_name: str) -> Dict[str, Any]:
    """Return a detailed business impact assessment for one service."""
    cleaned = _validate_service_name(service_name)
    try:
        assessment = await assess_business_impact(cleaned)
        return {
            "status": "success",
            "data": assessment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Error assessing business impact for {cleaned}: {exc}")
        raise HTTPException(status_code=500, detail=f"Impact assessment failed: {str(exc)}")
