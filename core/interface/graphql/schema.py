# -*- coding: utf-8 -*-
"""
GraphQL Schema Definition
Defines types, queries, and mutations for AIOps Agent
"""

from datetime import datetime
from enum import Enum
from typing import AsyncGenerator, List, Optional

import strawberry


@strawberry.enum
class AlertLevel(Enum):
    """Alert level enumeration"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@strawberry.enum
class Platform(Enum):
    """Platform enumeration"""

    WINDOWS = "windows"
    LINUX = "linux"


@strawberry.type
class SystemMetrics:
    """System metrics type"""

    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_rx: int
    network_tx: int
    timestamp: datetime


@strawberry.type
class ProcessInfo:
    """Process information"""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str


@strawberry.type
class Alert:
    """Alert type"""

    id: str
    level: AlertLevel
    title: str
    description: str
    platform: Platform
    timestamp: datetime
    resolved: bool = False


@strawberry.type
class RepairAction:
    """Repair action type"""

    id: str
    script_key: str
    success: bool
    duration_ms: int
    timestamp: datetime
    error_message: Optional[str] = None


@strawberry.type
class AIAnalysis:
    """AI analysis result"""

    id: str
    query: str
    result: str
    model_used: str
    timestamp: datetime
    tokens_used: int


@strawberry.input
class AlertFilter:
    """Alert filter input"""

    level: Optional[AlertLevel] = None
    platform: Optional[Platform] = None
    resolved: Optional[bool] = None
    limit: int = 10


@strawberry.input
class RepairInput:
    """Repair action input"""

    script_key: str
    parameters: Optional[dict] = None


@strawberry.type
class Query:
    """GraphQL query root"""

    @strawberry.field
    async def metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            from core.collector import collect_all

            data = collect_all()
            return SystemMetrics(
                cpu_usage=data.get("cpu", {}).get("usage_percent", 0.0),
                memory_usage=data.get("memory", {}).get("usage_percent", 0.0),
                disk_usage=data.get("disk", {}).get("usage_percent", 0.0),
                network_rx=data.get("network", {}).get("rx_bytes", 0),
                network_tx=data.get("network", {}).get("tx_bytes", 0),
                timestamp=datetime.now(),
            )
        except Exception:
            return SystemMetrics(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_rx=0,
                network_tx=0,
                timestamp=datetime.now(),
            )

    @strawberry.field
    async def alerts(self, filter: Optional[AlertFilter] = None) -> List[Alert]:
        """Get alerts with optional filtering"""
        try:
            from core.alert_service import alert_service

            result = alert_service.get_alerts(limit=(filter.limit if filter else 10))
            alerts_data = result.get("alerts", [])

            if filter:
                if filter.level:
                    alerts_data = [
                        a for a in alerts_data if a.get("level") == filter.level.value
                    ]
                if filter.platform:
                    alerts_data = [
                        a for a in alerts_data if a.get("platform") == filter.platform.value
                    ]
                if filter.resolved is not None:
                    alerts_data = [
                        a for a in alerts_data if a.get("resolved", False) == filter.resolved
                    ]

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
        except Exception:
            return []

    @strawberry.field
    async def top_processes(self, limit: int = 5) -> List[ProcessInfo]:
        """Get top processes by CPU usage"""
        try:
            import asyncio

            from core.collector import get_top_processes

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
        except Exception:
            return []

    @strawberry.field
    async def recent_repairs(self, limit: int = 10) -> List[RepairAction]:
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
                        repair.get("timestamp", datetime.now().isoformat())
                    ),
                )
                for repair in repairs
            ]
        except Exception:
            return []

    @strawberry.field
    async def alert(self, id: str) -> Optional[Alert]:
        """Get alert by ID"""
        try:
            from core.alert_engine import alert_history

            for alert_data in alert_history:
                if alert_data.get("id") == id:
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
        except Exception:
            return None


@strawberry.type
class Mutation:
    """GraphQL mutation root"""

    @strawberry.mutation
    async def execute_repair(self, input: RepairInput) -> RepairAction:
        """Execute a repair action"""
        import time

        from core.repair_engine import execute_repair

        start_time = time.time()
        result = await execute_repair(input.script_key, input.parameters or {})
        duration_ms = int((time.time() - start_time) * 1000)
        return RepairAction(
            id=result.get("id", f"repair-{start_time}"),
            script_key=input.script_key,
            success=result.get("success", False),
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            error_message=result.get("error"),
        )

    @strawberry.mutation
    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        try:
            from core.alert_engine import resolve_alert

            return resolve_alert(alert_id)
        except Exception:
            return False

    @strawberry.mutation
    async def create_alert(
        self, level: AlertLevel, title: str, description: str, platform: Platform
    ) -> Alert:
        """Create a new alert"""
        import uuid

        from core.alert_engine import alert_history

        alert_data = {
            "id": str(uuid.uuid4()),
            "level": level.value,
            "title": title,
            "description": description,
            "platform": platform.value,
            "timestamp": datetime.now().isoformat(),
            "resolved": False,
        }
        alert_history.appendleft(alert_data)
        return Alert(
            id=alert_data["id"],
            level=level,
            title=title,
            description=description,
            platform=platform,
            timestamp=datetime.fromisoformat(alert_data["timestamp"]),
            resolved=False,
        )


@strawberry.type
class Subscription:
    """GraphQL subscription root"""

    @strawberry.subscription
    async def alert_stream(self) -> AsyncGenerator[Alert, None]:
        """Stream new alerts"""
        # Real-time alert streaming requires a persistent alert bus; yield nothing when unavailable.
        if False:
            yield
        return

    @strawberry.subscription
    async def metrics_stream(self) -> AsyncGenerator[SystemMetrics, None]:
        """Stream system metrics updates"""
        # Real-time metrics streaming requires a persistent metrics bus; yield nothing when unavailable.
        if False:
            yield
        return
