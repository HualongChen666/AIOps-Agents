# -*- coding: utf-8 -*-
"""Alert notifier microservice."""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, cast

import httpx
from fastapi import FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.responses import Response

from services.alert_service.mq import message_queue
from services.alert_service.schemas import Alert, ServiceHealth

NOTIFICATIONS_SENT = Counter(
    "alerts_notifier_sent_total",
    "Notifications sent",
    ["channel", "status"],
)


@dataclass
class NotificationService:
    """Send notifications via webhook or log-only fallback."""

    webhook_url: str = field(default_factory=lambda: os.getenv("NOTIFY_WEBHOOK_URL", ""))
    min_level: str = field(default_factory=lambda: os.getenv("NOTIFY_MIN_LEVEL", "warning"))
    client: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient(timeout=10.0))
    history: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def _level_weight(level: str) -> int:
        weights = {"info": 0, "warning": 1, "high": 2, "critical": 3, "fatal": 4}
        return weights.get(level.lower(), 0)

    async def notify(self, alert: Alert) -> Dict[str, Any]:
        level = alert.level.value.lower()

        content = (
            f"【AIOps 告警】{alert.title}\n"
            f"级别:{alert.level.value}\n"
            f"详情:{alert.description}\n"
            f"主机:{alert.host or 'unknown'}"
        )

        result: Dict[str, Any]
        if self._level_weight(level) < self._level_weight(self.min_level):
            result = {
                "channel": "none",
                "success": True,
                "alert_id": alert.id,
                "detail": "below min level",
            }
            self.history.append(result)
            return result

        success = False
        detail = ""
        if self.webhook_url:
            try:
                resp = await self.client.post(
                    self.webhook_url,
                    json={"text": content, "alert_id": alert.id},
                    timeout=10.0,
                )
                success = resp.is_success
                detail = f"status {resp.status_code}"
            except Exception as exc:
                logger.error(f"Webhook notification failed: {exc}")
                detail = str(exc)[:200]
        else:
            success = True
            detail = "no webhook configured"

        result = {
            "channel": "webhook",
            "success": success,
            "alert_id": alert.id,
            "detail": detail,
        }
        self.history.append(result)
        NOTIFICATIONS_SENT.labels(channel="webhook", status="ok" if success else "error").inc()
        return result

    async def consume_loop(self, shutdown: asyncio.Event) -> None:
        while not shutdown.is_set():
            try:
                payload = await asyncio.wait_for(
                    message_queue.consume("alerts.routed"), timeout=1.0
                )
                if payload.get("type") == "routed_alert":
                    alert = Alert(**payload["alert"])
                    await self.notify(alert)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Notifier consume error: {exc}")

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.history[-limit:]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.service = NotificationService()
    app.state.shutdown = asyncio.Event()
    app.state.start_time = time.time()
    task = asyncio.create_task(app.state.service.consume_loop(app.state.shutdown))
    yield
    app.state.shutdown.set()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await app.state.service.client.aclose()


app = FastAPI(
    title="Alert Notifier",
    description="Sends notifications for routed alerts.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    return ServiceHealth(
        status="ok",
        service="alert-notifier",
        uptime_seconds=int(time.time() - app.state.start_time),
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/notify")
async def notify_alert(alert: Alert) -> Dict[str, Any]:
    return cast(Dict[str, Any], await app.state.service.notify(alert))


@app.get("/history")
async def notification_history(limit: int = 100) -> Dict[str, Any]:
    return {
        "total": len(app.state.service.history),
        "history": app.state.service.get_history(limit),
    }
