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
    html_path = BASE_DIR / "static" / "workflow_visualization.bak"
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
async def get_workflow_structure():
    """返回工作流结构的示例 JSON。

    实际项目请调用 LangGraph 实例的 `graph.get_state()` 或类似方法获取真实数据。
    """
    example_structure = {
        "nodes": [
            {"id": "start", "label": "Start", "type": "start"},
            {"id": "fetch_alert", "label": "Fetch Alert", "type": "process"},
            {"id": "check_sla", "label": "Check SLA", "type": "decision"},
            {"id": "invoke_agent", "label": "Invoke Agent", "type": "process"},
            {"id": "generate_runbook", "label": "Generate Runbook", "type": "process"},
            {"id": "apply_fix", "label": "Apply Fix", "type": "process"},
            {"id": "evaluate", "label": "Evaluate", "type": "decision"},
            {"id": "complete", "label": "Complete", "type": "end"},
        ],
        "edges": [
            {"source": "start", "target": "fetch_alert"},
            {"source": "fetch_alert", "target": "check_sla"},
            {"source": "check_sla", "target": "invoke_agent"},
            {"source": "invoke_agent", "target": "generate_runbook"},
            {"source": "generate_runbook", "target": "apply_fix"},
            {"source": "apply_fix", "target": "evaluate"},
            {"source": "evaluate", "target": "complete"},
        ],
        "metadata": {"description": "LangGraph 业务闭环工作流示例"},
    }
    return example_structure
