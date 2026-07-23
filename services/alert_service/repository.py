# -*- coding: utf-8 -*-
"""Alert repository abstraction."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from services.alert_service.schemas import Alert, AlertStatus


class AlertRepository:
    """Abstract alert repository."""

    async def save(self, alert: Alert) -> str:
        raise NotImplementedError

    async def get(self, alert_id: str) -> Optional[Alert]:
        raise NotImplementedError

    async def list(
        self,
        limit: int = 100,
        status: Optional[AlertStatus] = None,
        level: Optional[str] = None,
    ) -> List[Alert]:
        raise NotImplementedError

    async def update(self, alert_id: str, data: Dict[str, Any]) -> bool:
        raise NotImplementedError

    async def count(self) -> int:
        raise NotImplementedError

    async def delete(self, alert_id: str) -> bool:
        raise NotImplementedError

    async def clear(self) -> int:
        raise NotImplementedError


class InMemoryAlertRepository(AlertRepository):
    """In-memory repository for tests and local dev."""

    def __init__(self) -> None:
        self._alerts: Dict[str, Alert] = {}

    async def save(self, alert: Alert) -> str:
        if not alert.id:
            alert.id = f"alert-{datetime.utcnow().timestamp()}"
        self._alerts[alert.id] = alert
        logger.debug(f"Repository saved alert {alert.id}")
        return alert.id

    async def get(self, alert_id: str) -> Optional[Alert]:
        return self._alerts.get(alert_id)

    async def list(
        self,
        limit: int = 100,
        status: Optional[AlertStatus] = None,
        level: Optional[str] = None,
    ) -> List[Alert]:
        alerts = list(self._alerts.values())
        if status:
            alerts = [a for a in alerts if a.status == status]
        if level:
            alerts = [a for a in alerts if a.level == level]
        alerts.sort(key=lambda a: a.detected_at, reverse=True)
        return alerts[:limit]

    async def update(self, alert_id: str, data: Dict[str, Any]) -> bool:
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        for key, value in data.items():
            if hasattr(alert, key):
                setattr(alert, key, value)
        alert.detected_at = datetime.utcnow()
        return True

    async def count(self) -> int:
        return len(self._alerts)

    async def delete(self, alert_id: str) -> bool:
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            return True
        return False

    async def clear(self) -> int:
        count = len(self._alerts)
        self._alerts.clear()
        return count


async def get_repository(use_in_memory: bool = True) -> AlertRepository:
    """Return repository instance based on configuration."""
    return InMemoryAlertRepository()
