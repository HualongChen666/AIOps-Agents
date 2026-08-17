# -*- coding: utf-8 -*-
"""Dashboard router.

Provides a minimal health-like endpoint for the dashboard overview.
"""

from fastapi import APIRouter, Depends

from config import LINUX_HOSTS
from core.alert_engine import alert_history
from core.approval_store import get_pending_only_snapshot
from core.authentication import role_required

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    summary="仪表盘摘要",
    responses={
        200: {
            "description": "仪表盘摘要数据",
            "content": {
                "application/json": {"example": {"status": "ok", "message": "Dashboard summary"}}
            },
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
async def summary(user=Depends(role_required("user"))):
    """返回仪表盘聚合摘要（主机数、告警数、待审批修复）。"""
    total_hosts = len(LINUX_HOSTS) if LINUX_HOSTS else 0
    # 没有离线主机时默认健康数为总数；告警数>0则假设部分主机不健康
    total_alerts = len(alert_history)
    pending_repairs = len(get_pending_only_snapshot())
    healthy_hosts = max(0, total_hosts - min(total_alerts, total_hosts))

    return {
        "status": "ok",
        "total_hosts": total_hosts,
        "healthy_hosts": healthy_hosts,
        "total_alerts": total_alerts,
        "pending_repairs": pending_repairs,
    }
