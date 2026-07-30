# -*- coding: utf-8 -*-
"""HTTP client for the AIOps SRE Agent public API."""

from __future__ import annotations

from typing import Any, Optional, cast

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


class AgentClient:
    """Simple synchronous client for alert/approval/audit endpoints."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        internal_api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.internal_api_key = internal_api_key
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.internal_api_key:
            headers["X-Internal-Key"] = self.internal_api_key
        return headers

    def send_alert(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a Prometheus-style alert payload."""
        response = self._client.post(
            "/api/v1/alerts/prometheus", json=payload, headers=self._headers()
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def list_approvals(self) -> list[dict[str, Any]]:
        """List pending approvals."""
        response = self._client.get("/api/v1/approvals/pending", headers=self._headers())
        response.raise_for_status()
        data = response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        return cast(list[dict[str, Any]], items)

    def approve(self, alert_id: str | int) -> dict[str, Any]:
        """Approve a pending repair for an alert."""
        response = self._client.patch(f"/api/v1/approvals/{alert_id}", headers=self._headers())
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def reject(self, alert_id: str | int, reason: str = "用户驳回") -> dict[str, Any]:
        """Reject a pending repair for an alert."""
        response = self._client.post(
            "/api/v1/approvals/reject",
            json={"alert_id": str(alert_id), "reason": reason},
            headers=self._headers(),
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def get_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch recent audit events."""
        response = self._client.get(
            "/api/v1/audit", params={"limit": limit}, headers=self._headers()
        )
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())

    def get_health(self) -> dict[str, Any]:
        """Health check."""
        response = self._client.get("/health", headers=self._headers())
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AgentClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
