# -*- coding: utf-8 -*-
"""Collaboration API router.

Provides REST endpoints for incident collaboration workspaces.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.collaboration_engine import add_task as engine_add_task
from core.collaboration_engine import assign_task as engine_assign_task
from core.collaboration_engine import create_workspace as engine_create_workspace
from core.collaboration_engine import get_active_context as engine_get_active_context
from core.collaboration_engine import get_workspace as engine_get_workspace
from core.collaboration_engine import list_workspaces as engine_list_workspaces
from core.collaboration_engine import post_message as engine_post_message
from core.collaboration_engine import resolve_workspace as engine_resolve_workspace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/collaboration", tags=["协作工作区"])


class CreateWorkspaceRequest(BaseModel):
    """Request to create a collaboration workspace."""

    name: str = Field(..., min_length=1, max_length=128, description="Workspace name")
    alert_id: Optional[str] = Field(None, max_length=128, description="Linked active alert id")
    repair_id: Optional[str] = Field(None, max_length=128, description="Linked repair id")
    assignees: list[str] = Field(default_factory=list, description="Initial assignees")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "name": "Production CPU incident",
                "alert_id": "CPU-20260101-120000",
                "repair_id": "",
                "assignees": ["admin"],
            }
        },
    }


class PostMessageRequest(BaseModel):
    """Request to post a message."""

    user: str = Field(..., min_length=1, max_length=64, description="Sender name")
    content: str = Field(..., min_length=1, max_length=4000, description="Message content")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"user": "operator", "content": "Checking logs"}},
    }


class AddTaskRequest(BaseModel):
    """Request to add a task."""

    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    assignee: Optional[str] = Field(None, max_length=64, description="Assignee username")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"title": "Restart service", "assignee": "operator"}},
    }


class UpdateTaskRequest(BaseModel):
    """Request to update a task."""

    status: Optional[str] = Field(None, max_length=32, description="Task status")
    assignee: Optional[str] = Field(None, max_length=64, description="New assignee")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"status": "done", "assignee": "operator"}},
    }


@router.get(
    "/workspaces",
    summary="List collaboration workspaces",
    responses={
        200: {"description": "Workspace list"},
        500: {"description": "Server error"},
    },
)
async def get_workspaces(
    alert_id: Optional[str] = Query(None, description="Filter by linked alert id"),
    status: Optional[str] = Query(None, description="Filter by workspace status"),
) -> dict[str, Any]:
    """Return a list of collaboration workspace summaries."""
    try:
        workspaces = engine_list_workspaces(alert_id, status)
        return {"workspaces": workspaces}
    except Exception as exc:
        logger.error(f"Failed to list workspaces: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list workspaces: {str(exc)[:200]}")


@router.get(
    "/workspaces/{workspace_id}",
    summary="Get a workspace",
    responses={
        200: {"description": "Workspace details"},
        404: {"description": "Workspace not found"},
        500: {"description": "Server error"},
    },
)
async def get_workspace_by_id(workspace_id: str) -> dict[str, Any]:
    """Return the full details of a single workspace."""
    try:
        ws = engine_get_workspace(workspace_id)
    except Exception as exc:
        logger.error(f"Failed to get workspace {workspace_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workspace: {str(exc)[:200]}")
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.post(
    "/workspaces",
    summary="Create a workspace",
    status_code=201,
    responses={
        201: {"description": "Workspace created"},
        400: {"description": "Bad request"},
        500: {"description": "Server error"},
    },
)
async def create_workspace_endpoint(request: CreateWorkspaceRequest) -> dict[str, Any]:
    """Create a new collaboration workspace linked to an alert and/or repair."""
    try:
        return engine_create_workspace(
            name=request.name,
            alert_id=request.alert_id,
            repair_id=request.repair_id,
            assignees=request.assignees,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to create workspace: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {str(exc)[:200]}")


@router.post(
    "/workspaces/{workspace_id}/messages",
    summary="Post a message",
    responses={
        200: {"description": "Message posted"},
        404: {"description": "Workspace not found"},
        500: {"description": "Server error"},
    },
)
async def post_message_endpoint(workspace_id: str, request: PostMessageRequest) -> dict[str, Any]:
    """Post a message to a workspace."""
    try:
        return engine_post_message(workspace_id, request.user, request.content)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to post message: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to post message: {str(exc)[:200]}")


@router.post(
    "/workspaces/{workspace_id}/tasks",
    summary="Add a task",
    responses={
        200: {"description": "Task added"},
        404: {"description": "Workspace not found"},
        500: {"description": "Server error"},
    },
)
async def add_task_endpoint(workspace_id: str, request: AddTaskRequest) -> dict[str, Any]:
    """Add a task to a workspace."""
    try:
        return engine_add_task(workspace_id, request.title, request.assignee)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to add task: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add task: {str(exc)[:200]}")


@router.patch(
    "/workspaces/{workspace_id}/tasks/{task_id}",
    summary="Update a task",
    responses={
        200: {"description": "Task updated"},
        404: {"description": "Workspace or task not found"},
        500: {"description": "Server error"},
    },
)
async def update_task_endpoint(
    workspace_id: str, task_id: str, request: UpdateTaskRequest
) -> dict[str, Any]:
    """Update a task's assignee and/or status."""
    try:
        return engine_assign_task(workspace_id, task_id, request.assignee, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to update task: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(exc)[:200]}")


@router.post(
    "/workspaces/{workspace_id}/resolve",
    summary="Resolve a workspace",
    responses={
        200: {"description": "Workspace resolved"},
        404: {"description": "Workspace not found"},
        500: {"description": "Server error"},
    },
)
async def resolve_workspace_endpoint(workspace_id: str) -> dict[str, Any]:
    """Resolve a collaboration workspace."""
    try:
        return engine_resolve_workspace(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to resolve workspace: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to resolve workspace: {str(exc)[:200]}"
        )


@router.get(
    "/active-context",
    summary="Get active incidents and repairs",
    responses={
        200: {"description": "Active context"},
        500: {"description": "Server error"},
    },
)
async def get_active_context_endpoint() -> dict[str, Any]:
    """Return available active alerts and recent repairs for workspace creation."""
    try:
        return engine_get_active_context()
    except Exception as exc:
        logger.error(f"Failed to get active context: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get active context: {str(exc)[:200]}"
        )
