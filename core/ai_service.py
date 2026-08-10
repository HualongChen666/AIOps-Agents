# -*- coding: utf-8 -*-
"""
ai_service.py
-----------
AI 分析服务层

从 API 路由层提取的业务逻辑，提供富上下文采集、数据清洗等服务。
遵循分层架构原则：Controller → Service → Repository/Engine。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from datetime import timedelta
from typing import Any, List, Optional

from core.collector import get_cached_snapshot

logger = logging.getLogger(__name__)


# ============================================================
# 模块级常量
# ============================================================
_METRICS_CTX_MAX_LEN = 500

try:
    from config import AI_RICH_CONTEXT_TIMEOUT_SEC as _CFG_RC_TIMEOUT

    _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC: float = max(0.5, min(10.0, float(_CFG_RC_TIMEOUT)))
except (ImportError, AttributeError, ValueError, TypeError):
    _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC = 2.0


# ============================================================
# 辅助函数
# ============================================================
def _safe_alert_value(val: Any) -> Any:
    """统一处理 alert.value 字段"""
    if val is None or isinstance(val, (int, float, bool)):
        return val
    if isinstance(val, str):
        try:
            return float(val)
        except (ValueError, TypeError):
            return val[:64]
    return str(val)[:64]


def _safe_get_metric(
    snapshot: dict[str, Any],
    section: str,
    field: str,
    default: Any = "N/A",
) -> Any:
    """从 snapshot 中安全提取嵌套字段"""
    if not isinstance(snapshot, dict):
        return default
    section_data = snapshot.get(section)
    if not isinstance(section_data, dict):
        return default
    return section_data.get(field, default)


def _extract_gather_result(
    result: Any,
    name: str,
    expected_type: type,
) -> Any:
    """统一处理 asyncio.gather(return_exceptions=True) 结果"""
    if isinstance(result, asyncio.CancelledError):
        logger.error(f"富上下文 [{name}] CancelledError 未被上游处理(异常)")
        return None
    if isinstance(result, Exception):
        logger.warning(f"富上下文 [{name}] 任务异常: {type(result).__name__}: {result}")
        return None
    if result is None:
        return None
    if isinstance(result, expected_type):
        return result
    logger.warning(
        f"富上下文 [{name}] 返回类型异常: {type(result).__name__},期望 {expected_type.__name__}"
    )
    return None


# ============================================================
# 富上下文采集服务
# ============================================================
class AIContextService:
    """AI 上下文采集服务"""

    async def collect_rich_context(
        self,
        snapshot: Optional[dict] = None,
        service_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        采集富上下文（10 个数据源并行）

        覆盖 Prompt/数据层面要求的全部维度：
          1. 告警服务本身的指标（CPU/内存/延迟/错误率/连接池等）
          2. 上游调用方的行为变化（流量/QPS/失败率）
          3. 下游依赖的状态（数据库/缓存/消息队列/第三方 API）
          4. 基础设施层（节点/网络/磁盘/DNS）
          5. 最近变更记录（发布/配置变更/扩缩容）
          6. 同时段的其他告警（关联分析）
          7. 服务拓扑/依赖关系图

        Args:
            snapshot: 调用方传入的快照（可选）
            service_name: 告警涉及的服务名（用于精确拉取服务指标与拓扑）

        Returns:
            rich_context dict（失败的字段为默认空值）
        """
        rich_context: dict[str, Any] = {
            "top_processes": [],
            "recent_alerts": [],
            "recent_repairs": [],
            "stats": {},
            "service_metrics": {},
            "infrastructure_metrics": {},
            "dependencies": {},
            "upstream_callers": {},
            "downstream_dependencies": {},
            "change_events": [],
            "correlated_alerts": [],
            "topology": {},
        }

        # 优先获取一次 snapshot，避免多个数据源重复调用 get_cached_snapshot
        cached_snapshot = snapshot
        if not cached_snapshot or not isinstance(cached_snapshot, dict):
            try:
                cached_snapshot = get_cached_snapshot()
            except Exception as e:
                logger.warning(f"富上下文:获取缓存快照失败 {e}")
                cached_snapshot = {}
        if not isinstance(cached_snapshot, dict):
            cached_snapshot = {}

        # 数据源 1: Top 5 进程
        async def _fetch_processes():
            try:
                src = cached_snapshot
                if src and isinstance(src, dict):
                    top_procs = src.get("top_processes", [])
                    return top_procs[:5] if isinstance(top_procs, list) else []
            except Exception as e:
                logger.warning(f"富上下文:进程数据提取失败 {e}")
            return []

        # 数据源 2: 最近 10 条告警
        async def _fetch_alerts():
            try:
                from core.alert_engine import alert_history

                recent_alerts = list(alert_history)[:10]
                cleaned = []
                for a in recent_alerts:
                    if not isinstance(a, dict):
                        continue
                    level = a.get("level", "info")
                    if not isinstance(level, str):
                        level = str(level) if level is not None else "info"
                    cleaned.append(
                        {
                            "level": level,
                            "title": str(a.get("title", ""))[:200],
                            "desc": str(a.get("desc", ""))[:500],
                            "raw_time": str(a.get("raw_time", ""))[:32],
                            "metric": str(a.get("metric", ""))[:64],
                            "value": _safe_alert_value(a.get("value", 0)),
                            "host": str(a.get("host", ""))[:64],
                            "source": str(a.get("source", ""))[:64],
                        }
                    )
                return cleaned
            except Exception as e:
                logger.warning(f"富上下文:告警历史读取失败 {e}")
            return []

        # 数据源 3: 最近 5 次修复
        async def _fetch_repairs():
            try:
                from core.repair_engine import repair_history

                return list(repair_history)[:5]
            except Exception as e:
                logger.warning(f"富上下文:修复记录读取失败 {e}")
            return []

        # 数据源 4: 统计信息
        async def _fetch_stats():
            try:
                from core.metrics_history import metrics_history

                if hasattr(metrics_history, "get_stats"):
                    result = metrics_history.get_stats()
                    if isinstance(result, dict):
                        return result
                if hasattr(metrics_history, "to_dict"):
                    result = metrics_history.to_dict()
                    if isinstance(result, dict):
                        return result
                return {}
            except Exception as e:
                logger.warning(f"富上下文:统计信息读取失败 {e}")
            return {}

        # 数据源 5: 告警服务自身指标
        async def _fetch_service_metrics():
            try:
                from core.service_monitoring_manager import get_service_monitoring_manager

                if not service_name:
                    return {}
                mgr = get_service_monitoring_manager()
                metrics = mgr.get_service_metrics(service_name, time_range=timedelta(hours=1))
                result: dict[str, Any] = {}
                for m in metrics:
                    if hasattr(m, "metric_name"):
                        key = str(m.metric_name)
                        if hasattr(m, "value"):
                            result[key] = {
                                "value": m.value,
                                "timestamp": getattr(m, "timestamp", None),
                            }
                        else:
                            result[key] = (
                                asdict(m) if hasattr(m, "__dataclass_fields__") else str(m)
                            )
                return result
            except Exception as e:
                logger.warning(f"富上下文:服务指标读取失败 {e}")
            return {}

        # 数据源 6: 基础设施层指标（CPU/内存/磁盘/网络/系统）
        async def _fetch_infrastructure_metrics():
            try:
                src = cached_snapshot
                if src and isinstance(src, dict):
                    return {
                        "cpu": src.get("cpu", {}),
                        "memory": src.get("memory", {}),
                        "disk": src.get("disk", []),
                        "network": src.get("network", {}),
                        "system": src.get("system", {}),
                    }
            except Exception as e:
                logger.warning(f"富上下文:基础设施指标读取失败 {e}")
            return {}

        # 数据源 7: 服务拓扑/依赖关系
        async def _fetch_topology():
            try:
                from core.topology_engine import get_full_link_topology

                topo = await get_full_link_topology()
                if not isinstance(topo, dict):
                    return {}
                dependencies: dict[str, List[str]] = {}
                for edge in topo.get("edges", []):
                    if not isinstance(edge, dict):
                        continue
                    src = edge.get("source") or edge.get("from")
                    tgt = edge.get("target") or edge.get("to")
                    if src and tgt:
                        dependencies.setdefault(str(src), []).append(str(tgt))
                return {
                    "nodes": topo.get("nodes", []),
                    "edges": topo.get("edges", []),
                    "dependencies": dependencies,
                }
            except Exception as e:
                logger.warning(f"富上下文:拓扑读取失败 {e}")
            return {}

        # 数据源 8: 上游调用方行为
        async def _fetch_upstream_callers():
            # 默认从拓扑中解析指向 service_name 的边作为上游
            try:
                topo = rich_context.get("topology", {})
                dependencies = topo.get("dependencies", {})
                upstream: dict[str, List[str]] = {}
                for src, targets in dependencies.items():
                    if service_name and service_name in targets:
                        upstream.setdefault(service_name, []).append(src)
                    elif not service_name:
                        upstream.setdefault(src, []).extend(targets)
                # 如后续接入调用链系统，可在这里补充 QPS/错误率
                return upstream
            except Exception as e:
                logger.warning(f"富上下文:上游调用方读取失败 {e}")
            return {}

        # 数据源 9: 下游依赖状态
        async def _fetch_downstream_dependencies():
            try:
                topo = rich_context.get("topology", {})
                dependencies = topo.get("dependencies", {})
                downstream: dict[str, Any] = {}
                if service_name and service_name in dependencies:
                    for dep in dependencies[service_name]:
                        downstream[dep] = {"status": "unknown"}
                elif not service_name:
                    downstream = dependencies
                return downstream
            except Exception as e:
                logger.warning(f"富上下文:下游依赖读取失败 {e}")
            return {}

        # 数据源 10: 最近变更记录（配置变更/发布/扩缩容）
        async def _fetch_change_events():
            try:
                from core.config_manager import config_manager

                events = []
                for entry in getattr(config_manager, "_audit_log", [])[-10:]:
                    if not isinstance(entry, dict):
                        continue
                    events.append(
                        {
                            "timestamp": entry.get("timestamp"),
                            "type": "config_change",
                            "target": entry.get("change", ""),
                            "description": str(entry.get("details", ""))[:200],
                        }
                    )
                # 同时读取配置历史作为兜底
                for entry in getattr(config_manager, "_config_history", [])[-5:]:
                    if not isinstance(entry, dict):
                        continue
                    ts = entry.get("timestamp") or entry.get("applied_at")
                    if ts:
                        events.append(
                            {
                                "timestamp": ts,
                                "type": "config_history",
                                "target": "config",
                                "description": "配置历史版本快照",
                            }
                        )
                return sorted(events, key=lambda x: x.get("timestamp") or "", reverse=True)[:10]
            except Exception as e:
                logger.warning(f"富上下文:变更记录读取失败 {e}")
            return []

        # 数据源 11: 同时段关联告警
        async def _fetch_correlated_alerts():
            try:
                from core.alert_engine import alert_history

                all_alerts = list(alert_history)
                cleaned = []
                for a in all_alerts:
                    if not isinstance(a, dict):
                        continue
                    # 如果指定了服务名，只保留相关告警
                    if service_name:
                        txt = f"{
                            a.get(
                                'title',
                                '')} {
                            a.get(
                                'desc',
                                '')} {
                            a.get(
                                'host',
                                '')} {
                            a.get(
                                'source',
                                '')}"
                        if service_name not in txt:
                            continue
                    cleaned.append(
                        {
                            "level": str(a.get("level", "info")),
                            "title": str(a.get("title", ""))[:200],
                            "desc": str(a.get("desc", ""))[:500],
                            "raw_time": str(a.get("raw_time", ""))[:32],
                            "source": str(a.get("source", ""))[:64],
                            "host": str(a.get("host", ""))[:64],
                        }
                    )
                return cleaned[:20]
            except Exception as e:
                logger.warning(f"富上下文:关联告警读取失败 {e}")
            return []

        # 并行采集
        async def _with_timeout(async_fn, timeout: float, *args):
            try:
                coro = async_fn(*args)
                return await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.TimeoutError:
                return None

        tasks = [
            _with_timeout(_fetch_processes, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_alerts, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_repairs, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_stats, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_service_metrics, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_infrastructure_metrics, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_topology, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_change_events, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_correlated_alerts, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
        ]

        def _close_tasks():
            """Close coroutine objects to avoid RuntimeWarning in mocked gather paths."""
            for task in tasks:
                try:
                    if asyncio.iscoroutine(task):
                        task.close()
                except Exception as e:
                    logging.exception("Unexpected exception: %s", e)
                    logging.warning("Suppressed exception", exc_info=True)

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            _close_tasks()
            raise
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            _close_tasks()
            raise

        # 检测 CancelledError 并 reraise
        for result in results:
            if isinstance(result, asyncio.CancelledError):
                raise result

        # 解析结果（注意 topology 需要优先解析，供上下游使用）
        rich_context["topology"] = _extract_gather_result(results[6], "拓扑", dict) or {}

        rich_context["top_processes"] = _extract_gather_result(results[0], "进程", list) or []
        rich_context["recent_alerts"] = _extract_gather_result(results[1], "告警", list) or []
        rich_context["recent_repairs"] = _extract_gather_result(results[2], "修复", list) or []
        rich_context["stats"] = _extract_gather_result(results[3], "统计", dict) or {}
        rich_context["service_metrics"] = _extract_gather_result(results[4], "服务指标", dict) or {}
        rich_context["infrastructure_metrics"] = (
            _extract_gather_result(results[5], "基础设施", dict) or {}
        )
        rich_context["change_events"] = _extract_gather_result(results[7], "变更", list) or []
        rich_context["correlated_alerts"] = (
            _extract_gather_result(results[8], "关联告警", list) or []
        )

        # 基于 topology 再解析上下游
        rich_context["dependencies"] = rich_context["topology"].get("dependencies", {})
        rich_context["upstream_callers"] = (
            await _with_timeout(_fetch_upstream_callers, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC) or {}
        )
        rich_context["downstream_dependencies"] = (
            await _with_timeout(
                _fetch_downstream_dependencies, _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC
            )
            or {}
        )

        return rich_context


# 默认服务实例
ai_context_service = AIContextService()
