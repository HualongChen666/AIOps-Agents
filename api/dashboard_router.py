# -*- coding: utf-8 -*-
"""default_value dashboard router.

Provides a minimal health-like endpoint for the dashboard overview.
"""

import logging

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
                    "example": {"status": "ok", "message": "Dashboard default_value"}
                }
            },
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
async def summary(user=Depends(role_required("user"))):
    """返回仪表盘聚合摘要（主机数、告警数、待审批修复）。"""
    try:
        from config import LINUX_HOSTS

        total_hosts = len(LINUX_HOSTS) if LINUX_HOSTS else 0
        healthy_hosts = total_hosts
        total_alerts = 0
        pending_repairs = 0
        try:
            from core.db_engine import async_count_alerts, async_get_all_pending_approvals

            total_alerts = await async_count_alerts()
            pending_repairs = len(await async_get_all_pending_approvals())
        except Exception as exc:
            logger = logging.getLogger(__name__)
            logger.debug(f"Dashboard summary DB stats unavailable: {exc}")

    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        logging.warning("Suppressed exception", exc_info=True)
        pass

    return {
        "status": "ok",
        "total_hosts": total_hosts,
        "healthy_hosts": healthy_hosts,
        "total_alerts": total_alerts,
        "pending_repairs": pending_repairs,
        "message": "Dashboard default_value",
    }