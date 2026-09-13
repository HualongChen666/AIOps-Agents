# -*- coding: utf-8 -*-
"""Workflow visualization API (``/api/v1/workflow-visualization``).

Backs ``frontend/app/workflow/workflow-visualization``.  The graph is derived
from each workflow definition's steps (so it always matches the real
definition), annotated with the live execution state of the latest run.  The
chosen layout is persisted per workflow and the PNG export is rendered with
Pillow — a genuine image, not a placeholder.
"""

from __future__ import annotations

import io
import logging
import math
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from core.database import SessionLocal
from core.models import Workflow, WorkflowExecution
from core.workflow_page_support import get_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflow-visualization", tags=["工作流可视化"])

_VALID_LAYOUTS = {"horizontal", "vertical", "circular"}
_NODE_W, _NODE_H = 140, 56


class LayoutUpdate(BaseModel):
    """布局切换请求体。"""

    layout: str = Field(..., description="布局: horizontal/vertical/circular")


def _steps_of(workflow: Workflow) -> list[dict[str, Any]]:
    definition = workflow.definition if isinstance(workflow.definition, dict) else {}
    steps = definition.get("steps")
    return [s for s in steps if isinstance(s, dict)] if isinstance(steps, list) else []


def _position(index: int, total: int, layout: str) -> dict[str, int]:
    if layout == "vertical":
        return {"x": 120, "y": 40 + index * 120}
    if layout == "circular":
        radius = 220
        angle = (2 * math.pi * index / max(total, 1)) - math.pi / 2
        return {
            "x": int(400 + radius * math.cos(angle)),
            "y": int(320 + radius * math.sin(angle)),
        }
    return {"x": 40 + index * 200, "y": 120}


def _node_statuses(execution: WorkflowExecution | None, total: int) -> list[str]:
    if execution is None or not isinstance(execution.result, dict):
        return ["pending"] * total
    progress = execution.result.get("progress", 0)
    completed = min(total, round(progress / 100 * total))
    statuses = ["pending"] * total
    for i in range(completed):
        statuses[i] = "completed"
    if execution.status == "failed":
        if completed < total:
            statuses[completed] = "failed"
    elif execution.status == "running":
        if completed < total:
            statuses[completed] = "running"
    elif execution.status == "completed":
        statuses = ["completed"] * total
    return statuses


def _build_graph(workflow: Workflow, layout: str, execution: WorkflowExecution | None) -> dict[str, Any]:
    steps = _steps_of(workflow)
    statuses = _node_statuses(execution, len(steps))
    nodes: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        step_key = str(step.get("key") or f"step-{index}")
        node_type = "start" if index == 0 else ("end" if index == len(steps) - 1 else "task")
        if step.get("type") in {"start", "task", "condition", "end"}:
            node_type = str(step["type"])
        nodes.append(
            {
                "id": step_key,
                "name": str(step.get("title") or step_key),
                "type": node_type,
                "position": _position(index, len(steps), layout),
                "status": statuses[index] if index < len(statuses) else "pending",
                "dependencies": [str(steps[index - 1].get("key") or f"step-{index-1}")]
                if index > 0
                else [],
            }
        )
    edges = [
        {"from": nodes[i]["id"], "to": nodes[i + 1]["id"], "condition": None}
        for i in range(len(nodes) - 1)
    ]
    return {
        "id": workflow.id,
        "name": workflow.name,
        "nodes": nodes,
        "edges": edges,
        "layout": layout,
    }


def _layout_for(request: Request, workflow_id: str) -> str:
    store = get_store(request, "workflow_visualization_layout")
    entry = store.get(workflow_id) or {}
    layout = entry.get("layout", "horizontal") if isinstance(entry, dict) else "horizontal"
    return layout if layout in _VALID_LAYOUTS else "horizontal"


def _render_png(graph: dict[str, Any]) -> bytes:
    nodes = graph["nodes"]
    width = max(600, max((n["position"]["x"] for n in nodes), default=0) + _NODE_W + 60)
    height = max(300, max((n["position"]["y"] for n in nodes), default=0) + _NODE_H + 60)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    by_id = {n["id"]: n for n in nodes}

    colors = {
        "completed": ("#dcfce7", "#16a34a"),
        "running": ("#dbeafe", "#2563eb"),
        "failed": ("#fee2e2", "#dc2626"),
        "pending": ("#f3f4f6", "#9ca3af"),
    }
    for edge in graph["edges"]:
        src, dst = by_id.get(edge["from"]), by_id.get(edge["to"])
        if not src or not dst:
            continue
        x1 = src["position"]["x"] + _NODE_W
        y1 = src["position"]["y"] + _NODE_H // 2
        x2 = dst["position"]["x"]
        y2 = dst["position"]["y"] + _NODE_H // 2
        draw.line((x1, y1, x2, y2), fill="#94a3b8", width=2)
        draw.polygon([(x2, y2), (x2 - 10, y2 - 5), (x2 - 10, y2 + 5)], fill="#94a3b8")

    for node in nodes:
        fill, outline = colors.get(node["status"], colors["pending"])
        x, y = node["position"]["x"], node["position"]["y"]
        draw.rounded_rectangle(
            (x, y, x + _NODE_W, y + _NODE_H), radius=8, fill=fill, outline=outline, width=2
        )
        label = str(node["name"])[:16]
        draw.text((x + 8, y + 8), label, fill="#111827")
        draw.text((x + 8, y + 30), str(node["status"]), fill=outline)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@router.get("", summary="列出可可视化的工作流")
async def list_visualizations(request: Request) -> list[dict[str, Any]]:
    """Return a renderable graph for every workflow definition."""
    db = SessionLocal()
    try:
        workflows = db.query(Workflow).order_by(Workflow.created_at.asc()).all()
        result = []
        for workflow in workflows:
            latest = (
                db.query(WorkflowExecution)
                .filter(WorkflowExecution.workflow_id == workflow.id)
                .order_by(WorkflowExecution.started_at.desc())
                .first()
            )
            result.append(_build_graph(workflow, _layout_for(request, workflow.id), latest))
        return result
    except SQLAlchemyError as exc:
        logger.error("加载可视化数据失败: %s", exc)
        raise HTTPException(status_code=500, detail="加载可视化数据失败") from exc
    finally:
        db.close()


@router.patch("/{workflow_id}/layout", summary="更新可视化布局")
async def update_layout(workflow_id: str, payload: LayoutUpdate, request: Request) -> dict[str, Any]:
    """Persist the chosen layout for a workflow."""
    if payload.layout not in _VALID_LAYOUTS:
        raise HTTPException(status_code=400, detail="布局只能是 horizontal/vertical/circular")
    db = SessionLocal()
    try:
        if db.query(Workflow).filter(Workflow.id == workflow_id).first() is None:
            raise HTTPException(status_code=404, detail="工作流不存在")
    finally:
        db.close()
    store = get_store(request, "workflow_visualization_layout")
    store[workflow_id] = {"layout": payload.layout}
    return {"status": "success", "layout": payload.layout}


@router.get("/{workflow_id}/export", summary="导出可视化图片")
async def export_visualization(workflow_id: str, request: Request) -> Response:
    """Render and download the workflow graph as a PNG image."""
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow is None:
            raise HTTPException(status_code=404, detail="工作流不存在")
        latest = (
            db.query(WorkflowExecution)
            .filter(WorkflowExecution.workflow_id == workflow_id)
            .order_by(WorkflowExecution.started_at.desc())
            .first()
        )
        graph = _build_graph(workflow, _layout_for(request, workflow_id), latest)
        png = _render_png(graph)
        return Response(
            content=png,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{workflow.id}-workflow.png"'},
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("导出可视化失败: %s", exc)
        raise HTTPException(status_code=500, detail="导出可视化失败") from exc
    finally:
        db.close()
