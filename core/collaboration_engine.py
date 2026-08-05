# -*- coding: utf-8 -*-
"""Incident collaboration engine with JSON persistence.

Provides real collaboration workspaces tied to alerts and repairs.  Each
workspace stores messages, shared notes, tasks, assignees and a status.  All
state is persisted to ``data/collaboration.json``.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.alert_service import alert_service
from core.repair_engine import get_repair_history

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "collaboration.json"


class CollaborationEngine:
    """In-memory + JSON-persistent collaboration workspace manager."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._workspaces: dict[str, dict[str, Any]] = {}
        self._load()

    def _ensure_data_dir(self) -> None:
        """Create the data directory if it does not exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load workspaces from ``data/collaboration.json``."""
        self._ensure_data_dir()
        if not DATA_FILE.exists():
            self._save()
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict) and "workspaces" in payload:
                for ws in payload["workspaces"]:
                    if isinstance(ws, dict) and "id" in ws:
                        self._workspaces[str(ws["id"])] = ws
        except Exception as exc:
            logger.error(f"Failed to load collaboration data: {exc}", exc_info=True)
            self._workspaces = {}

    def _save(self) -> None:
        """Persist workspaces to ``data/collaboration.json``."""
        self._ensure_data_dir()
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"workspaces": list(self._workspaces.values())},
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
        except Exception as exc:
            logger.error(f"Failed to save collaboration data: {exc}", exc_info=True)

    @staticmethod
    def _now() -> str:
        """Return an ISO 8601 timestamp string."""
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _new_id(prefix: str) -> str:
        """Return a short unique id."""
        return f"{prefix}-{uuid.uuid4().hex[:8]}"

    def _active_alert_ids(self) -> set[str]:
        """Collect ids of currently active alerts."""
        try:
            alerts = alert_service.get_alerts(200).get("alerts", [])
            return {str(a.get("id")) for a in alerts if a.get("id")}
        except Exception as exc:
            logger.warning(f"Could not read active alerts: {exc}")
            return set()

    def _repair_records(self) -> list[dict[str, Any]]:
        """Collect recent repair history records."""
        try:
            return get_repair_history(100)
        except Exception as exc:
            logger.warning(f"Could not read repair history: {exc}")
            return []

    def list_workspaces(
        self, alert_id: Optional[str] = None, status: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Return workspace summaries, optionally filtered.

        Args:
            alert_id: Filter by linked alert id.
            status: Filter by workspace status.

        Returns:
            A list of workspace summary dictionaries.
        """
        with self._lock:
            result: list[dict[str, Any]] = []
            for ws in self._workspaces.values():
                if alert_id is not None and ws.get("alert_id") != alert_id:
                    continue
                if status is not None and ws.get("status") != status:
                    continue
                tasks = ws.get("tasks", [])
                done = sum(1 for t in tasks if t.get("status") == "done")
                result.append(
                    {
                        "id": ws["id"],
                        "name": ws["name"],
                        "status": ws["status"],
                        "alert_id": ws.get("alert_id"),
                        "repair_id": ws.get("repair_id"),
                        "members": len(ws.get("assignees", [])),
                        "last_activity": ws.get("updated_at"),
                        "task_summary": {"total": len(tasks), "done": done},
                    }
                )
            result.sort(key=lambda x: x["last_activity"] or "", reverse=True)
            return result

    def get_workspace(self, workspace_id: str) -> Optional[dict[str, Any]]:
        """Return a full workspace by id.

        Args:
            workspace_id: The workspace id.

        Returns:
            A deep-copied workspace dictionary, or ``None`` if not found.
        """
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return None
            # Deep copy via JSON to avoid accidental mutation of internal state.
            return json.loads(json.dumps(ws, default=str))

    def create_workspace(
        self,
        name: str,
        alert_id: Optional[str] = None,
        repair_id: Optional[str] = None,
        assignees: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Create a new collaboration workspace.

        Args:
            name: Human-readable workspace name.
            alert_id: Optional linked active alert id.
            repair_id: Optional linked repair history id.
            assignees: Initial member list.

        Returns:
            The newly created workspace.

        Raises:
            ValueError: If the referenced alert is not active.
        """
        with self._lock:
            if alert_id and alert_id not in self._active_alert_ids():
                raise ValueError(f"Alert {alert_id} is not an active incident")
            now = self._now()
            ws_id = f"CW-{uuid.uuid4().hex[:8].upper()}"
            ws: dict[str, Any] = {
                "id": ws_id,
                "name": name.strip() or f"Workspace {ws_id}",
                "alert_id": alert_id,
                "repair_id": repair_id,
                "status": "open",
                "assignees": list(assignees or []),
                "notes": [],
                "messages": [],
                "tasks": [],
                "created_at": now,
                "updated_at": now,
            }
            self._workspaces[ws["id"]] = ws
            self._save()
            return self.get_workspace(ws["id"])

    def post_message(self, workspace_id: str, user: str, content: str) -> dict[str, Any]:
        """Post a message to a workspace.

        Args:
            workspace_id: Target workspace id.
            user: Sender display name.
            content: Message body.

        Returns:
            The created message.

        Raises:
            ValueError: If the workspace does not exist.
        """
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"Workspace {workspace_id} not found")
            msg = {
                "id": self._new_id("msg"),
                "user": user,
                "content": content,
                "created_at": self._now(),
            }
            ws["messages"].append(msg)
            ws["updated_at"] = self._now()
            self._save()
            return msg

    def add_task(
        self, workspace_id: str, title: str, assignee: Optional[str] = None
    ) -> dict[str, Any]:
        """Add a task to a workspace.

        Args:
            workspace_id: Target workspace id.
            title: Task title.
            assignee: Optional assignee username.

        Returns:
            The created task.

        Raises:
            ValueError: If the workspace does not exist.
        """
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"Workspace {workspace_id} not found")
            task = {
                "id": self._new_id("task"),
                "title": title,
                "assignee": assignee or "",
                "status": "todo",
                "created_at": self._now(),
                "updated_at": self._now(),
            }
            ws["tasks"].append(task)
            if assignee and assignee not in ws["assignees"]:
                ws["assignees"].append(assignee)
            ws["updated_at"] = self._now()
            self._save()
            return task

    def assign_task(
        self,
        workspace_id: str,
        task_id: str,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update a task's assignee and/or status.

        Args:
            workspace_id: Target workspace id.
            task_id: Task id.
            assignee: New assignee, if provided.
            status: New status, if provided.

        Returns:
            The updated task.

        Raises:
            ValueError: If the workspace or task is not found.
        """
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"Workspace {workspace_id} not found")
            for task in ws["tasks"]:
                if task.get("id") == task_id:
                    if assignee is not None:
                        task["assignee"] = assignee
                        if assignee and assignee not in ws["assignees"]:
                            ws["assignees"].append(assignee)
                    if status is not None:
                        task["status"] = status
                    task["updated_at"] = self._now()
                    ws["updated_at"] = self._now()
                    self._save()
                    return task
            raise ValueError(f"Task {task_id} not found in workspace {workspace_id}")

    def resolve_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Resolve a workspace.

        Args:
            workspace_id: Workspace id to resolve.

        Returns:
            The updated workspace.

        Raises:
            ValueError: If the workspace is not found.
        """
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"Workspace {workspace_id} not found")
            ws["status"] = "resolved"
            ws["notes"].append(f"Resolved at {self._now()}")
            ws["updated_at"] = self._now()
            self._save()
            return self.get_workspace(ws["id"])

    def get_active_context(self) -> dict[str, Any]:
        """Return available active alerts and recent repairs for workspace creation.

        Returns:
            A dictionary with ``alerts`` and ``repairs`` lists.
        """
        return {
            "alerts": alert_service.get_alerts(200).get("alerts", []),
            "repairs": self._repair_records(),
        }


# Singleton instance used by the API router.
_collaboration_engine = CollaborationEngine()

list_workspaces = _collaboration_engine.list_workspaces
get_workspace = _collaboration_engine.get_workspace
create_workspace = _collaboration_engine.create_workspace
post_message = _collaboration_engine.post_message
add_task = _collaboration_engine.add_task
assign_task = _collaboration_engine.assign_task
resolve_workspace = _collaboration_engine.resolve_workspace
get_active_context = _collaboration_engine.get_active_context
