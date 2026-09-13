# -*- coding: utf-8 -*-
"""Workflow management API (``/api/v1/workflow-management``).

Backs ``frontend/app/workflow/workflow-management`` — CRUD over workflow
definitions stored in the durable ``workflows`` table.  The page's ``steps``
column is derived from the definition's step list, and ``version`` is bumped on
every content change (identical semantics to the workflow repository layer).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from core.database import SessionLocal
from core.models import Workflow
from core.workflow_page_support import iso_now, new_id, slugify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflow-management", tags=["工作流管理"])

_VALID_STATUS = {"active", "inactive", "draft"}


class WorkflowCreate(BaseModel):
    """创建/编辑工作流的请求体。"""

    name: str = Field(..., min_length=1, description="工作流名称")
    description: str = Field(default="", description="工作流描述")
    status: str = Field(default="draft", description="状态: active/inactive/draft")


class WorkflowStatusUpdate(BaseModel):
    """状态切换请求体。"""

    status: str = Field(..., description="状态: active/inactive")


def _serialize(workflow: Workflow) -> dict[str, Any]:
    definition = workflow.definition if isinstance(workflow.definition, dict) else {}
    steps = definition.get("steps")
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description or "",
        "status": workflow.status,
        "version": str(workflow.version),
        "steps": len(steps) if isinstance(steps, list) else 0,
        "createdAt": workflow.created_at.isoformat() if workflow.created_at else iso_now(),
        "updatedAt": workflow.updated_at.isoformat() if workflow.updated_at else iso_now(),
    }


@router.get("", summary="列出工作流")
async def list_workflows() -> list[dict[str, Any]]:
    """Return every workflow definition ordered by most recently updated."""
    db = SessionLocal()
    try:
        workflows = db.query(Workflow).order_by(Workflow.updated_at.desc()).all()
        return [_serialize(w) for w in workflows]
    except SQLAlchemyError as exc:
        logger.error("列出工作流失败: %s", exc)
        raise HTTPException(status_code=500, detail="列出工作流失败") from exc
    finally:
        db.close()


@router.post("", status_code=201, summary="创建工作流")
async def create_workflow(payload: WorkflowCreate) -> dict[str, Any]:
    """Create a new empty workflow definition."""
    status = payload.status if payload.status in _VALID_STATUS else "draft"
    db = SessionLocal()
    try:
        workflow_id = slugify(payload.name, fallback="workflow")
        if db.query(Workflow).filter(Workflow.id == workflow_id).first():
            workflow_id = new_id(workflow_id)

        workflow = Workflow(
            id=workflow_id,
            name=payload.name.strip(),
            description=payload.description,
            definition={"steps": []},
            status=status,
            version=1,
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return _serialize(workflow)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("创建工作流失败: %s", exc)
        raise HTTPException(status_code=500, detail="创建工作流失败") from exc
    finally:
        db.close()


@router.put("/{workflow_id}", summary="更新工作流")
async def update_workflow(workflow_id: str, payload: WorkflowCreate) -> dict[str, Any]:
    """Update a workflow definition's metadata and bump its version."""
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow is None:
            raise HTTPException(status_code=404, detail="工作流不存在")
        workflow.name = payload.name.strip()
        workflow.description = payload.description
        if payload.status in _VALID_STATUS:
            workflow.status = payload.status
        workflow.version = (workflow.version or 1) + 1
        db.commit()
        db.refresh(workflow)
        return _serialize(workflow)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("更新工作流失败: %s", exc)
        raise HTTPException(status_code=500, detail="更新工作流失败") from exc
    finally:
        db.close()


@router.delete("/{workflow_id}", summary="删除工作流")
async def delete_workflow(workflow_id: str) -> dict[str, Any]:
    """Delete a workflow definition."""
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow is None:
            raise HTTPException(status_code=404, detail="工作流不存在")
        db.delete(workflow)
        db.commit()
        return {"status": "success", "message": "工作流已删除"}
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("删除工作流失败: %s", exc)
        raise HTTPException(status_code=500, detail="删除工作流失败") from exc
    finally:
        db.close()


@router.patch("/{workflow_id}/status", summary="切换工作流状态")
async def update_workflow_status(
    workflow_id: str, payload: WorkflowStatusUpdate
) -> dict[str, Any]:
    """Activate or deactivate a workflow."""
    if payload.status not in {"active", "inactive"}:
        raise HTTPException(status_code=400, detail="状态只能是 active 或 inactive")
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow is None:
            raise HTTPException(status_code=404, detail="工作流不存在")
        workflow.status = payload.status
        db.commit()
        db.refresh(workflow)
        return _serialize(workflow)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("更新工作流状态失败: %s", exc)
        raise HTTPException(status_code=500, detail="更新工作流状态失败") from exc
    finally:
        db.close()
