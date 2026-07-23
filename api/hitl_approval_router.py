# -*- coding: utf-8 -*-
"""
HITL (Human‑In‑The‑Loop) 审批中心页面路由

提供一个静态 HTML 页面，用于展示待审批的修复请求列表，
页面会自行调用后端 `/api/mcp/approve_repair`、`/api/mcp/get_host_health` 等接口获取数据。

访问方式:
    GET /hitl/   -> 返回 static/hitl_approval.html（HTML）

如果页面文件不存在，返回 404 并记录错误日志。
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import BASE_DIR

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hitl", tags=["HITL Approval Center"])


@router.get(
    "/",
    response_class=FileResponse,
    summary="返回 HITL 审批中心页面",
    description="返回存放于 static 目录下的 HITL 审批中心 HTML 页面（hitl_approval.html）",
    responses={
        200: {"description": "HTML页面"},
        404: {"description": "页面未部署"},
    },
)
def hitl_approval_page() -> FileResponse:
    """读取并返回 static/hitl_approval.bak 文件。

    若文件缺失则记录错误日志并抛出 404。
    """
    page_path: Path = BASE_DIR / "static" / "hitl_approval.html"
    if not page_path.is_file():
        _logger.error("HITL 审批中心页面文件未找到: %s", page_path)
        raise HTTPException(status_code=404, detail="HITL Approval page not found")
    return FileResponse(page_path, media_type="text/html")
