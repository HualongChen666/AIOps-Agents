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
        # Placeholder - integrate with actual metrics collector
        return SystemMetrics(
            cpu_usage=45.2,
            memory_usage=68.3,
            disk_usage=52.1,
            network_rx=1024000,
            network_tx=512000,
            timestamp=datetime.now(),
        )

    @strawberry.field
    async def alerts(self, filter: Optional[AlertFilter] = None) -> List[Alert]:
        """Get alerts with optional filtering"""
        # Placeholder - integrate with actual alert engine
        return [
            Alert(
                id="alert-1",
                level=AlertLevel.WARNING,
                title="High CPU usage",
                description="CPU usage exceeds 80%",
                platform=Platform.LINUX,
                timestamp=datetime.now(),
                resolved=False,
            )
        ]

    @strawberry.field
    async def top_processes(self, limit: int = 5) -> List[ProcessInfo]:
        """Get top processes by CPU usage"""
        # Placeholder - integrate with actual process collector
        return [
            ProcessInfo(
                pid=1234, name="python", cpu_percent=25.5, memory_percent=10.2, status="running"
            )
        ]

    @strawberry.field
    async def recent_repairs(self, limit: int = 10) -> List[RepairAction]:
        """Get recent repair actions"""
        # Placeholder - integrate with actual repair engine
        return [
            RepairAction(
                id="repair-1",
                script_key="restart_service",
                success=True,
                duration_ms=1500,
                timestamp=datetime.now(),
            )
        ]

    @strawberry.field
    async def alert(self, id: str) -> Optional[Alert]:
        """Get alert by ID"""
        # Placeholder - integrate with actual alert engine
        if id == "alert-1":
            return Alert(
                id="alert-1",
                level=AlertLevel.WARNING,
                title="High CPU usage",
                description="CPU usage exceeds 80%",
                platform=Platform.LINUX,
                timestamp=datetime.now(),
                resolved=False,
            )
        return None


@strawberry.type
class Mutation:
    """GraphQL mutation root"""

    @strawberry.mutation
    async def execute_repair(self, input: RepairInput) -> RepairAction:
        """Execute a repair action"""
        # Placeholder - integrate with actual repair engine
        return RepairAction(
            id=f"repair-{datetime.now().timestamp()}",
            script_key=input.script_key,
            success=True,
            duration_ms=1500,
            timestamp=datetime.now(),
        )

    @strawberry.mutation
    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        # Placeholder - integrate with actual alert engine
        return True

    @strawberry.mutation
    async def create_alert(
        self, level: AlertLevel, title: str, description: str, platform: Platform
    ) -> Alert:
        """Create a new alert"""
        # Placeholder - integrate with actual alert engine
        return Alert(
            id=f"alert-{datetime.now().timestamp()}",
            level=level,
            title=title,
            description=description,
            platform=platform,
            timestamp=datetime.now(),
            resolved=False,
        )


@strawberry.type
class Subscription:
    """GraphQL subscription root"""

    @strawberry.subscription
    async def alert_stream(self) -> AsyncGenerator[Alert, None]:
        """Stream new alerts"""
        # Placeholder - implement WebSocket-based streaming
        yield Alert(
            id="alert-1",
            level=AlertLevel.WARNING,
            title="High CPU usage",
            description="CPU usage exceeds 80%",
            platform=Platform.LINUX,
            timestamp=datetime.now(),
            resolved=False,
        )

    @strawberry.subscription
    async def metrics_stream(self) -> AsyncGenerator[SystemMetrics, None]:
        """Stream system metrics updates"""
        # Placeholder - implement WebSocket-based streaming
        yield SystemMetrics(
            cpu_usage=45.2,
            memory_usage=68.3,
            disk_usage=52.1,
            network_rx=1024000,
            network_tx=512000,
            timestamp=datetime.now(),
        )
