# -*- coding: utf-8 -*-
"""
core/oncall_adapter.py
Oncall / paging schedule adapter.

Integrates with external on-call systems (PagerDuty, Opsgenie, or a custom
JSON schedule) to lookup the current on-call engineer/team for a given alert
category, service, or escalation policy.
"""

from __future__ import annotations

import json
import os
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

try:
    from core.notify_engine import _get_http_client
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    _get_http_client = None  # type: ignore[assignment]


@dataclass
class OncallContact:
    """Represents an on-call contact."""

    name: str
    email: str = ""
    phone: str = ""
    channel: str = ""
    team: str = ""
    role: str = ""


@dataclass
class OncallSchedule:
    """In-memory on-call schedule lookup."""

    _schedules: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def load_from_env(self) -> None:
        """Load schedule from ONCALL_SCHEDULE_JSON env variable."""
        raw = os.getenv("ONCALL_SCHEDULE_JSON", "{}").strip()
        if raw:
            try:
                self._schedules = json.loads(raw)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                self._schedules = {}

    def load_from_file(self, path: str) -> None:
        """Load schedule from a JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._schedules = json.load(f)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            self._schedules = {}

    def lookup(
        self,
        category: str = "",
        service: str = "",
        alert_type: str = "",
        team: str = "",
    ) -> list[OncallContact]:
        """Synchronously find on-call contacts from local schedule."""
        return self._lookup_local(category, service, alert_type, team)

    async def lookup_async(
        self,
        category: str = "",
        service: str = "",
        alert_type: str = "",
        team: str = "",
    ) -> list[OncallContact]:
        """Asynchronously find on-call contacts; tries external API then local schedule."""
        contacts: list[OncallContact] = []
        if (
            self.provider in ("pagerduty", "opsgenie", "victorops")
            and self.api_base
            and self.api_token
        ):
            contacts = await self._lookup_external(category, service, team)
        if not contacts:
            contacts = self._lookup_local(category, service, alert_type, team)
        return contacts

    def _lookup_local(
        self,
        category: str = "",
        service: str = "",
        alert_type: str = "",
        team: str = "",
    ) -> list[OncallContact]:
        """Find on-call contacts matching category/service/team in local JSON schedule."""
        results: list[OncallContact] = []
        if not self._schedules:
            self.load_from_env()

        for roster_name, members in self._schedules.items():
            match = (
                not category
                or category.lower() in roster_name.lower()
                or any(category.lower() in str(m.get("categories", [])).lower() for m in members)
            )
            service_match = not service or any(
                service.lower() in str(m.get("services", [])).lower() for m in members
            )
            team_match = (
                not team
                or team.lower() == roster_name.lower()
                or any(team.lower() == str(m.get("team", "")).lower() for m in members)
            )
            if match or service_match or team_match:
                for m in members:
                    results.append(
                        OncallContact(
                            name=str(m.get("name", "")),
                            email=str(m.get("email", "")),
                            phone=str(m.get("phone", "")),
                            channel=str(m.get("channel", roster_name)),
                            team=str(m.get("team", roster_name)),
                            role=str(m.get("role", "oncall")),
                        )
                    )
        return results


class OncallAdapter:
    """Adapter to query on-call schedules from local JSON or external API."""

    def __init__(self, provider: str = "") -> None:
        self.provider = provider or os.getenv("ONCALL_PROVIDER", "json").lower()
        self.api_token = os.getenv("ONCALL_API_TOKEN", "")
        self.api_base = os.getenv("ONCALL_API_BASE", "")
        self._local_schedule = OncallSchedule()
        self._local_schedule.load_from_env()

    def _http_client(self) -> httpx.AsyncClient:
        if _get_http_client:
            return _get_http_client()
        return httpx.AsyncClient(timeout=10.0)

    def lookup(
        self,
        category: str = "",
        service: str = "",
        alert_type: str = "",
        team: str = "",
    ) -> list[OncallContact]:
        """Public synchronous lookup: uses local schedule (mirrors async version)."""
        return self._local_schedule.lookup(category, service, alert_type, team)

    async def lookup_async(
        self,
        category: str = "",
        service: str = "",
        alert_type: str = "",
        team: str = "",
    ) -> list[OncallContact]:
        """Asynchronous lookup: tries external API first, falls back to local schedule."""
        contacts: list[OncallContact] = []
        if (
            self.provider in ("pagerduty", "opsgenie", "victorops")
            and self.api_base
            and self.api_token
        ):
            contacts = await self._lookup_external(category, service, team)
        if not contacts:
            contacts = self._local_schedule.lookup(category, service, alert_type, team)
        return contacts

    async def _lookup_external(self, category: str, service: str, team: str) -> list[OncallContact]:
        """Call external on-call API (generic webhook shape)."""
        url = urllib.parse.urljoin(self.api_base, "/api/v1/oncall")
        params: dict[str, Any] = {}
        if category:
            params["category"] = category
        if service:
            params["service"] = service
        if team:
            params["team"] = team
        try:
            client = self._http_client()
            headers = {"Authorization": f"Bearer {self.api_token}"}
            resp = await client.get(url, params=params, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            return [
                OncallContact(
                    name=str(m.get("name", "")),
                    email=str(m.get("email", "")),
                    phone=str(m.get("phone", "")),
                    channel=str(m.get("channel", "")),
                    team=str(m.get("team", "")),
                    role=str(m.get("role", "oncall")),
                )
                for m in data
                if isinstance(m, dict)
            ]
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(f"[oncall] external lookup failed: {exc}")
            return []

    def add_local_schedule(self, name: str, members: list[dict[str, Any]]) -> None:
        """Add a local roster for testing or static configuration."""
        self._local_schedule._schedules[name] = members


# Global singleton
_oncall_adapter: Optional[OncallAdapter] = None


def get_oncall_adapter() -> OncallAdapter:
    """Get or create global OncallAdapter instance."""
    global _oncall_adapter
    if _oncall_adapter is None:
        _oncall_adapter = OncallAdapter()
    return _oncall_adapter