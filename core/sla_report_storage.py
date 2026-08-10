# -*- coding: utf-8 -*-
"""
core/sla_report_storage.py
==========================

持久化存储由 ``generate_sla_report`` 生成的 SLA 合规报告。

设计原则:
- 每个报告都有唯一 id，生成时间 created_at。
- 默认 30 天过期；列出/生成时自动清理过期报告。
- 支持按 period 过滤、按 id 查询和删除。
"""

from __future__ import annotations

import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REPORTS_FILE = _DATA_DIR / "sla_reports.json"

DEFAULT_MAX_AGE_DAYS = 30


def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> dict[str, Any]:
    if not _REPORTS_FILE.exists():
        return {"reports": []}
    try:
        with _REPORTS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load SLA reports from %s: %s", _REPORTS_FILE, exc)
        return {"reports": []}


def _save(data: dict[str, Any]) -> None:
    _ensure_data_dir()
    with _REPORTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _is_expired(report: dict[str, Any], max_age_days: int) -> bool:
    created = report.get("created_at")
    if not created:
        return True
    try:
        created_dt = datetime.datetime.fromisoformat(created)
    except ValueError:
        return True
    return datetime.datetime.utcnow() - created_dt > datetime.timedelta(days=max_age_days)


def prune_reports(max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> int:
    """Remove reports older than max_age_days. Returns number removed."""
    data = _load()
    before = len(data["reports"])
    data["reports"] = [r for r in data["reports"] if not _is_expired(r, max_age_days)]
    after = len(data["reports"])
    if before != after:
        _save(data)
        logger.info("Pruned %d expired SLA reports", before - after)
    return before - after


def save_reports(reports: list[dict[str, Any]]) -> list[str]:
    """Persist generated reports and return their ids."""
    prune_reports()
    data = _load()
    ids: list[str] = []
    now = datetime.datetime.utcnow().isoformat()
    for report in reports:
        report_id = str(uuid.uuid4())
        report["id"] = report_id
        report["created_at"] = now
        data["reports"].append(report)
        ids.append(report_id)
    _save(data)
    logger.info("Saved %d SLA reports", len(ids))
    return ids


def list_reports(period: Optional[str] = None,
                 max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> list[dict[str, Any]]:
    """Return non-expired reports, optionally filtered by period."""
    prune_reports(max_age_days)
    data = _load()
    reports = [r for r in data["reports"] if not _is_expired(r, max_age_days)]
    if period is not None:
        reports = [r for r in reports if r.get("period") == period]
    # 最新的排在前面
    return sorted(reports, key=lambda r: r.get("created_at", ""), reverse=True)


def get_report(report_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single report by id."""
    data = _load()
    for report in data["reports"]:
        if report.get("id") == report_id:
            return report
    return None


def delete_report(report_id: str) -> bool:
    """Delete a report by id. Returns True if it existed."""
    data = _load()
    original = data["reports"]
    filtered = [r for r in original if r.get("id") != report_id]
    if len(filtered) == len(original):
        return False
    data["reports"] = filtered
    _save(data)
    logger.info("Deleted SLA report %s", report_id)
    return True
