# -*- coding: utf-8 -*-
"""Team collaboration and on-call management API.

Exposes endpoints for listing teams, retrieving active on-call rosters,
managing handoff notes and escalating incidents.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.team_collaboration_engine import (
    create_handoff,
    escalate_incident,
    get_team_oncall,
    list_dashboards,
    list_handoffs,
    list_teams,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/team-collaboration", tags=["team-collaboration"])


class HandoffCreate(BaseModel):
    """Request model for creating a handoff note."""

    from_user_id: Optional[str] = Field(default="system", description="发送者用户ID")
    to_user_id: Optional[str] = Field(default=None, description="接收者用户ID")
    notes: str = Field(..., min_length=1, description="交接内容")


class EscalateRequest(BaseModel):
    """Request model for escalating an incident."""

    team_id: str = Field(..., min_length=1, description="负责团队ID")
    reason: Optional[str] = Field(default=None, description="升级原因")


@router.get("/teams", summary="列出所有值班团队")
async def get_teams() -> list[dict[str, Any]]:
    """返回所有已配置的SRE团队，包含成员、轮值和升级策略。"""
    try:
        return await list_teams()
    except Exception as exc:
        logger.error("Failed to list teams: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/teams/{id}/oncall", summary="获取团队当前值班人员")
async def get_oncall(id: str) -> dict[str, Any]:
    """根据团队ID计算并返回当前的primary/secondary值班人员。"""
    try:
        oncall = await get_team_oncall(id)
        if not oncall.get("primary"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team has no active rotation",
            )
        return oncall
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Failed to get on-call for team %s: %s", id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/teams/{id}/handoffs",
    status_code=status.HTTP_201_CREATED,
    summary="创建团队交接记录",
)
async def post_handoff(id: str, request: HandoffCreate) -> dict[str, Any]:
    """为指定团队创建一条交接/Handoff记录。"""
    try:
        return await create_handoff(
            id,
            request.from_user_id,
            request.to_user_id,
            request.notes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Failed to create handoff for team %s: %s", id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/teams/{id}/handoffs", summary="获取团队交接记录")
async def get_handoffs(id: str) -> list[dict[str, Any]]:
    """返回指定团队的所有交接记录，按时间倒序排列。"""
    try:
        return await list_handoffs(team_id=id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Failed to list handoffs for team %s: %s", id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/incidents/{incident_id}/escalate", summary="升级事件")
async def post_escalate(incident_id: str, request: EscalateRequest) -> dict[str, Any]:
    """根据团队升级策略将事件升级到下一级负责人。"""
    try:
        return await escalate_incident(
            incident_id,
            request.team_id,
            request.reason,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Failed to escalate incident %s: %s", incident_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/dashboards", summary="获取共享仪表盘")
async def get_dashboards(team_id: Optional[str] = None) -> list[dict[str, Any]]:
    """返回所有共享仪表盘；支持按团队ID过滤。"""
    try:
        return await list_dashboards(team_id=team_id)
    except Exception as exc:
        logger.error("Failed to list dashboards: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
