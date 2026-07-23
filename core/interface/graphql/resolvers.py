# -*- coding: utf-8 -*-
"""
GraphQL Resolvers
Implements data fetching logic for GraphQL queries
"""

from datetime import datetime
from typing import List, Optional

from loguru import logger

from .schema import Alert, AlertLevel, Platform, ProcessInfo, RepairAction, SystemMetrics


class MetricsResolver:
    """Resolver for system metrics"""

    async def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            # Integrate with actual metrics collector
            from core.collector import collect_all

            data = collect_all()

            return SystemMetrics(
                cpu_usage=data.get("cpu", {}).get("usage_percent", 0),
                memory_usage=data.get("memory", {}).get("usage_percent", 0),
                disk_usage=data.get("disk", {}).get("usage_percent", 0),
                network_rx=data.get("network", {}).get("rx_bytes", 0),
                network_tx=data.get("network", {}).get("tx_bytes", 0),
                timestamp=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            # Return fallback metrics
            return SystemMetrics(
                cpu_usage=0,
                memory_usage=0,
                disk_usage=0,
                network_rx=0,
                network_tx=0,
                timestamp=datetime.now(),
            )


class AlertResolver:
    """Resolver for alerts"""

    async def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        platform: Optional[Platform] = None,
        resolved: Optional[bool] = None,
        limit: int = 10,
    ) -> List[Alert]:
        """Get alerts with filtering"""
        try:
            # Integrate with actual alert service
            from core.alert_service import alert_service

            result = alert_service.get_alerts(limit=limit)
            alerts_data = result.get("alerts", [])

            # Apply filtering (basic implementation)
            if level:
                alerts_data = [a for a in alerts_data if a.get("level") == level.value]
            if platform:
                alerts_data = [a for a in alerts_data if a.get("platform") == platform.value]
            if resolved is not None:
                alerts_data = [a for a in alerts_data if a.get("resolved", False) == resolved]

            return [
                Alert(
                    id=alert.get("id", ""),
                    level=AlertLevel(alert.get("level", "info")),
                    title=alert.get("title", ""),
                    description=alert.get("description", ""),
                    platform=Platform(alert.get("platform", "unknown")),
                    timestamp=datetime.fromisoformat(
                        alert.get("timestamp", datetime.now().isoformat())
                    ),
                    resolved=alert.get("resolved", False),
                )
                for alert in alerts_data
            ]
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

    async def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        try:
            from core.alert_engine import alert_history

            # Search in alert_history
            for alert_data in alert_history:
                if alert_data.get("id") == alert_id:
                    return Alert(
                        id=alert_data.get("id", ""),
                        level=AlertLevel(alert_data.get("level", "info")),
                        title=alert_data.get("title", ""),
                        description=alert_data.get("description", ""),
                        platform=Platform(alert_data.get("platform", "unknown")),
                        timestamp=datetime.fromisoformat(
                            alert_data.get("timestamp", datetime.now().isoformat())
                        ),
                        resolved=alert_data.get("resolved", False),
                    )
            return None
        except Exception as e:
            logger.error(f"Failed to get alert: {e}")
            return None

    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved"""
        try:
            from core.alert_engine import resolve_alert  # type: ignore

            return resolve_alert(alert_id)  # type: ignore
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False

    async def create_alert(
        self, level: AlertLevel, title: str, description: str, platform: Platform
    ) -> Alert:
        """Create new alert"""
        try:
            import uuid

            from core.alert_engine import alert_history

            # Create alert data
            alert_data = {
                "id": str(uuid.uuid4()),
                "level": level.value,
                "title": title,
                "description": description,
                "platform": platform.value,
                "timestamp": datetime.now().isoformat(),
                "resolved": False,
            }

            # Add to alert_history
            alert_history.appendleft(alert_data)

            return Alert(
                id=str(alert_data["id"]),
                level=level,
                title=title,
                description=description,
                platform=platform,
                timestamp=datetime.fromisoformat(str(alert_data["timestamp"])),
                resolved=False,
            )
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            raise


class ProcessResolver:
    """Resolver for process information"""

    async def get_top_processes(self, limit: int = 5) -> List[ProcessInfo]:
        """Get top processes by CPU usage"""
        try:
            # Integrate with actual process collector
            import asyncio

            from core.collector import get_top_processes

            # 🔧 性能优化: 使用 asyncio.to_thread 避免阻塞事件循环
            processes = await asyncio.to_thread(get_top_processes, limit)

            return [
                ProcessInfo(
                    pid=proc["pid"],
                    name=proc["name"],
                    cpu_percent=proc["cpu_percent"],
                    memory_percent=proc["memory_percent"],
                    status=proc["status"],
                )
                for proc in processes
            ]
        except Exception as e:
            logger.error(f"Failed to get processes: {e}")
            return []


class RepairResolver:
    """Resolver for repair actions"""

    async def execute_repair(
        self, script_key: str, parameters: Optional[dict] = None
    ) -> RepairAction:
        """Execute a repair action"""
        try:
            # Integrate with actual repair engine
            import time

            from core.repair_engine import execute_repair

            start_time = time.time()
            result = await execute_repair(script_key, parameters or {})
            duration_ms = int((time.time() - start_time) * 1000)

            return RepairAction(
                id=result.get("id", f"repair-{start_time}"),
                script_key=script_key,
                success=result.get("success", False),
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                error_message=result.get("error"),
            )
        except Exception as e:
            logger.error(f"Failed to execute repair: {e}")
            raise

    async def get_recent_repairs(self, limit: int = 10) -> List[RepairAction]:
        """Get recent repair actions"""
        try:
            from core.db_engine import async_query_repairs

            repairs = await async_query_repairs(today_only=False, limit=limit)

            return [
                RepairAction(
                    id=repair.get("id", ""),
                    script_key=repair.get("script_key", "unknown"),
                    success=repair.get("success", False),
                    duration_ms=int(repair.get("repair_duration_sec", 0) * 1000),
                    timestamp=datetime.fromisoformat(
                        repair.get("repair_time", datetime.now().isoformat())
                    ),
                    error_message=repair.get("error_message"),
                )
                for repair in repairs
            ]
        except Exception as e:
            logger.error(f"Failed to get repairs: {e}")
            return []
