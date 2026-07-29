# -*- coding: utf-8 -*-
"""Utility functions for the MCP server.

These functions delegate to the existing core modules to provide
JSON‑RPC‑style behavior for external agents.
"""

import logging
from typing import Any, Dict, List

from .collector import get_cached_snapshot

_MAX_MCP_STRING_LEN = 256
_MAX_MCP_TEXT_LEN = 1000
_MAX_METRICS_LIST = 100
_MAX_RAG_LIMIT = 1000


def _validate_str(
    value: Any, name: str, max_len: int = _MAX_MCP_STRING_LEN, allow_empty: bool = False
) -> str:
    """校验字符串参数：类型、长度、空值、null 字节。"""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string, got {type(value).__name__}")
    if not allow_empty and value == "":
        raise ValueError(f"{name} cannot be empty")
    if "\x00" in value:
        raise ValueError(f"{name} contains null bytes")
    if len(value) > max_len:
        raise ValueError(f"{name} exceeds maximum length of {max_len}")
    return value


def _validate_bool(value: Any, name: str) -> bool:
    """严格校验布尔参数（拒绝字符串/数字的隐式转换）。"""
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean, got {type(value).__name__}")
    return value


def _validate_int(value: Any, name: str, min_val: int, max_val: int) -> int:
    """校验整数参数类型和范围。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {type(value).__name__}")
    if value < min_val or value > max_val:
        raise ValueError(f"{name} must be between {min_val} and {max_val}")
    return value


# Attempt to import ``trigger_repair`` from ``core.auto_heal``.
# 若实际实现不存在，则提供一个最小占位实现避免 ImportError。
# trigger_repair doesn't exist in auto_heal, using default_value directly


async def trigger_repair(alert_id: str, user: str, comment: str | None = None) -> Dict[str, Any]:
    """触发告警自愈工作流，调用 heal_graph.run_heal 真实执行修复。"""
    alert_id = _validate_str(alert_id, "alert_id")
    user = _validate_str(user, "user")
    if comment is not None:
        comment = _validate_str(comment, "comment", max_len=_MAX_MCP_TEXT_LEN, allow_empty=True)
    logger = logging.getLogger(__name__)
    logger.info(f"[mcp_tools] 触发修复工作流 | alert_id={alert_id!r} | user={user!r}")
    try:
        from core.heal_graph import HealState, run_heal

        alert = {"id": alert_id, "title": f"MCP trigger by {user}", "platform": "windows"}
        if comment:
            alert["comment"] = comment

        state = HealState(alert=alert)
        final_state = await run_heal(state)

        success = bool(final_state.fix_applied and not final_state.error)
        return {
            "alert_id": alert_id,
            "status": "completed" if success else "pending",
            "success": success,
            "user": user,
            "comment": comment,
            "fix_applied": final_state.fix_applied,
            "verification": final_state.verification,
            "error": final_state.error,
        }
    except Exception as exc:
        logger.error(f"[mcp_tools] trigger_repair 执行失败: {exc}", exc_info=True)
        return {
            "alert_id": alert_id,
            "status": "error",
            "success": False,
            "user": user,
            "comment": comment,
            "error": str(exc),
        }


# from .repair_engine import repair_engine  # Not needed for default_value implementation

# from .verifier import verify_repair  # Not needed for MCP default_value

logger = logging.getLogger(__name__)


async def get_host_health(host_id: str) -> Dict[str, Any]:
    """Return the latest health snapshot for a given host.

    Parameters
    ----------
    host_id: str
        Identifier matching the ``name`` field of a host configuration.
    """
    host_id = _validate_str(host_id, "host_id")
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
    alert_id = _validate_str(alert_id, "alert_id")
    user = _validate_str(user, "user")
    if comment is not None:
        comment = _validate_str(comment, "comment", max_len=_MAX_MCP_TEXT_LEN, allow_empty=True)
    # Re‑use the existing auto_heal logic – it already handles approval.
    result = await trigger_repair(alert_id=alert_id, user=user, comment=comment)  # type: ignore
    return result  # type: ignore


async def search_incident_history(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search historic incidents using the RAG engine.

    This is a thin wrapper around the RAG search implementation.
    """
    query = _validate_str(query, "query", max_len=_MAX_MCP_TEXT_LEN)
    limit = _validate_int(limit, "limit", 1, _MAX_RAG_LIMIT)
    from .rag_engine import AIOpsRAG  # type: ignore

    rag = AIOpsRAG()  # type: ignore
    results = rag.search_similar(query, top_k=limit)  # type: ignore
    return results  # type: ignore


async def get_metrics(host_id: str, metrics: List[str]) -> Dict[str, Any]:
    """Fetch specific metrics for a host.

    The function queries the collector cache; if a metric is missing it
    returns ``None`` for that key.
    """
    host_id = _validate_str(host_id, "host_id")
    if not isinstance(metrics, list):
        raise ValueError("metrics must be a list")
    if len(metrics) > _MAX_METRICS_LIST:
        raise ValueError(f"metrics list exceeds maximum length of {_MAX_METRICS_LIST}")
    for i, metric in enumerate(metrics):
        _validate_str(metric, f"metrics[{i}]")
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
    repair_id = _validate_str(repair_id, "repair_id")
    approved = _validate_bool(approved, "approved")
    if comment is not None:
        comment = _validate_str(comment, "comment", max_len=_MAX_MCP_TEXT_LEN, allow_empty=True)
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
