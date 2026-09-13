# -*- coding: utf-8 -*-
"""
WebSocket Integration (Phase 2)
Integration of WebSocket real-time communication with system components
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from loguru import logger

if TYPE_CHECKING:
    from core.enhanced_websocket_manager import EnhancedWebSocketManager
    from core.websocket_manager import ConnectionManager


def _collect_system_metrics() -> Dict[str, Any]:
    """Collect real host metrics via psutil (CPU / memory / disk)."""
    metrics: Dict[str, Any] = {}
    try:
        import psutil

        metrics["cpu_usage"] = psutil.cpu_percent(interval=None)
        metrics["memory_usage"] = psutil.virtual_memory().percent
        metrics["disk_usage"] = psutil.disk_usage(os.path.abspath(os.sep)).percent
    except Exception as e:  # noqa: BLE001 - 采集失败时如实反映
        logger.warning(f"Failed to collect system metrics: {e}")
    return metrics


def _alert_identity(alert: Dict[str, Any]) -> Any:
    """Derive a stable identity for an alert dict (for de-duplication)."""
    if not isinstance(alert, dict):
        return repr(alert)
    for key in ("id", "alert_id", "alertId", "uuid"):
        if alert.get(key) is not None:
            return (key, str(alert[key]))
    return (
        str(alert.get("timestamp")),
        str(alert.get("title") or alert.get("name") or alert.get("message") or ""),
        str(alert.get("severity") or ""),
    )


async def _dispatch(handlers: List[Callable], payload: Any) -> None:
    """Invoke registered handlers, awaiting results when needed."""
    for handler in handlers:
        try:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:  # noqa: BLE001 - 单个 handler 失败不应中断广播
            logger.error(f"Streaming handler failed: {e}")


@dataclass
class WebSocketIntegrationConfig:
    """WebSocket integration configuration"""

    enable_realtime_alerts: bool = True
    enable_realtime_metrics: bool = True
    enable_realtime_logs: bool = True
    enable_realtime_status: bool = True
    alert_channel: str = "alerts"
    metrics_channel: str = "metrics"
    logs_channel: str = "logs"
    status_channel: str = "status"
    # 轮询周期（秒）：真实数据源采集/推送间隔
    alert_poll_interval: float = 10.0
    metrics_poll_interval: float = 5.0
    log_poll_interval: float = 1.0


class WebSocketIntegrator:
    """WebSocket integration with system components"""

    def __init__(self, config: Optional[WebSocketIntegrationConfig] = None):
        """
        Initialize WebSocket integrator

        Args:
            config: WebSocket integration configuration
        """
        self.config = config or WebSocketIntegrationConfig()

        # WebSocket manager reference
        self.websocket_manager: Optional["EnhancedWebSocketManager | ConnectionManager"] = None
        self._initialize_websocket_manager()

        # Event handlers
        self.alert_handlers: List[Callable] = []
        self.metrics_handlers: List[Callable] = []
        self.log_handlers: List[Callable] = []
        self.status_handlers: List[Callable] = []

        # Integration status
        self.is_running = False
        self.background_tasks: List[asyncio.Task] = []

        logger.info("WebSocket integrator initialized")

    def _initialize_websocket_manager(self):
        """Initialize WebSocket manager"""
        try:
            from core.enhanced_websocket_manager import get_enhanced_websocket_manager

            self.websocket_manager = get_enhanced_websocket_manager()
            logger.info("WebSocket manager initialized for integration")
        except ImportError:
            logger.warning("Enhanced WebSocket manager not available, using basic manager")
            try:
                from core.websocket_manager import manager

                self.websocket_manager = manager
                logger.info("Basic WebSocket manager initialized for integration")
            except ImportError:
                logger.error("No WebSocket manager available")

    async def start(self) -> None:
        """Start WebSocket integration"""
        if self.is_running:
            logger.warning("WebSocket integration already running")
            return

        try:
            # Start heartbeat if using enhanced manager
            if self.websocket_manager and hasattr(self.websocket_manager, "start_heartbeat"):
                await self.websocket_manager.start_heartbeat()  # type: ignore[union-attr]

            # Register message handlers
            self._register_message_handlers()

            # Start background tasks
            await self._start_background_tasks()

            self.is_running = True
            logger.info("WebSocket integration started successfully")

        except Exception as e:
            logger.error(f"Failed to start WebSocket integration: {e}")

    async def stop(self) -> None:
        """Stop WebSocket integration"""
        if not self.is_running:
            return

        try:
            # Stop background tasks
            for task in self.background_tasks:
                task.cancel()

            # Stop heartbeat if running
            if self.websocket_manager and hasattr(self.websocket_manager, "stop_heartbeat"):
                await self.websocket_manager.stop_heartbeat()  # type: ignore[union-attr]

            self.is_running = False
            logger.info("WebSocket integration stopped successfully")

        except Exception as e:
            logger.error(f"Failed to stop WebSocket integration: {e}")

    def _register_message_handlers(self) -> None:
        """Register message handlers"""
        if not self.websocket_manager:
            return

        try:
            from core.enhanced_websocket_manager import MessageType

            # Only register handlers if the manager supports it
            if not hasattr(self.websocket_manager, "register_message_handler"):
                logger.warning("WebSocket manager does not support message handlers")
                return

            # Register alert handler
            async def alert_handler(websocket, message):
                for handler in self.alert_handlers:
                    await handler(message.data)

            self.websocket_manager.register_message_handler(  # type: ignore[union-attr]
                MessageType.ALERT, alert_handler
            )

            # Register metrics handler
            async def metrics_handler(websocket, message):
                for handler in self.metrics_handlers:
                    await handler(message.data)

            self.websocket_manager.register_message_handler(  # type: ignore[union-attr]
                MessageType.METRIC, metrics_handler
            )

            # Register log handler
            async def log_handler(websocket, message):
                for handler in self.log_handlers:
                    await handler(message.data)

            self.websocket_manager.register_message_handler(  # type: ignore[union-attr]
                MessageType.LOG, log_handler
            )

            logger.info("WebSocket message handlers registered")

        except Exception as e:
            logger.error(f"Failed to register message handlers: {e}")

    async def _start_background_tasks(self) -> None:
        """Start background integration tasks"""
        # Alert monitoring task
        if self.config.enable_realtime_alerts:
            alert_task = asyncio.create_task(self._alert_monitoring_loop())
            self.background_tasks.append(alert_task)

        # Metrics streaming task
        if self.config.enable_realtime_metrics:
            metrics_task = asyncio.create_task(self._metrics_streaming_loop())
            self.background_tasks.append(metrics_task)

        # Log streaming task
        if self.config.enable_realtime_logs:
            log_task = asyncio.create_task(self._log_streaming_loop())
            self.background_tasks.append(log_task)

        # Status broadcasting task
        if self.config.enable_realtime_status:
            status_task = asyncio.create_task(self._status_broadcasting_loop())
            self.background_tasks.append(status_task)

        logger.info(f"Started {len(self.background_tasks)} background integration tasks")

    async def _alert_monitoring_loop(self) -> None:
        """Background alert monitoring loop (real alert source).

        历史问题（已修复）：曾仅 ``await asyncio.sleep(10)`` 空转（注释 "For now,
        simulate alert generation"），实时告警通道从不推送任何真实告警。现从真实告警
        引擎 ``core.alert_engine.alert_history`` 增量读取新告警并广播。
        """
        try:
            from core.alert_engine import alert_history
        except Exception as e:  # noqa: BLE001 - 无真实告警源则不启动（不伪造）
            logger.error(f"Alert engine unavailable; alert monitoring disabled: {e}")
            return

        seen = {_alert_identity(a) for a in list(alert_history)}
        try:
            while self.is_running:
                await asyncio.sleep(self.config.alert_poll_interval)
                pending = [
                    a for a in list(alert_history) if _alert_identity(a) not in seen
                ]
                # alert_history 为 appendleft，list() 为最新在前 -> 反转按时间顺序推送
                for alert in reversed(pending):
                    seen.add(_alert_identity(alert))
                    await _dispatch(self.alert_handlers, alert)
                    await self.broadcast_alert(alert)
                if len(seen) > 10000:  # 防止无界增长
                    seen = {_alert_identity(a) for a in list(alert_history)}
        except asyncio.CancelledError:
            logger.info("Alert monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Alert monitoring loop error: {e}")

    async def _metrics_streaming_loop(self) -> None:
        """Background metrics streaming loop (real host metrics).

        历史问题（已修复）：曾仅 ``await asyncio.sleep(5)`` 空转（注释 "For now,
        simulate metrics streaming"）。现按周期采集真实主机指标（psutil）并广播。
        """
        try:
            while self.is_running:
                metrics = await asyncio.to_thread(_collect_system_metrics)
                if metrics:
                    payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metrics": metrics,
                    }
                    await _dispatch(self.metrics_handlers, payload)
                    await self.broadcast_metrics(payload)
                await asyncio.sleep(self.config.metrics_poll_interval)
        except asyncio.CancelledError:
            logger.info("Metrics streaming loop cancelled")
        except Exception as e:
            logger.error(f"Metrics streaming loop error: {e}")

    async def _log_streaming_loop(self) -> None:
        """Background log streaming loop (real application logs).

        历史问题（已修复）：曾仅 ``await asyncio.sleep(15)`` 空转（注释 "For now,
        simulate log streaming"）。现挂接一个真实的 ``logging.Handler``，捕获应用日志
        记录并广播到日志通道；无日志时不推送任何内容（不伪造）。
        """
        import logging
        from collections import deque

        buffer: "deque[Dict[str, Any]]" = deque(maxlen=1000)

        class _BufferHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                try:
                    buffer.append(
                        {
                            "timestamp": datetime.fromtimestamp(
                                record.created, timezone.utc
                            ).isoformat(),
                            "level": record.levelname,
                            "logger": record.name,
                            "message": record.getMessage(),
                        }
                    )
                except Exception:  # noqa: BLE001 - 日志捕获失败不得影响主流程
                    pass

        handler = _BufferHandler(level=logging.INFO)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            while self.is_running:
                await asyncio.sleep(self.config.log_poll_interval)
                while buffer:
                    entry = buffer.popleft()
                    await _dispatch(self.log_handlers, entry)
                    await self.broadcast_log(entry)
        except asyncio.CancelledError:
            logger.info("Log streaming loop cancelled")
        except Exception as e:
            logger.error(f"Log streaming loop error: {e}")
        finally:
            root_logger.removeHandler(handler)

    async def _status_broadcasting_loop(self) -> None:
        """Background status broadcasting loop"""
        try:
            while self.is_running:
                # Broadcast system status
                status_data = await self._get_system_status()

                if self.websocket_manager:
                    try:
                        from core.enhanced_websocket_manager import MessageType, WebSocketMessage

                        status_message = WebSocketMessage(
                            message_type=MessageType.STATUS,
                            data=status_data,
                            channel=self.config.status_channel,
                        )
                        await self.websocket_manager.broadcast(
                            status_message, self.config.status_channel
                        )
                    except Exception as e:
                        logger.error(f"Failed to broadcast status: {e}")

                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("Status broadcasting loop cancelled")
        except Exception as e:
            logger.error(f"Status broadcasting loop error: {e}")

    async def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status (real host metrics via psutil).

        历史问题（已修复）：曾返回硬编码 cpu 45.2 / mem 62.8 / disk 38.5 与全层
        "healthy"。现采集真实指标，并由指标阈值推导整体及各层状态。
        """
        metrics = await asyncio.to_thread(_collect_system_metrics)
        thresholds = {"cpu_usage": 90.0, "memory_usage": 90.0, "disk_usage": 90.0}
        degraded = any(
            metrics.get(metric) is not None and metrics[metric] >= limit
            for metric, limit in thresholds.items()
        )
        overall = "degraded" if degraded else "healthy"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": overall,
            "components": {f"L{layer}": overall for layer in range(1, 8)},
            "metrics": metrics,
        }

    def register_alert_handler(self, handler: Callable) -> None:
        """
        Register alert handler

        Args:
            handler: Alert handler function
        """
        self.alert_handlers.append(handler)
        logger.info("Registered alert handler")

    def register_metrics_handler(self, handler: Callable) -> None:
        """
        Register metrics handler

        Args:
            handler: Metrics handler function
        """
        self.metrics_handlers.append(handler)
        logger.info("Registered metrics handler")

    def register_log_handler(self, handler: Callable) -> None:
        """
        Register log handler

        Args:
            handler: Log handler function
        """
        self.log_handlers.append(handler)
        logger.info("Registered log handler")

    def register_status_handler(self, handler: Callable) -> None:
        """
        Register status handler

        Args:
            handler: Status handler function
        """
        self.status_handlers.append(handler)
        logger.info("Registered status handler")

    async def broadcast_alert(self, alert_data: Dict[str, Any]) -> int:
        """
        Broadcast alert to WebSocket clients

        Args:
            alert_data: Alert data

        Returns:
            Number of clients message was sent to
        """
        if not self.websocket_manager or not self.is_running:
            return 0

        try:
            from core.enhanced_websocket_manager import MessageType, WebSocketMessage

            alert_message = WebSocketMessage(
                message_type=MessageType.ALERT, data=alert_data, channel=self.config.alert_channel
            )

            return await self.websocket_manager.broadcast(alert_message, self.config.alert_channel)

        except Exception as e:
            logger.error(f"Failed to broadcast alert: {e}")
            return 0

    async def broadcast_metrics(self, metrics_data: Dict[str, Any]) -> int:
        """
        Broadcast metrics to WebSocket clients

        Args:
            metrics_data: Metrics data

        Returns:
            Number of clients message was sent to
        """
        if not self.websocket_manager or not self.is_running:
            return 0

        try:
            from core.enhanced_websocket_manager import MessageType, WebSocketMessage

            metrics_message = WebSocketMessage(
                message_type=MessageType.METRIC,
                data=metrics_data,
                channel=self.config.metrics_channel,
            )

            return await self.websocket_manager.broadcast(
                metrics_message, self.config.metrics_channel
            )

        except Exception as e:
            logger.error(f"Failed to broadcast metrics: {e}")
            return 0

    async def broadcast_log(self, log_data: Dict[str, Any]) -> int:
        """
        Broadcast log to WebSocket clients

        Args:
            log_data: Log data

        Returns:
            Number of clients message was sent to
        """
        if not self.websocket_manager or not self.is_running:
            return 0

        try:
            from core.enhanced_websocket_manager import MessageType, WebSocketMessage

            log_message = WebSocketMessage(
                message_type=MessageType.LOG, data=log_data, channel=self.config.logs_channel
            )

            return await self.websocket_manager.broadcast(log_message, self.config.logs_channel)

        except Exception as e:
            logger.error(f"Failed to broadcast log: {e}")
            return 0

    def get_integration_status(self) -> Dict[str, Any]:
        """Get WebSocket integration status"""
        return {
            "is_running": self.is_running,
            "websocket_manager_available": self.websocket_manager is not None,
            "background_tasks_count": len(self.background_tasks),
            "config": {
                "enable_realtime_alerts": self.config.enable_realtime_alerts,
                "enable_realtime_metrics": self.config.enable_realtime_metrics,
                "enable_realtime_logs": self.config.enable_realtime_logs,
                "enable_realtime_status": self.config.enable_realtime_status,
                "alert_channel": self.config.alert_channel,
                "metrics_channel": self.config.metrics_channel,
                "logs_channel": self.config.logs_channel,
                "status_channel": self.config.status_channel,
            },
            "handlers": {
                "alert_handlers": len(self.alert_handlers),
                "metrics_handlers": len(self.metrics_handlers),
                "log_handlers": len(self.log_handlers),
                "status_handlers": len(self.status_handlers),
            },
        }


def get_websocket_integrator(
    config: Optional[WebSocketIntegrationConfig] = None,
) -> WebSocketIntegrator:
    """
    Factory function to get WebSocket integrator instance

    Args:
        config: Optional configuration

    Returns:
        WebSocketIntegrator: Integrator instance
    """
    return WebSocketIntegrator(config)
