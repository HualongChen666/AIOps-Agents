# -*- coding: utf-8 -*-
"""Real SRE maturity assessment engine backed by live project data."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional core dependencies – degrade gracefully if a module is unavailable.
try:
    from core.alert_service import alert_service
except ImportError:  # pragma: no cover
    alert_service = None

try:
    from core.auto_heal import get_pending_approvals
except ImportError:  # pragma: no cover

    async def get_pending_approvals() -> List[Dict[str, Any]]:  # type: ignore[misc]
        """Fallback when auto_heal is not available."""
        return []


try:
    from core.repair_engine import get_repair_history, get_repair_scripts
except ImportError:  # pragma: no cover

    def get_repair_history(limit: int = 50) -> List[Dict[str, Any]]:  # type: ignore[misc]
        """Fallback when repair_engine is not available."""
        return []

    def get_repair_scripts() -> List[Dict[str, Any]]:  # type: ignore[misc]
        """Fallback when repair_engine is not available."""
        return []


try:
    from core.stats_engine import get_decision_accuracy
except ImportError:  # pragma: no cover

    def get_decision_accuracy() -> Dict[str, Any]:  # type: ignore[misc]
        """Fallback when stats_engine is not available."""
        return {"success": False, "metrics": {}}


try:
    from core.collector import get_cached_snapshot
except ImportError:  # pragma: no cover

    # type: ignore[misc]
    def get_cached_snapshot(host_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fallback when collector is not available."""
        return None


DIMENSIONS_META: List[Dict[str, Any]] = [
    {
        "name": "可观测性",
        "description": "系统监控覆盖度和实时性",
        "maxScore": 100,
    },
    {
        "name": "可靠性",
        "description": "告警规则配置和响应效率",
        "maxScore": 100,
    },
    {
        "name": "自动化程度",
        "description": "自动化修复和运维操作",
        "maxScore": 100,
    },
    {
        "name": "事件响应",
        "description": "事件处理、MTTR 和审批闭环",
        "maxScore": 100,
    },
    {
        "name": "安全合规",
        "description": "风险识别、告警分级与合规覆盖",
        "maxScore": 100,
    },
    {
        "name": "文档与知识",
        "description": "Runbook、修复脚本和知识沉淀",
        "maxScore": 100,
    },
]

_OBSERVABILITY_KEYS = ("cpu", "memory", "disk", "network", "top_processes")


def _level_from_score(score: int) -> int:
    """Map a 0-100 score to a 1-5 maturity level."""
    if score >= 90:
        return 5
    if score >= 75:
        return 4
    if score >= 60:
        return 3
    if score >= 40:
        return 2
    return 1


def _safe_len(value: Any) -> int:
    """Return the length of a list-like value, or 1 for non-empty scalar."""
    if value is None:
        return 0
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1 if value else 0


def _is_collector_key_present(snapshot: Dict[str, Any], key: str) -> bool:
    """Check whether a metric group in the collector snapshot has real data."""
    value = snapshot.get(key)
    if not value:
        return False
    if key == "top_processes" and isinstance(value, list):
        return len(value) > 1
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return any(v not in (None, "", 0, 0.0) for v in value.values())
    return True


async def _get_collector_snapshot() -> Optional[Dict[str, Any]]:
    """Return the cached collector snapshot without blocking the event loop."""
    try:
        cached = get_cached_snapshot()
        if cached:
            return cached
    except Exception as exc:  # pragma: no cover
        logger.warning("get_cached_snapshot failed: %s", exc)

    return None


async def _gather_signals() -> Dict[str, Any]:
    """Collect real signals from alert, repair, approval and decision systems."""
    signals: Dict[str, Any] = {
        "total_alerts": 0,
        "alerts": [],
        "total_repairs": 0,
        "successful_repairs": 0,
        "repair_scripts_count": 0,
        "documented_scripts_count": 0,
        "pending_approvals": 0,
        "decision_total": 0,
        "decision_f1": 0.0,
        "coverage_ratio": 0.0,
        "snapshot": None,
        "severity_counts": {},
    }

    # Alert volume and severity distribution
    if alert_service is not None:
        try:
            alerts_data = alert_service.get_alerts(limit=10000)
            alerts = alerts_data.get("alerts", [])
            signals["alerts"] = alerts
            signals["total_alerts"] = int(alerts_data.get("total", len(alerts)))
        except Exception as exc:  # pragma: no cover
            logger.warning("alert_service.get_alerts failed: %s", exc)

    severity_counts: Dict[str, int] = {}
    for alert in signals["alerts"]:
        if not isinstance(alert, dict):
            continue
        level = str(alert.get("level") or alert.get("severity") or "unknown").lower()
        severity_counts[level] = severity_counts.get(level, 0) + 1
    signals["severity_counts"] = severity_counts

    # Repair history and playbook inventory
    try:
        repair_history = get_repair_history(limit=10000)
        signals["total_repairs"] = len(repair_history)
        signals["successful_repairs"] = sum(
            1 for r in repair_history if isinstance(r, dict) and r.get("success") is True
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("get_repair_history failed: %s", exc)

    try:
        repair_scripts = get_repair_scripts()
        signals["repair_scripts_count"] = len(repair_scripts)
        signals["documented_scripts_count"] = sum(
            1
            for s in repair_scripts
            if isinstance(s, dict) and bool(s.get("description") or s.get("name"))
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("get_repair_scripts failed: %s", exc)

    # Human-in-the-loop backlog
    try:
        if asyncio.iscoroutinefunction(get_pending_approvals):
            approvals = await get_pending_approvals()
        else:
            approvals = get_pending_approvals()  # type: ignore[call-arg,misc]
        signals["pending_approvals"] = len(approvals) if isinstance(approvals, list) else 0
    except Exception as exc:  # pragma: no cover
        logger.warning("get_pending_approvals failed: %s", exc)

    # AI / decision accuracy
    try:
        decision_result = get_decision_accuracy()
        metrics = decision_result.get("metrics", {}) if isinstance(decision_result, dict) else {}
        signals["decision_total"] = int(metrics.get("total", 0))
        signals["decision_f1"] = float(metrics.get("f1_score", 0.0) or 0.0)
    except Exception as exc:  # pragma: no cover
        logger.warning("get_decision_accuracy failed: %s", exc)

    # Collector coverage
    snapshot = await _get_collector_snapshot()
    signals["snapshot"] = snapshot
    if snapshot:
        present = sum(1 for key in _OBSERVABILITY_KEYS if _is_collector_key_present(snapshot, key))
        signals["coverage_ratio"] = present / len(_OBSERVABILITY_KEYS)

    return signals


def _score_observability(signals: Dict[str, Any]) -> int:
    """Score observability from collector coverage and system health."""
    coverage = signals.get("coverage_ratio", 0.0)
    snapshot = signals.get("snapshot") or {}
    cpu = snapshot.get("cpu") or {}
    mem = snapshot.get("memory") or {}
    cpu_ok = isinstance(cpu, dict) and cpu.get("usage_percent", 0) is not None
    mem_ok = isinstance(mem, dict) and mem.get("usage_percent", 0) is not None
    health_factor = 1.0 if (cpu_ok and mem_ok) else 0.7
    score = int(round(coverage * 80.0 * health_factor + coverage * 20.0))
    return min(100, max(0, score))


def _score_reliability(signals: Dict[str, Any]) -> int:
    """Score reliability from repair success and decision accuracy."""
    total_repairs = signals.get("total_repairs", 0)
    successful_repairs = signals.get("successful_repairs", 0)
    repair_success_rate = successful_repairs / total_repairs if total_repairs else 0.0
    f1 = signals.get("decision_f1", 0.0)
    if total_repairs == 0 and signals.get("decision_total", 0) == 0:
        return 0
    score = int(round(repair_success_rate * 50.0 + f1 * 50.0))
    return min(100, max(0, score))


def _score_automation(signals: Dict[str, Any]) -> int:
    """Score automation from repair throughput and playbook coverage."""
    total_alerts = max(signals.get("total_alerts", 0), 1)
    signals.get("total_repairs", 0)
    successful_repairs = signals.get("successful_repairs", 0)
    scripts_count = signals.get("repair_scripts_count", 0)

    handle_rate = min(successful_repairs / total_alerts, 1.0)
    script_maturity = min(scripts_count / 10.0, 1.0)
    pending = signals.get("pending_approvals", 0)
    backlog_penalty = min(pending / total_alerts, 1.0)

    score = int(round(handle_rate * 100.0 * 0.6 + script_maturity * 100.0 * 0.3))
    score = int(round(score * (1.0 - backlog_penalty * 0.4)))
    return min(100, max(0, score))


def _score_incident_response(signals: Dict[str, Any]) -> int:
    """Score incident response from alert backlog and severity distribution."""
    total_alerts = max(signals.get("total_alerts", 0), 1)
    pending = signals.get("pending_approvals", 0)
    severity_counts = signals.get("severity_counts", {})
    critical = severity_counts.get("critical", 0) + severity_counts.get("high", 0)

    pending_ratio = pending / total_alerts
    critical_ratio = critical / total_alerts
    score = 100 - int(round(pending_ratio * 60.0)) - int(round(critical_ratio * 40.0))

    f1 = signals.get("decision_f1", 0.0)
    if signals.get("decision_total", 0) > 0:
        score = int(round(score * 0.8 + f1 * 20.0))
    return min(100, max(0, score))


def _score_security(signals: Dict[str, Any]) -> int:
    """Score security from critical alert concentration."""
    total_alerts = signals.get("total_alerts", 0)
    if total_alerts == 0:
        return 50
    severity_counts = signals.get("severity_counts", {})
    critical = severity_counts.get("critical", 0) + severity_counts.get("high", 0)
    score = int(round(100.0 - (critical / total_alerts) * 100.0))
    return min(100, max(0, score))


def _score_documentation(signals: Dict[str, Any]) -> int:
    """Score documentation from available scripts and successful repair usage."""
    scripts_count = signals.get("repair_scripts_count", 0)
    documented = signals.get("documented_scripts_count", 0)
    successful_repairs = signals.get("successful_repairs", 0)
    base = min(scripts_count * 10, 100)
    bonus = min(documented * 2 + successful_repairs, 20)
    return min(100, base + bonus)


_SCORERS = {
    "可观测性": _score_observability,
    "可靠性": _score_reliability,
    "自动化程度": _score_automation,
    "事件响应": _score_incident_response,
    "安全合规": _score_security,
    "文档与知识": _score_documentation,
}


def _estimate_time(priority: str) -> str:
    """Return a rough estimated remediation time for a recommendation."""
    return {"high": "2-3个月", "medium": "1-2个月", "low": "2-4周"}.get(priority, "1个月")


def _recommendation_text(name: str, score: int) -> str:
    """Generate a concrete improvement text for a dimension."""
    texts = {
        "可观测性": "补齐 CPU / 内存 / 磁盘 / 网络 / 进程全覆盖监控, 降低采集失败率。",
        "可靠性": "提升修复成功率和 AI 决策 F1 分数, 减少无效告警和重复故障。",
        "自动化程度": "扩展自动修复脚本覆盖, 缩短人工审批等待队列。",
        "事件响应": "优化告警分级与审批流程, 降低高危告警积压。",
        "安全合规": "减少高/危急级别告警占比, 强化风险识别与审计。",
        "文档与知识": "补充 Runbook 描述和修复记录, 沉淀运维知识库。",
    }
    return texts.get(name, f"提升{name}能力, 达到下一成熟度等级。")


def _build_recommendations(
    dimensions: List[Dict[str, Any]], overall_level: int
) -> List[Dict[str, Any]]:
    """Build prioritized improvement recommendations from dimension scores."""
    recommendations: List[Dict[str, Any]] = []
    for idx, dim in enumerate(dimensions, start=1):
        score = dim["score"]
        if score >= 90:
            continue
        priority = "high" if score < 50 else "medium" if score < 75 else "low"
        recommendations.append(
            {
                "id": f"IMP-{idx:03d}",
                "category": dim["name"],
                "title": f"提升{dim['name']}",
                "description": _recommendation_text(dim["name"], score),
                "priority": priority,
                "estimatedTime": _estimate_time(priority),
                "targetLevel": min(dim["level"] + 1, 5),
            }
        )
    return recommendations


async def assess_maturity() -> Dict[str, Any]:
    """Assess SRE maturity from live project data.

    Returns:
        Dict with overall score, maturity level, per-dimension breakdown and
        prioritized improvement recommendations.
    """
    signals = await _gather_signals()

    dimensions: List[Dict[str, Any]] = []
    for meta in DIMENSIONS_META:
        name = meta["name"]
        score = _SCORERS[name](signals)
        dimensions.append(
            {
                "name": name,
                "score": score,
                "maxScore": meta["maxScore"],
                "description": meta["description"],
                "level": _level_from_score(score),
            }
        )

    overall_score = int(round(sum(d["score"] for d in dimensions) / len(dimensions)))
    overall_level = _level_from_score(overall_score)
    level_names = {1: "初始级", 2: "可重复级", 3: "已定义级", 4: "已管理级", 5: "优化级"}

    return {
        "overall_score": overall_score,
        "level": overall_level,
        "level_name": level_names.get(overall_level, "未知"),
        "dimensions": dimensions,
        "recommendations": _build_recommendations(dimensions, overall_level),
    }


def get_dimension_metadata() -> List[Dict[str, Any]]:
    """Return static metadata for all maturity dimensions."""
    return [dict(m) for m in DIMENSIONS_META]
