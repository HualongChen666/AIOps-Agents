# -*- coding: utf-8 -*-
"""Team and on-call collaboration engine.

Provides JSON-backed persistence for SRE teams, on-call rotations,
handoff notes and incident escalation policies. The ground truth is
stored in ``data/teams.json`` under the project root.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from config import BASE_DIR

DATA_DIR: Path = BASE_DIR / "data"
TEAMS_FILE: Path = DATA_DIR / "teams.json"

_persistence_lock = asyncio.Lock()


def _ensure_data_dir() -> None:
    """Create the data directory if it does not already exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _seed_data() -> dict[str, Any]:
    """Return the initial team/on-call dataset when no JSON file exists."""
    return {
        "teams": [
            {
                "id": "T-001",
                "name": "AIOps运维团队",
                "description": "负责AIOps平台的运维和监控",
                "members": [
                    {
                        "user_id": "U-001",
                        "username": "zhangsan",
                        "full_name": "张三",
                        "role": "Team Lead",
                        "status": "online",
                        "avatar": "",
                    },
                    {
                        "user_id": "U-002",
                        "username": "lisi",
                        "full_name": "李四",
                        "role": "DevOps Engineer",
                        "status": "online",
                        "avatar": "",
                    },
                    {
                        "user_id": "U-003",
                        "username": "wangwu",
                        "full_name": "王五",
                        "role": "SRE",
                        "status": "busy",
                        "avatar": "",
                    },
                    {
                        "user_id": "U-004",
                        "username": "zhaoliu",
                        "full_name": "赵六",
                        "role": "Developer",
                        "status": "offline",
                        "avatar": "",
                    },
                ],
                "rotation": {
                    "type": "weekly",
                    "start_date": "2026-01-01T00:00:00+00:00",
                    "order": ["U-001", "U-002", "U-003", "U-004"],
                    "shift_duration_days": 7,
                },
                "escalation_policy": {
                    "levels": [
                        {
                            "level": 1,
                            "delay_minutes": 15,
                            "contact_methods": ["phone", "email"],
                            "notify_role": "primary",
                        },
                        {
                            "level": 2,
                            "delay_minutes": 30,
                            "contact_methods": ["phone", "sms"],
                            "notify_role": "secondary",
                        },
                        {
                            "level": 3,
                            "delay_minutes": 60,
                            "contact_methods": ["phone", "sms", "email"],
                            "notify_role": "manager",
                        },
                    ]
                },
            }
        ],
        "handoffs": [],
        "incidents": {},
    }


def _read_data_file() -> dict[str, Any]:
    """Read and return the persisted JSON or seed a new one."""
    _ensure_data_dir()
    if not TEAMS_FILE.exists():
        data = _seed_data()
        _write_data_file(data)
        return data
    with TEAMS_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_data_file(data: dict[str, Any]) -> None:
    """Persist the data structure to JSON."""
    import os
    import stat

    _ensure_data_dir()
    with TEAMS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)

    # Set restrictive permissions for teams data file (600 - owner read/write only)
    try:
        os.chmod(TEAMS_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, AttributeError):
        # chmod may fail on Windows or non-Unix systems
        pass


async def _load_data() -> dict[str, Any]:
    """Thread-safe async load of the JSON data file."""
    async with _persistence_lock:
        return await asyncio.to_thread(_read_data_file)


async def _persist_data(data: dict[str, Any]) -> None:
    """Thread-safe async write of the JSON data file."""
    async with _persistence_lock:
        await asyncio.to_thread(_write_data_file, data)


def _find_team(data: dict[str, Any], team_id: str) -> dict[str, Any]:
    """Locate a team by identifier or raise a ValueError."""
    for team in data.get("teams", []):
        if team.get("id") == team_id:
            return team
    raise ValueError(f"Team '{team_id}' not found")


def _member_lookup(team: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a user_id -> member mapping for a team."""
    return {m["user_id"]: m for m in team.get("members", [])}


def _compute_oncall(team: dict[str, Any], at: Optional[datetime] = None) -> dict[str, Any]:
    """Calculate the current on-call primary and secondary for a team."""
    at = at or datetime.now(timezone.utc)
    rotation = team.get("rotation", {})
    order = rotation.get("order", [])
    if not order:
        return {
            "team_id": team.get("id"),
            "primary": None,
            "secondary": None,
            "since": None,
            "until": None,
            "rotation_type": rotation.get("type"),
        }

    start = datetime.fromisoformat(str(rotation.get("start_date")))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    shift_days = int(rotation.get("shift_duration_days", 7))

    elapsed = at - start
    if elapsed < timedelta(0):
        completed_shifts = 0
    else:
        completed_shifts = elapsed.days // shift_days

    idx = completed_shifts % len(order)
    primary_id = order[idx]
    secondary_id = order[(idx + 1) % len(order)]

    members = _member_lookup(team)
    since = start + timedelta(days=completed_shifts * shift_days)
    until = since + timedelta(days=shift_days)

    return {
        "team_id": team.get("id"),
        "primary": members.get(primary_id),
        "secondary": members.get(secondary_id),
        "since": since.isoformat(),
        "until": until.isoformat(),
        "rotation_type": rotation.get("type"),
        "shift_duration_days": shift_days,
        "next_rotation_in_hours": max(0, int((until - at).total_seconds() // 3600)),
    }


async def list_teams() -> list[dict[str, Any]]:
    """Return the list of configured on-call teams.

    Returns:
        A list of team dictionaries including members, rotation and
        escalation policy details.
    """
    data = await _load_data()
    return list(data.get("teams", []))


async def get_team_oncall(team_id: str, at: Optional[datetime] = None) -> dict[str, Any]:
    """Return the active on-call roster for a team.

    Args:
        team_id: Unique team identifier.
        at: Optional datetime for which to calculate the roster.

    Returns:
        On-call details including primary, secondary and shift boundaries.
    """
    data = await _load_data()
    team = _find_team(data, team_id)
    return _compute_oncall(team, at)


async def create_handoff(
    team_id: str,
    from_user_id: Optional[str],
    to_user_id: Optional[str],
    notes: str,
) -> dict[str, Any]:
    """Create a handoff note for a team.

    Args:
        team_id: The team receiving the handoff.
        from_user_id: User leaving the note, defaults to 'system'.
        to_user_id: Optional recipient user id.
        notes: Free-form handoff text.

    Returns:
        The created handoff record.
    """
    data = await _load_data()
    team = _find_team(data, team_id)
    members = _member_lookup(team)

    sender_id = from_user_id or "system"
    if sender_id != "system" and sender_id not in members:
        raise ValueError(f"From user '{sender_id}' is not a team member")
    if to_user_id and to_user_id not in members:
        raise ValueError(f"To user '{to_user_id}' is not a team member")

    handoff = {
        "id": f"H-{uuid.uuid4().hex[:8]}",
        "team_id": team_id,
        "from_user_id": sender_id,
        "to_user_id": to_user_id,
        "from_name": members.get(sender_id, {}).get("full_name", sender_id),
        "to_name": members.get(to_user_id, {}).get("full_name") if to_user_id else None,
        "notes": notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data.setdefault("handoffs", []).insert(0, handoff)
    await _persist_data(data)
    logger.info("Created handoff %s for team %s", handoff["id"], team_id)
    return handoff


async def list_handoffs(team_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Return handoff notes, optionally filtered by team.

    Args:
        team_id: Optional team identifier to filter on.

    Returns:
        A chronologically descending list of handoff records.
    """
    data = await _load_data()
    handoffs = data.get("handoffs", [])
    if team_id:
        handoffs = [h for h in handoffs if h.get("team_id") == team_id]
    return sorted(handoffs, key=lambda h: h.get("created_at", ""), reverse=True)


async def escalate_incident(
    incident_id: str,
    team_id: str,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """Escalate an incident to the next level for a team.

    Args:
        incident_id: External incident identifier.
        team_id: Team that owns the incident.
        reason: Optional human-readable escalation reason.

    Returns:
        The escalation record including the notified user and policy details.
    """
    data = await _load_data()
    team = _find_team(data, team_id)
    members = _member_lookup(team)
    oncall = _compute_oncall(team)

    incidents = data.setdefault("incidents", {})
    current = incidents.get(incident_id)
    level = (current.get("level", 0) if current else 0) + 1

    levels = team.get("escalation_policy", {}).get("levels", [])
    level_config = next((item for item in levels if item.get("level") == level), None)
    if not level_config:
        raise ValueError("Maximum escalation level reached for this team")

    notify_role = level_config.get("notify_role", "primary")
    if notify_role == "primary":
        notify_id = oncall.get("primary", {}).get("user_id") if oncall.get("primary") else None
    elif notify_role == "secondary":
        notify_id = oncall.get("secondary", {}).get("user_id") if oncall.get("secondary") else None
    else:
        manager = next(
            (
                m
                for m in team.get("members", [])
                if m.get("role", "").lower() in ("team lead", "manager", "lead")
            ),
            None,
        )
        notify_id = manager["user_id"] if manager else oncall.get("primary", {}).get("user_id")

    if not notify_id:
        notify_id = team.get("members", [{}])[0].get("user_id", "unknown")

    record = {
        "incident_id": incident_id,
        "team_id": team_id,
        "level": level,
        "reason": reason,
        "notified_user_id": notify_id,
        "notified_user": members.get(notify_id),
        "contact_methods": level_config.get("contact_methods", []),
        "delay_minutes": level_config.get("delay_minutes", 0),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "escalated",
    }
    incidents[incident_id] = record
    data["incidents"] = incidents
    await _persist_data(data)
    logger.warning(
        "Incident %s escalated to level %s, notified %s",
        incident_id,
        level,
        notify_id,
    )
    return record


async def list_dashboards(team_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Return shared dashboards, optionally filtered by team."""
    data = await _load_data()
    dashboards = data.get("shared_dashboards", [])
    if team_id:
        dashboards = [d for d in dashboards if d.get("team_id") == team_id]
    return dashboards
