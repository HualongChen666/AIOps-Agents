# -*- coding: utf-8 -*-
"""Dashboard router.

Provides a minimal health-like endpoint for the dashboard overview.
"""

from typing import List

from fastapi import APIRouter, Depends

from config import LINUX_HOSTS
from core.alert_engine import alert_history
from core.approval_store import get_pending_only_snapshot
from core.authentication import role_required

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

#: Alert levels that mark the owning host as unhealthy.
_UNHEALTHY_LEVELS = {"critical", "high", "error"}


def _configured_host_names() -> List[str]:
    """Names of the hosts configured for monitoring (``LINUX_HOSTS``)."""
    hosts = LINUX_HOSTS.get("hosts", []) if isinstance(LINUX_HOSTS, dict) else LINUX_HOSTS
    names: List[str] = []
    for host in hosts or []:
        if isinstance(host, dict):
            name = host.get("name") or host.get("host")
        else:
            name = host
        if name:
            names.append(str(name))
    return names


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
    """返回仪表盘聚合摘要（主机数、告警数、待审批修复）。

    ``healthy_hosts`` is derived from the actual alert history: a configured
    host counts as unhealthy only when it currently owns a critical/high alert.
    """
    host_names = _configured_host_names()
    total_hosts = len(host_names)
    total_alerts = len(alert_history)
    pending_repairs = len(get_pending_only_snapshot())

    unhealthy_hosts = {
        str(alert.get("host"))
        for alert in alert_history
        if alert.get("host")
        and str(alert.get("level", "")).strip().lower() in _UNHEALTHY_LEVELS
    }
    healthy_hosts = sum(1 for name in host_names if name not in unhealthy_hosts)

    return {
        "status": "ok",
        "total_hosts": total_hosts,
        "healthy_hosts": healthy_hosts,
        "unhealthy_hosts": total_hosts - healthy_hosts,
        "total_alerts": total_alerts,
        "pending_repairs": pending_repairs,
    }
