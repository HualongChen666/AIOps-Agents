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
from typing import Any, Optional

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
    ) -> dict[str, Any]:
        """
        采集富上下文（4 个数据源并行）

        改造要点:
          1. 4 个数据源 asyncio.gather 并行
          2. 各数据源独立超时
          3. 优先复用 get_cached_snapshot()
          4. return_exceptions=True 确保单个失败不中断

        Args:
            snapshot: 调用方传入的快照（可选）

        Returns:
            rich_context dict（失败的字段为默认空值）
        """
        rich_context: dict[str, Any] = {
            "top_processes": [],
            "recent_alerts": [],
            "recent_repairs": [],
            "stats": {},
        }

        # 数据源 1: Top 5 进程
        async def _fetch_processes():
            try:
                src = snapshot
                if not src or not isinstance(src, dict):
                    src = get_cached_snapshot()
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

                return metrics_history.to_dict()
            except Exception as e:
                logger.warning(f"富上下文:统计信息读取失败 {e}")
            return {}

        # 并行采集
        async def _with_timeout(coro, timeout: float):
            try:
                return await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.TimeoutError:
                return None

        tasks = [
            _with_timeout(_fetch_processes(), _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_alerts(), _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_repairs(), _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
            _with_timeout(_fetch_stats(), _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC),
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            raise

        # 检测 CancelledError 并 reraise
        for result in results:
            if isinstance(result, asyncio.CancelledError):
                raise result

        # 解析结果
        rich_context["top_processes"] = _extract_gather_result(results[0], "进程", list) or []
        rich_context["recent_alerts"] = _extract_gather_result(results[1], "告警", list) or []
        rich_context["recent_repairs"] = _extract_gather_result(results[2], "修复", list) or []
        rich_context["stats"] = _extract_gather_result(results[3], "统计", dict) or {}

        return rich_context


# 默认服务实例
ai_context_service = AIContextService()
