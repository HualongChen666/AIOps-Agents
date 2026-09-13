# -*- coding: utf-8 -*-
"""Change records API (``/api/v1/change-records``).

Backs ``frontend/app/workflow/change-records``.  Records are the *history view*
of finished change requests from :mod:`core.change_management_engine`:
``implemented`` → completed, ``rolled_back`` → rolled back, ``rejected`` →
failed.  Durations and the actual start/end timestamps are derived from the
request's real audit trail.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from core.change_management_engine import list_requests
from core.change_page_support import record_stats, to_record
from core.workflow_page_support import csv_rows, rows_to_csv, tenant_of

router = APIRouter(prefix="/api/v1/change-records", tags=["变更记录"])

_EXPORT_COLUMNS = [
    "id",
    "changeTitle",
    "type",
    "status",
    "riskLevel",
    "requester",
    "approver",
    "executor",
    "scheduledStart",
    "actualStart",
    "actualEnd",
    "duration",
    "rollbackExecuted",
]


def _as_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        try:
            return date.fromisoformat(value[:10])
        except (TypeError, ValueError):
            return None


async def _all_records(request: Request) -> list[dict[str, Any]]:
    requests = await list_requests(tenant_id=tenant_of(request))
    records = [to_record(r.model_dump(mode="json")) for r in requests]
    return [r for r in records if r is not None]


@router.get("", summary="列出变更记录")
async def list_records(
    request: Request,
    status: Optional[str] = Query(None, description="completed/rolled_back/failed"),
    type: Optional[str] = Query(None, description="routine/standard/emergency"),
    search: Optional[str] = Query(None, description="按变更标题搜索"),
    dateFrom: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    dateTo: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
) -> dict[str, Any]:
    """Return filtered change records plus their summary statistics."""
    try:
        records = await _all_records(request)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="加载变更记录失败") from exc

    if status:
        records = [r for r in records if r["status"] == status]
    if type:
        records = [r for r in records if r["type"] == type]
    if search:
        needle = search.lower()
        records = [r for r in records if needle in str(r["changeTitle"]).lower()]

    start_date, end_date = _as_date(dateFrom), _as_date(dateTo)
    if start_date or end_date:
        filtered = []
        for record in records:
            record_date = _as_date(record.get("completedAt") or record.get("createdAt"))
            if record_date is None:
                continue
            if start_date and record_date < start_date:
                continue
            if end_date and record_date > end_date:
                continue
            filtered.append(record)
        records = filtered

    records.sort(key=lambda r: str(r.get("completedAt") or ""), reverse=True)
    return {"records": records, "stats": record_stats(records)}


@router.get("/export", summary="导出变更记录 CSV")
async def export_records(
    request: Request,
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    dateFrom: Optional[str] = Query(None),
    dateTo: Optional[str] = Query(None),
) -> Response:
    """Download the (filtered) change records as a CSV file."""
    body = await list_records(
        request, status=status, type=type, search=None, dateFrom=dateFrom, dateTo=dateTo
    )
    csv_text = rows_to_csv(list(csv_rows(body["records"], _EXPORT_COLUMNS)), _EXPORT_COLUMNS)
    filename = f"change-records-{date.today().isoformat()}.csv"
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
