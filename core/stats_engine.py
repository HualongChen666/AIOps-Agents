# -*- coding: utf-8 -*-
# Compatibility functions for alert_engine
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SUMMARY_CACHE_TTL_SECONDS = 300
_summary_cache: Dict[str, Any] = {}


def record_ingestion(data_points: int = 1) -> None:
    """Placeholder for record_ingestion – logs the call."""
    logger.info(f"record_ingestion called with {data_points} point(s)")


def record_alert_noise(raw_count: int, effective_count: int) -> None:
    """Placeholder for record_alert_noise – logs the metrics."""
    logger.info(f"record_alert_noise: raw={raw_count}, effective={effective_count}")


# ---------------------------------------------------------------------------
# Async query/insert stubs – tests patch these so engine stays testable.
# ---------------------------------------------------------------------------
async def query_alert_stats(
    start_time: Optional[str] = None, end_time: Optional[str] = None
) -> Dict[str, Any]:
    """Placeholder for querying alert stats."""
    return {}


async def query_hourly_stats() -> List[Dict[str, Any]]:
    """Placeholder for querying hourly alert stats."""
    return []


async def query_daily_stats() -> List[Dict[str, Any]]:
    """Placeholder for querying daily alert stats."""
    return []


async def query_repair_stats(group_by: Optional[str] = None) -> Dict[str, Any]:
    """Placeholder for querying repair stats."""
    return {}


async def query_repair_history(limit: int = 50, host: Optional[str] = None) -> List[Dict[str, Any]]:
    """Placeholder for querying repair history."""
    return []


async def query_system_stats() -> Dict[str, Any]:
    """Placeholder for querying system stats."""
    return {}


async def insert_repair_record(repair_data: Dict[str, Any]) -> str:
    """Placeholder for inserting a repair record."""
    return "repair-001"


# ---------------------------------------------------------------------------
# Public stats API
# ---------------------------------------------------------------------------
async def get_alert_stats(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    aggregation: Optional[str] = None,
) -> Dict[str, Any]:
    """Get alert stats with optional time range and aggregation."""
    try:
        if aggregation == "hourly":
            data = await query_hourly_stats()
            return {"hourly": data}
        if aggregation == "daily":
            data = await query_daily_stats()
            return {"daily": data}
        return await query_alert_stats(start_time, end_time)
    except Exception as e:  # pragma: no cover
        logger.error(f"get_alert_stats failed: {e}")
        return {"success": False, "error": str(e)}


async def get_repair_stats(group_by: Optional[str] = None) -> Dict[str, Any]:
    """Get repair stats, optionally grouped."""
    try:
        return await query_repair_stats(group_by=group_by)
    except Exception as e:  # pragma: no cover
        logger.error(f"get_repair_stats failed: {e}")
        return {"success": False, "error": str(e)}


async def get_repair_history(limit: int = 50, host: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get repair history with optional host filter."""
    try:
        return await query_repair_history(limit=limit, host=host)
    except Exception as e:  # pragma: no cover
        logger.error(f"get_repair_history failed: {e}")
        return []


async def get_system_stats() -> Dict[str, Any]:
    """Get system stats."""
    try:
        return await query_system_stats()
    except Exception as e:  # pragma: no cover
        logger.error(f"get_system_stats failed: {e}")
        return {"success": False, "error": str(e)}


async def record_repair(repair_data: Dict[str, Any]) -> Dict[str, Any]:
    """Record a repair event."""
    if (
        not isinstance(repair_data, dict)
        or not repair_data.get("script_key")
        or not repair_data.get("host")
    ):
        logger.warning("Invalid repair data: %s", repair_data)
        return {"success": False, "error": "invalid repair data"}

    try:
        repair_id = await insert_repair_record(repair_data)
        logger.info(f"Recorded repair {repair_id}")
        return {"success": True, "repair_id": repair_id}
    except Exception as e:
        logger.error(f"record_repair failed: {e}")
        return {"success": False, "error": str(e)}


async def get_real_summary() -> Dict[str, Any]:
    """Combine alert/repair/system stats with a short-lived in-memory cache."""
    global _summary_cache
    now = datetime.now(timezone.utc).timestamp()
    cached = _summary_cache.get("data")
    cached_at = _summary_cache.get("timestamp")

    if cached is not None and cached_at is not None and now - cached_at < SUMMARY_CACHE_TTL_SECONDS:
        result = dict(cached)
        result["from_cache"] = True
        return result

    alerts, repairs, systems = await asyncio.gather(
        get_alert_stats(),
        get_repair_stats(),
        get_system_stats(),
    )

    summary = {
        "alerts": alerts,
        "repairs": repairs,
        "systems": systems,
        "from_cache": False,
    }
    _summary_cache = {"data": summary, "timestamp": now}
    return summary


def validate_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that success + failure equals total."""
    if not isinstance(stats, dict):
        return {"valid": False, "error": "stats must be a dict"}

    try:
        total = int(stats.get("total", 0))
        success = int(stats.get("success", 0))
        failure = int(stats.get("failure", 0))
    except (TypeError, ValueError):
        return {"valid": False, "error": "inconsistent stats: non-numeric values"}

    if success + failure == total:
        return {"valid": True}

    return {
        "valid": False,
        "error": f"inconsistent stats: success({success}) + failure({failure}) != total({total})",
    }


def _get_http_client():
    """Get HTTP client for stats engine (stub)."""
    return None


# Stub function for cloud_collector compatibility
def record_collect(collect_data: dict) -> None:
    """Record collect data (stub for cloud_collector compatibility)."""
    logger.info(f"record_collect called with data: {collect_data.get('provider', 'unknown')}")
