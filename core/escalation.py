# -*- coding: utf-8 -*-
"""Escalation helpers for critical failures such as rollback failure."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from loguru import logger


def _webhook_url() -> str:
    return os.getenv("ROLLBACK_FAILURE_WEBHOOK", "").strip()


def _notification_channels() -> list[str]:
    return os.getenv("ROLLBACK_FAILURE_CHANNELS", "slack,teams,email").lower().split(",")


async def notify_rollback_failure(
    alert_id: str,
    rollback_command: str,
    error: str,
    snapshot_id: str | None = None,
    extra: Dict[str, Any] | None = None,
) -> None:
    """Notify operators and escalation systems that a rollback has failed.

    This is a best-effort function: failures to notify are logged but never raise.
    """
    payload = {
        "event": "ROLLBACK_FAILURE",
        "alert_id": alert_id,
        "snapshot_id": snapshot_id,
        "rollback_command": rollback_command,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": "critical",
        "requires_manual_intervention": True,
    }
    if extra:
        payload.update(extra)

    logger.critical(
        f"[escalation] Rollback failed for alert {alert_id}: {error} | "
        f"snapshot={snapshot_id} | command={rollback_command}"
    )

    url = _webhook_url()
    if url:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                logger.info(
                    f"[escalation] Webhook notification sent | status={response.status_code}"
                )
        except Exception as exc:
            logger.warning(f"[escalation] Failed to send webhook notification: {exc}")

    # Log to every configured channel even if no webhook is configured
    for channel in _notification_channels():
        logger.warning(
            f"[escalation] Notifying {channel} about rollback failure for alert {alert_id}"
        )


def escalate_rollback_failure_sync(
    alert_id: str,
    rollback_command: str,
    error: str,
    snapshot_id: str | None = None,
) -> None:
    """Synchronous fallback to record a rollback failure escalation.

    Used in contexts where an async event loop is not available.
    """
    logger.critical(
        f"[escalation] SYNC rollback failure escalation for alert {alert_id}: {error} | "
        f"snapshot={snapshot_id}"
    )
