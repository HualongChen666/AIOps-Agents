# -*- coding: utf-8 -*-
"""
alert_service.py
--------------
告警服务层

提供告警查询、清空等业务逻辑，遵循分层架构原则：Controller → Service → Repository。
"""

from __future__ import annotations

import logging
from typing import Any

from core.alert_engine import alert_history
from core.db_engine import clear_alerts as db_clear_alerts
from core.query_optimization import query_cache

logger = logging.getLogger(__name__)


class AlertService:
    """告警服务"""

    def get_alerts(self, limit: int = 20) -> dict[str, Any]:
        """
        获取告警历史列表（使用查询优化）

        Args:
            limit: 返回的告警最大条数

        Returns:
            包含 total 和 alerts 的字典
        """
        cache_key = f"alerts_{limit}"

        # 尝试从缓存获取（仅当缓存中的 total 与当前 alert_history 长度一致时才命中，避免返回过期数据）
        cached_result = query_cache.get(cache_key)
        if cached_result is not None and cached_result.get("total") == len(alert_history):
            logger.debug(f"告警查询缓存命中: {cache_key}")
            return cached_result  # type: ignore[no-any-return]

        logger.info(f"查询告警历史列表,limit={limit}")

        try:
            alerts_list = list(alert_history)
        except Exception as e:
            logger.error(f"alert_history 转换异常: {e}", exc_info=True)
            return {"total": 0, "alerts": []}

        latest_alerts = alerts_list[:limit]

        result = {"total": len(alerts_list), "alerts": latest_alerts}

        # 缓存结果
        query_cache.set(cache_key, result, ttl=60)  # 1分钟缓存

        logger.debug(f"告警查询完成 | 总计={len(alerts_list)}条 | 返回={len(latest_alerts)}条")

        return result

        return {
            "total": len(alerts_list),
            "alerts": latest_alerts,
        }

    def clear_alerts(self, operator_ip: str = "unknown") -> dict[str, Any]:
        """
        清空告警历史

        Args:
            operator_ip: 操作人 IP

        Returns:
            操作结果字典
        """
        logger.info(f"清空告警历史,操作人 IP={operator_ip}")

        try:
            snapshot = list(alert_history)
            count_before = len(snapshot)
            alert_history.clear()
        except Exception as e:
            logger.error(
                f"内存告警清空异常: {e} | operator={operator_ip}",
                exc_info=True,
            )
            return {
                "status": "error",
                "msg": f"内存清空异常: {str(e)[:200]}",
                "deleted_count": 0,
            }

        logger.warning(
            f"⚠️ 执行告警历史清空操作 | operator={operator_ip} | 清空前共 {count_before} 条记录"
        )

        # SQLite 清空(失败不影响内存清空结果)
        db_deleted = 0
        try:
            db_deleted = db_clear_alerts()
        except Exception as db_err:
            logger.error(
                f"SQLite 告警清空失败(内存已清): {db_err}",
                exc_info=True,
            )

        logger.warning(
            f"✅ 告警历史已清空 | operator={operator_ip} | "
            f"内存删除={count_before}条 | SQLite删除={db_deleted}条"
        )

        return {
            "status": "ok",
            "msg": "告警历史已清空",
            "deleted_count": count_before,
            "sqlite_deleted": db_deleted,
            "operator_ip": operator_ip,
        }


# 默认服务实例
alert_service = AlertService()
