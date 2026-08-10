# -*- coding: utf-8 -*-
# Compatibility functions for alert_engine
from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

SUMMARY_CACHE_TTL_SECONDS = 300
_summary_cache: Dict[str, Any] = {}


def record_ingestion(data_points: int = 1) -> None:
    """Record ingestion data points in the in-memory summary cache."""
    _summary_cache.setdefault("ingestion", {"total_points": 0, "records": 0})
    _summary_cache["ingestion"]["total_points"] += data_points
    _summary_cache["ingestion"]["records"] += 1
    logger.info(f"record_ingestion called with {data_points} point(s)")


def record_alert_noise(raw_count: int, effective_count: int) -> None:
    """Record raw vs effective alert counts in the in-memory summary cache."""
    _summary_cache.setdefault("alert_noise", {"raw": 0, "effective": 0})
    _summary_cache["alert_noise"]["raw"] += raw_count
    _summary_cache["alert_noise"]["effective"] += effective_count
    logger.info(f"record_alert_noise: raw={raw_count}, effective={effective_count}")


# ---------------------------------------------------------------------------
# Async query/insert stubs – tests patch these so engine stays testable.
# ---------------------------------------------------------------------------
async def query_alert_stats(
    start_time: Optional[str] = None, end_time: Optional[str] = None
) -> Dict[str, Any]:
    """Return alert stats from the in-memory summary cache."""
    noise = _summary_cache.get("alert_noise", {})
    ingestion = _summary_cache.get("ingestion", {})
    return {
        "alerts": noise,
        "ingestion": ingestion,
        "period": {"start_time": start_time, "end_time": end_time},
    }


async def query_hourly_stats() -> List[Dict[str, Any]]:
    """Return hourly alert stats when available; otherwise empty."""
    return _summary_cache.get("hourly_stats", [])


async def query_daily_stats() -> List[Dict[str, Any]]:
    """Return daily alert stats when available; otherwise empty."""
    return _summary_cache.get("daily_stats", [])


async def query_repair_stats(group_by: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate repair stats from the in-memory summary cache."""
    history = _summary_cache.get("repair_history", [])
    if not group_by:
        return {"total_repairs": len(history), "repairs": history}
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in history:
        key = rec.get(group_by, "unknown")
        grouped[key].append(rec)
    return {k: len(v) for k, v in grouped.items()}


async def query_repair_history(limit: int = 50, host: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return repair history from the cache, filtered and limited."""
    history = list(_summary_cache.get("repair_history", []))
    if host:
        history = [r for r in history if r.get("host") == host]
    return history[:limit]


async def query_system_stats() -> Dict[str, Any]:
    """Return system stats from the cache or a safe fallback."""
    return _summary_cache.get(
        "system_stats",
        {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def insert_repair_record(repair_data: Dict[str, Any]) -> str:
    """Persist a repair record in memory and return a UUID repair id."""
    repair_id = str(uuid.uuid4())
    record = {
        **repair_data,
        "repair_id": repair_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _summary_cache.setdefault("repair_history", []).append(record)
    return repair_id


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


# ---------------------------------------------------------------------------
# Decision accuracy metrics (O20)
# ---------------------------------------------------------------------------


@dataclass
class _DecisionRecord:
    decision_id: str
    decision_type: str
    prediction: bool
    actual: Optional[bool] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_decisions: List[_DecisionRecord] = []


def record_decision(prediction: bool, decision_type: str = "general") -> str:
    """Record an AI/agent decision prediction."""
    decision_id = str(uuid.uuid4())
    record = _DecisionRecord(
        decision_id=decision_id,
        decision_type=decision_type,
        prediction=bool(prediction),
    )
    _decisions.append(record)
    logger.info(f"Decision recorded: {decision_id} type={decision_type} prediction={prediction}")
    return decision_id


def record_outcome(decision_id: str, actual: bool) -> bool:
    """Record the actual outcome for a previous decision."""
    for record in _decisions:
        if record.decision_id == decision_id:
            record.actual = bool(actual)
            logger.info(f"Outcome recorded for {decision_id}: actual={actual}")
            return True
    return False


def _compute_accuracy(records: Sequence[_DecisionRecord]) -> Dict[str, Any]:
    """Compute precision, recall, F1 and accuracy from labeled decisions."""
    tp = sum(1 for r in records if r.prediction and r.actual)
    fp = sum(1 for r in records if r.prediction and not r.actual)
    tn = sum(1 for r in records if not r.prediction and not r.actual)
    fn = sum(1 for r in records if not r.prediction and r.actual)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(records) if records else 0.0

    return {
        "total": len(records),
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }


def get_decision_accuracy(decision_type: Optional[str] = None) -> Dict[str, Any]:
    """Get decision accuracy metrics, optionally filtered by type."""
    try:
        if decision_type:
            records = [
                d for d in _decisions if d.decision_type == decision_type and d.actual is not None
            ]
        else:
            records = [d for d in _decisions if d.actual is not None]
        metrics = _compute_accuracy(records)
        metrics["decision_type"] = decision_type or "all"
        return {"success": True, "metrics": metrics}
    except Exception as e:  # pragma: no cover
        logger.error(f"get_decision_accuracy failed: {e}")
        return {"success": False, "error": str(e)}


def get_decision_summary() -> Dict[str, Any]:
    """Aggregate decision accuracy by decision type."""
    try:
        by_type: Dict[str, List[_DecisionRecord]] = defaultdict(list)
        for d in _decisions:
            if d.actual is not None:
                by_type[d.decision_type].append(d)

        summary = {}
        for dtype, records in by_type.items():
            summary[dtype] = _compute_accuracy(records)
        summary["all"] = _compute_accuracy([d for d in _decisions if d.actual is not None])
        return {"success": True, "summary": summary}
    except Exception as e:  # pragma: no cover
        logger.error(f"get_decision_summary failed: {e}")
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
    """Get HTTP client for stats engine (returns httpx.Client if available)."""
    try:
        import httpx

        return httpx.Client(timeout=30)
    except ImportError:
        try:
            import requests

            return requests.Session()
        except ImportError:
            logger.warning("Neither httpx nor requests available; returning None")
            return None


# component function for cloud_collector compatibility
def record_collect(collect_data: dict) -> None:
    """Record collect data (component for cloud_collector compatibility)."""
    logger.info(f"record_collect called with data: {collect_data.get('provider', 'unknown')}")
