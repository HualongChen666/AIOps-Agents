# -*- coding: utf-8 -*-
"""Placeholder dashboard router.

Provides a minimal health-like endpoint for the dashboard overview.
"""

from fastapi import APIRouter, Depends

from core.authentication import role_required

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    summary="仪表盘摘要",
    responses={
        200: {
            "description": "仪表盘摘要数据",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "message": "Dashboard placeholder"}
                }
            },
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
async def summary(user=Depends(role_required("user"))):
    return {"status": "ok", "message": "Dashboard placeholder"}
