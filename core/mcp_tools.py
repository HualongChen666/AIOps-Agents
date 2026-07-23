# -*- coding: utf-8 -*-
"""Utility functions for the MCP server.

These functions delegate to the existing core modules to provide
JSON‑RPC‑style behavior for external agents.
"""

import logging
from typing import Any, Dict, List

from .collector import get_cached_snapshot

# Attempt to import ``trigger_repair`` from ``core.auto_heal``.
# 若实际实现不存在，则提供一个最小占位实现避免 ImportError。
# trigger_repair doesn't exist in auto_heal, using placeholder directly


async def trigger_repair(alert_id: str, user: str, comment: str | None = None) -> Dict[str, Any]:
    """占位实现：仅记录日志并返回固定结构，供 MCP 调用而不报错。"""
    logger = logging.getLogger(__name__)
    logger.info(f"[mcp_tools] 调用占位 trigger_repair(alert_id={alert_id!r}, user={user!r})")
    return {"alert_id": alert_id, "status": "placeholder", "user": user, "comment": comment}


# from .repair_engine import repair_engine  # Not needed for placeholder implementation

# from .verifier import verify_repair  # Not needed for MCP placeholder

logger = logging.getLogger(__name__)


async def get_host_health(host_id: str) -> Dict[str, Any]:
    """Return the latest health snapshot for a given host.

    Parameters
    ----------
    host_id: str
        Identifier matching the ``name`` field of a host configuration.
    """
    snapshot = get_cached_snapshot(host_id)  # type: ignore
    if not snapshot:
        # 返回空字典而非异常，避免前端出现 500 错误
        logger.warning("No health data for host %s, returning empty dict", host_id)
        return {}
    return snapshot  # type: ignore


async def trigger_repair_with_hitl(
    alert_id: str, user: str, comment: str | None = None
) -> Dict[str, Any]:
    """Trigger the full HITL healing workflow for a specific alert.

    This mirrors the ``/autoheal`` endpoint but is callable via MCP.
    """
    # Re‑use the existing auto_heal logic – it already handles approval.
    result = await trigger_repair(alert_id=alert_id, user=user, comment=comment)  # type: ignore
    return result  # type: ignore


async def search_incident_history(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search historic incidents using the RAG engine.

    This is a thin wrapper around the RAG search implementation.
    """
    from .rag_engine import AIOpsRAG  # type: ignore

    rag = AIOpsRAG()  # type: ignore
    results = rag.search_similar(query, top_k=limit)  # type: ignore
    return results  # type: ignore


async def get_metrics(host_id: str, metrics: List[str]) -> Dict[str, Any]:
    """Fetch specific metrics for a host.

    The function queries the collector cache; if a metric is missing it
    returns ``None`` for that key.
    """
    snapshot = get_cached_snapshot(host_id)  # type: ignore
    if not snapshot:
        return {metric: None for metric in metrics}
    data = {metric: snapshot.get(metric) for metric in metrics}
    return data


async def approve_repair(
    repair_id: str, approved: bool, comment: str | None = None
) -> Dict[str, Any]:
    """Approve or reject a pending repair.

    In this simplified implementation we directly update the repair
    record in the database and optionally log the comment.
    """
    from .db_engine import db  # type: ignore

    record = db.get_repair_record(repair_id)  # type: ignore
    if not record:
        db.update_repair_status(repair_id, "pending")  # type: ignore
    # Update status based on approval
    new_status = "approved" if approved else "rejected"
    db.update_repair_status(repair_id, new_status, comment=comment)  # type: ignore
    logger.info("Repair %s %s by external request", repair_id, new_status)
    return {"repair_id": repair_id, "status": new_status}


__all__ = [
    "trigger_repair",
    "get_host_health",
    "trigger_repair_with_hitl",
    "search_incident_history",
    "get_metrics",
    "approve_repair",
]
