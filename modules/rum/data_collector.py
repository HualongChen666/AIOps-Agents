# -*- coding: utf-8 -*-
"""
data_collector.py
----------------
RUM 建设 - 数据采集模块。

功能：
- RUM 数据接收
- 数据验证
- 数据聚合
- 数据存储
- 实时分析
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 事件类型枚举
# ----------------------------------------------------------------------
class RUMEventType(Enum):
    """RUM 事件类型"""

    PAGE_VIEW = "page_view"
    PAGE_LOAD = "page_load"
    ERROR = "error"
    CUSTOM = "custom"
    SCREEN_VIEW = "screen_view"
    LCP = "lcp"
    FCP = "fcp"
    TTFB = "ttfb"


# ----------------------------------------------------------------------
# 2️⃣ RUM 事件
# ----------------------------------------------------------------------
@dataclass
class RUMEvent:
    """RUM 事件"""

    event_id: str
    event_type: RUMEventType
    session_id: str
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]
    received_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "received_at": self.received_at.isoformat(),
        }


# ----------------------------------------------------------------------
# 3️⃣ 会话聚合数据
# ----------------------------------------------------------------------
@dataclass
class SessionAggregation:
    """会话聚合数据"""

    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    page_views: int = 0
    errors: int = 0
    total_duration: float = 0.0
    avg_load_time: float = 0.0
    platform: str = ""
    browser: str = ""
    device: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "page_views": self.page_views,
            "errors": self.errors,
            "total_duration": self.total_duration,
            "avg_load_time": self.avg_load_time,
            "platform": self.platform,
            "browser": self.browser,
            "device": self.device,
        }


# ----------------------------------------------------------------------
# 4️⃣ 数据验证器
# ----------------------------------------------------------------------
class RUMDataValidator:
    """RUM 数据验证器"""

    def __init__(self):
        self.required_fields = {
            "session_id": str,
            "timestamp": str,
        }

    def validate_event(self, event_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        验证事件数据

        Parameters
        ----------
        event_data : Dict[str, Any]
            事件数据

        Returns
        -------
        tuple[bool, List[str]]
            (是否有效, 错误列表)
        """
        errors = []

        # 检查必需字段
        for field_name, field_type in self.required_fields.items():
            if field_name not in event_data:
                errors.append(f"Missing required field: {field_name}")
            elif not isinstance(event_data[field_name], field_type):
                errors.append(f"Invalid type for {field_name}: expected {field_type}")

        # 验证时间戳格式
        if "timestamp" in event_data:
            try:
                datetime.fromisoformat(event_data["timestamp"])
            except ValueError:
                errors.append("Invalid timestamp format")

        # 验证会话 ID 格式
        if "session_id" in event_data:
            session_id = event_data["session_id"]
            if not isinstance(session_id, str) or len(session_id) < 10:
                errors.append("Invalid session_id format")

        return len(errors) == 0, errors

    def sanitize_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理数据

        Parameters
        ----------
        event_data : Dict[str, Any]
            原始数据

        Returns
        -------
        Dict[str, Any]
            清理后的数据
        """
        sanitized = event_data.copy()

        # 移除敏感字段
        sensitive_fields = ["password", "token", "secret", "api_key"]
        for field_name in sensitive_fields:
            if field_name in sanitized:
                sanitized[field_name] = "***REDACTED***"

        # 限制字符串长度
        for key, value in sanitized.items():
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "...[truncated]"

        return sanitized


# ----------------------------------------------------------------------
# 5️⃣ 数据接收器
# ----------------------------------------------------------------------
class RUMDataReceiver:
    """RUM 数据接收器"""

    def __init__(self):
        self.validator = RUMDataValidator()
        self.received_events: List[RUMEvent] = []
        self.rejected_events: List[Dict[str, Any]] = []

    def receive_event(self, event_data: Dict[str, Any]) -> Optional[RUMEvent]:
        """
        接收事件

        Parameters
        ----------
        event_data : Dict[str, Any]
            事件数据

        Returns
        -------
        RUMEvent or None
            解析后的事件
        """
        # 验证数据
        is_valid, errors = self.validator.validate_event(event_data)

        if not is_valid:
            self.rejected_events.append(
                {
                    "data": event_data,
                    "errors": errors,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            logger.warning(f"Invalid event data: {errors}")
            return None

        # 清理数据
        sanitized_data = self.validator.sanitize_data(event_data)

        # 创建事件对象
        event = RUMEvent(
            event_id=f"evt-{int(datetime.now().timestamp() * 1000)}",
            event_type=RUMEventType(sanitized_data.get("type", "custom")),
            session_id=sanitized_data["session_id"],
            user_id=sanitized_data.get("user_id", "anonymous"),
            timestamp=datetime.fromisoformat(sanitized_data["timestamp"]),
            data=sanitized_data,
        )

        self.received_events.append(event)
        logger.debug(f"Received event: {event.event_type.value} for session {event.session_id}")

        return event

    def receive_batch(self, events_data: List[Dict[str, Any]]) -> List[RUMEvent]:
        """
        批量接收事件

        Parameters
        ----------
        events_data : List[Dict[str, Any]]
            事件数据列表

        Returns
        -------
        List[RUMEvent]
            解析后的事件列表
        """
        events = []

        for event_data in events_data:
            event = self.receive_event(event_data)
            if event:
                events.append(event)

        return events

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_received": len(self.received_events),
            "total_rejected": len(self.rejected_events),
            "by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> Dict[str, int]:
        """按类型统计"""
        counts: Dict[str, int] = {}
        for event in self.received_events:
            event_type = event.event_type.value
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts


# ----------------------------------------------------------------------
# 6️⃣ 数据聚合器
# ----------------------------------------------------------------------
class RUMDataAggregator:
    """RUM 数据聚合器"""

    def __init__(self):
        self.session_aggregations: Dict[str, SessionAggregation] = {}
        self.load_times: List[float] = []

    def aggregate_event(self, event: RUMEvent):
        """
        聚合事件

        Parameters
        ----------
        event : RUMEvent
            RUM 事件
        """
        session_id = event.session_id

        # 获取或创建会话聚合
        if session_id not in self.session_aggregations:
            self.session_aggregations[session_id] = SessionAggregation(
                session_id=session_id,
                user_id=event.user_id,
                start_time=event.timestamp,
            )

        aggregation = self.session_aggregations[session_id]

        # 根据事件类型更新聚合数据
        if event.event_type == RUMEventType.PAGE_VIEW:
            aggregation.page_views += 1
        elif event.event_type == RUMEventType.ERROR:
            aggregation.errors += 1
        elif event.event_type == RUMEventType.PAGE_LOAD:
            load_time = event.data.get("load_time", 0)
            if load_time > 0:
                self.load_times.append(load_time)
                # 更新平均加载时间
                aggregation.avg_load_time = sum(self.load_times) / len(self.load_times)

        # 更新会话信息
        aggregation.end_time = event.timestamp
        aggregation.total_duration = (aggregation.end_time - aggregation.start_time).total_seconds()

        # 提取设备信息
        if "userAgent" in event.data:
            aggregation.browser = self._extract_browser(event.data["userAgent"])
        if "platform" in event.data:
            aggregation.platform = event.data["platform"]

    def _extract_browser(self, user_agent: str) -> str:
        """提取浏览器信息"""
        user_agent_lower = user_agent.lower()

        if "chrome" in user_agent_lower:
            return "Chrome"
        elif "firefox" in user_agent_lower:
            return "Firefox"
        elif "safari" in user_agent_lower:
            return "Safari"
        elif "edge" in user_agent_lower:
            return "Edge"
        else:
            return "Unknown"

    def get_session_aggregation(self, session_id: str) -> Optional[SessionAggregation]:
        """获取会话聚合数据"""
        return self.session_aggregations.get(session_id)

    def get_all_aggregations(self) -> List[SessionAggregation]:
        """获取所有聚合数据"""
        return list(self.session_aggregations.values())

    def get_aggregation_statistics(self) -> Dict[str, Any]:
        """获取聚合统计"""
        aggregations = self.get_all_aggregations()

        if not aggregations:
            return {}

        total_sessions = len(aggregations)
        total_page_views = sum(a.page_views for a in aggregations)
        total_errors = sum(a.errors for a in aggregations)
        avg_duration = sum(a.total_duration for a in aggregations) / total_sessions
        avg_load_time = (
            sum(a.avg_load_time for a in aggregations if a.avg_load_time > 0)
            / len([a for a in aggregations if a.avg_load_time > 0])
            if aggregations
            else 0
        )

        return {
            "total_sessions": total_sessions,
            "total_page_views": total_page_views,
            "total_errors": total_errors,
            "avg_session_duration": avg_duration,
            "avg_page_load_time": avg_load_time,
            "error_rate": total_errors / total_page_views if total_page_views > 0 else 0,
        }


# ----------------------------------------------------------------------
# 7️⃣ 实时分析器
# ----------------------------------------------------------------------
class RUMRealTimeAnalyzer:
    """RUM 实时分析器"""

    def __init__(self):
        self.alert_thresholds = {
            "avg_load_time": 3000,  # 毫秒
            "error_rate": 0.05,  # 5%
            "session_duration": 0,  # 不限制
        }
        self.alerts: List[Dict[str, Any]] = []

    def analyze_event(self, event: RUMEvent):
        """
        分析事件

        Parameters
        ----------
        event : RUMEvent
            RUM 事件
        """
        # 检查页面加载时间
        if event.event_type == RUMEventType.PAGE_LOAD:
            load_time = event.data.get("load_time", 0)
            if load_time > self.alert_thresholds["avg_load_time"]:
                self._create_alert(
                    "slow_page_load",
                    f"Slow page load detected: {load_time}ms",
                    event.session_id,
                )

        # 检查错误
        if event.event_type == RUMEventType.ERROR:
            self._create_alert(
                "error_detected",
                f"Error detected: {event.data.get('errorMessage', 'Unknown')}",
                event.session_id,
            )

    def analyze_aggregation(self, aggregation: SessionAggregation):
        """
        分析聚合数据

        Parameters
        ----------
        aggregation : SessionAggregation
            会话聚合数据
        """
        # 检查错误率
        if aggregation.page_views > 0:
            error_rate = aggregation.errors / aggregation.page_views
            if error_rate > self.alert_thresholds["error_rate"]:
                self._create_alert(
                    "high_error_rate",
                    f"High error rate: {error_rate:.2%}",
                    aggregation.session_id,
                )

    def _create_alert(
        self,
        alert_type: str,
        message: str,
        session_id: str,
    ):
        """创建告警"""
        alert = {
            "alert_type": alert_type,
            "message": message,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }

        self.alerts.append(alert)
        logger.warning(f"RUM Alert: {message}")

    def get_alerts(
        self,
        hours: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        获取告警

        Parameters
        ----------
        hours : int
            时间范围（小时）

        Returns
        -------
        List[Dict[str, Any]]
            告警列表
        """
        cutoff = datetime.now() - timedelta(hours=hours)

        return [
            alert for alert in self.alerts if datetime.fromisoformat(alert["timestamp"]) >= cutoff
        ]


# ----------------------------------------------------------------------
# 8️⃣ RUM 数据收集器
# ----------------------------------------------------------------------
class RUMDataCollector:
    """RUM 数据收集器"""

    def __init__(self):
        self.receiver = RUMDataReceiver()
        self.aggregator = RUMDataAggregator()
        self.analyzer = RUMRealTimeAnalyzer()

    def process_event(self, event_data: Dict[str, Any]) -> Optional[RUMEvent]:
        """
        处理事件

        Parameters
        ----------
        event_data : Dict[str, Any]
            事件数据

        Returns
        -------
        RUMEvent or None
            处理后的事件
        """
        # 接收事件
        event = self.receiver.receive_event(event_data)

        if event:
            # 聚合事件
            self.aggregator.aggregate_event(event)

            # 实时分析
            self.analyzer.analyze_event(event)

        return event

    def process_batch(self, events_data: List[Dict[str, Any]]) -> List[RUMEvent]:
        """
        批量处理事件

        Parameters
        ----------
        events_data : List[Dict[str, Any]]
            事件数据列表

        Returns
        -------
        List[RUMEvent]
            处理后的事件列表
        """
        events = []

        for event_data in events_data:
            event = self.process_event(event_data)
            if event:
                events.append(event)

        return events

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        return {
            "receiver_stats": self.receiver.get_statistics(),
            "aggregation_stats": self.aggregator.get_aggregation_statistics(),
            "recent_alerts": self.analyzer.get_alerts(hours=1),
            "top_sessions": self._get_top_sessions(),
        }

    def _get_top_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取顶级会话"""
        aggregations = self.aggregator.get_all_aggregations()

        # 按页面浏览量排序
        sorted_sessions = sorted(
            aggregations,
            key=lambda a: a.page_views,
            reverse=True,
        )

        return [a.to_dict() for a in sorted_sessions[:limit]]


# ----------------------------------------------------------------------
# 9️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_rum_data_collector() -> RUMDataCollector:
    """创建 RUM 数据收集器"""
    return RUMDataCollector()


# ----------------------------------------------------------------------
# 🔟 CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试 RUM 数据收集器
    logger.info("Testing RUM data collector")

    collector = create_rum_data_collector()

    # 模拟接收事件
    test_events = [
        {
            "type": "page_view",
            "session_id": "session-123",
            "user_id": "user-1",
            "timestamp": datetime.now().isoformat(),
            "pageUrl": "https://example.com/home",
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
        },
        {
            "type": "page_load",
            "session_id": "session-123",
            "user_id": "user-1",
            "timestamp": datetime.now().isoformat(),
            "loadTime": 2500,
            "domContentLoaded": 1500,
            "firstPaint": 800,
        },
        {
            "type": "error",
            "session_id": "session-123",
            "user_id": "user-1",
            "timestamp": datetime.now().isoformat(),
            "errorMessage": "ReferenceError: foo is not defined",
            "stackTrace": "at bar (script.js:10)",
        },
    ]

    # 处理事件
    for event_data in test_events:
        collector.process_event(event_data)  # type: ignore

    # 获取仪表板数据
    dashboard = collector.get_dashboard_data()
    logger.info(f"Dashboard data: {dashboard}")

    logger.info("Test passed!")
