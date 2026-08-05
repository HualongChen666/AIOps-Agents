# -*- coding: utf-8 -*-
"""
工作流可视化页面路由

提供一个简易的 HTML 页面，用于展示工作流（LangGraph）
的可视化图谱。页面通过 JavaScript 调用后端 `/api/workflow/visualization`
接口获取工作流结构的 JSON 数据并进行渲染（此处仅返回 JSON，
前端自行渲染），便于用户在浏览器中直观看到工作流节点与流向。
"""

# from pathlib import Path  # not needed
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import BASE_DIR
from core.workflow_engine import get_workflow_definitions

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["工作流可视化"])


# ----------------------------------------------------------------------
# 页面路由 – 返回本地静态 HTML（位于 static/workflow_visualization.bak）
# ----------------------------------------------------------------------
@router.get(
    "/visualization",
    response_class=FileResponse,
    summary="工作流可视化页面",
    description="返回工作流可视化的 HTML 页面，页面内部通过 fetch 调用后端接口获取工作流结构 JSON。",
    responses={
        200: {"description": "HTML页面"},
        404: {"description": "页面未找到"},
    },
)
async def workflow_visualization_page() -> FileResponse:
    """返回工作流可视化 HTML 页面。

    若页面文件不存在则记录错误日志并抛出 404。
    """
    html_path = BASE_DIR / "static" / "workflow_visualization.html"
    if not html_path.is_file():
        _logger.error("Workflow visualization page not found: %s", html_path)
        raise HTTPException(status_code=404, detail="Workflow visualization page not found")
    return FileResponse(str(html_path), media_type="text/html")


# ----------------------------------------------------------------------
# API 路由 – 返回工作流结构的 JSON（示例实现）
# ----------------------------------------------------------------------
@router.get(
    "/structure",
    summary="获取工作流结构 JSON",
    description="返回当前工作流的节点、边、元数据等结构化信息，供前端可视化使用。",
    responses={
        200: {"description": "工作流结构JSON"},
        500: {"description": "获取失败"},
    },
)
async def get_workflow_structure(key: str | None = None):
    """从 core.workflow_engine 的真实工作流定义生成可视化结构。

    未指定 key 时返回第一个工作流，支持通过 query 参数切换工作流。
    """
    try:
        definitions = get_workflow_definitions()
    except Exception as exc:
        _logger.error("Failed to load workflow definitions: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="工作流定义加载失败") from exc

    if not definitions:
        raise HTTPException(status_code=404, detail="未找到工作流定义")

    if key is None:
        key = next(iter(definitions))
    elif key not in definitions:
        raise HTTPException(status_code=404, detail=f"未找到工作流: {key}")

    wf = definitions[key]
    steps = wf.get("steps", [])
    if not isinstance(steps, list) or not steps:
        _logger.error("Workflow '%s' has invalid steps: %s", key, steps)
        raise HTTPException(status_code=500, detail=f"工作流 {key} 缺少 steps 定义")

    nodes = []
    for idx, step in enumerate(steps):
        if isinstance(step, dict):
            node_id = step.get("key") or f"step-{idx}"
            label = step.get("title") or node_id
            description = step.get("desc", "")
        else:
            node_id = str(step)
            label = node_id
            description = ""

        if idx == 0:
            node_type = "start"
        elif idx == len(steps) - 1:
            node_type = "end"
        else:
            node_type = "process"

        nodes.append(
            {
                "id": node_id,
                "label": label,
                "description": description,
                "type": node_type,
            }
        )

    edges = []
    for idx in range(len(nodes) - 1):
        edges.append({"source": nodes[idx]["id"], "target": nodes[idx + 1]["id"]})

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "workflow_key": key,
            "workflow_name": wf.get("name", key),
            "description": wf.get("description") or wf.get("name", key),
        },
    }
