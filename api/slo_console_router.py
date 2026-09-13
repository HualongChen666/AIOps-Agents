# -*- coding: utf-8 -*-
"""SLO 控制台后端路由（``/api/v1/slo`` 缺失子资源补齐）。

``frontend/app/slo/`` 的若干页面调用后端**尚不存在**的子资源，导致加载即
``error``：

* ``GET/POST /kpi-management`` 与 ``DELETE /kpi-management/{id}`` —— KPI 定义；
* ``GET /kpi-config`` 与 ``PUT /kpi-config/{id}`` —— KPI → 数据源绑定；
* ``GET/POST /sla-management`` —— SLA 合约。

这些属于 SLO 域的真实实体，与 ``slo_router``（SLO 规则）和
``slo_advanced_router``（definitions/objectives/alerts/budgets/reports）**并列不重复**。

存储使用 :class:`core.persistent_store.PersistentStore`（落 ``persistent_records``
表，跨进程/重启不丢），与 ``api/security_console_router.py``、
``api/task_scheduler_router.py`` 等一致。KPI 当前值/趋势由真实
``core.metrics_history.METRICS_HISTORY`` 采样计算（未绑定指标时为 ``null``，
不编造数据）。
"""

from __future__ import annotations

import datetime
import logging
import statistics
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from api.slo_advanced_router import _get_current_user_or_internal
from core.auth_service import User, require_roles
from core.metrics_history import METRICS_HISTORY as metrics_history
from core.persistent_store import PersistentStore
from core.workflow_page_support import tenant_of

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/slo", tags=["SLO/SLA"])

_DOMAIN = "slo_console"


def _store(request: Request, kind: str) -> PersistentStore:
    """Return the tenant-scoped persistent store for *kind*."""
    return PersistentStore(_DOMAIN, kind, tenant_id=tenant_of(request))


def _rows(request: Request, kind: str) -> List[Dict[str, Any]]:
    store = _store(request, kind)
    rows = [dict(r) for r in store.values_list()]
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return rows


def _put(request: Request, kind: str, record: Dict[str, Any]) -> Dict[str, Any]:
    _store(request, kind)[record["id"]] = record
    return record


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# KPI 定义
# --------------------------------------------------------------------------- #
class KPICreate(BaseModel):
    """Request body for creating a KPI."""

    name: str
    category: str = ""
    unit: str = ""
    target: float = 0.0
    # Optional binding to a real metric; when present the current value/trend are
    # computed from METRICS_HISTORY instead of being left null.
    metric: Optional[str] = None
    service: str = "default"


def _kpi_measure(kpi: Dict[str, Any]) -> tuple[Optional[float], str]:
    """Compute the KPI's current value and trend from real metric history."""
    metric = kpi.get("metric")
    if not metric:
        return None, "stable"
    service = kpi.get("service") or "default"
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=7)
    points = metrics_history.query(metric, service, start, end)
    if not points:
        return None, "stable"
    values = [float(p.value) for p in points[-10:]]
    current = round(values[-1], 4)
    if len(values) >= 2:
        half = max(1, len(values) // 2)
        first = statistics.mean(values[:half])
        last = statistics.mean(values[half:])
        if last > first * 1.05:
            trend = "up"
        elif last < first * 0.95:
            trend = "down"
        else:
            trend = "stable"
    else:
        trend = "stable"
    return current, trend


def _serialize_kpi(kpi: Dict[str, Any]) -> Dict[str, Any]:
    current, trend = _kpi_measure(kpi)
    return {
        "id": kpi["id"],
        "name": kpi["name"],
        "category": kpi.get("category", ""),
        "unit": kpi.get("unit", ""),
        "target": kpi.get("target", 0.0),
        "metric": kpi.get("metric"),
        "service": kpi.get("service", "default"),
        "current": current,
        "trend": trend,
        "last_updated": _now_iso(),
    }


@router.get("/kpi-management", summary="列出 KPI")
async def list_kpis(
    request: Request,
    current_user: User = Depends(_get_current_user_or_internal),
) -> Dict[str, Any]:
    """Return all KPI definitions with their live value/trend."""
    return {"kpis": [_serialize_kpi(k) for k in _rows(request, "kpi")]}


@router.post("/kpi-management", summary="创建 KPI", status_code=status.HTTP_201_CREATED)
async def create_kpi(
    request: Request,
    body: KPICreate,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> Dict[str, Any]:
    """Create a KPI definition."""
    record = {
        "id": _new_id("kpi"),
        "name": body.name,
        "category": body.category,
        "unit": body.unit,
        "target": body.target,
        "metric": body.metric,
        "service": body.service,
        "created_at": _now_iso(),
    }
    _put(request, "kpi", record)
    return _serialize_kpi(record)


@router.delete("/kpi-management/{kpi_id}", summary="删除 KPI")
async def delete_kpi(
    kpi_id: str,
    request: Request,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> Dict[str, Any]:
    """Delete a KPI definition and its data-source binding."""
    store = _store(request, "kpi")
    if store.get(kpi_id) is None:
        raise HTTPException(status_code=404, detail="KPI not found")
    del store[kpi_id]
    return {"ok": True, "id": kpi_id}


# --------------------------------------------------------------------------- #
# KPI 配置（KPI → 数据源绑定；随 KPI 自动生成，可编辑）
# --------------------------------------------------------------------------- #
class KPIConfigUpdate(BaseModel):
    """Editable fields of a KPI data-source binding."""

    data_source: Optional[str] = None
    query: Optional[str] = None
    aggregation: Optional[str] = None
    interval: Optional[str] = None
    alert_threshold: Optional[float] = None
    alert_enabled: Optional[bool] = None


def _default_config(kpi: Dict[str, Any]) -> Dict[str, Any]:
    metric = kpi.get("metric") or kpi.get("name")
    return {
        "id": f"cfg-{kpi['id']}",
        "kpi_id": kpi["id"],
        "kpi_name": kpi.get("name", ""),
        "data_source": "metrics_history",
        "query": f"metric={metric} service={kpi.get('service', 'default')}",
        "aggregation": "avg",
        "interval": "5m",
        "alert_threshold": kpi.get("target", 0.0),
        "alert_enabled": False,
        "created_at": kpi.get("created_at", _now_iso()),
    }


def _config_for(request: Request, kpi: Dict[str, Any]) -> Dict[str, Any]:
    stored = _store(request, "kpi_config").get(f"cfg-{kpi['id']}")
    config = _default_config(kpi)
    if stored:
        config.update({k: v for k, v in dict(stored).items() if v is not None})
    return config


@router.get("/kpi-config", summary="列出 KPI 配置")
async def list_kpi_configs(
    request: Request,
    current_user: User = Depends(_get_current_user_or_internal),
) -> Dict[str, Any]:
    """Return the data-source binding for every KPI."""
    configs = [_config_for(request, kpi) for kpi in _rows(request, "kpi")]
    return {"configs": configs}


@router.put("/kpi-config/{config_id}", summary="更新 KPI 配置")
async def update_kpi_config(
    config_id: str,
    request: Request,
    body: KPIConfigUpdate,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> Dict[str, Any]:
    """Persist edits to a KPI data-source binding."""
    kpi_id = config_id[4:] if config_id.startswith("cfg-") else config_id
    kpi = _store(request, "kpi").get(kpi_id)
    if kpi is None:
        raise HTTPException(status_code=404, detail="KPI config not found")
    config = _config_for(request, dict(kpi))
    config.update(body.model_dump(exclude_unset=True, exclude_none=True))
    config["updated_at"] = _now_iso()
    _put(request, "kpi_config", config)
    return config


# --------------------------------------------------------------------------- #
# SLA 合约
# --------------------------------------------------------------------------- #
class SLACreate(BaseModel):
    """Request body for creating an SLA contract."""

    name: str
    customer: str = ""
    service: str = ""
    availability_target: float = Field(99.9, ge=0, le=100)
    response_time_target: float = Field(0.0, ge=0)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


def _sla_status(sla: Dict[str, Any]) -> str:
    today = datetime.date.today().isoformat()
    start = sla.get("start_date") or ""
    end = sla.get("end_date") or ""
    if start and start > today:
        return "pending"
    if end and end < today:
        return "expired"
    return "active"


def _serialize_sla(sla: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": sla["id"],
        "name": sla.get("name", ""),
        "customer": sla.get("customer", ""),
        "service": sla.get("service", ""),
        "availability_target": sla.get("availability_target", 0.0),
        "response_time_target": sla.get("response_time_target", 0.0),
        "start_date": sla.get("start_date", ""),
        "end_date": sla.get("end_date", ""),
        "status": _sla_status(sla),
    }


@router.get("/sla-management", summary="列出 SLA 合约")
async def list_slas(
    request: Request,
    current_user: User = Depends(_get_current_user_or_internal),
) -> Dict[str, Any]:
    """Return all SLA contracts."""
    return {"slas": [_serialize_sla(s) for s in _rows(request, "sla")]}


@router.post("/sla-management", summary="创建 SLA 合约", status_code=status.HTTP_201_CREATED)
async def create_sla(
    request: Request,
    body: SLACreate,
    current_user: User = Depends(require_roles("admin", "operator")),
) -> Dict[str, Any]:
    """Create an SLA contract."""
    record = {
        "id": _new_id("sla"),
        "name": body.name,
        "customer": body.customer,
        "service": body.service,
        "availability_target": body.availability_target,
        "response_time_target": body.response_time_target,
        "start_date": body.start_date or datetime.date.today().isoformat(),
        "end_date": body.end_date or "",
        "created_at": _now_iso(),
    }
    _put(request, "sla", record)
    return _serialize_sla(record)
